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

STATE = {
    "target_map": {},
    "backlinks": {},
    "all_pages": [],
    "frontmatter": {},
    "all_edges": set(),
}