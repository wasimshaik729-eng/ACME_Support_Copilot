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
