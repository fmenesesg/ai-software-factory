# Database notes

**MVP default:** SQLite file at `SAMPLE_APP_DB_PATH` (defaults to `sample-app/db/sample.db`).

**Optional Postgres:** Point the Deployment at a Postgres DSN in a later profile; keep the same
REST contract (`/api/v1/inventory`, `/api/v1/orders`). Schema source of truth for SQLite is
`schema.sql`. Do not commit live database files.
