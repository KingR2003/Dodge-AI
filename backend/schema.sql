-- SAP O2C JSONL → SQLite
-- Column names use snake_case; loaders map from JSON camelCase.
-- IDs and quantities stay TEXT where source JSON uses strings (avoids precision surprises).

PRAGMA foreign_keys = OFF;
-- SQLite cannot add all FKs without load order; relationships are enforced by queries + indexes.

-- ---------------------------------------------------------------------------
-- Sales documents
-- ---------------------------------------------------------------------------

CREATE TABLE sales_order_headers (
  sales_order TEXT NOT NULL PRIMARY KEY,
  sales_order_type TEXT,
  sales_organization TEXT,
  distribution_channel TEXT,
  organization_division TEXT,
  sales_group TEXT,
  sales_office TEXT,
  sold_to_party TEXT,
  creation_date TEXT,
  created_by_user TEXT,
  last_change_date_time TEXT,
  total_net_amount TEXT,
  overall_delivery_status TEXT,
  overall_ord_reltd_billg_status TEXT,
  overall_sd_doc_reference_status TEXT,
  transaction_currency TEXT,
  pricing_date TEXT,
  requested_delivery_date TEXT,
  header_billing_block_reason TEXT,
  delivery_block_reason TEXT,
  incoterms_classification TEXT,
  incoterms_location1 TEXT,
  customer_payment_terms TEXT,
  total_credit_check_status TEXT
);

CREATE TABLE sales_order_items (
  sales_order TEXT NOT NULL,
  sales_order_item TEXT NOT NULL,
  sales_order_item_category TEXT,
  material TEXT,
  requested_quantity TEXT,
  requested_quantity_unit TEXT,
  transaction_currency TEXT,
  net_amount TEXT,
  material_group TEXT,
  production_plant TEXT,
  storage_location TEXT,
  sales_document_rjcn_reason TEXT,
  item_billing_block_reason TEXT,
  PRIMARY KEY (sales_order, sales_order_item)
);

CREATE TABLE sales_order_schedule_lines (
  sales_order TEXT NOT NULL,
  sales_order_item TEXT NOT NULL,
  schedule_line TEXT NOT NULL,
  confirmed_delivery_date TEXT,
  order_quantity_unit TEXT,
  confd_order_qty_by_matl_avail_check TEXT,
  PRIMARY KEY (sales_order, sales_order_item, schedule_line)
);

-- ---------------------------------------------------------------------------
-- Deliveries
-- ---------------------------------------------------------------------------

CREATE TABLE outbound_delivery_headers (
  delivery_document TEXT NOT NULL PRIMARY KEY,
  creation_date TEXT,
  creation_time_json TEXT,
  last_change_date TEXT,
  actual_goods_movement_date TEXT,
  actual_goods_movement_time_json TEXT,
  delivery_block_reason TEXT,
  hdr_general_incompletion_status TEXT,
  header_billing_block_reason TEXT,
  overall_goods_movement_status TEXT,
  overall_picking_status TEXT,
  overall_proof_of_delivery_status TEXT,
  shipping_point TEXT
);

CREATE TABLE outbound_delivery_items (
  delivery_document TEXT NOT NULL,
  delivery_document_item TEXT NOT NULL,
  reference_sd_document TEXT,
  reference_sd_document_item TEXT,
  plant TEXT,
  storage_location TEXT,
  batch TEXT,
  actual_delivery_quantity TEXT,
  delivery_quantity_unit TEXT,
  item_billing_block_reason TEXT,
  last_change_date TEXT,
  PRIMARY KEY (delivery_document, delivery_document_item)
);

-- ---------------------------------------------------------------------------
-- Billing
-- ---------------------------------------------------------------------------

