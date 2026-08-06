#!/usr/bin/env python3
"""Generate HTML cost-by-run_id report from OTel-like span attribute JSON."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow running from repo root without install.
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "packages" / "agent-sdk" / "src"))

# Import submodule directly to avoid pulling FastAPI via agent_sdk.__init__.
from agent_sdk.cost import cost_by_run_id, render_cost_html  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="ASF cost report from OTel span attrs JSON")
    parser.add_argument(
        "spans_json",
        nargs="?",
        help="JSON file: list of {attributes: {...}} or flat attr dicts",
    )
    parser.add_argument("-o", "--output", default="-", help="Output HTML path or - for stdout")
    args = parser.parse_args()

    if not args.spans_json:
        parser.print_help()
        return 0

    data = json.loads(Path(args.spans_json).read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise SystemExit("spans_json must be a JSON array")
    html = render_cost_html(cost_by_run_id(data))
    if args.output == "-":
        print(html)
    else:
        Path(args.output).write_text(html, encoding="utf-8")
        print(f"Wrote {args.output}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
