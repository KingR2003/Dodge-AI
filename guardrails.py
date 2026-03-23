from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple


FIXED_REJECTION_MESSAGE = (
    "This system is designed to answer questions related to the provided dataset only."
)

ALLOWED_TOOLS = {
    "top_products_by_billing",
    "trace_billing_document",
    "incomplete_sales_orders",
    "top_customers",
    "payment_trace",
    "out_of_scope",
}

MODE_VALUES = {"delivered_not_billed", "billed_without_delivery", "both"}


DOMAIN_KEYWORDS: List[str] = [
    # Document / flow terms
    "sales order",
    "sales_order",
    "delivery",
    "outbound delivery",
    "billing",
    "billing document",
    "journal entry",
    "payment",
    # Entity terms
    "customer",
    "product",
    "material",
    "plant",
    # Query intent terms
    "top",
    "highest",
    "trace",
    "flow",
    "incomplete",
    "broken",
    "delivered",
    "not billed",
    "billed without",
    "unbilled",
    # Common SAP-ish labels
    "accounting",
    "ar",
    "receivable",
]

DISALLOWED_KEYWORDS: List[str] = [
    # Creative writing / poems
    "poem",
    "poems",
    "write a poem",
    "sonnet",
    "story",
    "short story",
    "lyrics",
    "creative writing",
    "fantasy",
    # Broad general knowledge patterns (heuristic)
    "capital of",
    "weather",
    "how to bake",
    "explain gravity",
    "who is",
    "what is",
]


def _contains_any(haystack_lower: str, needles: List[str]) -> bool:
    return any(n in haystack_lower for n in needles)


def is_out_of_domain(user_text: str) -> bool:
    """
    Simple heuristic guardrail:
    - If it strongly looks like creative writing / general knowledge → out-of-domain.
    - If it does not mention any domain keywords → out-of-domain.
    """
    t = (user_text or "").strip().lower()
    if not t:
        return True

    if _contains_any(t, DISALLOWED_KEYWORDS):
        return True

    # If it has no domain keywords, reject.
    if not _contains_any(t, DOMAIN_KEYWORDS):
        return True

    return False


def _is_non_bool_int(x: Any) -> bool:
    return isinstance(x, int) and not isinstance(x, bool)


def _validate_tool_call_structure(tool_call: Any) -> Tuple[bool, Optional[str]]:
    if not isinstance(tool_call, dict):
        return False, "tool_call must be a JSON object"
    tool = tool_call.get("tool")
    args = tool_call.get("args", {})
    if tool not in ALLOWED_TOOLS:
        return False, "unknown tool"
    if not isinstance(args, dict):
        return False, "args must be an object"
    return True, None


def validate_tool_call(tool_call: Any) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Returns:
      (True, validated_tool_call) if ok
      (False, None) otherwise
    """
    ok, _reason = _validate_tool_call_structure(tool_call)
    if not ok:
        return False, None

    tool = tool_call["tool"]
    args = tool_call.get("args", {})

    if tool == "top_products_by_billing":
        if "limit" in args:
            limit = args["limit"]
            if not _is_non_bool_int(limit) or not (1 <= limit <= 50):
                return False, None
        if "company_code" in args:
            cc = args["company_code"]
            if not isinstance(cc, str) or not cc.strip():
                return False, None
        # Allow only known keys
        allowed_keys = {"limit", "company_code"}
        if set(args.keys()) - allowed_keys:
            return False, None

    elif tool == "trace_billing_document":
        allowed_keys = {"billing_document", "include_journal_entry", "include_payments"}
        if set(args.keys()) - allowed_keys:
            return False, None

        bd = args.get("billing_document")
        if not isinstance(bd, str) or not bd.strip():
            return False, None

        if "include_journal_entry" in args and not isinstance(args["include_journal_entry"], bool):
            return False, None
        if "include_payments" in args and not isinstance(args["include_payments"], bool):
            return False, None

    elif tool == "incomplete_sales_orders":
        allowed_keys = {"company_code", "limit", "mode"}
        if set(args.keys()) - allowed_keys:
            return False, None

        if "limit" in args:
            limit = args["limit"]
            if not _is_non_bool_int(limit) or not (1 <= limit <= 100):
                return False, None

        if "company_code" in args:
            cc = args["company_code"]
            if not isinstance(cc, str) or not cc.strip():
                return False, None

        if "mode" in args:
            mode = args["mode"]
            if not isinstance(mode, str) or mode not in MODE_VALUES:
                return False, None

    elif tool == "top_customers":
        allowed_keys = {"limit", "company_code"}
        if set(args.keys()) - allowed_keys:
            return False, None

        if "limit" in args:
            limit = args["limit"]
            if not _is_non_bool_int(limit) or not (1 <= limit <= 50):
                return False, None

        if "company_code" in args:
            cc = args["company_code"]
            if not isinstance(cc, str) or not cc.strip():
                return False, None

    elif tool == "payment_trace":
        allowed_keys = {"billing_document", "include_journal_entry"}
        if set(args.keys()) - allowed_keys:
            return False, None

        bd = args.get("billing_document")
        if not isinstance(bd, str) or not bd.strip():
            return False, None

        if "include_journal_entry" in args and not isinstance(args["include_journal_entry"], bool):
            return False, None

    elif tool == "out_of_scope":
        if set(args.keys()) - set():
            # args must be empty object
            return False, None

    else:
        return False, None

    # Normalize missing optional args (leave as-is; backend can default)
    return True, {"tool": tool, "args": args}


def guardrails_decide(user_text: str, tool_call: Any) -> Dict[str, Any]:
    """
    Decide whether to execute tool_call or reject.

    Output:
      - If rejected: { "rejected": true, "message": FIXED_REJECTION_MESSAGE }
      - If allowed:  { "rejected": false, "tool_call": <validated> }
    """
    if is_out_of_domain(user_text):
        return {"rejected": True, "message": FIXED_REJECTION_MESSAGE}

    validated_ok, validated = validate_tool_call(tool_call)
    if not validated_ok or validated is None:
        return {"rejected": True, "message": FIXED_REJECTION_MESSAGE}

    return {"rejected": False, "tool_call": validated}


def example_rejection_detection() -> None:
    assert is_out_of_domain("Write a poem about trucks") is True
    assert is_out_of_domain("What is the capital of France?") is True
    assert is_out_of_domain("Trace billing document 90504248") is False