CREATE TABLE billing_document_headers (
  billing_document TEXT NOT NULL PRIMARY KEY,
  billing_document_type TEXT,
  creation_date TEXT,
  creation_time_json TEXT,
  last_change_date_time TEXT,
  billing_document_date TEXT,
  billing_document_is_cancelled INTEGER,
  cancelled_billing_document TEXT,
  total_net_amount TEXT,
  transaction_currency TEXT,
  company_code TEXT,
  fiscal_year TEXT,
  accounting_document TEXT,
  sold_to_party TEXT
);

CREATE TABLE billing_document_items (
  billing_document TEXT NOT NULL,
  billing_document_item TEXT NOT NULL,
  material TEXT,
  billing_quantity TEXT,
  billing_quantity_unit TEXT,
  net_amount TEXT,
  transaction_currency TEXT,
  reference_sd_document TEXT,
  reference_sd_document_item TEXT,
  PRIMARY KEY (billing_document, billing_document_item)
);

CREATE TABLE billing_document_cancellations (
  billing_document TEXT NOT NULL PRIMARY KEY,
  billing_document_type TEXT,
  creation_date TEXT,
  creation_time_json TEXT,
  last_change_date_time TEXT,
  billing_document_date TEXT,
  billing_document_is_cancelled INTEGER,
  cancelled_billing_document TEXT,
  total_net_amount TEXT,
  transaction_currency TEXT,
  company_code TEXT,
  fiscal_year TEXT,
  accounting_document TEXT,
  sold_to_party TEXT
);

-- ---------------------------------------------------------------------------
-- Finance: journal (AR) & payments
-- ---------------------------------------------------------------------------

CREATE TABLE journal_entry_items_ar (
  company_code TEXT NOT NULL,
  fiscal_year TEXT NOT NULL,
  accounting_document TEXT NOT NULL,
  accounting_document_item TEXT NOT NULL,
  gl_account TEXT,
  reference_document TEXT,
  cost_center TEXT,
  profit_center TEXT,
  transaction_currency TEXT,
  amount_in_transaction_currency TEXT,
  company_code_currency TEXT,
  amount_in_company_code_currency TEXT,
  posting_date TEXT,
  document_date TEXT,
  accounting_document_type TEXT,
  assignment_reference TEXT,
  last_change_date_time TEXT,
  customer TEXT,
  financial_account_type TEXT,
  clearing_date TEXT,
  clearing_accounting_document TEXT,
  clearing_doc_fiscal_year TEXT,
  PRIMARY KEY (company_code, fiscal_year, accounting_document, accounting_document_item)
);

CREATE TABLE payment_items_ar (
  company_code TEXT NOT NULL,
  fiscal_year TEXT NOT NULL,
  accounting_document TEXT NOT NULL,
  accounting_document_item TEXT NOT NULL,
  clearing_date TEXT,
  clearing_accounting_document TEXT,
  clearing_doc_fiscal_year TEXT,
  amount_in_transaction_currency TEXT,
  transaction_currency TEXT,
  amount_in_company_code_currency TEXT,
  company_code_currency TEXT,
  customer TEXT,
  invoice_reference TEXT,
  invoice_reference_fiscal_year TEXT,
  sales_document TEXT,
  sales_document_item TEXT,
  posting_date TEXT,
  document_date TEXT,
  assignment_reference TEXT,
  gl_account TEXT,
  financial_account_type TEXT,
  profit_center TEXT,
  cost_center TEXT,
  PRIMARY KEY (company_code, fiscal_year, accounting_document, accounting_document_item)
);

-- ---------------------------------------------------------------------------
-- Products & logistics masters
-- ---------------------------------------------------------------------------

CREATE TABLE products (
  product TEXT NOT NULL PRIMARY KEY,
  product_type TEXT,
  cross_plant_status TEXT,
  cross_plant_status_validity_date TEXT,
  creation_date TEXT,
  created_by_user TEXT,
  last_change_date TEXT,
  last_change_date_time TEXT,
  is_marked_for_deletion INTEGER,
  product_old_id TEXT,
  gross_weight TEXT,
  weight_unit TEXT,
  net_weight TEXT,
  product_group TEXT,
  base_unit TEXT,
  division TEXT,
  industry_sector TEXT
);

