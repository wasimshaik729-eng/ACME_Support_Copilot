from __future__ import annotations

from datetime import datetime
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field

OrderStatus = Literal["placed", "shipped", "delivered", "returned", "refunded"]
TicketStatus = Literal["open", "in_progress", "resolved", "closed"]
Priority = Literal["low", "medium", "high"]
Channel = Literal["email", "chat", "whatsapp", "phone"]

T = TypeVar("T")


class CustomerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    phone: str
    city: str
    state: str
    created_at: datetime


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    customer_id: int
    product: str
    category: str
    quantity: int
    amount_inr: float
    payment_method: str
    status: OrderStatus
    created_at: datetime


class OrderStatusUpdate(BaseModel):
    status: OrderStatus


class TicketCreate(BaseModel):
    customer_id: int
    order_id: str | None = None
    subject: str = Field(min_length=3, max_length=200)
    message: str = Field(min_length=5, max_length=5000)
    channel: Channel = "email"
    priority: Priority = "medium"


class TicketOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_id: int
    order_id: str | None = None
    subject: str
    message: str
    channel: Channel
    priority: Priority
    status: TicketStatus
    created_at: datetime


class TicketStatusUpdate(BaseModel):
    status: TicketStatus


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
