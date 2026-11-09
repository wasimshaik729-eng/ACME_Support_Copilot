from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from sqlalchemy import select

from app.models import Customer, Order, Ticket

SEED_FILE = Path(__file__).resolve().parent.parent / "data" / "seed.json"


def _as_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value)


def load_seed(db, seed_file: Path = SEED_FILE) -> bool:
    if db.scalar(select(Customer.id).limit(1)) is not None:
        return False

    with seed_file.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    for customer in payload["customers"]:
        db.add(
            Customer(
                id=customer["id"],
                name=customer["name"],
                email=customer["email"],
                phone=customer["phone"],
                city=customer["city"],
                state=customer["state"],
                created_at=_as_datetime(customer["created_at"]),
            )
        )
    db.flush()

    for order in payload["orders"]:
        db.add(
            Order(
                id=order["id"],
                customer_id=order["customer_id"],
                product=order["product"],
                category=order["category"],
                quantity=order["quantity"],
                amount_inr=order["amount_inr"],
                payment_method=order["payment_method"],
                status=order["status"],
                created_at=_as_datetime(order["created_at"]),
            )
        )
    db.flush()

    for ticket in payload["tickets"]:
        db.add(
            Ticket(
                id=ticket["id"],
                customer_id=ticket["customer_id"],
                order_id=ticket["order_id"],
                subject=ticket["subject"],
                message=ticket["message"],
                channel=ticket["channel"],
                priority=ticket["priority"],
                status=ticket["status"],
                created_at=_as_datetime(ticket["created_at"]),
            )
        )

    db.commit()
    return True
