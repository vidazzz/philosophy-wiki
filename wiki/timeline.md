---
title: 时间轴
---

# 时间轴

本页用 **vis-timeline** 渲染 Wiki 中所有**有时间标记**的页面 — 哲学家（寿命）、学派（活动期）、时期（背景带）。沿垂直坐标从上往下俯瞰整个哲学史的时间结构。

- **三层并列**（自左向右）：时期（背景色带）→ 学派（条带）→ 哲学家（细条）
- **垂直滚动**沿时间线向下浏览，**滚轮**缩放
- **悬停**查看精确生卒年/活跃期（tooltip 跟随鼠标）
- **点击**跳转对应词条
- **BC / AD** 时间轴自动分开（公元前在上半段）

> 数据来源：每页 Markdown 的 frontmatter `birth_death` / `year_range` / `period` 字段；构建时由 `hooks/timeline.py` 解析为统一 ISO 格式并写入 `site/assets/timeline.json`。

<div class="timeline-legend">
  <span><span class="legend-dot" style="background:#26c6da"></span>时期（背景色带）</span> &nbsp;
  <span><span class="legend-dot" style="background:#ab47bc"></span>学派（条带）</span> &nbsp;
  <span><span class="legend-dot" style="background:#5c6bc0"></span>哲学家（寿命）</span> &nbsp;
  <span style="margin-left:1em; font-size:0.85em; opacity:0.7">拖动 · 滚轮缩放 · 悬停查看 · 点击跳转</span>
</div>

<div id="timeline-container"></div>

