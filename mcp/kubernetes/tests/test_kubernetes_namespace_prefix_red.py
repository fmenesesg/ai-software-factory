"""RED tests: Kubernetes MCP denies namespaces outside NAMESPACE_PREFIX."""

from __future__ import annotations

import pytest

from mcp_kubernetes.config import KubernetesMcpSettings
from mcp_kubernetes.security import KubernetesSecurityError, assert_namespace_allowed
from mcp_kubernetes.tools import InMemoryKubernetesClient, KubernetesTools


PREFIX = "asf-workshop-"


@pytest.fixture()
def tools() -> KubernetesTools:
    client = InMemoryKubernetesClient()
    client.objects[("asf-workshop-pr-3", "configmap", "app")] = {
        "kind": "ConfigMap",
        "metadata": {"name": "app", "namespace": "asf-workshop-pr-3"},
    }
    return KubernetesTools(
        KubernetesMcpSettings(namespace_prefix=PREFIX, dry_run=False),
        client=client,
    )


@pytest.mark.parametrize(
    "ns",
    ["default", "kube-public", "openshift-ingress", "prod", "asf-workshop", ""],
)
def test_red_outside_prefix_denied(ns: str) -> None:
    with pytest.raises(KubernetesSecurityError):
        assert_namespace_allowed(ns, PREFIX)


def test_red_get_outside_prefix_denied(tools: KubernetesTools) -> None:
    with pytest.raises(KubernetesSecurityError, match="outside NAMESPACE_PREFIX"):
        tools.call("k8s_get", {"namespace": "default", "kind": "ConfigMap", "name": "x"})


def test_red_apply_outside_prefix_denied(tools: KubernetesTools) -> None:
    with pytest.raises(KubernetesSecurityError, match="outside NAMESPACE_PREFIX"):
        tools.call(
            "k8s_apply",
            {
                "namespace": "kube-system",
                "manifest": {"kind": "ConfigMap", "metadata": {"name": "evil"}},
            },
        )


def test_get_under_prefix_ok(tools: KubernetesTools) -> None:
    result = tools.call(
        "k8s_get",
        {"namespace": "asf-workshop-pr-3", "kind": "ConfigMap", "name": "app"},
    )
    assert result["ok"] is True
    assert result["object"]["metadata"]["name"] == "app"


def test_apply_dry_run_blocks_write() -> None:
    dry = KubernetesTools(
        KubernetesMcpSettings(namespace_prefix=PREFIX, dry_run=True),
        client=InMemoryKubernetesClient(),
    )
    result = dry.call(
        "k8s_apply",
        {
            "namespace": "asf-workshop-pr-3",
            "manifest": {
                "kind": "ConfigMap",
                "metadata": {"name": "app", "namespace": "asf-workshop-pr-3"},
            },
        },
    )
    assert result["blocked"] is True
