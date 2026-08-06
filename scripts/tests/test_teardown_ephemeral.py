"""Teardown script prefix-safety tests (no live cluster required)."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "teardown-ephemeral.sh"


def test_teardown_script_exists_and_executable() -> None:
    assert SCRIPT.is_file()
    assert os.access(SCRIPT, os.X_OK)


def test_teardown_refuses_empty_prefix(tmp_path: Path) -> None:
    fake_oc = tmp_path / "oc"
    fake_oc.write_text("#!/bin/sh\necho default\n", encoding="utf-8")
    fake_oc.chmod(0o755)
    env = os.environ.copy()
    env["NAMESPACE_PREFIX"] = ""
    env["KUBE_BIN"] = str(fake_oc)
    env["DRY_RUN"] = "true"
    proc = subprocess.run(
        ["bash", str(SCRIPT)],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode != 0
    assert "NAMESPACE_PREFIX" in proc.stderr


def test_teardown_dry_run_only_lists_prefixed(tmp_path: Path) -> None:
    fake_oc = tmp_path / "oc"
    fake_oc.write_text(
        "#!/bin/sh\n"
        "if [ \"$1\" = get ]; then\n"
        "  printf '%s\\n' asf-workshop-pr-1 default kube-system asf-workshop-pr-2\n"
        "  exit 0\n"
        "fi\n"
        "echo unexpected >&2; exit 1\n",
        encoding="utf-8",
    )
    fake_oc.chmod(0o755)
    env = os.environ.copy()
    env["NAMESPACE_PREFIX"] = "asf-workshop-"
    env["KUBE_BIN"] = str(fake_oc)
    env["DRY_RUN"] = "true"
    proc = subprocess.run(
        ["bash", str(SCRIPT)],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert "asf-workshop-pr-1" in proc.stdout
    assert "asf-workshop-pr-2" in proc.stdout
    assert "would delete namespace/default" not in proc.stdout
    assert "kube-system" not in proc.stdout
