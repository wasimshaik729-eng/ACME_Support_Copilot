# Build the Acme Support Copilot backend with GitHub Copilot

You will build the backend that the rest of the course grows on: customers, orders and support
tickets for **Acme**, a fictional Indian online store. GitHub Copilot (Agent mode) writes the code;
you review every diff, run the tests, and decide when a phase is done.

## Before you start

1. VS Code with the **GitHub Copilot** and **GitHub Copilot Chat** extensions, signed in.
2. Course environment activated: `source .venv/bin/activate` (Python 3.12, FastAPI, SQLAlchemy 2,
   Pydantic v2, pytest, ruff are already in `requirements.txt`).
3. Make an empty folder and open it in VS Code: `my_acme_support_copilot/`.
4. Copy two files from the course repo into it — **do not let Copilot write these**, everyone must
   have identical data:
   - `Section_04_AI_Coding_Tools/acme_support_copilot/scripts/generate_seed.py` → `scripts/generate_seed.py`
   - `Section_04_AI_Coding_Tools/acme_support_copilot/data/seed.json` → `data/seed.json`
5. Open Copilot Chat (`Ctrl+Alt+I` / `Cmd+Ctrl+I`), switch the mode dropdown to **Agent**, and pick
   the strongest model you have.

## How to use these prompts

- Paste **Phase 0** first. It saves the full spec into the repo so every later prompt can point at
  it with `#file:` — Copilot forgets chat history, it does not forget files.
- Then paste **one phase at a time**. After each phase: read the diff, click *Keep* only for changes
  you understand, run `pytest -q` and `ruff check .` yourself, and commit.
- If a phase goes wrong, tell Copilot what failed (paste the error) rather than starting over.
- Start a **new chat** for each phase to keep the context small.

---

## Phase 0 — Save the spec and the project rules

Paste this whole block:

````text
You are helping me build "Acme Support Copilot", a FastAPI backend for the customer-support team of
Acme, a fictional Indian online store. Do NOT write application code yet. In this step, create
exactly two files with the content below, then stop and list what you created.

FILE 1: .github/copilot-instructions.md

# Copilot instructions — Acme Support Copilot
- Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2 (typed `Mapped[...]` style), SQLite, pytest, ruff
- The full spec lives in specs/acme_backend_spec.md — follow it exactly; ask me if it is unclear
- Every new endpoint needs a Pydantic model in app/schemas.py and tests in tests/
- Routes take the database as `db: DbSession` (from app/db.py); list endpoints use `paginate()`
- Return Pydantic/ORM objects via `response_model`; raise `HTTPException` with the status codes in the spec
- No new dependencies beyond requirements.txt
- Never edit data/seed.json or scripts/generate_seed.py; never read .env or print secrets
- Run `ruff check .`, `ruff format .` and `pytest -q` before you say you are finished
- Keep code small and readable: short module docstrings, comments only where the "why" is not obvious

FILE 2: specs/acme_backend_spec.md

# Acme Support Copilot — backend spec

## 1. Who uses it and why
Acme sells kurtas, sarees, pressure cookers, smartphones, cricket bats, JEE workbooks and more across
India. Prices are in rupees (₹). Customers pay by UPI, Card, Cash on Delivery, Net Banking or Wallet,
and contact support by email, chat, WhatsApp or phone. Support agents use this API to look up
customers and orders, move orders through their lifecycle, and work the ticket queue. Later in the
course an AI copilot will call these same endpoints, so the contract must be exact and predictable.

## 2. Business use cases (each must be possible through the API)
UC1  Health check — ops can confirm the service is up.
UC2  Browse customers — list all customers, optionally only those in one city, paginated.
UC3  Look up one customer by id.
UC4  See a customer's order history — every order of that customer, newest first.
UC5  Browse all orders — paginated, newest first.
UC6  Search orders — combine filters: status, customer_id, date range (inclusive), paginated, newest
     first. Example question it must answer: "show me all refunded orders of customer 12 from March".
UC7  Look up one order by its id, e.g. "A-1042".
UC8  Move an order through its lifecycle — only forward, one step at a time:
     placed → shipped → delivered → returned → refunded. Any other move is rejected.
UC9  Raise a support ticket for a customer, optionally about one of THAT customer's orders.
UC10 Work the ticket queue — list tickets filtered by status, priority and/or customer, newest first,
     paginated.
UC11 Look up one ticket by id.
UC12 Change a ticket's status (open, in_progress, resolved, closed) — any change is allowed EXCEPT
     once a ticket is closed it can never change again.

## 3. Database (SQLite file `acme.db` in the project root, SQLAlchemy 2 ORM)

