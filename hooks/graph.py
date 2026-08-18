"""Knowledge-graph JSON generator.

At end of build, write `site/assets/graph.json` containing:
    nodes : [{id, label, url, type, status}, ...]
    edges : [{from, to}, ...]

Hook event: on_post_build
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Make `hooks` importable when this file is loaded as a standalone module.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from hooks import STATE  # noqa: E402


def on_post_build(config):
    site_dir = config["site_dir"]

    nodes = []
    for (name, url, type_, _src) in STATE["all_pages"]:
        fm = STATE["frontmatter"].get(name, {})
        nodes.append({
            "id": name,
            "label": name,
            "url": url,
            "type": type_,
            "group": type_,
            "status": fm.get("status", "stub"),
        })

    edges = [
        {"from": src, "to": tgt}
        for (src, tgt) in sorted(STATE["all_edges"])
        if src != tgt  # ignore self-links
    ]

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