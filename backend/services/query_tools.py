from __future__ import annotations

import sqlite3
from typing import Any, Dict, List, Optional


def _rows_to_dicts(rows: List[sqlite3.Row]) -> List[Dict[str, Any]]:
    return [dict(r) for r in rows]


def top_customers(
    conn: sqlite3.Connection,
    *,
    limit: int,
    company_code: Optional[str] = None,
) -> List[Dict[str, Any]]:
    conn.row_factory = sqlite3.Row
    sql = """
    SELECT
      bdh.sold_to_party AS customer,
      COALESCE(bp.business_partner_full_name, bdh.sold_to_party) AS customer_name,
      COUNT(DISTINCT bdh.billing_document) AS billing_document_count
    FROM billing_document_headers bdh
    LEFT JOIN business_partners bp
      ON bp.customer = bdh.sold_to_party
    WHERE (:company_code IS NULL OR bdh.company_code = :company_code)
    GROUP BY bdh.sold_to_party, COALESCE(bp.business_partner_full_name, bdh.sold_to_party)
    ORDER BY billing_document_count DESC, customer ASC
    LIMIT :limit;
    """
    rows = conn.execute(sql, {"limit": limit, "company_code": company_code}).fetchall()
    return _rows_to_dicts(rows)


def top_products_by_billing(
    conn: sqlite3.Connection,
    *,
    limit: int,
    company_code: Optional[str] = None,
) -> List[Dict[str, Any]]:
    conn.row_factory = sqlite3.Row
    sql = """
    SELECT
      bdi.material AS product,
      COALESCE(pd.product_description, p.product) AS product_name,
      COUNT(DISTINCT bdi.billing_document) AS billing_document_count
    FROM billing_document_items bdi
    JOIN billing_document_headers bdh
      ON bdh.billing_document = bdi.billing_document
    JOIN products p
      ON p.product = bdi.material
    LEFT JOIN product_descriptions pd
      ON pd.product = p.product
     AND pd.language = 'EN'
    WHERE (:company_code IS NULL OR bdh.company_code = :company_code)
    GROUP BY bdi.material, COALESCE(pd.product_description, p.product)
    ORDER BY billing_document_count DESC, product ASC
    LIMIT :limit;
    """
    rows = conn.execute(sql, {"limit": limit, "company_code": company_code}).fetchall()
    return _rows_to_dicts(rows)


