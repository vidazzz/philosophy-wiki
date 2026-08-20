"""Wikilink preprocessor.

Resolves `[[X]]` and `[[X|Y]]` syntax to either real links (when the
target page exists) or styled "stub" spans (for forward links).

Hook events:
    on_files          — build target_map, all_pages, frontmatter
    on_page_markdown  — rewrite `[[...]]` occurrences in body
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

# Make `hooks` importable when this file is loaded as a standalone module.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from hooks import STATE, rel_url  # noqa: E402


WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#([^\]|]+))?(?:\|([^\]]+))?\]\]")

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def _split_frontmatter(text: str) -> tuple[dict, str]:
    """Pull YAML frontmatter out of a Markdown source string.

    Tries YAML first. If it fails — usually because a value contains
    CJK brackets / unescaped quotes that confuse PyYAML — falls back to
    a line-by-line scan that extracts the keys we actually need
    (``name``, ``type``, ``status``).
    """
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    inner = m.group(1)
    try:
        data = yaml.safe_load(inner) or {}
    except yaml.YAMLError:
        data = _fallback_frontmatter(inner)
    return data, text[m.end():]


def _fallback_frontmatter(inner: str) -> dict:
    """Line-by-line scan when YAML parsing fails.

    Captures only simple ``key: value`` pairs at column 0; nested YAML
    structures (``sources:`` lists, etc.) are ignored. This is good
    enough for the fields the graph and wikilink hooks need.
    """
    data: dict[str, str] = {}
    for line in inner.splitlines():
        line = line.rstrip()
        if not line or line[0] in (" ", "\t", "-"):
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key in ("name", "type", "status"):
            data[key] = value
    return data


def on_files(files, config):
    """Walk every .md, parse frontmatter, build target_map + supporting state."""
    name_to_url: dict[str, str] = {}
    name_to_fm: dict[str, dict] = {}
    all_pages: list[tuple[str, str, str, str]] = []

    # MkDocs's File.url is actually an absolute filesystem path (e.g.
    # "/Users/.../wiki/works/论法律/"), NOT a web URL. We need to derive
    # the proper web URL ourselves from abs_src_path minus docs_dir.
    docs_dir = Path(config["docs_dir"]).resolve()

    for f in files:
        if not f.src_path.endswith(".md"):
            continue
        # Skip subdirectory index.md placeholders — they're just nav stubs,
        # not content nodes. Keep wiki/index.md (the site root index).
        try:
            rel = Path(f.abs_src_path).resolve().relative_to(docs_dir)
        except ValueError:
            continue
        if rel.name == "index.md" and len(rel.parts) > 1:
            continue
        try:
            text = Path(f.abs_src_path).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        fm, _ = _split_frontmatter(text)
        name = fm.get("name") or Path(f.src_path).stem
        # Web URL: relative path from docs_dir, with .md dropped and
        # directory URLs (trailing /) for nested files. The site root
        # (wiki/index.md) maps to empty string.
        if rel.name == "index.md":
            url = ""  # site root (empty string, not "/")
        else:
            url = str(rel.with_suffix("")).replace("\\", "/") + "/"
        name_to_url[name] = url
        name_to_fm[name] = fm
        all_pages.append((name, url, fm.get("type", "page"), f.src_path))

    STATE["target_map"] = name_to_url
    STATE["frontmatter"] = name_to_fm
    STATE["all_pages"] = all_pages
    STATE["backlinks"] = {n: [] for (n, _, _, _) in all_pages}
    STATE["all_edges"] = set()
    # Per-page occurrence tracking: src_name -> {target_name -> [{line, anchor}, ...]}
    # Populated by on_page_markdown; consumed by graph.py to build the edge popup.
    STATE["edge_occurrences"] = {}
    return files


def on_page_markdown(markdown, page, config, files):
    """Rewrite [[X]] / [[X|Y]] / [[X#anchor]] in the body (skip frontmatter).

    While rewriting, record every [[X]] occurrence with its line number so
    the graph can build a per-edge occurrence list. Each occurrence also
    gets an HTML anchor (``cite-{line}-{idx}``) injected onto the link so
    the browser can scroll there on demand.
    """
    src_name = page.meta.get("name") or page.title or ""

    # Skip frontmatter block (first ---...---) so we don't touch raw YAML.
    parts = markdown.split("---", 2)
    if len(parts) >= 3 and parts[0].strip() == "":
        fm_text = parts[1]
        body = parts[2]
        rewritten = WIKILINK_RE.sub(_repl_factory(src_name, page.url, body), body)
        return f"---\n{fm_text}\n---\n{rewritten}"

    return WIKILINK_RE.sub(_repl_factory(src_name, page.url, markdown), markdown)


def _repl_factory(src_name: str, src_url: str, body: str):
    """Build a re.sub callback bound to (src_name, src_url, body).

    ``body`` is the substring we're running the regex against — either
    the page text after frontmatter was peeled off, or the full markdown
    if no frontmatter was present. Counting newlines in
    ``body[:m.start()]`` gives the 1-indexed line of the match.

    Each match produces an anchor of the form ``cite-{line}-{idx}``
    where ``idx`` disambiguates multiple matches on the same line.
    """
    src_occurrences = STATE["edge_occurrences"].setdefault(src_name, {})
    counter = [0]

    def repl(m: re.Match) -> str:
        counter[0] += 1
        idx = counter[0]
        target = m.group(1).strip()
        anchor = (m.group(2) or "").strip()
        alias = (m.group(3) or target).strip()
        line = body[: m.start()].count("\n") + 1
        anchor_id = f"cite-{line}-{idx}"

        # Per-target occurrence list for graph.py (line + scroll anchor).
        src_occurrences.setdefault(target, []).append({
            "line": line,
            "anchor": anchor_id,
        })

        STATE["all_edges"].add((src_name, target))

        url = STATE["target_map"].get(target)
        if url is None:
            # forward link → styled stub (no anchor; nothing to scroll to)
            return (
                f'<span class="wikilink-stub" title="待创建页面: {target}">'
                f'{alias}<sup class="wikilink-stub-marker">待创建</sup></span>'
            )

        STATE["backlinks"].setdefault(target, []).append(
            (src_name, src_url, anchor or None)
        )
        # Compute a relative URL from the current page to the target so the
        # link works no matter where the site is mounted (e.g. when GitHub
        # Pages hosts it under /philosophy-wiki/).
        href = rel_url(src_url, url) + (f"#{anchor}" if anchor else "")
        # attr_list puts {:id=...} on the parent <a>, so the link itself
        # becomes the scroll target for click-from-graph navigation.
        return f"[{alias}]({href}){{:id={anchor_id}}}"

    return repl