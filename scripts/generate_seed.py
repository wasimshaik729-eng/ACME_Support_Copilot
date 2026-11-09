from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from random import Random

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SEED_PATH = PROJECT_ROOT / "data" / "seed.json"

rnd = Random(42)

CUSTOMER_NAMES = [f"Customer {i}" for i in range(1, 201)]

CITIES = [
    ("Mumbai", "Maharashtra"),
    ("Delhi", "Delhi"),
    ("Bengaluru", "Karnataka"),
    ("Hyderabad", "Telangana"),
    ("Chennai", "Tamil Nadu"),
    ("Kolkata", "West Bengal"),
    ("Pune", "Maharashtra"),
    ("Ahmedabad", "Gujarat"),
    ("Jaipur", "Rajasthan"),
    ("Lucknow", "Uttar Pradesh"),
    ("Kanpur", "Uttar Pradesh"),
    ("Nagpur", "Maharashtra"),
    ("Visakhapatnam", "Andhra Pradesh"),
    ("Bhopal", "Madhya Pradesh"),
    ("Patna", "Bihar"),
    ("Thiruvananthapuram", "Kerala"),
    ("Coimbatore", "Tamil Nadu"),
    ("Indore", "Madhya Pradesh"),
    ("Bhubaneswar", "Odisha"),
    ("Surat", "Gujarat"),
    ("Vadodara", "Gujarat"),
    ("Nashik", "Maharashtra"),
    ("Rajkot", "Gujarat"),
    ("Pune", "Maharashtra"),
]

PRODUCTS = [
    ("Kurtas", "fashion"),
    ("Sarees", "fashion"),
    ("Pressure Cooker", "home_kitchen"),
    ("Smartphone", "electronics"),
    ("Cricket Bat", "sports"),
    ("JEE Workbook", "books"),
    ("Face Serum", "beauty"),
    ("Handbag", "accessories"),
    ("Bluetooth Speaker", "electronics"),
    ("Dinner Set", "home_kitchen"),
    ("Leather Wallet", "accessories"),
    ("Gym Bag", "sports"),
    ("Anarkali Suit", "fashion"),
    ("Rice Cooker", "home_kitchen"),
    ("Earbuds", "electronics"),
    ("Yoga Mat", "sports"),
    ("Novel Set", "books"),
    ("Lip Balm", "beauty"),
    ("Sunglasses", "accessories"),
    ("Laptop Stand", "electronics"),
]

PAYMENT_METHODS = ["UPI", "Card", "Cash on Delivery", "Net Banking", "Wallet"]
ORDER_STATUSES = ["placed", "shipped", "delivered", "returned", "refunded"]
TICKET_PRIORITIES = ["low", "medium", "high"]
TICKET_CHANNELS = ["email", "chat", "whatsapp", "phone"]
TICKET_STATUSES = ["open", "in_progress", "resolved", "closed"]


def iso(dt: datetime) -> str:
    return dt.isoformat(timespec="seconds")


def generate_customers() -> list[dict]:
    customers = []
    for i in range(1, 201):
        name = CUSTOMER_NAMES[i - 1]
        city, state = CITIES[(i - 1) % len(CITIES)]
        customers.append(
            {
                "id": i,
                "name": name,
                "email": f"{name.lower().replace(' ', '.')}+{i}@example.com",
                "phone": f"+91 {rnd.randint(7000000000, 9999999999)}",
                "city": city,
                "state": state,
                "created_at": iso(datetime(2024, 1, 1) + timedelta(days=i * 3)),
            }
        )
    return customers


def generate_orders(customers: list[dict]) -> list[dict]:
    orders = []
    for i in range(1001, 2001):
        customer = customers[(i - 1001) % len(customers)]
        product, category = PRODUCTS[(i - 1001) % len(PRODUCTS)]
        status = ORDER_STATUSES[(i - 1001) % len(ORDER_STATUSES)]
        orders.append(
            {
                "id": f"A-{i}",
                "customer_id": customer["id"],
                "product": product,
                "category": category,
                "quantity": rnd.randint(1, 5),
                "amount_inr": round(rnd.uniform(299.0, 65000.0), 2),
                "payment_method": PAYMENT_METHODS[(i - 1001) % len(PAYMENT_METHODS)],
                "status": status,
                "created_at": iso(
                    datetime(2025, 1, 1)
                    + timedelta(days=(i - 1001) % 365, hours=(i % 12), minutes=(i % 59))
                ),
            }
        )
    return orders


def generate_tickets(customers: list[dict], orders: list[dict]) -> list[dict]:
    tickets = []
    order_lookup = {order["id"]: order for order in orders}
    for i in range(1, 301):
        customer = customers[(i - 1) % len(customers)]
        order_id = None
        if i % 4 == 0:
            order_id = orders[(i - 1) % len(orders)]["id"]
            if order_lookup.get(order_id, {}).get("customer_id") != customer["id"]:
                order_id = None
        tickets.append(
            {
                "id": i,
                "customer_id": customer["id"],
                "order_id": order_id,
                "subject": f"Support ticket {i}: {PRODUCTS[(i - 1) % len(PRODUCTS)][0]}",
                "message": f"This is ticket number {i}. Please review the issue and respond as quickly as possible. Thanks.",
                "channel": TICKET_CHANNELS[(i - 1) % len(TICKET_CHANNELS)],
                "priority": TICKET_PRIORITIES[(i - 1) % len(TICKET_PRIORITIES)],
                "status": TICKET_STATUSES[(i - 1) % len(TICKET_STATUSES)],
                "created_at": iso(
                    datetime(2025, 3, 1)
                    + timedelta(days=(i - 1) % 180, hours=(i % 16), minutes=(i % 59))
                ),
            }
        )
    return tickets


def build_seed() -> dict:
    customers = generate_customers()
    orders = generate_orders(customers)
    tickets = generate_tickets(customers, orders)
    return {"customers": customers, "orders": orders, "tickets": tickets}


if __name__ == "__main__":
    seed = build_seed()
    SEED_PATH.parent.mkdir(parents=True, exist_ok=True)
    SEED_PATH.write_text(json.dumps(seed, indent=2), encoding="utf-8")
    print(
        f"Wrote {len(seed['customers'])} customers, {len(seed['orders'])} orders, {len(seed['tickets'])} tickets to {SEED_PATH}"
    )
