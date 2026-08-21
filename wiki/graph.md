# 知识图谱

本页可视化 Wiki 中所有页面（节点）与所有 `[[wikilink]]`（边）。

- **节点颜色**：哲学家用靛蓝、概念用绿、著作用橙、学派用紫、时期用青、论证用红
- **节点大小**：关联越多节点越大（Obsidian 风格）— 节点的圆点越大表示被引用越多
- **节点透明度**：stub 状态略透明，active/mature 状态实心
- **无方向箭头**（Obsidian 风格）：边不表示方向，只表示两节点相互引用过
- **悬停**查看类型与状态信息，**点击**跳转页面（点击边会弹出该来源页中所有引用位置）
- **拖拽**节点，**滚轮**缩放

<div class="graph-legend">
  <span><span class="legend-dot" style="background:#5c6bc0"></span>哲学家</span> &nbsp;
  <span><span class="legend-dot" style="background:#66bb6a"></span>概念</span> &nbsp;
  <span><span class="legend-dot" style="background:#ffa726"></span>著作</span> &nbsp;
  <span><span class="legend-dot" style="background:#ab47bc"></span>学派</span> &nbsp;
  <span><span class="legend-dot" style="background:#26c6da"></span>时期</span> &nbsp;
  <span><span class="legend-dot" style="background:#ef5350"></span>论证</span> &nbsp;
  <span style="margin-left:1em; font-size:0.85em; opacity:0.7">节点越大 = 关联越多 · 较透明 = stub · 实心 = active/mature</span>
</div>

<div id="graph-container"></div>

<!-- 边点击预览选单：单次出现自动跳转，多次出现时列出所有引用位置供选择 -->
<div id="edge-popup" class="edge-popup" style="display: none;">
  <div class="edge-popup-header">
    <div class="edge-popup-title">
      <span class="popup-from"></span>
      <span class="popup-relation">引用了</span>
      <span class="popup-to"></span>
    </div>
    <button class="edge-popup-close" type="button" aria-label="关闭">×</button>
  </div>
  <div class="edge-popup-hint"><span class="popup-from"></span> 中共有 <span class="popup-count">0</span> 处对 <span class="popup-to"></span> 的引用，点击行号跳转：</div>
  <ol class="edge-popup-list"></ol>
</div>

