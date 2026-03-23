from __future__ import annotations

import sqlite3
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, TypedDict


class GraphNode(TypedDict):
    id: str
    type: str
    metadata: Dict[str, Any]


class GraphEdge(TypedDict):
    source: str
    target: str
    relationship: str


NodeFromRow = Callable[[sqlite3.Row], Optional[GraphNode]]
EdgeFromRow = Callable[[sqlite3.Row], Optional[GraphEdge]]


def query_sqlite_to_graph(
    conn: sqlite3.Connection,
    sql: str,
    params: Optional[Sequence[Any]],
    *,
    node_from_row: NodeFromRow,
    edge_from_row: EdgeFromRow,
    dedupe_edges: bool = True,
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Execute a SQLite query and convert result rows into:
      {
        "nodes": [{"id", "type", "metadata"}, ...],
        "edges": [{"source", "target", "relationship"}, ...]
      }

    Efficiency:
    - Streams rows via iteration (no full materialization of result sets).
    - Deduplicates nodes by `id` and optionally edges by (source, target, relationship).
    """

    # Use named columns for easier node/edge mapping callbacks.
    conn.row_factory = sqlite3.Row

    nodes_by_id: Dict[str, GraphNode] = {}
    edges: List[GraphEdge] = []
    edge_keys: set[Tuple[str, str, str]] = set()

    cur = conn.execute(sql, params or [])

    for row in cur:
        node = node_from_row(row)
        if node is not None:
            node_id = node["id"]
            existing = nodes_by_id.get(node_id)
            if existing is None:
                # Defensive copy to avoid caller accidentally sharing dicts.
                nodes_by_id[node_id] = {"id": node["id"], "type": node["type"], "metadata": dict(node.get("metadata", {}) or {})}
            else:
                # Merge metadata if the same node is described multiple times across rows.
                existing["metadata"].update(node.get("metadata", {}) or {})

        edge = edge_from_row(row)
        if edge is not None:
            if dedupe_edges:
                key = (edge["source"], edge["target"], edge["relationship"])
                if key in edge_keys:
                    continue
                edge_keys.add(key)
            edges.append(edge)

    return {
        "nodes": list(nodes_by_id.values()),
        "edges": edges,
    }

