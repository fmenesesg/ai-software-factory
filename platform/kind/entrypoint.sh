#!/bin/sh
set -eu
APP="${ASF_UVICORN_APP:?ASF_UVICORN_APP is required}"
PORT="${ASF_PORT:-8080}"
# Best-effort OTLP setup (no-op if endpoint unset or exporter missing).
python -c 'from agent_sdk.otel_setup import configure_otel_from_env; configure_otel_from_env()' \
  || true
exec python -m uvicorn "${APP}" --host 0.0.0.0 --port "${PORT}"
