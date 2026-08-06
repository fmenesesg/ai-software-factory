"""SQLite-backed store for demo orders/inventory (Postgres optional via DATABASE_URL)."""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


def default_sqlite_path() -> Path:
    raw = os.environ.get("SAMPLE_APP_DB_PATH", "").strip()
    if raw:
        return Path(raw)
    return Path(__file__).resolve().parents[3] / "db" / "sample.db"


def connect(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path or default_sqlite_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS inventory (
            sku TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 0 CHECK (quantity >= 0)
        );
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sku TEXT NOT NULL,
            quantity INTEGER NOT NULL CHECK (quantity > 0),
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (sku) REFERENCES inventory(sku)
        );
        """
    )
    cur = conn.execute("SELECT COUNT(*) AS c FROM inventory")
    if int(cur.fetchone()["c"]) == 0:
        conn.executemany(
            "INSERT INTO inventory (sku, name, quantity) VALUES (?, ?, ?)",
            [
                ("SKU-WIDGET", "Demo Widget", 100),
                ("SKU-GADGET", "Demo Gadget", 50),
                ("SKU-PART", "Demo Spare Part", 200),
            ],
        )
    conn.commit()


@contextmanager
def session(db_path: Path | None = None) -> Iterator[sqlite3.Connection]:
    conn = connect(db_path)
    try:
        init_schema(conn)
        yield conn
    finally:
        conn.close()


def list_inventory(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute("SELECT sku, name, quantity FROM inventory ORDER BY sku").fetchall()
    return [dict(r) for r in rows]


def list_orders(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT id, sku, quantity, status, created_at FROM orders ORDER BY id DESC"
    ).fetchall()
    return [dict(r) for r in rows]


def create_order(conn: sqlite3.Connection, sku: str, quantity: int) -> dict[str, Any]:
    inv = conn.execute("SELECT quantity FROM inventory WHERE sku = ?", (sku,)).fetchone()
    if inv is None:
        raise ValueError(f"unknown sku: {sku}")
    if int(inv["quantity"]) < quantity:
        raise ValueError(f"insufficient stock for {sku}")
    conn.execute(
        "UPDATE inventory SET quantity = quantity - ? WHERE sku = ?",
        (quantity, sku),
    )
    cur = conn.execute(
        "INSERT INTO orders (sku, quantity, status) VALUES (?, ?, 'pending')",
        (sku, quantity),
    )
    conn.commit()
    row = conn.execute(
        "SELECT id, sku, quantity, status, created_at FROM orders WHERE id = ?",
        (cur.lastrowid,),
    ).fetchone()
    return dict(row)
