from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.api.pagination import PageParam, PageSizeParam, paginate
from app.db import DbSession
from app.models import Customer, Order, Ticket
from app.schemas import (
    Page,
    Priority,
    TicketCreate,
    TicketOut,
    TicketStatus,
    TicketStatusUpdate,
)

router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.post("", response_model=TicketOut, status_code=201)
def create_ticket(payload: TicketCreate, db: DbSession):
    customer = db.get(Customer, payload.customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")

    if payload.order_id is not None:
        order = db.get(Order, payload.order_id)
        if order is None or order.customer_id != payload.customer_id:
            raise HTTPException(
                status_code=404, detail="Order not found for this customer"
            )

    ticket = Ticket(
        customer_id=payload.customer_id,
        order_id=payload.order_id,
        subject=payload.subject,
        message=payload.message,
        channel=payload.channel,
        priority=payload.priority,
        status="open",
        created_at=datetime.now(timezone.utc),
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


@router.get("", response_model=Page[TicketOut])
def list_tickets(
    db: DbSession,
    status: TicketStatus | None = None,
    priority: Priority | None = None,
    customer_id: int | None = None,
    page: PageParam = 1,
    page_size: PageSizeParam = 20,
):
    stmt = select(Ticket)
    if status is not None:
        stmt = stmt.where(Ticket.status == status)
    if priority is not None:
        stmt = stmt.where(Ticket.priority == priority)
    if customer_id is not None:
        stmt = stmt.where(Ticket.customer_id == customer_id)
    stmt = stmt.order_by(Ticket.created_at.desc(), Ticket.id.desc())
    return paginate(db, stmt, page, page_size)


@router.get("/{ticket_id}", response_model=TicketOut)
def get_ticket(ticket_id: int, db: DbSession):
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


@router.patch("/{ticket_id}/status", response_model=TicketOut)
def update_ticket_status(ticket_id: int, payload: TicketStatusUpdate, db: DbSession):
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if ticket.status == "closed":
        raise HTTPException(status_code=409, detail="Closed tickets cannot be reopened")

    ticket.status = payload.status
    db.commit()
    db.refresh(ticket)
    return ticket
