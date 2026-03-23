from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class GraphNode(BaseModel):
    id: str
    type: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    source: str
    target: str
    relationship: str


class GraphPayload(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]


class ChatRequest(BaseModel):
    question: str


class ChatResponse(BaseModel):
    tool: Optional[str] = None
    answer: str
    graph: Optional[GraphPayload] = None
    data: Optional[Dict[str, Any]] = None