def trace_billing_document(
    conn: sqlite3.Connection,
    *,
    billing_document: str,
    include_journal_entry: bool = True,
    include_payments: bool = False,
) -> Dict[str, Any]:
    conn.row_factory = sqlite3.Row

    # 1) Flow (billing → delivery → sales order), plus material/product and customer name.
    flow_sql = """
    SELECT
      bdh.billing_document,
      bdh.billing_document_type,
      bdh.company_code,
      bdh.fiscal_year,
      bdh.accounting_document,
      bdh.sold_to_party AS billing_customer,

      bdi.billing_document_item,
      bdi.material AS product,
      COALESCE(pd.product_description, p.product) AS product_name,
      bdi.billing_quantity,
      bdi.billing_quantity_unit,
      bdi.net_amount AS billing_net_amount,

      bdi.reference_sd_document AS delivery_document,
      bdi.reference_sd_document_item AS delivery_document_item_ref,

      odi.delivery_document_item AS delivery_document_item,
      odi.plant AS delivery_plant,
      odi.storage_location AS delivery_storage_location,

      osi.sales_order AS sales_order,
      osi.sales_order_item AS sales_order_item,
      osi.requested_quantity AS sales_order_item_requested_qty,
      osi.requested_quantity_unit AS sales_order_item_requested_qty_unit,

      soh.creation_date AS sales_order_creation_date,
      soh.overall_delivery_status AS sales_order_overall_delivery_status,
      bp.business_partner_full_name AS customer_name
    FROM billing_document_headers bdh
    JOIN billing_document_items bdi
      ON bdi.billing_document = bdh.billing_document
    JOIN products p
      ON p.product = bdi.material
    LEFT JOIN product_descriptions pd
      ON pd.product = p.product
     AND pd.language = 'EN'

    LEFT JOIN outbound_delivery_items odi
      ON odi.delivery_document = bdi.reference_sd_document
     AND ltrim(odi.delivery_document_item, '0') = ltrim(bdi.reference_sd_document_item, '0')

    LEFT JOIN sales_order_items osi
      ON osi.sales_order = odi.reference_sd_document
     AND ltrim(osi.sales_order_item, '0') = ltrim(odi.reference_sd_document_item, '0')

    LEFT JOIN sales_order_headers soh
      ON soh.sales_order = osi.sales_order

    LEFT JOIN business_partners bp
      ON bp.customer = bdh.sold_to_party

    WHERE bdh.billing_document = :billing_document
    ORDER BY bdi.billing_document_item;
    """
    flow_rows = conn.execute(flow_sql, {"billing_document": billing_document}).fetchall()

    # 2) Journal entries (by FI key from billing header).
    journal_rows: List[Dict[str, Any]] = []
    payment_rows: List[Dict[str, Any]] = []

    if include_journal_entry or include_payments:
        header_sql = """
        SELECT company_code, fiscal_year, accounting_document
        FROM billing_document_headers
        WHERE billing_document = :billing_document
        """
        header = conn.execute(header_sql, {"billing_document": billing_document}).fetchone()
        if header:
            company_code = header["company_code"]
            fiscal_year = header["fiscal_year"]
            accounting_document = header["accounting_document"]

            if include_journal_entry:
                journal_sql = """
                SELECT
                  company_code,
                  fiscal_year,
                  accounting_document,
                  accounting_document_item,
                  gl_account,
                  reference_document,
                  profit_center,
                  transaction_currency,
                  amount_in_transaction_currency,
                  amount_in_company_code_currency,
                  posting_date,
                  document_date,
                  clearing_date,
                  clearing_accounting_document,
                  clearing_doc_fiscal_year
                FROM journal_entry_items_ar
                WHERE company_code = :company_code
                  AND fiscal_year = :fiscal_year
                  AND accounting_document = :accounting_document
                ORDER BY accounting_document_item
                LIMIT 2000;
                """
                jr = conn.execute(
                    journal_sql,
                    {
                        "company_code": company_code,
                        "fiscal_year": fiscal_year,
                        "accounting_document": accounting_document,
                    },
                ).fetchall()
                journal_rows = _rows_to_dicts(jr)

            if include_payments:
                payment_sql = """
                SELECT
                  company_code,
                  fiscal_year,
                  accounting_document,
                  accounting_document_item,
                  clearing_date,
                  clearing_accounting_document,
                  clearing_doc_fiscal_year,
                  amount_in_transaction_currency,
                  transaction_currency,
                  amount_in_company_code_currency,
                  customer,
                  posting_date,
                  document_date,
                  gl_account,
                  profit_center,
                  financial_account_type
                FROM payment_items_ar
                WHERE company_code = :company_code
                  AND fiscal_year = :fiscal_year
                  AND accounting_document = :accounting_document
                ORDER BY accounting_document_item
                LIMIT 2000;
                """
                pr = conn.execute(
                    payment_sql,
                    {
                        "company_code": company_code,
                        "fiscal_year": fiscal_year,
                        "accounting_document": accounting_document,
                    },
                ).fetchall()
                payment_rows = _rows_to_dicts(pr)

    return {
        "flow_rows": _rows_to_dicts(flow_rows),
        "journal_rows": journal_rows,
        "payment_rows": payment_rows,
    }


