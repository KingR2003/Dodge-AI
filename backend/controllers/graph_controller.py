import logging
import traceback
from pathlib import Path

import sqlite3
from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from services.db import sqlite_connection
from services.graph_service import build_graph_for_billing_document

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/graph")
def get_graph(
    billing_document: Optional[str] = Query(default=None),
    include_journal_entry: bool = Query(default=False),
    include_payments: bool = Query(default=False),
) -> Any:
    try:
        # Resolve absolute paths for debugging and verification
        BASE_DIR = Path(__file__).resolve().parent.parent
        DATA_DIR = BASE_DIR / "sap-o2c-data"
        DB_PATH = BASE_DIR / "o2c.sqlite"

        logger.info(f"Loading graph data from: {BASE_DIR}")

        if not DATA_DIR.exists():
            logger.error(f"Data directory missing: {DATA_DIR}")
            # The API currently only needs the .sqlite file, but we verify this per requirements.
        
        if not DB_PATH.exists():
            raise FileNotFoundError(f"Database file not found at: {DB_PATH}")

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
            
    except Exception as e:
        err_msg = f"Error in /graph endpoint: {str(e)}"
        logger.error(err_msg)
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error",
                "detail": str(e),
                "traceback": traceback.format_exc()
            }
        )

