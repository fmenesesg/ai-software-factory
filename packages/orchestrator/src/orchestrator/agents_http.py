"""HTTP client for Kind OSS agent + MCP services."""

from __future__ import annotations

import os
from typing import Any

import httpx


def agent_http_enabled() -> bool:
    return os.environ.get("ASF_AGENT_HTTP", "").lower() in {"1", "true", "yes"}


def _agent_base(name: str, default_port: int = 8080) -> str:
    env_key = f"ASF_AGENT_{name.upper().replace('-', '_')}_URL"
    return os.environ.get(env_key, f"http://asf-agent-{name}:{default_port}").rstrip("/")


def mcp_github_url() -> str:
    return os.environ.get("MCP_GITHUB_URL", "http://asf-mcp-github:8091").rstrip("/")


def invoke_agent(
    name: str,
    *,
    run_id: str,
    artifacts: dict[str, Any],
    input_data: dict[str, Any] | None = None,
    timeout: float = 60.0,
) -> dict[str, Any]:
    """POST /v1/invoke on an agent Service; returns response JSON."""
    url = f"{_agent_base(name)}/v1/invoke"
    payload = {
        "run_id": run_id,
        "artifacts": artifacts,
        "input": input_data or {},
    }
    with httpx.Client(timeout=timeout) as client:
        resp = client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
    if not isinstance(data, dict):
        raise RuntimeError(f"agent {name}: unexpected response")
    return data


def call_mcp_github(tool: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    url = f"{mcp_github_url()}/tools/call"
    with httpx.Client(timeout=60.0) as client:
        resp = client.post(url, json={"name": tool, "arguments": arguments or {}})
        resp.raise_for_status()
        data = resp.json()
    if not isinstance(data, dict):
        raise RuntimeError(f"mcp-github {tool}: unexpected response")
    return data


def create_kind_pipelinerun(*, run_id: str, pr_number: str, namespace: str = "asf-factory") -> dict[str, Any]:
    """Create a Tekton PipelineRun for sample-app-pr-kind via in-cluster API (or MCP fallback)."""
    pr_safe = "".join(c if c.isalnum() else "-" for c in str(pr_number))[:20] or "0"
    run_safe = "".join(c if c.isalnum() else "-" for c in run_id.lower())[:40]
    name = f"sample-app-pr-kind-{pr_safe}-{run_safe}"[:63].strip("-")
    manifest = {
        "apiVersion": "tekton.dev/v1",
        "kind": "PipelineRun",
        "metadata": {
            "name": name,
            "namespace": namespace,
            "labels": {
                "app.kubernetes.io/part-of": "ai-software-factory",
                "asf.run-id": run_safe[:63],
            },
        },
        "spec": {
            "pipelineRef": {"name": "sample-app-pr-kind"},
            "taskRunTemplate": {"serviceAccountName": "asf-tekton-ephemeral"},
            "params": [
                {"name": "PR_NUMBER", "value": str(pr_number)},
                {"name": "IMAGE", "value": "localhost/asf-sample-app:kind"},
            ],
        },
    }

    # Prefer in-cluster Kubernetes API (orchestrator SA + Role).
    token_path = "/var/run/secrets/kubernetes.io/serviceaccount/token"
    ca_path = "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt"
    host = os.environ.get("KUBERNETES_SERVICE_HOST")
    port = os.environ.get("KUBERNETES_SERVICE_PORT", "443")
    if host and os.path.isfile(token_path):
        try:
            token = open(token_path, encoding="utf-8").read().strip()
            url = (
                f"https://{host}:{port}/apis/tekton.dev/v1/namespaces/"
                f"{namespace}/pipelineruns"
            )
            with httpx.Client(verify=ca_path, timeout=30.0) as client:
                resp = client.post(
                    url,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    },
                    json=manifest,
                )
                if resp.status_code in {200, 201}:
                    return {
                        "ok": True,
                        "stub": False,
                        "pipeline_run_url": f"tekton://{namespace}/pipelinerun/{name}",
                        "pr_number": pr_number,
                        "name": name,
                    }
                if resp.status_code == 409:
                    return {
                        "ok": True,
                        "stub": False,
                        "pipeline_run_url": f"tekton://{namespace}/pipelinerun/{name}",
                        "pr_number": pr_number,
                        "name": name,
                        "already_exists": True,
                    }
                print(
                    f"create_kind_pipelinerun k8s api {resp.status_code}: {resp.text[:300]}",
                    flush=True,
                )
        except Exception as exc:  # noqa: BLE001
            print(f"create_kind_pipelinerun k8s api error: {exc!r}", flush=True)

    # MCP kubernetes fallback (may be stub in Kind).
    k8s_url = os.environ.get("MCP_KUBERNETES_URL", "http://asf-mcp-kubernetes:8095").rstrip("/")
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                f"{k8s_url}/tools/call",
                json={"name": "k8s_apply", "arguments": {"namespace": namespace, "manifest": manifest}},
            )
            if resp.status_code < 400:
                data = resp.json()
                if isinstance(data, dict) and not data.get("stub"):
                    data.setdefault("pipeline_run_url", f"tekton://{namespace}/pipelinerun/{name}")
                    return data
    except Exception:
        pass
    return {
        "ok": True,
        "stub": True,
        "pipeline_run_url": f"tekton://{namespace}/pipelinerun/{name}",
        "pr_number": pr_number,
        "name": name,
    }
