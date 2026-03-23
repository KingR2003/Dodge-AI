import asyncio
import json
import logging
import os
import random
from pathlib import Path
from typing import Any, Dict, Optional

import httpx
from dotenv import load_dotenv

_ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(_ENV_PATH, override=True)

logger = logging.getLogger(__name__)

# ─── User-facing safe messages ────────────────────────────────────────────────
_MSG_RATE_LIMIT   = "System is currently busy. Please try again in a few seconds."
_MSG_API_FAILURE  = "Unable to process your request right now. Please try again shortly."
_MSG_INVALID_RESP = "Received an unexpected response. Please try again."
_MSG_NO_KEY       = "Service is not configured. Please contact the administrator."


class GeminiRateLimitError(Exception):
    """Raised when Gemini returns HTTP 429 Too Many Requests."""


class GeminiAPIError(Exception):
    """Raised for any non-rate-limit API error."""


class GeminiParseError(Exception):
    """Raised when Gemini response cannot be parsed as valid JSON."""


def get_gemini_api_key() -> str:
    key = (os.environ.get("GEMINI_API_KEY") or "").strip()
    if not key:
        raise RuntimeError(_MSG_NO_KEY)
    return key


def _extract_first_json_object(text: str) -> Optional[Dict[str, Any]]:
    if not text:
        return None
    
    # Pre-clean: remove Markdown code blocks if present
    text = text.replace("```json", "").replace("```", "").strip()
    
    start = text.find("{")
    end   = text.rfind("}")
    
    if start == -1:
        return None
    
    # Simple auto-repair: if no closing brace found, try adding one
    if end == -1 or end <= start:
        text += "}"
        end = text.rfind("}")
    
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        # One last ditch effort: try to close any open quotes/braces if common partial output
        try:
            return json.loads(text[start : end + 1] + '"}}')
        except:
            return None


async def select_tool_call_gemini(
    *,
    system_prompt: str,
    user_question: str,
) -> Dict[str, Any]:
    """
    Calls Gemini (gemini-flash-latest) to select a tool.
    Retries once if JSON is invalid or missing required fields.
    """
    api_key = get_gemini_api_key()
    model   = "gemini-flash-latest"
    url     = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    
    payload: Dict[str, Any] = {
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"role": "user", "parts": [{"text": user_question}]}],
        "generationConfig": {
            "temperature":    0,
            "maxOutputTokens": 512,  # Increased slightly to avoid truncation
            "topP":           1,
        },
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Try up to 2 times (Initial + 1 Retry) for logic/format errors
        for attempt in range(2):
            try:
                resp = await client.post(
                    url,
                    headers={"Content-Type": "application/json"},
                    json=payload,
                )

                if resp.status_code == 429:
                    # Rate limit follows its own retry logic (up to 2 times)
                    # But for simplicity, we treat it as a retryable error here too
                    if attempt < 1:
                        await asyncio.sleep(2)
                        continue
                    raise GeminiRateLimitError(_MSG_RATE_LIMIT)
                
                if not resp.is_success:
                    logger.error("Gemini HTTP %d: %s", resp.status_code, resp.text[:200])
                    raise GeminiAPIError(_MSG_API_FAILURE)

                data = resp.json()
                raw_text = (
                    data.get("candidates", [{}])[0]
                    .get("content", {})
                    .get("parts", [{}])[0]
                    .get("text", "")
                )
                
                logger.info("Raw Gemini Response (Attempt %d): %s", attempt + 1, raw_text.strip())

                parsed = _extract_first_json_object(raw_text)
                
                # Validation: must be JSON and must have "tool" field
                if not parsed or "tool" not in parsed:
                    if attempt < 1:
                        logger.warning("Invalid/Incomplete JSON or missing 'tool' field. Retrying...")
                        continue
                    logger.error("Gemini failed to return valid tool mapping after retry.")
                    raise GeminiParseError(_MSG_INVALID_RESP)

                return parsed

            except (GeminiRateLimitError, GeminiAPIError, GeminiParseError, httpx.HTTPError) as exc:
                if attempt < 1:
                    logger.warning("Attempt %d failed: %s. Retrying once...", attempt + 1, exc)
                    await asyncio.sleep(1)
                    continue
                else:
                    logger.error("Gemini mapping failed after final attempt: %s", exc)
                    raise

    raise GeminiAPIError(_MSG_API_FAILURE)