### customers
| column     | type          | rules                          |
|------------|---------------|--------------------------------|
| id         | Integer       | primary key                    |
| name       | String(100)   | required                       |
| email      | String(200)   | required, unique               |
| phone      | String(20)    | required, e.g. "+91 9xxxxxxxxx"|
| city       | String(60)    | required, indexed              |
| state      | String(60)    | required                       |
| created_at | DateTime      | required                       |
Relationship: one customer has many orders.

### orders
| column         | type        | rules                                                    |
|----------------|-------------|----------------------------------------------------------|
| id             | String(20)  | primary key, format "A-<number>" (seed: A-1001…A-2000)   |
| customer_id    | Integer     | FK → customers.id, indexed                               |
| product        | String(100) | required                                                 |
| category       | String(40)  | fashion, home_kitchen, electronics, accessories, sports, books, beauty |
| quantity       | Integer     | required                                                 |
| amount_inr     | Float       | required, total in rupees                                |
| payment_method | String(30)  | UPI, Card, Cash on Delivery, Net Banking, Wallet         |
| status         | String(20)  | placed, shipped, delivered, returned, refunded; indexed  |
| created_at     | DateTime    | required, indexed                                        |
Relationship: each order belongs to one customer.

### tickets
| column      | type        | rules                                                 |
|-------------|-------------|-------------------------------------------------------|
| id          | Integer     | primary key, autoincrement                            |
| customer_id | Integer     | FK → customers.id, indexed                            |
| order_id    | String(20)  | FK → orders.id, nullable                              |
| subject     | String(200) | required                                              |
| message     | Text        | required                                              |
| channel     | String(20)  | email, chat, whatsapp, phone                          |
| priority    | String(10)  | low, medium, high; indexed                            |
| status      | String(20)  | open, in_progress, resolved, closed; indexed          |
| created_at  | DateTime    | required, set by the server on create                 |

Keep the allowed values as tuples in app/models.py (ORDER_STATUSES, TICKET_STATUSES,
TICKET_PRIORITIES) and as `Literal` types in app/schemas.py (OrderStatus, TicketStatus, Priority,
Channel) so FastAPI returns 422 for anything else.

### Seed data
data/seed.json (already provided, never edit) has keys "customers" (200), "orders" (1,000) and
"tickets" (300). Dates are ISO strings like "2026-03-14T10:22:00". On app startup (FastAPI lifespan):
create all tables, and if the customers table is empty load customers, then orders, then tickets
(flush between them so foreign keys exist), converting created_at to datetime. If data already
exists, do nothing. Put this in app/seed.py as `load_seed(db, seed_file=SEED_FILE) -> bool`
(True if it loaded data).

## 4. API contract

### Pagination (every list endpoint marked "paginated")
Query params: page (int ≥ 1, default 1), page_size (int 1–100, default 20). Out of range → 422.
Response: {"items": [...], "total": <int>, "page": <int>, "page_size": <int>}.
Implement once in app/api/pagination.py: `PageParam`, `PageSizeParam` (Annotated Query types) and
`paginate(db, stmt, page, page_size) -> dict` that counts the full filtered query and returns the
slice. Use a generic `Page[T]` Pydantic model as the response_model.

### Endpoints
| UC  | Method | Path                       | Success | Errors |
|-----|--------|----------------------------|---------|--------|
| 1   | GET    | /health                    | 200 {"status": "ok"} | — |
| 2   | GET    | /customers?city=&page=&page_size= | 200 Page[CustomerOut], ordered by id | 422 bad paging |
| 3   | GET    | /customers/{customer_id}   | 200 CustomerOut | 404 "Customer not found" |
| 4   | GET    | /customers/{customer_id}/orders | 200 list[OrderOut], newest first (not paginated) | 404 "Customer not found" |
| 5   | GET    | /orders                    | 200 Page[OrderOut], created_at desc then id | 422 bad paging |
| 6   | GET    | /orders/search?status=&customer_id=&date_from=&date_to=&page=&page_size= | 200 Page[OrderOut], newest first | 422 invalid status/date/paging; 422 "date_from must be on or before date_to" |
| 7   | GET    | /orders/{order_id}         | 200 OrderOut | 404 "Order not found" |
| 8   | PATCH  | /orders/{order_id}/status  body {"status": ...} | 200 OrderOut (updated) | 404 "Order not found"; 409 "Cannot change status from '<old>' to '<new>'"; 422 unknown status |
| 9   | POST   | /tickets  body TicketCreate | 201 TicketOut with status "open" | 404 "Customer not found"; 404 "Order not found for this customer" (order missing OR belongs to someone else); 422 validation |
| 10  | GET    | /tickets?status=&priority=&customer_id=&page=&page_size= | 200 Page[TicketOut], created_at desc then id | 422 invalid filter/paging |
| 11  | GET    | /tickets/{ticket_id}       | 200 TicketOut | 404 "Ticket not found" |
| 12  | PATCH  | /tickets/{ticket_id}/status body {"status": ...} | 200 TicketOut (updated) | 404 "Ticket not found"; 409 "Closed tickets cannot be reopened"; 422 unknown status |

