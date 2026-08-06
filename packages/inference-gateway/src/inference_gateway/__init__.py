"""Inference gateway — OpenAI-compatible proxy skeleton (M1)."""

from inference_gateway.app import create_app
from inference_gateway.config import GatewaySettings

__all__ = ["GatewaySettings", "create_app"]