<script src="https://unpkg.com/vis-network@9.1.9/standalone/umd/vis-network.min.js"></script>
<script>
(async function() {
  const isDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  const theme = {
    text:      isDark ? '#e0e0e0' : '#212121',
    edge:      isDark ? '#666666' : '#bdbdbd',
    edgeHover: isDark ? '#90caf9' : '#1976d2',
  };

  // Re-load when the user *manually* toggles Material's palette. The
  // first mutation we see is Material setting `data-md-color-scheme`
  // on page load (sometimes AFTER our script runs, depending on the
  // browser) — we adopt that value as the baseline and ignore it. Any
  // subsequent change is treated as a user action.
  let lastKnownScheme = document.body.getAttribute('data-md-color-scheme');
  let observerReady = false;
  let reloadTimer = null;
  new MutationObserver(() => {
    const current = document.body.getAttribute('data-md-color-scheme');
    if (!observerReady) {
      observerReady = true;
      lastKnownScheme = current;
      return; // first mutation is Material's bootstrap — adopt as baseline
    }
    if (current === lastKnownScheme || reloadTimer) return;
    lastKnownScheme = current;
    reloadTimer = setTimeout(() => location.reload(), 250);
  }).observe(document.body, {
    attributes: true,
    attributeFilter: ['data-md-color-scheme'],
  });

  const res = await fetch('../assets/graph.json');
  if (!res.ok) { document.getElementById('graph-container').innerText = 'graph.json 未找到'; return; }
  const data = await res.json();

  const COLOR = {
    philosopher: '#5c6bc0',
    concept:     '#66bb6a',
    work:        '#ffa726',
    school:      '#ab47bc',
    period:      '#26c6da',
    argument:    '#ef5350',
  };

  // Obsidian-style: node size scales with degree (number of connections).
  // A node with many in/out edges becomes a larger dot — clusters visually.
  const degreeById = {};
  for (const e of data.edges) {
    degreeById[e.from] = (degreeById[e.from] || 0) + 1;
    degreeById[e.to]   = (degreeById[e.to]   || 0) + 1;
  }

  const nodes = data.nodes.map(n => {
    const fill = COLOR[n.type] || '#9e9e9e';
    const isStub = n.status === 'stub';
    const degree = degreeById[n.id] || 0;
    // Base size: stub 10, active/mature 14. Bonus from sqrt(degree).
    // Caps at 28 so hub nodes don't dominate the canvas.
    const baseSize = isStub ? 10 : 14;
    const size = Math.min(baseSize + Math.sqrt(degree) * 3.5, 28);
    return {
      id: n.id,
      label: n.label,
      url: n.url,
      title: n.id + ' — ' + n.type + ' [' + n.status + ']（关联 ' + degree + ' 次）',
      size: size,
      // Obsidian uses circles for everything — no shape distinction.
      // Stub nodes fade slightly so active/mature pages stand out.
      shape: 'dot',
      color: {
        background: fill,
        border: fill,
        // Stub: 60% opacity on background (faded dot).
        // Active/Mature: full opacity.
        opacity: isStub ? 0.55 : 1.0,
        highlight: { background: fill, border: '#000', opacity: 1.0 },
      },
      // Show the label below the dot (Obsidian style). Stub labels are
      // slightly faded to match their dot opacity. Larger degree = more
      // prominent label.
      font: {
        color: theme.text,
        face: 'Noto Sans SC, sans-serif',
        size: 12,
        strokeWidth: 0,
        strokeColor: 'transparent',
      },
    };
  });

  const edges = data.edges.map(e => ({
    id: e.id,
    from: e.from,
    to: e.to,
    // Keep the navigation metadata the click handler and popup need.
    // (Forgetting any of these makes the edge "click does nothing" bug
    // reappear — see commit b1323cd → ... in git history.)
    fromUrl: e.fromUrl,
    toUrl: e.toUrl,
    fromLabel: e.fromLabel,
    toLabel: e.toLabel,
    firstLine: e.firstLine,
    firstAnchor: e.firstAnchor,
    allOccurrences: e.allOccurrences || [],
    // Obsidian-style: NO ARROWS in the visualization. Edges are
    // undirected lines showing "these two pages reference each other".
    // But the TOOLTIP keeps the arrow direction — the title is text,
    // not the canvas, so direction is still discoverable on hover.
    arrows: '',
    // Hover tooltip: source → target + occurrence count + click hint.
    // Desktop only — mobile has no hover (use long-press instead).
    title: `${e.fromLabel} → ${e.toLabel}（${(e.allOccurrences || []).length} 处引用，点击查看）`,
    color: { color: theme.edge, highlight: theme.edgeHover, opacity: 0.6 },
    smooth: { type: 'continuous' },
    // Thinner than before (was 1.5). Obsidian uses hairline edges so
    // clusters read as clusters, not as messy line tangles.
    width: 0.7,
    selectionWidth: 1.5,
  }));

  const container = document.getElementById('graph-container');
  const network = new vis.Network(container, {
    nodes: new vis.DataSet(nodes),
    edges: new vis.DataSet(edges),
  }, {
    physics: {
      stabilization: { iterations: 300 },
      // Obsidian-feel: tighter clusters since nodes are smaller dots now.
      // - Strong central pull so the graph doesn't drift to a corner.
      // - Longer springs so related nodes can form visible clusters.
      // - High damping so it stops jiggling quickly.
      barnesHut: {
        gravitationalConstant: -12000,
        springLength: 180,
        springConstant: 0.04,
        damping: 0.5,
        avoidOverlap: 0.3,
      },
    },
    interaction: { hover: true, tooltipDelay: 100, hideEdgesOnDrag: true },
    nodes: { borderWidth: 1 },
    edges: { smooth: { type: 'continuous' } },
  });

  // Click handler — node click navigates to the node's page; edge click
  // navigates to the *source* page (where the [[link]] was authored). The
  // graph page itself sits at /graph/, so all target URLs need a `../`
  // prefix to escape it (otherwise the browser resolves them relative
  // to /graph/ and 404s).
  //
  // When the same source page contains several [[X]] links to the same
  // target, clicking the edge shows a popup listing every occurrence
  // line; the user picks which line to land on. Single-occurrence edges
  // jump directly without a popup.
  function hideEdgePopup() {
    const popup = document.getElementById('edge-popup');
    if (popup) popup.style.display = 'none';
  }

  function showEdgePopup(edge, pointer) {
    const occurrences = edge.allOccurrences || [];

    // 0 occurrences recorded (shouldn't happen, but be defensive) or
    // exactly 1 occurrence: just navigate directly.
    if (occurrences.length <= 1) {
      const anchor = occurrences.length === 1 ? '#' + occurrences[0].anchor : '';
      window.location.href = '../' + edge.fromUrl + anchor;
      return;
    }

    const popup = document.getElementById('edge-popup');
    if (!popup) return;

    popup.querySelectorAll('.popup-from').forEach(el => el.textContent = edge.fromLabel);
    popup.querySelectorAll('.popup-to').forEach(el => el.textContent = edge.toLabel);
    popup.querySelector('.popup-count').textContent = occurrences.length;

    const listEl = popup.querySelector('.edge-popup-list');
    listEl.innerHTML = '';
    for (const occ of occurrences) {
      const li = document.createElement('li');
      const a = document.createElement('a');
      a.href = '../' + edge.fromUrl + '#' + occ.anchor;
      a.textContent = '第 ' + occ.line + ' 行';
      li.appendChild(a);
      listEl.appendChild(li);
    }

    // Position with fixed coordinates; vis-network's pointer.DOM is
    // page-relative, so subtract scroll to get viewport coords.
    const dom = (pointer && pointer.DOM) || { x: window.innerWidth / 2, y: window.innerHeight / 2 };
    popup.style.display = 'block';   // show first so offsetWidth/Height are real
    const margin = 8;
    const popupW = popup.offsetWidth;
    const popupH = popup.offsetHeight;
    const vpX = dom.x - window.scrollX;
    const vpY = dom.y - window.scrollY;
    const x = Math.min(Math.max(vpX, margin), window.innerWidth - popupW - margin);
    const y = Math.min(Math.max(vpY, margin), window.innerHeight - popupH - margin);
    popup.style.left = x + 'px';
    popup.style.top = y + 'px';
  }

  // Dismiss popup with × button
  document.querySelector('#edge-popup .edge-popup-close')
    .addEventListener('click', hideEdgePopup);
  // Esc key also dismisses
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') hideEdgePopup();
  });

  // Bind the click handler to the vis-network INSTANCE (not the DOM
  // container). vis-network uses hammer.js internally and calls
  // `preventDefault()` on touch events, which means the browser does
  // NOT synthesize a `click` event on mobile — so `container.on('click')`
  // would never fire there. `network.on('click')` is vis-network's own
  // event and fires for both desktop clicks and mobile taps.
  network.on('click', params => {
    hideEdgePopup();   // always reset popup state on any graph click
    if (params.nodes.length > 0) {
      const node = nodes.find(n => n.id === params.nodes[0]);
      if (node && node.url !== undefined) {
        window.location.href = '../' + node.url;
      }
    } else if (params.edges.length > 0) {
      const edge = edges.find(e => e.id === params.edges[0]);
      if (edge && edge.fromUrl !== undefined) {
        showEdgePopup(edge, params.pointer);
      }
    }
  });

  // Mobile fallback: edges are thin lines and notoriously hard to tap
  // precisely on a touchscreen. Long-press (the vis-network `hold` event)
  // gives mobile users a reliable way to access an edge: it shows the
  // same popup (or directly navigates if there's only one occurrence).
  // On desktop this maps to a right-click-style "context" gesture, so
  // it doesn't interfere with normal click navigation.
  network.on('hold', params => {
    if (params.edges.length > 0 && params.nodes.length === 0) {
      const edge = edges.find(e => e.id === params.edges[0]);
      if (edge && edge.fromUrl !== undefined) {
        hideEdgePopup();
        showEdgePopup(edge, params.pointer);
      }
    }
  });
})();
</script>