Rules that are easy to get wrong:
- /orders/search must be declared BEFORE /orders/{order_id}, or "search" is treated as an order id.
- date_from/date_to are dates (YYYY-MM-DD) and inclusive: date_from matches from 00:00:00,
  date_to matches up to 23:59:59.999999 of that day.
- Order transitions are a dict ALLOWED_TRANSITIONS in app/api/orders.py:
  placed→{shipped}, shipped→{delivered}, delivered→{returned}, returned→{refunded}, refunded→{}.
  Same-status updates (e.g. placed→placed) and skipping steps are 409.
- A closed ticket rejects every status change with 409, including closed→closed.

### Schemas (app/schemas.py)
- CustomerOut: id, name, email, phone, city, state, created_at
- OrderOut: id, customer_id, product, category, quantity, amount_inr, payment_method, status, created_at
- OrderStatusUpdate: status (OrderStatus)
- TicketCreate: customer_id (int), order_id (str | None = None), subject (3–200 chars),
  message (5–5000 chars), channel (Channel, default "email"), priority (Priority, default "medium")
- TicketOut: id, customer_id, order_id, subject, message, channel, priority, status, created_at
- TicketStatusUpdate: status (TicketStatus)
- Page[T]: items, total, page, page_size
All *Out models use `model_config = ConfigDict(from_attributes=True)`.

## 5. Project layout
app/__init__.py
app/main.py          FastAPI app (title "Acme Support Copilot", version "0.1.0"), lifespan loads seed, /health, includes routers
app/db.py            engine for sqlite:///<project>/acme.db (check_same_thread=False), SessionLocal
                     (autoflush=False, expire_on_commit=False), Base, get_db(), DbSession = Annotated[Session, Depends(get_db)]
app/models.py        Customer, Order, Ticket + allowed-value tuples
app/schemas.py       all Pydantic models above
app/seed.py          load_seed()
app/api/__init__.py
app/api/pagination.py
app/api/customers.py router prefix /customers, tag customers
app/api/orders.py    router prefix /orders, tag orders
app/api/tickets.py   router prefix /tickets, tag tickets
tests/conftest.py    fixtures (below)
tests/test_health.py, test_customers.py, test_orders.py, test_order_search.py, test_tickets.py
data/seed.json, scripts/generate_seed.py   (provided — never edit)
README.md

## 6. Testing rules
- tests/conftest.py `client` fixture: a fresh in-memory SQLite engine per test
  (`sqlite://`, check_same_thread=False, poolclass=StaticPool), create tables, run load_seed on it,
  override get_db via app.dependency_overrides, yield `TestClient(app)` (NOT as a context manager,
  so the real acme.db startup does not run), then clear the overrides.
- A session-scoped `seed` fixture returns the parsed seed.json so tests compute expected values
  from the data instead of hard-coding them.
- Every use case has at least one happy-path test and one test per error code it can return.
- Tests never touch acme.db and never depend on test order.

## 7. Definition of done
`uvicorn app.main:app --reload` starts, http://127.0.0.1:8000/docs shows all 12 endpoints grouped by
tag, `pytest -q` passes (aim for 30+ tests), `ruff check .` is clean.
````

---

## Phase 1 — Database, models and seed loading

```text
Read #file:specs/acme_backend_spec.md and #file:.github/copilot-instructions.md.

Implement sections 3 and 5 for the data layer only: app/__init__.py, app/db.py, app/models.py,
app/seed.py, and app/main.py with the lifespan seed loading and GET /health (UC1). No other routes yet.

Then write tests/conftest.py exactly as section 6 describes, plus tests/test_health.py, plus a test
that load_seed loads 200 customers, 1,000 orders and 300 tickets into an empty database and returns
False when called a second time.

Run ruff and pytest, fix any failures, and finish with a short summary of the tables you created.
```

**Check yourself:** `uvicorn app.main:app --reload`, then `sqlite3 acme.db "select count(*) from orders;"` → `1000`.

---

## Phase 2 — Schemas, pagination and customers

```text
Read #file:specs/acme_backend_spec.md.

1. Create app/schemas.py with every schema in section 4 (including the generic Page[T]).
2. Create app/api/pagination.py (PageParam, PageSizeParam, paginate) as section 4 describes.
3. Create app/api/customers.py for UC2, UC3 and UC4 and register the router in app/main.py.
4. Write tests/test_customers.py covering: default paging shape and total=200, page_size cap
   (101 → 422, 0 → 422, page 0 → 422), city filter (compute the expected count from the seed fixture),
   get one customer, unknown customer → 404, customer orders newest-first and all belonging to that
   customer, orders of unknown customer → 404.

Run ruff and pytest; fix until green.
```