CREATE TABLE product_descriptions (
  product TEXT NOT NULL,
  language TEXT NOT NULL,
  product_description TEXT,
  PRIMARY KEY (product, language)
);

CREATE TABLE product_plants (
  product TEXT NOT NULL,
  plant TEXT NOT NULL,
  country_of_origin TEXT,
  region_of_origin TEXT,
  production_invtry_managed_loc TEXT,
  availability_check_type TEXT,
  fiscal_year_variant TEXT,
  profit_center TEXT,
  mrp_type TEXT,
  PRIMARY KEY (product, plant)
);

CREATE TABLE product_storage_locations (
  product TEXT NOT NULL,
  plant TEXT NOT NULL,
  storage_location TEXT NOT NULL,
  physical_inventory_block_ind TEXT,
  date_of_last_posted_cnt_un_rstrcd_stk TEXT,
  PRIMARY KEY (product, plant, storage_location)
);

CREATE TABLE plants (
  plant TEXT NOT NULL PRIMARY KEY,
  plant_name TEXT,
  valuation_area TEXT,
  plant_customer TEXT,
  plant_supplier TEXT,
  factory_calendar TEXT,
  default_purchasing_organization TEXT,
  sales_organization TEXT,
  address_id TEXT,
  plant_category TEXT,
  distribution_channel TEXT,
  division TEXT,
  language TEXT,
  is_marked_for_archiving INTEGER
);

-- ---------------------------------------------------------------------------
-- Business partners & customers
-- ---------------------------------------------------------------------------

CREATE TABLE business_partners (
  business_partner TEXT NOT NULL PRIMARY KEY,
  customer TEXT,
  business_partner_category TEXT,
  business_partner_full_name TEXT,
  business_partner_grouping TEXT,
  business_partner_name TEXT,
  correspondence_language TEXT,
  created_by_user TEXT,
  creation_date TEXT,
  creation_time_json TEXT,
  first_name TEXT,
  form_of_address TEXT,
  industry TEXT,
  last_change_date TEXT,
  last_name TEXT,
  organization_bp_name1 TEXT,
  organization_bp_name2 TEXT,
  business_partner_is_blocked INTEGER,
  is_marked_for_archiving INTEGER
);

CREATE TABLE business_partner_addresses (
  business_partner TEXT NOT NULL,
  address_id TEXT NOT NULL,
  validity_start_date TEXT,
  validity_end_date TEXT,
  address_uuid TEXT,
  address_time_zone TEXT,
  city_name TEXT,
  country TEXT,
  po_box TEXT,
  po_box_deviating_city_name TEXT,
  po_box_deviating_country TEXT,
  po_box_deviating_region TEXT,
  po_box_is_without_number INTEGER,
  po_box_lobby_name TEXT,
  po_box_postal_code TEXT,
  postal_code TEXT,
  region TEXT,
  street_name TEXT,
  tax_jurisdiction TEXT,
  transport_zone TEXT,
  PRIMARY KEY (business_partner, address_id)
);

CREATE TABLE customer_sales_area_assignments (
  customer TEXT NOT NULL,
  sales_organization TEXT NOT NULL,
  distribution_channel TEXT NOT NULL,
  division TEXT NOT NULL,
  billing_is_blocked_for_customer TEXT,
  complete_delivery_is_defined INTEGER,
  credit_control_area TEXT,
  currency TEXT,
  customer_payment_terms TEXT,
  delivery_priority TEXT,
  incoterms_classification TEXT,
  incoterms_location1 TEXT,
  sales_group TEXT,
  sales_office TEXT,
  shipping_condition TEXT,
  sls_unlmtd_ovrdeliv_is_allwd INTEGER,
  supplying_plant TEXT,
  sales_district TEXT,
  exchange_rate_type TEXT,
  PRIMARY KEY (customer, sales_organization, distribution_channel, division)
);

