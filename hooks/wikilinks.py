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

from hooks import STATE  # noqa: E402


WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#([^\]|]+))?(?:\|([^\]]+))?\]\]")

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def _split_frontmatter(text: str) -> tuple[dict, str]:
    """Pull YAML frontmatter out of a Markdown source string."""
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    try:
        data = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        data = {}
    return data, text[m.end():]


def on_files(files, config):
    """Walk every .md, parse frontmatter, build target_map + supporting state."""
    name_to_url: dict[str, str] = {}
    name_to_fm: dict[str, dict] = {}
    all_pages: list[tuple[str, str, str, str]] = []

    for f in files:
        if not f.src_path.endswith(".md"):
            continue
        try:
            text = Path(f.abs_src_path).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        fm, _ = _split_frontmatter(text)
        name = fm.get("name") or Path(f.src_path).stem
        # Normalize url: index.md's url is './'; canonical form is empty string.
        url = "" if f.url in ("./", ".") else f.url
        name_to_url[name] = url
        name_to_fm[name] = fm
        all_pages.append((name, url, fm.get("type", "page"), f.src_path))

    STATE["target_map"] = name_to_url
    STATE["frontmatter"] = name_to_fm
    STATE["all_pages"] = all_pages
    STATE["backlinks"] = {n: [] for (n, _, _, _) in all_pages}
    STATE["all_edges"] = set()
    return files


def on_page_markdown(markdown, page, config, files):
    """Rewrite [[X]] / [[X|Y]] / [[X#anchor]] in the body (skip frontmatter)."""
    src_name = page.meta.get("name") or page.title or ""

    # Skip frontmatter block (first ---...---) so we don't touch raw YAML.
    parts = markdown.split("---", 2)
    if len(parts) >= 3 and parts[0].strip() == "":
        fm_text = parts[1]
        body = parts[2]
        rewritten = WIKILINK_RE.sub(_repl_factory(src_name, page.url), body)
        return f"---\n{fm_text}\n---\n{rewritten}"

    return WIKILINK_RE.sub(_repl_factory(src_name, page.url), markdown)


def _repl_factory(src_name: str, src_url: str):
    """Build a re.sub callback bound to (src_name, src_url)."""
    def repl(m: re.Match) -> str:
        target = m.group(1).strip()
        anchor = (m.group(2) or "").strip()
        alias = (m.group(3) or target).strip()

        STATE["all_edges"].add((src_name, target))

        url = STATE["target_map"].get(target)
        if url is None:
            # forward link → styled stub
            return (
                f'<span class="wikilink-stub" title="待创建页面: {target}">'
                f'{alias}<sup class="wikilink-stub-marker">待创建</sup></span>'
            )

        STATE["backlinks"].setdefault(target, []).append(
            (src_name, src_url, anchor or None)
        )
        # Make the URL absolute (site-root-relative) so MkDocs doesn't
        # try to interpret it as a relative path from the source page.
        abs_url = "/" + url.lstrip("/") if url else "/"
        href = abs_url + (f"#{anchor}" if anchor else "")
        return f"[{alias}]({href})"

    return repl