from __future__ import annotations

from fastapi import FastAPI

from backend.controllers.chat_controller import router as chat_router
from backend.controllers.graph_controller import router as graph_router


app = FastAPI(title="SAP O2C Graph Query API")

app.include_router(graph_router)
app.include_router(chat_router)

