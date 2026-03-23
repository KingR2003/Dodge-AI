# SAP O2C Context Graph + LLM Query System

This project builds a context graph over SAP-style Order-to-Cash (O2C) data and exposes a conversational query interface that returns only data-backed answers.

The system is designed for reliability first: natural-language questions are mapped to predefined query tools, not arbitrary SQL generation.

## What the system does

- Ingests JSONL files from `sap-o2c-data/` into a normalized SQLite schema
- Builds a graph representation across O2C entities (Sales Orders, Deliveries, Billing Documents, Journal Entries, Customers, Products)
- Visualizes graph nodes and relationships in a React UI
- Accepts natural-language questions in chat
- Uses an LLM to select a predefined query tool and arguments
- Executes parameterized SQL and returns concise, factual responses
- Rejects out-of-domain prompts with a fixed message

---

## Architecture decisions

### Why SQLite

SQLite was chosen as the primary analytical store for this assignment because it provides:

- **Fast local setup and reproducibility**: single-file DB, no infrastructure overhead
- **Strong support for join-heavy workflows**: ideal for O2C document-chain queries
- **Operational simplicity**: easy to package, run, and deploy in lightweight environments
- **Good fit for deterministic tool execution**: predefined SQL templates are transparent and testable

For the current data size and scope, SQLite gives excellent latency with minimal complexity.

### Why a graph layer on top of relational tables

The source data is relational and heterogeneous, but user tasks are relationship-driven ("trace document flow", "find breaks in flow"). A graph layer provides:

- **Entity-centric navigation** in UI (`nodes` + `edges`)
- **Flow explainability** for end-to-end trace questions
- **Natural alignment with business semantics** (order -> delivery -> billing -> journal entry)

Relational storage remains the source of truth; graph payloads are produced from SQL-backed joins.

---

## System architecture

### Backend (`FastAPI`)

- `GET /graph`
  - Returns graph payload: `{ nodes: [{id, type, metadata}], edges: [{source, target, relationship}] }`
  - Supports loading a billing-document-centric subgraph
- `POST /chat`
  - Receives user question
  - Calls LLM for tool selection JSON
  - Runs guardrails (domain + schema validation)
  - Executes one allowlisted query tool
  - Returns answer + optional graph update

### Frontend (`React + react-force-graph-2d`)

- Force-directed graph view
- Node click to focus on one-hop neighborhood (lightweight expansion)
- Node metadata inspection panel
- Chat panel integrated with `/chat`

### Data pipeline

- `ingest_sap_o2c.py` reads JSONL by entity folder
- Maps camelCase JSON keys to snake_case schema columns
- Uses batch `executemany` inserts for performance
- Logs progress and skips malformed/missing-key records safely

---

## Graph modeling approach

The graph is modeled around stable business entities and explicit relationship semantics.

### Node types

- `SalesOrder`
- `Delivery`
- `BillingDocument`
- `JournalEntry`
- `Customer`
- `Product`

### Stable node IDs

- `SalesOrder:{sales_order}`
- `Delivery:{delivery_document}`
- `BillingDocument:{billing_document}`
- `JournalEntry:{company_code}:{fiscal_year}:{accounting_document}`
- `Customer:{customer}`
- `Product:{product}`

### Core edges

- `SalesOrder -> Delivery` (`delivered_as`)
- `Delivery -> BillingDocument` (`billed_as`)
- `BillingDocument -> JournalEntry` (`posted_as`)
- `BillingDocument -> Customer` (`has_customer`)
- `SalesOrder/BillingDocument -> Product` (`has_product`)
- `JournalEntry -> Customer` (`belongs_to_customer`)

### Key implementation detail

Some item identifiers vary in formatting (`"10"` vs `"000010"`). Join logic normalizes these with leading-zero handling to preserve linkage quality.

---

## LLM tool-based query design

The LLM is used for **intent-to-tool routing**, not direct SQL generation.

### Allowlisted tools

1. `top_products_by_billing`
2. `trace_billing_document`
3. `incomplete_sales_orders`

### Execution flow

1. User question -> LLM prompt constrained to JSON output
2. LLM returns `{ "tool": "...", "args": { ... } }`
3. Guardrails validate tool + args
4. Backend executes predefined parameterized SQL
5. Response formatter returns concise data-backed answer

### Why this is production-safer than raw SQL generation

- Removes arbitrary SQL generation risk
- Bounds execution to known, indexed query shapes
- Improves determinism and debuggability
- Reduces hallucination surface by separating planning from execution

---

## Guardrails

Guardrails are implemented in `guardrails.py` and enforced before query execution.

### 1) Domain filter

Heuristic checks reject prompts that are:

- Creative writing (poems, stories, lyrics)
- General knowledge not tied to O2C data
- Missing domain context keywords

### 2) Tool and args validator

- Tool name must be in explicit allowlist
- Arg schema is validated per tool (types, allowed keys, value bounds)
- Invalid structures are rejected

### 3) Fixed rejection behavior

Rejected requests return:

`This system is designed to answer questions related to the provided dataset only.`

---

## Tradeoffs and rationale

### Chosen tradeoffs

- **Tool routing over free-form SQL**
  - Pro: safer and more reliable
  - Con: lower query expressiveness for novel question types

- **SQLite over external OLAP/graph DB**
  - Pro: simple deployment and strong assignment fit
  - Con: limited horizontal scaling and concurrency compared to managed DBs

- **Graph payload generated from SQL joins (not persisted graph DB)**
  - Pro: no duplicated source of truth, simpler data consistency
  - Con: more compute at request time for larger graph traversals

- **Heuristic domain classifier**
  - Pro: lightweight and transparent
  - Con: can be conservative for borderline prompts; can be improved with model-based moderation

### Production evolution path

- Add richer tool catalog and semantic parser confidence scoring
- Introduce query telemetry and regression tests per tool
- Add caching/materialized graph slices for high-traffic traces
- Move to managed DB + async workers for larger datasets
- Add role-aware access control and audit trails

---

## Run locally

### 1) Build SQLite database

```powershell
python "d:\Dodge AI\ingest_sap_o2c.py" --init-db --sqlite-path "d:\Dodge AI\o2c.sqlite"
```

### 2) Install backend dependencies

```powershell
pip install -r "d:\Dodge AI\requirements.txt"
```

### 3) Configure LLM provider (Google Gemini)

This project uses `python-dotenv` to load environment variables from a local `.env` file.

Create `d:\Dodge AI\.env` with:

```text
GEMINI_API_KEY=your_api_key_here
```

Optional:

- `GEMINI_MODEL` (optional; default: `gemini-1.5-flash`)
- `SQLITE_PATH` (optional; defaults to local file)

### 4) Start backend

```powershell
cd "d:\Dodge AI"
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### 5) Start frontend

```powershell
cd "d:\Dodge AI\frontend"
npm install
npm run dev
```

UI runs on `http://localhost:5173`, proxying `/graph` and `/chat` to backend.

