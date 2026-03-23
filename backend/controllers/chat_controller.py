from __future__ import annotations

from fastapi import APIRouter

from models import ChatRequest, ChatResponse
from services.chat_service import chat


router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def post_chat(req: ChatRequest) -> ChatResponse:
    return await chat(req.question)

