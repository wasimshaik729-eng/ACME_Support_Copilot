# Acme Support Copilot

Acme Support Copilot is a FastAPI backend for customer support operations at Acme, a fictional Indian online store. It exposes endpoints for looking up customers and orders, moving orders through their lifecycle, and reviewing support tickets for agents and downstream AI tooling.

## Run the app

```bash
py -3.12 -m uvicorn app.main:app --reload
```

Then open http://127.0.0.1:8000/docs to browse the API docs.

## Test the app

```bash
py -3.12 -m pytest -q
py -3.12 -m ruff check .
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
py -3.12 -m uvicorn app.main:app --reload
```

```powershell
.\.venv312\Scripts\python.exe -m streamlit run streamlit_app.py
```

Open http://localhost:8501. The backend defaults to `http://127.0.0.1:8000`; set `ACME_API_URL` or change the Backend URL field in the sidebar when the API runs elsewhere.

The **Agent desk** retrieves passages from `knowledge_base/`, analyzes a ticket and linked order, drafts a response, and prepares a synthetic internal case brief with policy citations. It requires staff approval for workflow changes. This demo does not send replies or process payments; changing an order to `refunded` records workflow state only and is not proof of transfer. Generated briefs are explicitly watermarked and must not be used as receipts or transaction evidence.

By default, reply drafts are generated locally from policy-grounded templates. An optional OpenAI-compatible chat-completions endpoint can be enabled with `ACME_LLM_API_KEY`, `ACME_AGENT_ALLOW_EXTERNAL_LLM=true`, and optional `ACME_LLM_BASE_URL` / `ACME_LLM_MODEL`. Ticket text may contain personal information, so enable external processing only with an approved provider and appropriate authorization. The key is read from the process environment and is never displayed by the app.

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
  test_tickets.py
data/
  seed.json
knowledge_base/
  document_safety.md
  refunds.md
tests/
  test_support_agent.py
README.md
requirements.txt
```
##Wasim