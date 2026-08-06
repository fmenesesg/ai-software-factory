#!/usr/bin/env bash
# Presenter-led workshop vertical slice helper (audience observes).
# Usage: ./demo/workshop/run-slice.sh --help
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PROFILE="${PROFILE:-standard}"
DRY_RUN="${DRY_RUN:-true}"

usage() {
  cat <<'EOF'
AI Software Factory — presenter workshop slice

Usage:
  ./demo/workshop/run-slice.sh [--help] [--dry-run] [--profile PROFILE]

Options:
  --help              Show this help
  --dry-run           Skip mutating bootstrap writes (default: true)
  --profile PROFILE   minimal | standard | full (default: standard)

Audience: observe only. Presenter runs bootstrap + orchestrator + GitHub HITL.

See:
  demo/workshop/presenter-script.md
  demo/workshop/audience-guide.md
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --help|-h)
      usage
      exit 0
      ;;
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    --profile)
      PROFILE="${2:-}"
      shift 2
      ;;
    *)
      echo "Unknown arg: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

echo "Workshop slice (presenter-led)"
echo "  ROOT=${ROOT}"
echo "  PROFILE=${PROFILE}"
echo "  DRY_RUN=${DRY_RUN}"
echo "  Next: review demo/workshop/presenter-script.md"

if [[ ! -x "${ROOT}/scripts/workshop-bootstrap.sh" ]]; then
  echo "Missing scripts/workshop-bootstrap.sh" >&2
  exit 1
fi

export PROFILE DRY_RUN
if [[ "${DRY_RUN}" == "true" ]]; then
  "${ROOT}/scripts/workshop-bootstrap.sh" --dry-run || true
else
  "${ROOT}/scripts/workshop-bootstrap.sh"
fi

echo "Slice helper finished (bootstrap checked). Continue with orchestrator run per presenter script."
