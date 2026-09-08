"""Timeline JSON generator.

At end of build, write `site/assets/timeline.json` containing:
    meta   : {generated_by, entity_count, earliest, latest}
    groups : [{id, content, order}, ...]
    items  : [{id, group, start, end, type, content, title, url, label, raw}, ...]

Hook event: on_post_build

Sources for each entity type:
    philosopher : birth_death  (fallback: period)
    period      : year_range   (fallback: period)
    school      : period

Date parsing: tolerates 7 shape variants (see _PATTERNS below) after stripping
parenthetical notes, the 约 prefix, and the 年 suffix. All years are emitted as
ISO-8601 zero-padded 4-digit strings with `-` for BC, e.g. `-0470-01-01`. vis-
timeline's internal moment.js handles the format directly.
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


# ---------------------------------------------------------------------------
# Date parsing
# ---------------------------------------------------------------------------

# Strip Chinese / English parenthetical notes and surrounding noise.
_NOISE_PAREN = re.compile(r"[（(].*?[)）]")
_BRACKET_LINK = re.compile(r"\[\s*[^\[\]]*?\s*\]")
_APPROX = re.compile(r"^约\s*")
_HAL = re.compile(r"[\s　]+")
_TRAILING_LOC = re.compile(
    r"[\s　]*(雅典|罗马|巴黎|日内瓦|伦敦|爱丁堡|科隆|斯德哥尔摩|波士顿|阿姆斯特丹|海牙)[\s　]*$"
)
_LATE_EARLY = re.compile(r"(早期|晚期|上半叶|下半叶|中叶)")


def _clean(raw: str) -> str:
    """Strip noise before regex matching."""
    s = _NOISE_PAREN.sub("", raw)
    s = _BRACKET_LINK.sub("", s)
    s = _APPROX.sub("", s)
    s = _HAL.sub(" ", s).strip()
    s = _LATE_EARLY.sub("", s)
    # Drop ALL 年 (mid-string "1453 年 CE" as well as trailing 年).
    s = s.replace("年", "")
    s = _HAL.sub(" ", s).strip()
    s = _TRAILING_LOC.sub("", s).strip()
    return s


# Regex patterns ordered from most specific to most general. First match wins.
# `公元` is allowed everywhere `前`/`公元前` is, as the AD prefix.
_PATTERNS = [
    # 1. Single century:  前 5 世纪  /  公元前 5 世纪  /  17 世纪  /  公元 4 世纪
    re.compile(r"^(前|公元前|公元)?\s*(\d+)\s*世纪\s*$"),
    # 2. 5C shorthand:  前 5C
    re.compile(r"^(前|公元前|公元)?\s*(\d+)\s*C\s*$"),
    # 3. Two centuries:  前 6 世纪 – 前 5 世纪  /  公元 3 – 6 世纪  /  前 4 世纪 – 公元 4 世纪
    re.compile(
        r"^(前|公元前|公元)?\s*(\d+)\s*世纪\s*[-–—]\s*"
        r"(前|公元前|公元)?\s*(\d+)\s*世纪\s*$"
    ),
    # 4. Explicit years with CE suffix:  354 – 430 CE  /  约 800 – 1500 CE  /  476 – 1453 CE
    re.compile(
        r"^(前|公元前|公元)?\s*(\d+)\s*[-–—]\s*(\d+)\s*CE\s*$"
    ),
    # 5. Explicit years without CE:  前 470 – 前 399  /  1596 – 1650  /  前 323 – 31
    re.compile(
        r"^(前|公元前|公元)?\s*(\d+)\s*[-–—]\s*"
        r"(前|公元前|公元)?\s*(\d+)\s*$"
    ),
]


def _is_bc(prefix: str | None) -> bool:
    return prefix in ("前", "公元前")


def _compute_century(n: int, prefix: str | None, *, is_end: bool) -> int:
    """Convert a century number + (前|公元前|公元|None) to an actual year.

    Convention:
        nth century BC = -(n*100) ... -(n*100 - 99)    → "前 5 世纪" = -500..-401
        nth century AD = (n-1)*100 + 1 ... n*100        → "17 世纪"  = 1601..1700
    """
    if _is_bc(prefix):
        # BC: start of n-th = -(n*100); end of n-th = -(n*100 - 99)
        # e.g. n=5: start=-500, end=-401
        if is_end:
            return -(n * 100 - 99)
        return -(n * 100)
    # AD: start of n-th = (n-1)*100 + 1; end of n-th = n*100
    # e.g. n=17: start=1601, end=1700
    if is_end:
        return n * 100
    return (n - 1) * 100 + 1


def _to_iso(year: int, *, is_end: bool) -> str:
    """ISO 8601 extended format with sign for BC years.

    Returns e.g. '-000470-01-01' or '1712-12-31'. BC years always carry the
    `-` sign followed by **6** zero-padded digits (the ISO 8601 extended
    form for signed years) — moment.js and vis-graph2d only accept this
    shape. The previous 4-digit BC form (e.g. `-0470-01-01`) silently
    fell back to `new Date()` and produced invalid ranges.
    """
    md = "-12-31" if is_end else "-01-01"
    if year < 0:
        # Sign + 6 digits: ISO 8601 extended format (mandatory for BC).
        return f"-{abs(year):06d}{md}"
    return f"{year:04d}{md}"


def parse_range(raw: str) -> tuple[str | None, str | None]:
    """Parse a Chinese-ish date range string into (start_iso, end_iso).

    Returns (None, None) when parsing fails. Never raises.
    """
    if not raw or not raw.strip():
        return (None, None)

    cleaned = _clean(raw)

    # --- Pattern 3: two centuries (must come before pattern 1 + 5 chained) ---
    m = _PATTERNS[2].match(cleaned)
    if m:
        pre1, n1, pre2, n2 = m.groups()
        start = _compute_century(int(n1), pre1, is_end=False)
        end = _compute_century(int(n2), pre2, is_end=True)
        return (_to_iso(start, is_end=False), _to_iso(end, is_end=True))

    # --- Pattern 3b: leading number range + single "世纪"  (e.g. 公元 3 – 6 世纪) ---
    # The reverse of pattern 3. The `世纪` suffix applies to both numbers.
    m = re.compile(
        r"^(前|公元前|公元)?\s*(\d+)\s*[-–—]\s*(\d+)\s*世纪\s*$"
    ).match(cleaned)
    if m:
        prefix, n1, n2 = m.groups()
        start = _compute_century(int(n1), prefix, is_end=False)
        end = _compute_century(int(n2), prefix, is_end=True)
        return (_to_iso(start, is_end=False), _to_iso(end, is_end=True))

    # --- Pattern 1: single century ---
    m = _PATTERNS[0].match(cleaned)
    if m:
        prefix, n = m.groups()
        return (
            _to_iso(_compute_century(int(n), prefix, is_end=False), is_end=False),
            _to_iso(_compute_century(int(n), prefix, is_end=True), is_end=True),
        )

    # --- Pattern 2: 5C shorthand ---
    m = _PATTERNS[1].match(cleaned)
    if m:
        prefix, n = m.groups()
        return (
            _to_iso(_compute_century(int(n), prefix, is_end=False), is_end=False),
            _to_iso(_compute_century(int(n), prefix, is_end=True), is_end=True),
        )

    # --- Pattern 4: explicit years + CE ---
    m = _PATTERNS[3].match(cleaned)
    if m:
        pre1, n1, n2 = m.groups()
        start = -int(n1) if _is_bc(pre1) else int(n1)
        end = -int(n2) if _is_bc(pre1) else int(n2)
        return (_to_iso(start, is_end=False), _to_iso(end, is_end=True))

    # --- Pattern 5: explicit years no CE ---
    m = _PATTERNS[4].match(cleaned)
    if m:
        pre1, n1, pre2, n2 = m.groups()
        # Mixed BC/AD handling: if only one prefix, it applies to both halves.
        # If both prefixes given, each half keeps its own.
        if pre1 and pre2:
            start = -int(n1)
            end = -int(n2) if _is_bc(pre2) else int(n2)
        elif pre1:
            start = -int(n1)
            end = -int(n2)
        elif pre2:
            start = int(n1)
            end = -int(n2) if _is_bc(pre2) else int(n2)
        else:
            start = int(n1)
            end = int(n2)
        return (_to_iso(start, is_end=False), _to_iso(end, is_end=True))

    return (None, None)


# ---------------------------------------------------------------------------
# JSON assembly
# ---------------------------------------------------------------------------

# Map entity type → (item group id, item type for vis-timeline)
_TYPE_MAP = {
    "period":      ("period",      "background"),
    "school":      ("school",      "range"),
    "philosopher": ("philosopher", "range"),
}

# Field fallback order per entity type.
_FIELD_ORDER = {
    "philosopher": ("birth_death", "period"),
    "period":      ("year_range",  "period"),
    "school":      ("period",),
}


def _label_for(name: str) -> str:
    fm = STATE["frontmatter"].get(name, {})
    return fm.get("name", name)


def _gather() -> list[dict]:
    """Walk STATE and produce timeline item dicts (one per entity)."""
    items: list[dict] = []
    for (name, url, type_, _src_path) in STATE["all_pages"]:
        if type_ not in _TYPE_MAP:
            continue

        group, vis_type = _TYPE_MAP[type_]
        fm = STATE["frontmatter"].get(name, {})

        raw = None
        for field in _FIELD_ORDER[type_]:
            val = fm.get(field)
            if val:
                raw = val
                break
        if raw is None:
            continue

        start_iso, end_iso = parse_range(raw)
        if start_iso is None or end_iso is None:
            print(f"[timeline.py] skipping {name}: cannot parse {raw!r}")
            continue

        label = _label_for(name)
        items.append({
            "id":      f"{type_}/{name}",
            "group":   group,
            "start":   start_iso,
            "end":     end_iso,
            "type":    vis_type,
            "content": label,
            "title":   f"{label}（{raw}）",
            "url":     url,
            "label":   label,
            "raw":     raw,
        })
    return items


def on_post_build(config):
    site_dir = config["site_dir"]

    items = _gather()
    items.sort(key=lambda x: x["start"])

    earliest = items[0]["start"] if items else None
    latest = items[-1]["end"] if items else None

    payload = {
        "meta": {
            "generated_by": "hooks/timeline.py",
            "entity_count": len(items),
            "earliest":     earliest,
            "latest":       latest,
        },
        "groups": [
            {"id": "period",      "content": "时期（背景色带）", "order": 1},
            {"id": "school",      "content": "学派（条带）",     "order": 2},
            {"id": "philosopher", "content": "哲学家（寿命）",   "order": 3},
        ],
        "items": items,
    }

    out_dir = os.path.join(site_dir, "assets")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "timeline.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(
        f"[timeline.py] wrote {len(items)} items "
        f"({earliest} → {latest}) → {out_path}"
    )