---

## Phase 3 — Orders and the order lifecycle

```text
Read #file:specs/acme_backend_spec.md.

Create app/api/orders.py for UC5, UC7 and UC8 (not search yet) and register it. Use the
ALLOWED_TRANSITIONS dict from the spec.

Write tests/test_orders.py covering: list is paginated and newest first; get "A-1001"; unknown order
→ 404; every valid forward transition succeeds and is persisted (GET it again); skipping a step
(placed → delivered) → 409 with the exact message; moving backwards → 409; same status → 409;
refunded → anything → 409; unknown status value → 422; unknown order → 404.
Pick orders for each case from the seed fixture by their current status, don't hard-code ids.

Run ruff and pytest; fix until green.
```

---

## Phase 4 — Order search

```text
Read #file:specs/acme_backend_spec.md.

Add GET /orders/search (UC6) to app/api/orders.py. It must be declared before /orders/{order_id}.

Write tests/test_order_search.py covering: no filters returns total 1000; each filter alone
(status, customer_id, date_from, date_to) matches a count computed from the seed fixture; all filters
combined; date_to is inclusive of the whole day; date_from > date_to → 422; invalid status → 422;
malformed date → 422; results are newest first; last page and a page past the end (empty items, same
total); GET /orders/A-1001 still works.

Run ruff and pytest; fix until green.
```

---

## Phase 5 — Support tickets

```text
Read #file:specs/acme_backend_spec.md.

Create app/api/tickets.py for UC9, UC10, UC11 and UC12 and register it.

Write tests/test_tickets.py covering:
- create a ticket without an order → 201, status "open", defaults channel "email" and priority "medium"
- create with one of the customer's own orders → 201
- unknown customer → 404 "Customer not found"
- unknown order → 404, and an order that belongs to a DIFFERENT customer → 404 "Order not found for this customer"
- subject too short, message too short, invalid channel, invalid priority → 422
- the new ticket appears first in GET /tickets?customer_id=…
- filters status, priority, customer_id each match counts computed from the seed; combined filters work
- get one ticket; unknown ticket → 404
- status change open → in_progress → resolved → closed succeeds
- any change on a closed ticket (including closed → closed) → 409 "Closed tickets cannot be reopened"
- unknown status → 422; unknown ticket → 404

Run ruff and pytest; fix until green.
```

---

## Phase 6 — Review, README and polish

```text
Read #file:specs/acme_backend_spec.md, then review the whole project against it like a strict senior
engineer. Report, before changing anything:
1. Any use case UC1–UC12 that is missing or behaves differently from the spec (status codes, error
   messages, ordering, defaults).
2. Any database column, type, index, FK or unique constraint that differs from section 3.
3. Any endpoint without a test for each of its error codes.
4. Bugs, N+1 queries, duplicated code, or anything that ignores .github/copilot-instructions.md.

Then fix what you found, and write README.md with: one-paragraph intro, how to run (uvicorn, /docs),
how to test (pytest -q, ruff check .), the data section (seed.json, never edit), the endpoints table,
the pagination response shape, and the project layout tree.

Finish by running ruff and pytest and pasting the final summary line of pytest.
```

---

## Final checklist (do this yourself, not Copilot)

- [ ] `pytest -q` — all green, 30+ tests
- [ ] `ruff check .` — no errors
- [ ] `/docs` shows 12 endpoints under `health`, `customers`, `orders`, `tickets`
- [ ] Try in `/docs`: search refunded orders for customer 12 in March 2026
      (`status=refunded&customer_id=12&date_from=2026-03-01&date_to=2026-03-31`)
- [ ] Try: move a `placed` order to `delivered` → 409
- [ ] Try: raise a ticket using another customer's order → 404
- [ ] Try: close a ticket, then set it to `open` → 409
- [ ] `git diff data/seed.json` is empty
- [ ] Compare your API with `Section_04_AI_Coding_Tools/acme_support_copilot/` — note one thing Copilot
      did better and one thing it did worse in `docs/tool_comparison.md`

## Stretch goals (optional — keep them out of the core contract)

Each one is a new spec in `specs/` and a new Copilot session. Write the spec first (Goal, Context,
Acceptance criteria, Constraints, Out of scope — see `specs/order_search.md` in the reference project).

- `GET /stats/tickets` — counts by status and by priority, plus open tickets older than 48 hours.
- `GET /customers/{id}/tickets` — a customer's tickets, newest first.
- `GET /tickets?order_id=` filter, and `GET /orders/{id}/tickets`.
- Add `updated_at` to tickets and orders, set on every status change (write a migration note).
