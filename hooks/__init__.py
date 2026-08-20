"""MkDocs hooks for the 西方哲学研读 Wiki.

Shared state across hooks. Populated by `wikilinks.on_files`,
consumed by `wikilinks.on_page_markdown`, `backlinks.on_page_content`,
and `graph.on_post_build`.

Keys:
    target_map   : dict[str, str]   name -> URL (e.g. "philosophers/柏拉图/")
    backlinks    : dict[str, list]  target_name -> [(src_name, src_url, anchor)]
    all_pages    : list[tuple]      ordered list of (name, url, type, src_path)
    frontmatter  : dict[str, dict]  name -> parsed YAML frontmatter
    all_edges    : set[tuple]       (src_name, tgt_name) — includes unresolved forward links
"""

from __future__ import annotations

import os


STATE = {
    "target_map": {},
    "backlinks": {},
    "all_pages": [],
    "frontmatter": {},
    "all_edges": set(),
}


def rel_url(src_url: str, target_url: str) -> str:
    """Return a relative URL from `src_url` (the page being rendered) to
    `target_url` (the link target).

    MkDocs is inconsistent about URL form:
      - ``File.url`` is a site-root-absolute URL (``/works/论法律/``)
      - ``Page.url`` is a doc-dir-relative URL (``works/论法律/``)
    This helper accepts either form and emits a path that resolves
    correctly when inserted into an ``href`` attribute. The result has no
    leading ``/`` so the link works regardless of deployment sub-path
    (e.g. ``/philosophy-wiki/``).
    """
    src = src_url.lstrip("/") if src_url else ""
    tgt = target_url.lstrip("/") if target_url else ""
    if not src:
        src_dir = "."
    else:
        src_dir = os.path.dirname(src)
        if not src_dir:
            src_dir = "."
    if not tgt:
        # Target is the site root
        return os.path.relpath(".", start=src_dir)
    return os.path.relpath(tgt, start=src_dir)