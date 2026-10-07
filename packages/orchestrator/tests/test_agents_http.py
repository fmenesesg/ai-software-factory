"""Agent HTTP helpers — unit smoke without live cluster."""

from orchestrator.agents_http import agent_http_enabled


def test_agent_http_disabled_by_default(monkeypatch) -> None:
    monkeypatch.delenv("ASF_AGENT_HTTP", raising=False)
    assert agent_http_enabled() is False


def test_agent_http_enabled(monkeypatch) -> None:
    monkeypatch.setenv("ASF_AGENT_HTTP", "true")
    assert agent_http_enabled() is True
