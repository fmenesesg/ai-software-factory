"""FastAPI orders/inventory API with /health and OpenAPI."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from sample_app_backend import __version__
from sample_app_backend.db import create_order, list_inventory, list_orders, session


def _frontend_dir() -> Path | None:
    env = os.environ.get("FRONTEND_DIR", "").strip()
    if env:
        path = Path(env)
        return path if path.is_dir() else None
    # Repo layout: sample-app/backend/src/sample_app_backend → sample-app/frontend
    candidate = Path(__file__).resolve().parents[3] / "frontend"
    if candidate.is_dir():
        return candidate
    # Container layout: /opt/app/sample_app_backend + /opt/app/frontend
    sibling = Path(__file__).resolve().parents[1] / "frontend"
    return sibling if sibling.is_dir() else None


class OrderCreate(BaseModel):
    sku: str = Field(min_length=1, max_length=64)
    quantity: int = Field(gt=0, le=10_000)


def create_app(*, serve_frontend: bool = True) -> FastAPI:
    app = FastAPI(
        title="Sample Orders/Inventory API",
        version=__version__,
        description="Neutral cloud-native demo workload for AI Software Factory (ADR-012).",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict[str, Any]:
        with session() as conn:
            conn.execute("SELECT 1").fetchone()
        return {"status": "ready", "service": "sample-app", "version": __version__}

    @app.get("/ready")
    def ready() -> dict[str, str]:
        return {"status": "ready"}

    @app.get("/api/v1/inventory")
    def get_inventory() -> dict[str, Any]:
        with session() as conn:
            return {"items": list_inventory(conn)}

    @app.get("/api/v1/orders")
    def get_orders() -> dict[str, Any]:
        with session() as conn:
            return {"orders": list_orders(conn)}

    @app.post("/api/v1/orders", status_code=201)
    def post_order(body: OrderCreate) -> dict[str, Any]:
        try:
            with session() as conn:
                order = create_order(conn, body.sku.strip(), body.quantity)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"order": order}

    if serve_frontend:
        frontend = _frontend_dir()
        if frontend is not None:
            app.mount("/", StaticFiles(directory=str(frontend), html=True), name="frontend")

    return app


app = create_app()
