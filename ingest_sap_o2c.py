import argparse
import json
import logging
import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


FOLDER_TO_TABLE = {
    "sales_order_headers": "sales_order_headers",
    "sales_order_items": "sales_order_items",
    "sales_order_schedule_lines": "sales_order_schedule_lines",
    "outbound_delivery_headers": "outbound_delivery_headers",
    "outbound_delivery_items": "outbound_delivery_items",
    "billing_document_headers": "billing_document_headers",
    "billing_document_items": "billing_document_items",
    "billing_document_cancellations": "billing_document_cancellations",
    "journal_entry_items_accounts_receivable": "journal_entry_items_ar",
    "payments_accounts_receivable": "payment_items_ar",
    "products": "products",
    "product_descriptions": "product_descriptions",
    "product_plants": "product_plants",
    "product_storage_locations": "product_storage_locations",
    "plants": "plants",
    "business_partners": "business_partners",
    "business_partner_addresses": "business_partner_addresses",
    "customer_sales_area_assignments": "customer_sales_area_assignments",
    "customer_company_assignments": "customer_company_assignments",
}

REQUIRED_COLS = {
    "sales_order_headers": ["sales_order"],
    "sales_order_items": ["sales_order", "sales_order_item"],
    "sales_order_schedule_lines": ["sales_order", "sales_order_item", "schedule_line"],
    "outbound_delivery_headers": ["delivery_document"],
    "outbound_delivery_items": ["delivery_document", "delivery_document_item"],
    "billing_document_headers": ["billing_document"],
    "billing_document_items": ["billing_document", "billing_document_item"],
    "billing_document_cancellations": ["billing_document"],
    "journal_entry_items_ar": ["company_code", "fiscal_year", "accounting_document", "accounting_document_item"],
    "payment_items_ar": ["company_code", "fiscal_year", "accounting_document", "accounting_document_item"],
    "products": ["product"],
    "product_descriptions": ["product", "language"],
    "product_plants": ["product", "plant"],
    "product_storage_locations": ["product", "plant", "storage_location"],
    "plants": ["plant"],
    "business_partners": ["business_partner"],
    "business_partner_addresses": ["business_partner", "address_id"],
    "customer_sales_area_assignments": ["customer", "sales_organization", "distribution_channel", "division"],
    "customer_company_assignments": ["customer", "company_code"],
}


def to_snake(s: str) -> str:
    # Converts e.g. "salesOrderItem" or "lastChangeDateTime" → "sales_order_item", "last_change_date_time".
    out: List[str] = []
    prev_lower = False
    for ch in s:
        if ch.isupper():
            if prev_lower:
                out.append("_")
            out.append(ch.lower())
            prev_lower = False
        else:
            out.append(ch.lower())
            prev_lower = ch.isalpha() and ch.islower()
    return "".join(out)


def setup_logging(log_level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(message)s",
    )


def get_table_columns(conn: sqlite3.Connection, table: str) -> List[str]:
    cur = conn.execute(f"PRAGMA table_info({table})")
    # PRAGMA returns: cid, name, type, notnull, dflt_value, pk
    cols = [row[1] for row in cur.fetchall()]
    if not cols:
        raise RuntimeError(f"Table {table!r} not found or has no columns.")
    return cols


def record_to_row(
    record: Dict[str, Any],
    table_columns_set: set,
) -> Dict[str, Any]:
    row: Dict[str, Any] = {}
    for k, v in record.items():
        col_base = to_snake(k)
        if isinstance(v, (dict, list)):
            col_candidate = f"{col_base}_json"
            if col_candidate in table_columns_set:
                row[col_candidate] = json.dumps(v, ensure_ascii=False)
        else:
            if col_base in table_columns_set:
                row[col_base] = v
    return row


def iter_jsonl_files(folder: Path) -> Iterable[Path]:
    # Deterministic order for reproducibility.
    yield from sorted(folder.glob("*.jsonl"))


