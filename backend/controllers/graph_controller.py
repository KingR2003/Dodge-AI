from __future__ import annotations

from typing import Any, Dict, Optional

import sqlite3
from fastapi import APIRouter, Query

from services.db import sqlite_connection
from services.graph_service import build_graph_for_billing_document


router = APIRouter()


@router.get("/graph")
def get_graph(
    billing_document: Optional[str] = Query(default=None),
    include_journal_entry: bool = Query(default=False),
    include_payments: bool = Query(default=False),
) -> Dict[str, Any]:
    with sqlite_connection() as conn:
        doc = billing_document
        if not doc:
            row = conn.execute(
                "SELECT billing_document FROM billing_document_headers ORDER BY billing_document LIMIT 1"
            ).fetchone()
            if not row:
                return {"nodes": [], "edges": []}
            doc = row[0]

        return build_graph_for_billing_document(
            conn,
            billing_document=str(doc),
            include_journal_entry=include_journal_entry,
            include_payments=include_payments,
        )

