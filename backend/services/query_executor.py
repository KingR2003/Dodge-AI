from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import sqlite3

from backend.services.graph_service import build_graph_for_billing_document
from backend.services.query_tools import (
    incomplete_sales_orders,
    payment_trace,
    top_customers,
    top_products_by_billing,
    trace_billing_document,
)


def _format_list(values: List[Any], max_items: int = 5) -> str:
    trimmed = values[:max_items]
    return ", ".join(str(v) for v in trimmed)


def execute_selected_tool(
    conn: sqlite3.Connection,
    *,
    tool: str,
    args: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Execute one allowlisted query tool and return a structured result:
      { "tool": tool, "answer": str, "data": {...}, "graph": optional {...} }
    """
    if tool == "top_products_by_billing":
        limit = int(args.get("limit", 10))
        company_code = args.get("company_code")
        rows = top_products_by_billing(conn, limit=limit, company_code=company_code)
        if not rows:
            return {"tool": tool, "answer": "No relevant data found"}

        parts: List[str] = []
        for r in rows[:limit]:
            name = r.get("product_name") or r.get("product")
            cnt = r.get("billing_document_count")
            parts.append(f"- **{name}**: {cnt} billing documents")

        header = f"Top {len(parts)} products by billing document count:\n"
        return {
            "tool": tool,
            "answer": header + "\n".join(parts),
            "data": {"rows": rows},
        }

    if tool == "top_customers":
        limit = int(args.get("limit", 10))
        company_code = args.get("company_code")
        rows = top_customers(conn, limit=limit, company_code=company_code)
        if not rows:
            return {"tool": tool, "answer": "No relevant data found"}

        parts: List[str] = []
        for r in rows[:limit]:
            name = r.get("customer_name") or r.get("customer")
            cnt = r.get("billing_document_count")
            parts.append(f"- **{name}**: {cnt} billing documents")

        header = f"Top {len(parts)} customers by billing document count:\n"
        return {
            "tool": tool,
            "answer": header + "\n".join(parts),
            "data": {"rows": rows},
        }

    if tool == "trace_billing_document":
        billing_document = args["billing_document"]
        include_journal_entry = bool(args.get("include_journal_entry", True))
        include_payments = bool(args.get("include_payments", False))

        result = trace_billing_document(
            conn,
            billing_document=billing_document,
            include_journal_entry=include_journal_entry,
            include_payments=include_payments,
        )
        flow_rows: List[Dict[str, Any]] = result["flow_rows"]
        journal_rows: List[Dict[str, Any]] = result["journal_rows"]

        if not flow_rows:
            return {"tool": tool, "answer": "No relevant data found"}

        delivery_docs = sorted({r.get("delivery_document") for r in flow_rows if r.get("delivery_document")})
        sales_orders = sorted({r.get("sales_order") for r in flow_rows if r.get("sales_order")})

        billing_doc = flow_rows[0].get("billing_document")
        company_code = flow_rows[0].get("company_code")
        fiscal_year = flow_rows[0].get("fiscal_year")
        accounting_document = flow_rows[0].get("accounting_document")
        customer_id = flow_rows[0].get("billing_customer")
        customer_name = flow_rows[0].get("customer_name")

        journal_info = ""
        if include_journal_entry and journal_rows:
            journal_id = f"JournalEntry:{company_code}:{fiscal_year}:{accounting_document}"
            journal_info = f" Journal entry: {journal_id}."

        answer = (
            f"Billing document {billing_doc} (company_code {company_code}) is linked to customer "
            f"{customer_name or customer_id}. Deliveries: {_format_list(delivery_docs)}. "
            f"Sales orders: {_format_list(sales_orders)}."
            f"{journal_info}"
        )

        graph = build_graph_for_billing_document(
            conn,
            billing_document=str(billing_document),
            include_journal_entry=include_journal_entry,
            include_payments=include_payments,
        )

        return {
            "tool": tool,
            "answer": answer,
            "graph": graph,
            "data": {"flow_rows": flow_rows, "journal_rows": journal_rows},
        }

    if tool == "incomplete_sales_orders":
        limit = int(args.get("limit", 50))
        company_code = args.get("company_code")
        mode = str(args.get("mode", "both"))

        rows = incomplete_sales_orders(conn, limit=limit, company_code=company_code, mode=mode)
        if not rows:
            return {"tool": tool, "answer": "No relevant data found"}

        so_list = []
        for r in rows[:limit]:
            so = r.get("sales_order")
            cust = r.get("customer")
            so_list.append(f"- **Sales Order {so}**: Customer {cust}")

        header = "Delivered but not billed sales orders:\n"
        return {
            "tool": tool,
            "answer": header + "\n".join(so_list),
            "data": {"rows": rows},
        }

    if tool == "payment_trace":
        billing_document = args["billing_document"]
        include_journal_entry = bool(args.get("include_journal_entry", True))

        result = payment_trace(
            conn,
            billing_document=billing_document,
            include_journal_entry=include_journal_entry,
            include_payments=True,
        )
        payment_rows = result["payment_rows"]
        journal_rows = result["journal_rows"]

        if not payment_rows and not journal_rows:
            return {"tool": tool, "answer": "No relevant data found"}

        answer_parts: List[str] = []
        if payment_rows:
            answer_parts.append(f"{len(payment_rows)} payment line(s)")
        if include_journal_entry and journal_rows:
            answer_parts.append(f"{len(journal_rows)} journal line(s)")

        answer = f"Payment trace for billing document {billing_document}: " + "; ".join(answer_parts) + "."
        return {
            "tool": tool,
            "answer": answer,
            "data": {"payment_rows": payment_rows, "journal_rows": journal_rows},
        }

    # Should not happen (guardrails already validated tool allowlist).
    return {"tool": tool, "answer": "No relevant data found"}

