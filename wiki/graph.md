# 知识图谱

本页可视化 Wiki 中所有页面（节点）与所有 `[[wikilink]]`（边）。

- **节点形状**：方框 = active/mature 页面，圆点 = stub 页面
- **节点颜色**：哲学家用靛蓝、概念用绿、著作用橙、学派用紫、时期用青、论证用红
- **悬停**查看类型信息，**点击**跳转页面
- **拖拽**节点，**滚轮**缩放

<div class="graph-legend">
  <span><span class="legend-dot" style="background:#5c6bc0"></span>哲学家</span> &nbsp;
  <span><span class="legend-dot" style="background:#66bb6a"></span>概念</span> &nbsp;
  <span><span class="legend-dot" style="background:#ffa726"></span>著作</span> &nbsp;
  <span><span class="legend-dot" style="background:#ab47bc"></span>学派</span> &nbsp;
  <span><span class="legend-dot" style="background:#26c6da"></span>时期</span> &nbsp;
  <span><span class="legend-dot" style="background:#ef5350"></span>论证</span> &nbsp;
  <span><span class="legend-dot" style="background:#9e9e9e"></span>stub / 待创建</span>
</div>

<div id="graph-container"></div>

<script src="https://unpkg.com/vis-network@9.1.9/standalone/umd/vis-network.min.js"></script>
<script>
(async function() {
  const isDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  const theme = {
    text:      isDark ? '#e0e0e0' : '#212121',
    edge:      isDark ? '#666666' : '#bdbdbd',
    edgeHover: isDark ? '#90caf9' : '#1976d2',
  };
  // Re-load when Material's color scheme flips
  new MutationObserver(() => location.reload()).observe(
    document.body, { attributes: true, attributeFilter: ['data-md-color-scheme'] }
  );

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

  const nodes = data.nodes.map(n => {
    const fill = COLOR[n.type] || '#9e9e9e';
    return {
      id: n.id,
      label: n.label,
      url: n.url,
      title: n.id + ' — ' + n.type + ' [' + n.status + ']',
      color: {
        background: fill,
        border: n.status === 'stub' ? '#9e9e9e' : fill,
        highlight: { background: fill, border: '#000' },
      },
      shape: n.status === 'stub' ? 'dot' : 'box',
      font: { color: theme.text, face: 'Noto Sans SC, sans-serif', size: 14 },
    };
  });

  const edges = data.edges.map(e => ({
    from: e.from,
    to: e.to,
    arrows: 'to',
    color: { color: theme.edge, highlight: theme.edgeHover },
    smooth: { type: 'continuous' },
  }));

  const container = document.getElementById('graph-container');
  new vis.Network(container, {
    nodes: new vis.DataSet(nodes),
    edges: new vis.DataSet(edges),
  }, {
    physics: {
      stabilization: { iterations: 200 },
      barnesHut: { gravitationalConstant: -8000, springLength: 120 },
    },
    interaction: { hover: true, tooltipDelay: 100 },
    nodes: { borderWidth: 2 },
  });

  container.on('click', params => {
    if (params.nodes.length > 0) {
      const node = nodes.find(n => n.id === params.nodes[0]);
      if (node && node.url) window.location.href = node.url;
    }
  });
})();
</script>