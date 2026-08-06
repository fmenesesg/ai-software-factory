"""Shared agent SDK: MCP/inference clients, OTel helpers, artifact contracts."""

from agent_sdk.artifacts import ArtifactIds, validate_artifact_id, validate_artifact_ids
from agent_sdk.inference import InferenceClient, InferenceClientConfig
from agent_sdk.mcp import McpClient, McpClientConfig
from agent_sdk.otel import FactorySpanAttrs, start_factory_span
from agent_sdk.runtime import AgentInvokeRequest, AgentInvokeResponse

__all__ = [
    "AgentInvokeRequest",
    "AgentInvokeResponse",
    "ArtifactIds",
    "FactorySpanAttrs",
    "InferenceClient",
    "InferenceClientConfig",
    "McpClient",
    "McpClientConfig",
    "start_factory_span",
    "validate_artifact_id",
    "validate_artifact_ids",
]