<script>
(async function() {
  // ---- Dynamically load vis-timeline UMD bundle ----
  // Don't use a plain <script src="..."> in the markdown: MkDocs Material's
  // `navigation.instant` feature fetches subsequent pages via XHR and injects
  // them with innerHTML — browsers do NOT execute <script src=...> tags that
  // arrive via innerHTML, so the global `vis` would never be defined and
  // `new vis.Timeline(...)` below would throw `ReferenceError: vis is not defined`.
  // Loading dynamically inside the IIFE works in both first-load and instant-nav cases.
  function loadScript(src) {
    return new Promise((resolve, reject) => {
      if (document.querySelector(`script[src="${src}"]`)) { resolve(); return; }
      const s = document.createElement('script');
      s.src = src;
      s.onload = () => resolve();
      s.onerror = () => reject(new Error('failed to load ' + src));
      document.head.appendChild(s);
    });
  }
  try {
    await loadScript('../javascripts/vendor/vis-timeline-graph2d.min.js');
  } catch (e) {
    document.getElementById('timeline-container').innerText = 'vis-timeline 加载失败：' + e.message;
    return;
  }

  // ---- Inject vis-timeline stylesheet (must come before the timeline is
  // created, so the container has correct sizing/styling on first paint). ----
  // Markdown-wrapped <link> tags are inconsistent (some renderers wrap
  // them in <p>), so we attach the stylesheet programmatically.
  if (!document.querySelector('link[data-vis-timeline]')) {
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.type = 'text/css';
    link.href = '../stylesheets/vendor/vis-timeline-graph2d.min.css';
    link.dataset.visTimeline = '1';
    document.head.appendChild(link);
  }

  // ---- Dark / light theme handling ----
  const isDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  const theme = {
    text:      isDark ? '#e0e0e0' : '#212121',
    edge:      isDark ? '#666666' : '#bdbdbd',
    background: isDark ? '#1e1e1e' : '#ffffff',
  };

  // Material toggles `data-md-color-scheme` when the user clicks the
  // palette switch — reload to pick up our updated `isDark`. Adopting the
  // first observed value as the baseline, since Material sets it on
  // bootstrap *after* this script sometimes.
  let lastKnownScheme = document.body.getAttribute('data-md-color-scheme');
  let observerReady = false;
  let reloadTimer = null;
  new MutationObserver(() => {
    const current = document.body.getAttribute('data-md-color-scheme');
    if (!observerReady) {
      observerReady = true;
      lastKnownScheme = current;
      return;
    }
    if (current === lastKnownScheme || reloadTimer) return;
    lastKnownScheme = current;
    reloadTimer = setTimeout(() => location.reload(), 250);
  }).observe(document.body, {
    attributes: true,
    attributeFilter: ['data-md-color-scheme'],
  });

  // ---- Load timeline.json ----
  const res = await fetch('../assets/timeline.json');
  if (!res.ok) {
    document.getElementById('timeline-container').innerText = 'timeline.json 未找到';
    return;
  }
  const payload = await res.json();

  const COLOR = {
    philosopher: { background: '#5c6bc0', border: '#3f51b5' },
    school:      { background: '#ab47bc88', border: '#ab47bc' },
    period:      { background: '#26c6da44', border: '#26c6da' },
  };

  // ---- Build vis-timeline items ----
  // Graph2d's vertical orientation uses the *value* axis as the
  // categorical X (where groups live) and the *time* axis as the
  // scrolling Y. So we have to assign each item a numeric `value` —
  // one per group — so periods/schools/philosophers stack into three
  // distinct vertical columns. The `group` field keeps the existing
  // grouping/styling intact.
  const VALUE = { period: 1, school: 2, philosopher: 3 };
  const itemsById = {};
  const items = payload.items.map(it => {
    itemsById[it.id] = it;
    const c = COLOR[it.group] || COLOR.philosopher;
    return {
      id:      it.id,
      group:   it.group,
      content: it.content,
      start:   it.start,
      end:     it.end,
      // 'background' renders behind everything (for period bands).
      // 'range' draws as a normal bar (school + philosopher).
      type:    it.type,
      title:   it.title,
      // Graph2d vertical: X = value, Y = time. Assign per-group values
      // so the three layers stack left→right.
      value:   VALUE[it.group] || 3,
      style:   `background-color:${c.background}; border-color:${c.border}; color:${theme.text};`,
    };
  });

  // ---- Construct Timeline (Graph2d with vertical orientation) ----
  // vis-timeline's `Timeline` class only supports horizontal orientation
  // (`top` | `bottom` | `both` | `none`). To get a vertical timeline we
  // use `vis.Graph2d` from the same bundle — it accepts `orientation:
  // 'vertical'` and renders time on the Y axis with the value axis as
  // a categorical X. Each group then becomes its own vertical column.
  const container = document.getElementById('timeline-container');

  // Note: Graph2d does NOT support Timeline-style `groups` — passing them
  // even as `{id: {...}}` triggers validator errors like "Unknown option
  // detected: period". Grouping is implicit via their `value` field:
  // items at value=1 (period) stack at column 1, value=2 (school) at 2,
  // value=3 (philosopher) at 3. The HTML legend at the top of the page
  // tells the user which color is which group.

  const timeline = new vis.Graph2d(container, items, {
    // Vertical: time flows top→bottom on Y axis; items at different
    // `value`s stack left→right (X axis). Each philosopher's life
    // becomes a single horizontal bar across its value column.
    orientation: 'vertical',
    // ~1 month in, ~5000 years out — covers all of antiquity through modern
    zoomMin: 1000 * 60 * 60 * 24 * 30,
    zoomMax: 1000 * 60 * 60 * 24 * 365 * 5000,
    showCurrentTime: false,
    multiselect: false,
    // We only render range bars — no point markers — so this kills the
    // default dot that Graph2d draws for each data point.
    drawPoints: false,
    // Pin the value axis to our three group columns with a little padding
    // so the bars don't kiss the chart border. Graph2d supports only
    // `visible`, `left/right.range`, `showMinorLabels`, `icons`, `width`.
    dataAxis: {
      visible: true,
      left: { range: { min: 0, max: 4 } },
      icons: false,
      showMinorLabels: false,
    },
    // Item-level `title` is honoured by Graph2d for native tooltip on hover
    // — no need for the timeline-style `tooltip` option here.
  });

  // Auto-fit the entire range on load — otherwise the user lands on
  // "now" (empty page) for an ancient-philosophy dataset.
  timeline.fit();

  // ---- Click navigation ----
  // Graph2d's click event uses `props.items` (array) instead of Timeline's
  // `props.item` (single). Pick the first item if the user clicked a range bar.
  // timeline.md sits at /timeline/ — need ../ to escape before reaching
  // sibling directories like /philosophers/, /schools/, /periods/.
  timeline.on('click', props => {
    if (props.items && props.items.length > 0) {
      const it = itemsById[props.items[0]];
      if (it && it.url) {
        window.location.href = '../' + it.url;
      }
    }
  });

  // ---- Expose for debugging ----
  window.__timeline = timeline;
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