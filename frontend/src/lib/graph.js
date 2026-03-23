function shortenId(id) {
  if (!id) return "";
  const parts = String(id).split(":");
  return parts.length > 1 ? parts[parts.length - 1] : id;
}

export function toForceGraphData(graph) {
  if (!graph || !graph.nodes || !graph.edges) {
    return { nodes: [], links: [] };
  }

  const nodes = graph.nodes.map((n) => ({
    ...n,
    label: shortenId(n.id),
  }));

  const links = graph.edges.map((e) => ({
    source: e.source,
    target: e.target,
    relationship: e.relationship,
    label: shortenId(e.relationship),
  }));

  return { nodes, links };
}

export function oneHopSubgraph(graph, selectedId) {
  if (!graph || !selectedId) return graph;
  const idSet = new Set([selectedId]);

  for (const e of graph.edges || []) {
    if (e.source === selectedId) idSet.add(e.target);
    if (e.target === selectedId) idSet.add(e.source);
  }

  const nodes = (graph.nodes || []).filter((n) => idSet.has(n.id));
  const edges = (graph.edges || []).filter((e) => idSet.has(e.source) && idSet.has(e.target));

  return { nodes, edges };
}

