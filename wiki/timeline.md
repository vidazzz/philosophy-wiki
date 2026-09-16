---
title: 时间轴
---

# 时间轴

本页用 CSS + JS 自渲染 Wiki 中所有**有时间标记**的页面 — 哲学家（寿命）、学派（活动期）、时期（背景色带）。从上往下俯瞰整个哲学史的时间结构。

> **为什么不用 vis-timeline / vis-graph2d？** 两个库都不支持真正的纵向时间轴 —— Timeline 的 `orientation: 'vertical'` 被静默忽略；Graph2d 的 `orientation` 只接受 `bottom/top`，时间轴始终在 X 方向。所以这里用纯 CSS 渲染三列纵向时间轴，简单可控。

- **三层并列**（自左向右）：时期 → 学派 → 哲学家
- **每列内**按起点年份从上到下排列（越早越靠上）
- **悬停** → 卡片高亮 + tooltip 显示完整寿命
- **点击** → 跳转到对应词条
- **BC / AD** 标记自动区分

> 数据来源：每页 Markdown 的 frontmatter `birth_death` / `year_range` / `period` 字段；构建时由 `hooks/timeline.py` 解析为统一 ISO 格式并写入 `site/assets/timeline.json`。

<div class="timeline-legend">
  <span><span class="legend-dot" style="background:#26c6da"></span>时期（背景色带）</span> &nbsp;
  <span><span class="legend-dot" style="background:#ab47bc"></span>学派（条带）</span> &nbsp;
  <span><span class="legend-dot" style="background:#5c6bc0"></span>哲学家（寿命）</span> &nbsp;
  <span style="margin-left:1em; font-size:0.85em; opacity:0.7">悬停查看 · 点击跳转</span>
</div>

<div id="timeline-container" aria-busy="true">
  <div class="timeline-loading">加载中…</div>
</div>

<script>
(async function() {
  // ---- Load timeline.json ----
  const res = await fetch('../assets/timeline.json');
  if (!res.ok) {
    document.getElementById('timeline-container').innerText = 'timeline.json 未找到';
    return;
  }
  const payload = await res.json();

  const COLOR = {
    philosopher: { fg: '#5c6bc0', bg: '#5c6bc022', border: '#3f51b5' },
    school:      { fg: '#ab47bc', bg: '#ab47bc22', border: '#ab47bc' },
    period:      { fg: '#26c6da', bg: '#26c6da33', border: '#26c6da' },
  };

  // ---- Group items by category ----
  // payload.items[] contains {id, group, content, start, end, title, url, type}
  const groups = { period: [], school: [], philosopher: [] };
  const itemById = {};
  for (const it of payload.items) {
    if (!groups[it.group]) continue;        // skip unknown groups
    itemById[it.id] = it;
    groups[it.group].push(it);
  }
  // Sort each group by start date (chronological top→bottom).
  // `start` is an ISO string like "-000323-01-01" or "1712-01-01".
  // String comparison on ISO 8601 dates is lexicographic and correct
  // because the format is fixed-width with explicit BC sign.
  for (const g of Object.keys(groups)) {
    groups[g].sort((a, b) => a.start.localeCompare(b.start));
  }

  // ---- Render three vertical columns ----
  const container = document.getElementById('timeline-container');
  container.removeAttribute('aria-busy');
  container.innerHTML = '';

  const COL_TITLES = {
    period:      '时期（背景色带）',
    school:      '学派（条带）',
    philosopher: '哲学家（寿命）',
  };

  for (const groupKey of ['period', 'school', 'philosopher']) {
    const col = document.createElement('div');
    col.className = 'vt-column vt-column-' + groupKey;

    const header = document.createElement('div');
    header.className = 'vt-column-header';
    header.textContent = COL_TITLES[groupKey];
    col.appendChild(header);

    const list = document.createElement('div');
    list.className = 'vt-list';
    for (const it of groups[groupKey]) {
      const card = document.createElement(it.url ? 'a' : 'div');
      card.className = 'vt-card vt-card-' + groupKey;
      card.href = it.url ? '../' + it.url : '';
      card.title = it.title || it.content;
      card.setAttribute('data-id', it.id);

      const titleEl = document.createElement('div');
      titleEl.className = 'vt-card-title';
      titleEl.textContent = it.content;
      card.appendChild(titleEl);

      const dateEl = document.createElement('div');
      dateEl.className = 'vt-card-date';
      dateEl.textContent = formatYears(it.start, it.end);
      card.appendChild(dateEl);

      list.appendChild(card);
    }
    col.appendChild(list);
    container.appendChild(col);
  }

  // ---- Format ISO year string to "前 427" / "1650" ----
  // Accepts "-000427-01-01" → "前 427", "1650-01-01" → "1650", etc.
  // When start == end, just returns one year.
  function formatYears(startIso, endIso) {
    const sy = isoYear(startIso);
    const ey = isoYear(endIso);
    if (sy === ey) return sy;
    return sy + ' – ' + ey;
  }
  function isoYear(iso) {
    if (!iso) return '?';
    if (iso.startsWith('-')) {
      // ISO 8601 extended BC: "-000106" → year 106 BC
      return '前 ' + String(Math.abs(parseInt(iso.slice(1, 5), 10)));
    }
    return String(parseInt(iso.slice(0, 4), 10));
  }

  // ---- Expose for debugging ----
  window.__timeline = { groups, itemById };
})();
</script>

## 数据说明

时间范围从 **公元前 6 世纪**（前苏格拉底时期）到 **公元 19 世纪**（拉普拉斯，1827 年逝世）。

| 类型 | 数量 | 字段来源 |
|------|------|----------|
| 哲学家 | 20 | `birth_death`（生卒年） |
| 学派 | 9 | `period`（活跃期） |
| 时期 | 6 | `year_range` 或 `period` |

⚠️ **精度提示**：某些时段以"世纪"为单位（如"前 5 世纪"），解析为 100 年窗口。"前 5 世纪" = 公元前 500 年 至 前 401 年。"约 1600 – 1750" 这类括号内精确年份若与外层" 17 世纪"冲突，外层优先。

### 解析器规则（参考 `hooks/timeline.py`，仓库根目录）

支持的 6 类日期格式：

1. 单世纪：`前 5 世纪` / `17 世纪` / `公元 4 世纪`
2. 世纪简写：`前 5C`（仅智者派使用）
3. 双世纪范围：`前 6 世纪 – 前 5 世纪` / `公元 3 – 6 世纪`
4. 显式年份 + CE 后缀：`354 – 430 CE` / `476 – 1453 CE`
5. 显式年份无 CE：`前 470 – 前 399` / `1596 – 1650` / `前 323 – 前 31`
6. 跨 BC/AD 混合：`前 4 世纪 – 公元 4 世纪`

预处理：删除圆括号注释、`约` 前缀、wikilink 残余、年份修饰词（早期/晚期）、城市名等噪声。

### 相关页面

- [知识图谱](graph.md) — Wiki 所有页面的网络视图
- [Wiki 总索引](index.md)
- [时期目录](periods/index.md)
- [学派目录](schools/index.md)
- [哲学家目录](philosophers/index.md)