from __future__ import annotations

import logging
from typing import Any, Dict, List

from backend.models import ChatResponse
from backend.prompts import TOOL_SELECTOR_SYSTEM_PROMPT
from backend.services.db import sqlite_connection
from backend.services.gemini_client import (
    GeminiAPIError,
    GeminiParseError,
    GeminiRateLimitError,
    get_gemini_api_key,
    select_tool_call_gemini,
)
from backend.services.query_executor import execute_selected_tool
from guardrails import FIXED_REJECTION_MESSAGE, guardrails_decide

logger = logging.getLogger(__name__)

# ─── User-facing safe fallback messages ───────────────────────────────────────
_BUSY_MSG    = "System is currently busy. Please try again in a few seconds."
_FAILURE_MSG = "Unable to process your request right now. Please try again shortly."
_CONFIG_MSG  = "Service is not configured. Please contact the administrator."


def _format_list(values: List[Any], max_items: int = 5) -> str:
    return ", ".join(str(v) for v in values[:max_items])


# Simple in-memory cache for ChatResponse
# Stores: { normalized_question: ChatResponse }
_chat_cache: Dict[str, ChatResponse] = {}


async def chat(question: str) -> ChatResponse:
    # Normalize question for caching
    q_norm = question.strip().lower()
    if q_norm and q_norm in _chat_cache:
        logger.info("Chat cache hit for: '%s'", q_norm)
        return _chat_cache[q_norm]

    # 1) Verify API key is configured — fail fast with a safe message.
    try:
        get_gemini_api_key()
    except RuntimeError as exc:
        logger.error("Gemini API key missing: %s", exc)
        return ChatResponse(tool=None, answer=_CONFIG_MSG)

    # 2) Call Gemini to select a tool.
    try:
        tool_call: Dict[str, Any] = await select_tool_call_gemini(
            system_prompt=TOOL_SELECTOR_SYSTEM_PROMPT,
            user_question=question,
        )

    except GeminiRateLimitError:
        # 429 — already logged in gemini_client; surface a friendly message
        return ChatResponse(tool=None, answer=_BUSY_MSG)

    except GeminiParseError:
        # Model returned something we couldn't parse — already logged
        return ChatResponse(tool=None, answer=_FAILURE_MSG)

    except GeminiAPIError:
        # Network error, 5xx, timeout — already logged
        return ChatResponse(tool=None, answer=_FAILURE_MSG)

    except Exception as exc:
        # Catch-all: log full detail, never expose it to the user
        logger.exception("Unexpected error during Gemini tool selection: %s", exc)
        return ChatResponse(tool=None, answer=_FAILURE_MSG)

    # 3) Guardrails validate / reject.
    try:
        decision = guardrails_decide(question, tool_call)
    except Exception as exc:
        logger.exception("Guardrails error: %s", exc)
        return ChatResponse(tool=None, answer=_FAILURE_MSG)

    if decision["rejected"]:
        return ChatResponse(tool=None, answer=decision["message"])

    validated = decision["tool_call"]
    tool = validated["tool"]
    args = validated["args"]

    if tool == "out_of_scope":
        return ChatResponse(tool=None, answer=FIXED_REJECTION_MESSAGE)

    # 4) Execute bounded, allowlisted query tool.
    try:
        with sqlite_connection() as conn:
            executed = execute_selected_tool(conn, tool=tool, args=args)
            resp = ChatResponse(
                tool=executed.get("tool"),
                answer=executed.get("answer", FIXED_REJECTION_MESSAGE),
                graph=executed.get("graph"),
                data=executed.get("data"),
            )
            # Store in cache if normalized question is non-empty
            if q_norm:
                _chat_cache[q_norm] = resp
            return resp
    except Exception as exc:
        logger.exception("Query execution error for tool '%s': %s", tool, exc)
        return ChatResponse(tool=None, answer=_FAILURE_MSG)
