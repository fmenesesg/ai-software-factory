"""RED tests: OpenShift MCP denies namespaces outside NAMESPACE_PREFIX."""

from __future__ import annotations

import pytest

from mcp_openshift.config import OpenShiftMcpSettings
from mcp_openshift.security import OpenShiftSecurityError, assert_namespace_allowed
from mcp_openshift.tools import InMemoryOpenShiftClient, OpenShiftTools


PREFIX = "asf-workshop-"


@pytest.fixture()
def tools() -> OpenShiftTools:
    return OpenShiftTools(
        OpenShiftMcpSettings(namespace_prefix=PREFIX, dry_run=False),
        client=InMemoryOpenShiftClient(),
    )


def test_assert_allows_prefixed_namespace() -> None:
    assert assert_namespace_allowed("asf-workshop-pr-12", PREFIX) == "asf-workshop-pr-12"


@pytest.mark.parametrize(
    "ns",
    [
        "default",
        "kube-system",
        "openshift-operators",
        "asf-other-pr-1",
        "ASF-workshop-pr-1",
        "../asf-workshop-evil",
        "asf-workshop-/../evil",
        "",
    ],
)
def test_red_outside_prefix_denied_at_security_layer(ns: str) -> None:
    with pytest.raises(OpenShiftSecurityError):
        assert_namespace_allowed(ns, PREFIX)


@pytest.mark.parametrize(
    "tool_name,args",
    [
        ("oc_ensure_namespace", {"namespace": "default"}),
        ("oc_apply", {"namespace": "kube-system", "manifest": {"kind": "ConfigMap", "metadata": {"name": "x"}}}),
        ("oc_route_url", {"namespace": "openshift", "name": "console"}),
        ("oc_logs", {"namespace": "kube-system", "name": "coredns"}),
    ],
)
def test_red_tools_deny_outside_prefix(tools: OpenShiftTools, tool_name: str, args: dict) -> None:
    with pytest.raises(OpenShiftSecurityError, match="outside NAMESPACE_PREFIX"):
        tools.call(tool_name, args)


def test_apply_allows_prefixed_and_dry_run_blocks_write() -> None:
    dry = OpenShiftTools(
        OpenShiftMcpSettings(namespace_prefix=PREFIX, dry_run=True),
        client=InMemoryOpenShiftClient(),
    )
    result = dry.call(
        "oc_apply",
        {
            "namespace": "asf-workshop-pr-9",
            "manifest": {"kind": "ConfigMap", "metadata": {"name": "demo", "namespace": "asf-workshop-pr-9"}},
        },
    )
    assert result["blocked"] is True
    assert result["dry_run"] is True


def test_manifest_namespace_mismatch_denied(tools: OpenShiftTools) -> None:
    with pytest.raises(OpenShiftSecurityError, match="metadata.namespace"):
        tools.call(
            "oc_apply",
            {
                "namespace": "asf-workshop-pr-9",
                "manifest": {
                    "kind": "ConfigMap",
                    "metadata": {"name": "x", "namespace": "default"},
                },
            },
        )


def test_route_url_under_prefix(tools: OpenShiftTools) -> None:
    result = tools.call("oc_route_url", {"namespace": "asf-workshop-pr-9", "name": "sample-app"})
    assert result["ok"] is True
    assert "asf-workshop-pr-9" in result["url"]
