"""Knowledge-graph JSON generator.

At end of build, write `site/assets/graph.json` containing:
    nodes : [{id, label, url, type, status}, ...]
    edges : [{from, to}, ...]

Hook event: on_post_build
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

# Make `hooks` importable when this file is loaded as a standalone module.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from hooks import STATE  # noqa: E402


# Special-page label overrides: pages without frontmatter (like `index.md`
# and `graph.md`) get friendly labels so they show up correctly in the graph.
_LABEL_OVERRIDES = {
    "index": "Wiki 总索引",
    "graph": "知识图谱",
}

_H1_RE = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)


def _label_for(name: str, src_path: str) -> str:
    """Pick the best display label for a node.

    Priority: frontmatter ``name`` → override map → H1 title in source →
    filename stem.
    """
    fm = STATE["frontmatter"].get(name, {})
    if "name" in fm:
        return fm["name"]
    if name in _LABEL_OVERRIDES:
        return _LABEL_OVERRIDES[name]
    try:
        text = Path(src_path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return name
    m = _H1_RE.search(text)
    if m:
        # Strip surrounding [[ ]] / wikilink markers if present
        title = m.group(1).strip()
        title = re.sub(r"^\[\[(.+?)\]\]$", r"\1", title)
        return title
    return name


def on_post_build(config):
    site_dir = config["site_dir"]

    # Build a name → (url, src_path) lookup so we can enrich edges with the
    # source/target page URLs (the graph page needs them to navigate when
    # the user clicks an arrow).
    name_to_url = {n: u for (n, u, _, _) in STATE["all_pages"]}
    name_to_src = {n: s for (n, _, _, s) in STATE["all_pages"]}

    nodes = []
    for (name, url, type_, src_path) in STATE["all_pages"]:
        fm = STATE["frontmatter"].get(name, {})
        nodes.append({
            "id": name,
            "label": _label_for(name, src_path),
            "url": url,
            "type": type_,
            "group": type_,
            "status": fm.get("status", "stub"),
        })

    edges = []
    for i, (src, tgt) in enumerate(sorted(STATE["all_edges"])):
        if src == tgt:
            continue  # ignore self-links

        # All [[X]] occurrences of `tgt` inside `src`, with their line
        # numbers and the anchor IDs injected onto each link. The graph
        # page uses these to (a) jump directly when only one reference
        # exists, and (b) build a preview menu when several do.
        occurrences = (
            STATE.get("edge_occurrences", {}).get(src, {}).get(tgt, [])
        )

        edges.append({
            "id": f"e{i}",
            "from": src,
            "to": tgt,
            "fromUrl": name_to_url.get(src, ""),
            "toUrl": name_to_url.get(tgt, ""),
            "fromLabel": _label_for(src, name_to_src.get(src, "")),
            "toLabel": _label_for(tgt, name_to_src.get(tgt, "")),
            "firstLine": occurrences[0]["line"] if occurrences else None,
            "firstAnchor": occurrences[0]["anchor"] if occurrences else None,
            "allOccurrences": occurrences,  # [{line, anchor}, ...]
        })

    payload = {
        "nodes": nodes,
        "edges": edges,
        "meta": {
            "generated_by": "hooks/graph.py",
            "node_count": len(nodes),
            "edge_count": len(edges),
        },
    }

    out_dir = os.path.join(site_dir, "assets")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "graph.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"[graph.py] wrote {len(nodes)} nodes, {len(edges)} edges → {out_path}")