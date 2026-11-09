from __future__ import annotations

from datetime import date, datetime, time

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.api.pagination import PageParam, PageSizeParam, paginate
from app.db import DbSession
from app.models import Order
from app.schemas import OrderOut, OrderStatus, OrderStatusUpdate, Page

router = APIRouter(prefix="/orders", tags=["orders"])

ALLOWED_TRANSITIONS = {
    "placed": {"shipped"},
    "shipped": {"delivered"},
    "delivered": {"returned"},
    "returned": {"refunded"},
    "refunded": set(),
}


@router.get("", response_model=Page[OrderOut])
def list_orders(
    db: DbSession,
    page: PageParam = 1,
    page_size: PageSizeParam = 20,
):
    stmt = select(Order).order_by(Order.created_at.desc(), Order.id.desc())
    return paginate(db, stmt, page, page_size)


@router.get("/search", response_model=Page[OrderOut])
def search_orders(
    db: DbSession,
    status: OrderStatus | None = None,
    customer_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    page: PageParam = 1,
    page_size: PageSizeParam = 20,
):
    if date_from is not None and date_to is not None and date_from > date_to:
        raise HTTPException(
            status_code=422, detail="date_from must be on or before date_to"
        )

    stmt = select(Order)
    if status is not None:
        stmt = stmt.where(Order.status == status)
    if customer_id is not None:
        stmt = stmt.where(Order.customer_id == customer_id)
    if date_from is not None:
        stmt = stmt.where(Order.created_at >= datetime.combine(date_from, time.min))
    if date_to is not None:
        stmt = stmt.where(Order.created_at <= datetime.combine(date_to, time.max))
    stmt = stmt.order_by(Order.created_at.desc(), Order.id.desc())
    return paginate(db, stmt, page, page_size)


@router.get("/{order_id}", response_model=OrderOut)
def get_order(order_id: str, db: DbSession):
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.patch("/{order_id}/status", response_model=OrderOut)
def update_order_status(order_id: str, payload: OrderStatusUpdate, db: DbSession):
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    current = order.status
    new_status = payload.status
    if new_status not in ALLOWED_TRANSITIONS.get(current, set()):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot change status from '{current}' to '{new_status}'",
        )

    order.status = new_status
    db.commit()
    db.refresh(order)
    return order
