#!/bin/sh
set -eu
APP="${ASF_UVICORN_APP:?ASF_UVICORN_APP is required}"
PORT="${ASF_PORT:-8080}"
exec python -m uvicorn "${APP}" --host 0.0.0.0 --port "${PORT}"
