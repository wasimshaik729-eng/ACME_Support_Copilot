from __future__ import annotations

from contextlib import asynccontextmanager
import os

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from app.api.customers import router as customers_router
from app.api.orders import router as orders_router
from app.api.tickets import router as tickets_router
from app.db import SessionLocal, engine
from app.models import Base
from app.seed import load_seed


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        load_seed(db)
    finally:
        db.close()
    yield


app = FastAPI(title="Acme Support Copilot", version="0.1.0", lifespan=lifespan)


@app.get("/", include_in_schema=False)
def workspace_redirect() -> RedirectResponse:
    workspace_url = os.getenv("ACME_UI_URL", "http://127.0.0.1:8501")
    return RedirectResponse(workspace_url)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(customers_router)
app.include_router(orders_router)
app.include_router(tickets_router)