def incomplete_sales_orders(
    conn: sqlite3.Connection,
    *,
    limit: int,
    company_code: Optional[str] = None,
    mode: str = "both",
) -> List[Dict[str, Any]]:
    """
    Currently implements delivered_not_billed robustly (data is present via reference_sd_document fields).
    billed_without_delivery is returned as empty to avoid guessing without direct mapping in this dataset.
    """
    if mode == "billed_without_delivery":
        return []

    conn.row_factory = sqlite3.Row
    sql = """
    WITH delivered AS (
      SELECT
        odi.reference_sd_document AS sales_order,
        ltrim(odi.reference_sd_document_item, '0') AS sales_order_item_norm,
        odi.delivery_document,
        ltrim(odi.delivery_document_item, '0') AS delivery_document_item_norm
      FROM outbound_delivery_items odi
      WHERE odi.reference_sd_document IS NOT NULL
    ),
    billed AS (
      SELECT
        bdi.reference_sd_document AS delivery_document,
        ltrim(bdi.reference_sd_document_item, '0') AS delivery_document_item_norm,
        bdi.billing_document
      FROM billing_document_items bdi
      WHERE bdi.reference_sd_document IS NOT NULL
    )
    SELECT
      soh.sales_order,
      soh.sold_to_party AS customer,
      COUNT(DISTINCT d.delivery_document) AS delivered_delivery_count,
      SUM(CASE WHEN bi.billing_document IS NULL THEN 1 ELSE 0 END) AS undelivered_or_unbilled_item_rows
    FROM delivered d
    JOIN sales_order_headers soh
      ON soh.sales_order = d.sales_order
    LEFT JOIN billed bi
      ON bi.delivery_document = d.delivery_document
     AND bi.delivery_document_item_norm = d.delivery_document_item_norm
    GROUP BY soh.sales_order, soh.sold_to_party
    HAVING SUM(CASE WHEN bi.billing_document IS NULL THEN 1 ELSE 0 END) > 0
    ORDER BY undelivered_or_unbilled_item_rows DESC, soh.sales_order ASC
    LIMIT :limit;
    """
    # Note: schema has no direct company_code on sales_order_headers in this dataset.
    # We keep company_code arg for the API but currently ignore it safely.
    _ = company_code
    rows = conn.execute(sql, {"limit": limit}).fetchall()
    return _rows_to_dicts(rows)


def payment_trace(
    conn: sqlite3.Connection,
    *,
    billing_document: str,
    include_journal_entry: bool = True,
    include_payments: bool = True,
) -> Dict[str, Any]:
    """
    Trace payments and (optionally) journal entries associated with a billing document.

    Uses FI linkage from billing_document_headers:
      (company_code, fiscal_year, accounting_document) → journal/payment tables.
    """
    conn.row_factory = sqlite3.Row

    header_sql = """
    SELECT company_code, fiscal_year, accounting_document, sold_to_party
    FROM billing_document_headers
    WHERE billing_document = :billing_document
    LIMIT 1;
    """
    header = conn.execute(header_sql, {"billing_document": billing_document}).fetchone()
    if not header:
        return {"payment_rows": [], "journal_rows": []}

    company_code = header["company_code"]
    fiscal_year = header["fiscal_year"]
    accounting_document = header["accounting_document"]

    journal_rows: List[Dict[str, Any]] = []
    payment_rows: List[Dict[str, Any]] = []

    if include_journal_entry:
        journal_sql = """
        SELECT
          company_code,
          fiscal_year,
          accounting_document,
          accounting_document_item,
          gl_account,
          reference_document,
          profit_center,
          transaction_currency,
          amount_in_transaction_currency,
          amount_in_company_code_currency,
          posting_date,
          document_date,
          clearing_date,
          clearing_accounting_document,
          clearing_doc_fiscal_year,
          customer
        FROM journal_entry_items_ar
        WHERE company_code = :company_code
          AND fiscal_year = :fiscal_year
          AND accounting_document = :accounting_document
        ORDER BY accounting_document_item
        LIMIT 2000;
        """
        jr = conn.execute(
            journal_sql,
            {
                "company_code": company_code,
                "fiscal_year": fiscal_year,
                "accounting_document": accounting_document,
            },
        ).fetchall()
        journal_rows = _rows_to_dicts(jr)

    if include_payments:
        payment_sql = """
        SELECT
          company_code,
          fiscal_year,
          accounting_document,
          accounting_document_item,
          clearing_date,
          clearing_accounting_document,
          clearing_doc_fiscal_year,
          amount_in_transaction_currency,
          transaction_currency,
          amount_in_company_code_currency,
          customer,
          posting_date,
          document_date,
          gl_account,
          profit_center,
          financial_account_type
        FROM payment_items_ar
        WHERE company_code = :company_code
          AND fiscal_year = :fiscal_year
          AND accounting_document = :accounting_document
        ORDER BY accounting_document_item
        LIMIT 2000;
        """
        pr = conn.execute(
            payment_sql,
            {
                "company_code": company_code,
                "fiscal_year": fiscal_year,
                "accounting_document": accounting_document,
            },
        ).fetchall()
        payment_rows = _rows_to_dicts(pr)

    return {"payment_rows": payment_rows, "journal_rows": journal_rows}