def ingest_one_table(
    conn: sqlite3.Connection,
    dataset_root: Path,
    folder_name: str,
    table_name: str,
    batch_size: int,
    dry_run: bool,
    log_every: int,
) -> None:
    src_folder = dataset_root / folder_name
    if not src_folder.exists():
        logging.warning("Skipping %s (folder missing): %s", table_name, src_folder)
        return

    insert_columns = get_table_columns(conn, table_name)
    insert_columns_set = set(insert_columns)
    required = REQUIRED_COLS.get(table_name, [])

    placeholders = ", ".join(["?"] * len(insert_columns))
    columns_sql = ", ".join(insert_columns)
    insert_sql = f"INSERT OR IGNORE INTO {table_name} ({columns_sql}) VALUES ({placeholders})"

    total_processed = 0
    total_inserted_attempt = 0
    total_skipped_missing = 0
    total_bad_json = 0

    jsonl_files = list(iter_jsonl_files(src_folder))
    if not jsonl_files:
        logging.warning("Skipping %s (no jsonl files): %s", table_name, src_folder)
        return

    logging.info("Ingesting %s → %s (%d files)", folder_name, table_name, len(jsonl_files))

    for file_idx, jsonl_path in enumerate(jsonl_files, start=1):
        logging.info("  File %d/%d: %s", file_idx, len(jsonl_files), jsonl_path)

        batch: List[Tuple[Any, ...]] = []
        file_processed = 0

        def flush_batch() -> None:
            nonlocal batch, total_inserted_attempt
            if not batch:
                return
            if not dry_run:
                conn.executemany(insert_sql, batch)
            total_inserted_attempt += len(batch)
            batch = []

        with jsonl_path.open("r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                file_processed += 1
                total_processed += 1

                try:
                    record = json.loads(line)
                    if not isinstance(record, dict):
                        raise ValueError("JSONL line was not an object")
                except Exception:
                    total_bad_json += 1
                    if total_bad_json <= 5:
                        logging.warning(
                            "    Bad JSON at %s:%d (skipping)",
                            jsonl_path,
                            line_no,
                        )
                    continue

                row_dict = record_to_row(record, insert_columns_set)

                missing = False
                for col in required:
                    v = row_dict.get(col, None)
                    if v is None or v == "":
                        missing = True
                        break

                if missing:
                    total_skipped_missing += 1
                    if total_skipped_missing <= 5:
                        logging.warning(
                            "    Missing required fields for %s at %s:%d (skipping)",
                            table_name,
                            jsonl_path,
                            line_no,
                        )
                    continue

                batch.append(tuple(row_dict.get(c) for c in insert_columns))

                if len(batch) >= batch_size:
                    flush_batch()

                if (file_processed % log_every) == 0:
                    logging.info(
                        "    Progress %s: %d records processed (insert attempts so far: %d)",
                        table_name,
                        file_processed,
                        total_inserted_attempt,
                    )

        # Flush remainder.
        flush_batch()

        logging.info(
            "  Done file: %s (processed=%d, skipped_missing=%d, bad_json=%d)",
            jsonl_path.name,
            file_processed,
            total_skipped_missing,
            total_bad_json,
        )

    logging.info(
        "Finished %s: processed=%d, inserted_attempt=%d, skipped_missing=%d, bad_json=%d",
        table_name,
        total_processed,
        total_inserted_attempt,
        total_skipped_missing,
        total_bad_json,
    )


def init_db_from_schema(conn: sqlite3.Connection, schema_path: Path) -> None:
    if not schema_path.exists():
        raise FileNotFoundError(f"schema.sql not found: {schema_path}")
    sql = schema_path.read_text(encoding="utf-8")
    conn.executescript(sql)
    conn.commit()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest SAP O2C JSONL into SQLite with batch inserts.")
    parser.add_argument(
        "--dataset-root",
        type=str,
        default=str(Path(__file__).resolve().parent / "sap-o2c-data"),
        help="Root folder containing entity subfolders (sap-o2c-data/...).",
    )
    parser.add_argument(
        "--sqlite-path",
        type=str,
        default=str(Path(__file__).resolve().parent / "o2c.sqlite"),
        help="SQLite database file to create/update.",
    )
    parser.add_argument(
        "--schema-path",
        type=str,
        default=str(Path(__file__).resolve().parent / "schema.sql"),
        help="Path to schema.sql used for --init-db.",
    )
    parser.add_argument("--init-db", action="store_true", help="Recreate tables using schema.sql.")
    parser.add_argument("--dry-run", action="store_true", help="Parse and validate but do not insert.")
    parser.add_argument("--batch-size", type=int, default=2000, help="SQLite batch size for executemany.")
    parser.add_argument("--log-every", type=int, default=50000, help="Log progress every N records per file.")
    parser.add_argument("--log-level", type=str, default="INFO", help="Logging level: DEBUG/INFO/WARNING/ERROR.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    setup_logging(args.log_level)

    dataset_root = Path(args.dataset_root).resolve()
    sqlite_path = Path(args.sqlite_path).resolve()
    schema_path = Path(args.schema_path).resolve()

    if not dataset_root.exists():
        raise FileNotFoundError(f"--dataset-root does not exist: {dataset_root}")

    if args.init_db and sqlite_path.exists():
        sqlite_path.unlink()

    conn = sqlite3.connect(str(sqlite_path))
    try:
        # Speed oriented but safe enough for local ingestion.
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")

        if args.init_db:
            init_db_from_schema(conn, schema_path)

        # If not init-db, assume tables already exist.
        for folder_name, table_name in FOLDER_TO_TABLE.items():
            ingest_one_table(
                conn=conn,
                dataset_root=dataset_root,
                folder_name=folder_name,
                table_name=table_name,
                batch_size=args.batch_size,
                dry_run=args.dry_run,
                log_every=args.log_every,
            )
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    main()

