-- Sample-app schema (SQLite demo default).
-- For PostgreSQL, map types (SERIAL/INTEGER, TIMESTAMPTZ) and set DATABASE_URL / SAMPLE_APP_DB_PATH
-- via Helm values. MVP uses embedded SQLite for k8s-free local runs and simple Containerfile demos.

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
