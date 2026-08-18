"""Backlink panel injector.

After each page is rendered to HTML, append a "被引用于" block listing
all pages that link TO the current page.

Hook event: on_page_content
"""

from __future__ import annotations

import sys
from html import escape
from pathlib import Path

# Make `hooks` importable when this file is loaded as a standalone module.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from hooks import STATE  # noqa: E402


TEMPLATE = """
<aside class="backlinks">
  <h2>被引用于</h2>
  {rows}
</aside>
"""


def on_page_content(html, page, config, files):
    name = page.meta.get("name") or page.title or ""

    sources = STATE["backlinks"].get(name, [])
    if not sources:
        rows = '<p class="backlinks-empty">暂无其他页面引用</p>'
    else:
        # de-dup by (source_name, source_url); keep anchors
        seen: dict[tuple[str, str], list[str]] = {}
        for src_name, src_url, anchor in sources:
            seen.setdefault((src_name, src_url), []).append(anchor)

        items: list[str] = []
        for (src_name, src_url), anchors in sorted(seen.items()):
            anchor_tags = "".join(
                f' <sup>[{escape(a)}]</sup>' for a in anchors if a
            )
            abs_href = "/" + src_url.lstrip("/") if src_url else "/"
            items.append(
                f'<li><a href="{escape(abs_href)}">{escape(src_name)}</a>'
                f'{anchor_tags}</li>'
            )
        rows = "<ul>" + "".join(items) + "</ul>"

    return html + TEMPLATE.format(rows=rows)