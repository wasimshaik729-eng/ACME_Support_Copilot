from __future__ import annotations

from typing import TypeVar

from fastapi import Query
from sqlalchemy import Select, func, select
from typing_extensions import Annotated

PageParam = Annotated[int, Query(ge=1)]
PageSizeParam = Annotated[int, Query(ge=1, le=100)]

T = TypeVar("T")


def paginate(db, stmt: Select, page: int, page_size: int) -> dict:
    total = (
        db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    )
    items = (
        db.execute(stmt.offset((page - 1) * page_size).limit(page_size)).scalars().all()
    )
    return {"items": items, "total": total, "page": page, "page_size": page_size}
