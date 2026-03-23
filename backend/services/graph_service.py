from __future__ import annotations

import sqlite3
from typing import Any, Dict, List, Optional, Set, Tuple

from backend.services.query_tools import trace_billing_document


def _node_id(node_type: str, raw_id: str) -> str:
    return f"{node_type}:{raw_id}"


def build_graph_for_billing_document(
    conn: sqlite3.Connection,
    *,
    billing_document: str,
    include_journal_entry: bool = False,
    include_payments: bool = False,
) -> Dict[str, Any]:
    """
    Returns:
      { "nodes": [{id,type,metadata},...], "edges":[{source,target,relationship},...] }

    Graph is assembled from the trace_billing_document flow rows, then optionally
    linked to journal/payment nodes using the FI key found on the billing header.
    """

    result = trace_billing_document(
        conn,
        billing_document=billing_document,
        include_journal_entry=include_journal_entry,
        include_payments=include_payments,
    )

    flow_rows: List[Dict[str, Any]] = result["flow_rows"]
    journal_rows: List[Dict[str, Any]] = result["journal_rows"]
    # payments currently not represented as separate nodes

    nodes_by_id: Dict[str, Dict[str, Any]] = {}
    edges: List[Dict[str, Any]] = []
    edge_keys: Set[Tuple[str, str, str]] = set()

    def add_node(node_id: str, node_type: str, metadata: Dict[str, Any]) -> None:
        if node_id in nodes_by_id:
            nodes_by_id[node_id]["metadata"].update(metadata)
            return
        nodes_by_id[node_id] = {"id": node_id, "type": node_type, "metadata": dict(metadata)}

    def add_edge(source: str, target: str, relationship: str) -> None:
        key = (source, target, relationship)
        if key in edge_keys:
            return
        edge_keys.add(key)
        edges.append({"source": source, "target": target, "relationship": relationship})

    if not flow_rows:
        return {"nodes": [], "edges": []}

    # Document-level nodes
    h = flow_rows[0]
    billing_document_id = _node_id("BillingDocument", str(h["billing_document"]))
    company_code = h["company_code"]
    fiscal_year = h["fiscal_year"]
    accounting_document = h["accounting_document"]

    add_node(
        billing_document_id,
        "BillingDocument",
        {
            "billing_document_type": h.get("billing_document_type"),
            "company_code": company_code,
            "fiscal_year": fiscal_year,
            "accounting_document": accounting_document,
            "billing_net_amount": h.get("billing_net_amount"),
            "billing_quantity": h.get("billing_quantity"),
            "billing_quantity_unit": h.get("billing_quantity_unit"),
        },
    )

    # Customer node
    customer_id_raw = h.get("billing_customer")
    if customer_id_raw is not None:
        customer_node_id = _node_id("Customer", str(customer_id_raw))
        add_node(
            customer_node_id,
            "Customer",
            {"customer_name": h.get("customer_name")},
        )
        add_edge(billing_document_id, customer_node_id, "has_customer")

    # Flow rows
    for r in flow_rows:
        delivery_document = r.get("delivery_document")
        sales_order = r.get("sales_order")
        product = r.get("product")

        if delivery_document:
            delivery_id = _node_id("Delivery", str(delivery_document))
            add_node(
                delivery_id,
                "Delivery",
                {
                    "delivery_document_item": r.get("delivery_document_item"),
                    "plant": r.get("delivery_plant"),
                    "storage_location": r.get("delivery_storage_location"),
                    "reference_so": r.get("sales_order"),
                },
            )
            add_edge(delivery_id, billing_document_id, "billed_as")

        if sales_order:
            so_id = _node_id("SalesOrder", str(sales_order))
            add_node(
                so_id,
                "SalesOrder",
                {
                    "creation_date": r.get("sales_order_creation_date"),
                    "overall_delivery_status": r.get("sales_order_overall_delivery_status"),
                    "requested_quantity": r.get("sales_order_item_requested_qty"),
                },
            )

            if delivery_document:
                delivery_id = _node_id("Delivery", str(delivery_document))
                add_edge(so_id, delivery_id, "delivered_as")

        if product:
            product_id = _node_id("Product", str(product))
            add_node(
                product_id,
                "Product",
                {"product_name": r.get("product_name")},
            )
            add_edge(billing_document_id, product_id, "has_product")
            if sales_order:
                add_edge(_node_id("SalesOrder", str(sales_order)), product_id, "has_product")

    # Optional journal entry
    if include_journal_entry and journal_rows and company_code and fiscal_year and accounting_document:
        journal_id = f"JournalEntry:{company_code}:{fiscal_year}:{accounting_document}"
        # We can add more info to JournalEntry if we want, but these are often high volume.
        add_node(journal_id, "JournalEntry", {"item_count": len(journal_rows)})
        add_edge(billing_document_id, journal_id, "posted_as")
        customer_id_raw = h.get("billing_customer")
        if customer_id_raw:
            add_edge(journal_id, _node_id("Customer", str(customer_id_raw)), "belongs_to_customer")

    return {"nodes": list(nodes_by_id.values()), "edges": edges}