CREATE TABLE customer_company_assignments (
  customer TEXT NOT NULL,
  company_code TEXT NOT NULL,
  accounting_clerk TEXT,
  accounting_clerk_fax_number TEXT,
  accounting_clerk_internet_address TEXT,
  accounting_clerk_phone_number TEXT,
  alternative_payer_account TEXT,
  payment_blocking_reason TEXT,
  payment_methods_list TEXT,
  payment_terms TEXT,
  reconciliation_account TEXT,
  deletion_indicator INTEGER,
  customer_account_group TEXT,
  PRIMARY KEY (customer, company_code)
);

-- ---------------------------------------------------------------------------
-- Indexes: join-heavy O2C paths + graph expansion
-- ---------------------------------------------------------------------------

-- Sales order → items → material / plant
CREATE INDEX idx_sales_order_items_order ON sales_order_items (sales_order);
CREATE INDEX idx_sales_order_items_material ON sales_order_items (material);
CREATE INDEX idx_sales_order_items_plant ON sales_order_items (production_plant);
CREATE INDEX idx_schedule_lines_order ON sales_order_schedule_lines (sales_order);
CREATE INDEX idx_schedule_lines_order_item ON sales_order_schedule_lines (sales_order, sales_order_item);

CREATE INDEX idx_sales_order_headers_sold_to ON sales_order_headers (sold_to_party);

-- Delivery ↔ sales order (item reference)
CREATE INDEX idx_outbound_delivery_items_doc ON outbound_delivery_items (delivery_document);
CREATE INDEX idx_outbound_delivery_items_ref_so
  ON outbound_delivery_items (reference_sd_document, reference_sd_document_item);
CREATE INDEX idx_outbound_delivery_items_plant ON outbound_delivery_items (plant);

CREATE INDEX idx_outbound_delivery_headers_ship_pt ON outbound_delivery_headers (shipping_point);

-- Billing ↔ delivery / material / customer flow
CREATE INDEX idx_billing_headers_accounting
  ON billing_document_headers (company_code, fiscal_year, accounting_document);
CREATE INDEX idx_billing_headers_sold_to ON billing_document_headers (sold_to_party);

CREATE INDEX idx_billing_items_doc ON billing_document_items (billing_document);
CREATE INDEX idx_billing_items_material ON billing_document_items (material);
CREATE INDEX idx_billing_items_ref_delivery
  ON billing_document_items (reference_sd_document, reference_sd_document_item);

-- Journal ↔ billing (reference_document = billing document)
CREATE INDEX idx_journal_ar_ref_billing ON journal_entry_items_ar (reference_document);
CREATE INDEX idx_journal_ar_customer ON journal_entry_items_ar (customer);
CREATE INDEX idx_journal_ar_doc ON journal_entry_items_ar (company_code, fiscal_year, accounting_document);
CREATE INDEX idx_journal_ar_clearing ON journal_entry_items_ar (clearing_accounting_document, clearing_doc_fiscal_year);

-- Payments ↔ accounting document / customer
CREATE INDEX idx_payments_ar_doc ON payment_items_ar (company_code, fiscal_year, accounting_document);
CREATE INDEX idx_payments_ar_customer ON payment_items_ar (customer);
CREATE INDEX idx_payments_ar_clearing ON payment_items_ar (clearing_accounting_document, clearing_doc_fiscal_year);
CREATE INDEX idx_payments_ar_sales_doc ON payment_items_ar (sales_document, sales_document_item);

-- Product graph
CREATE INDEX idx_product_descriptions_product ON product_descriptions (product);
CREATE INDEX idx_product_plants_plant ON product_plants (plant);
CREATE INDEX idx_product_storage_plant ON product_storage_locations (plant);
