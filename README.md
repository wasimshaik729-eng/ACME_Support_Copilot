# Acme Support Copilot

Acme Support Copilot is a FastAPI backend for customer support operations at Acme, a fictional Indian online store. It exposes endpoints for looking up customers and orders, moving orders through their lifecycle, and reviewing support tickets for agents and downstream AI tooling.

## Setup

Use Python 3.12. Only if `.venv312` does not exist, create it once:

```powershell
py -3.12 -m venv .venv312
```

Install the requirements into that environment:

```powershell
.\.venv312\Scripts\python.exe -m pip install -r requirements.txt -r requirements-ui.txt
```

## Run the app

```powershell
.\.venv312\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8002
```

Then open http://127.0.0.1:8002/docs to browse the API docs. If port 8002 is unavailable, choose another port and use it in `ACME_API_URL` for the UI.

## Deploy to Render with Docker

Push this repository to GitHub, then in Render choose **New → Blueprint**, select the repository, and apply `render.yaml`. The Blueprint creates separate Docker web services for the FastAPI API and Streamlit UI. After deployment, open the URL for the `acme-support-ui` service. The UI service reads the API's public URL from the Blueprint service reference.

The Blueprint uses free instances for a demo. The API stores data in SQLite, and the free container filesystem is ephemeral; tickets and status changes can reset when Render restarts or redeploys the API. Do not use this setup for durable or production customer data. A persistent database and appropriate access controls are required for that.

To enable hosted model drafting, set `ACME_LLM_API_KEY` and `ACME_AGENT_ALLOW_EXTERNAL_LLM=true` on the UI service in Render's environment settings. The secret is not stored in `render.yaml`; the Agent Desk still requires explicit per-investigation consent before sending ticket data to the provider.

## Test the app

```bash
.\.venv312\Scripts\python.exe -m pytest -q
.\.venv312\Scripts\python.exe -m ruff check .
```

## Seed data

The project relies on `data/seed.json` for the initial seed data set. 
It should be treated as read-only and never edited by the application or tests.

## Endpoints

| Use case | Method | Path |
| --- | --- | --- |
| Health check | GET | /health |
| List customers | GET | /customers |
| Get customer | GET | /customers/{customer_id} |
| Customer orders | GET | /customers/{customer_id}/orders |
| List orders | GET | /orders |
| Search orders | GET | /orders/search |
| Get order | GET | /orders/{order_id} |
| Update order status | PATCH | /orders/{order_id}/status |
| Create ticket | POST | /tickets |
| List tickets | GET | /tickets |
| Get ticket | GET | /tickets/{ticket_id} |
| Update ticket status | PATCH | /tickets/{ticket_id}/status |

## Pagination response shape

```json
{
  "items": [],
  "total": 0,
  "page": 1,
  "page_size": 20
}
```

## Streamlit support workspace

Run the API and UI in separate terminals. The UI reads and writes data through the FastAPI backend.

```powershell
.\.venv312\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8002
```

```powershell
$env:ACME_API_URL = "http://127.0.0.1:8002"
.\.venv312\Scripts\python.exe -m streamlit run streamlit_app.py
```

Open http://localhost:8501. The backend defaults to `http://127.0.0.1:8000`; set `ACME_API_URL` or change the Backend URL field in the sidebar when the API runs elsewhere.

The **Agent desk** runs an investigation graph built with LangGraph. It reads ticket, customer, and order records through fixed allowlisted tools, retrieves relevant markdown policy passages locally using lexical ranking, analyzes the order state, and prepares a reply draft and cited internal case brief. Ticket text is treated as untrusted input. Retrieval uses the local `knowledge_base/` files; no embedding service or vector database is required.

By default, reply drafts use local policy-grounded templates. An optional OpenAI-compatible model can use read-only API tools when `ACME_LLM_API_KEY` and `ACME_AGENT_ALLOW_EXTERNAL_LLM=true` are set; `ACME_LLM_BASE_URL` and `ACME_LLM_MODEL` are optional. The Agent Desk also requires a per-investigation checkbox before sending ticket/customer/order data to that provider. Use only a provider approved for that data. The key is read from the process environment and is never displayed.

Model tools are read-only (`read_ticket`, `read_customer`, `read_order`, `read_customer_orders`, and `retrieve_support_policy`). The model cannot invoke write operations. Ticket pickup, resolution, and recording a refund status pause at a LangGraph approval interrupt and require a human decision. Resolution additionally requires confirmation that staff sent the reply; recording a refund additionally requires staff confirmation from the finance system. This demo cannot send replies or move money, and a `refunded` workflow status is not proof of a transfer. Pending approvals use an in-memory checkpointer and are lost if the Streamlit process restarts. Generated case briefs are labeled synthetic and are not receipts or transaction evidence.

## Project layout

```text
app/
  __init__.py
  db.py
  main.py
  models.py
  schemas.py
  seed.py
  support_agent.py
  agent_graph.py
  api/
    __init__.py
    customers.py
    orders.py
    pagination.py
    tickets.py
scripts/
  generate_seed.py
specs/
  acme_backend_spec.md
tests/
  conftest.py
  test_customers.py
  test_health.py
  test_order_search.py
  test_orders.py
  test_support_agent.py
  test_agent_graph.py
  test_tickets.py
data/
  seed.json
knowledge_base/
  document_safety.md
  refunds.md
streamlit_app.py
requirements-ui.txt
Dockerfile
render.yaml
.dockerignore
.gitignore
README.md
requirements.txt
```
##Wasim