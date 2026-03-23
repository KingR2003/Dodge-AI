from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

import httpx


def get_env(name: str, default: Optional[str] = None) -> Optional[str]:
    return os.environ.get(name, default)


def _extract_first_json_object(text: str) -> Optional[Dict[str, Any]]:
    if not text:
        return None
    # Best-effort extraction: find first '{' and last '}'.
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    candidate = text[start : end + 1]
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return None


async def select_tool_call(
    *,
    system_prompt: str,
    user_question: str,
) -> Dict[str, Any]:
    """
    Calls an OpenAI-compatible Chat Completions endpoint and returns parsed JSON.

    Required env vars:
      - LLM_API_KEY
      - LLM_API_BASE_URL (e.g., https://openrouter.ai/api/v1 or https://api.groq.com/openai/v1)
      - LLM_MODEL (e.g., a provider model name)
    """

    api_key = get_env("LLM_API_KEY")
    api_base = get_env("LLM_API_BASE_URL")
    model = get_env("LLM_MODEL")
    if not api_key or not api_base or not model:
        raise RuntimeError(
            "Missing LLM configuration. Set LLM_API_KEY, LLM_API_BASE_URL, and LLM_MODEL."
        )

    url = api_base.rstrip("/") + "/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload: Dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_question},
        ],
        "temperature": 0,
    }

    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
        resp = await client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()

    # OpenAI-compatible shape.
    content = (
        data.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
    )
    parsed = _extract_first_json_object(content)
    if parsed is None:
        raise RuntimeError("LLM did not return valid JSON.")
    return parsed

