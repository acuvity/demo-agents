"""Configuration loader for the Langgraph agent."""

import os
from typing import TypedDict

import yaml


class OtelConfig(TypedDict):
    """OpenTelemetry configuration."""

    enabled: bool
    service_name: str
    send_spans: bool
    console_export: bool
    no_file_export: bool
    file: str
    otlp_endpoint: str | None
    insecure: bool


class McpServerConfig(TypedDict):
    """MCP server connection configuration."""

    url: str


class AgentConfig(TypedDict):
    """Top-level agent configuration."""

    app_name: str
    title: str
    cors_origins: str | list[str]
    instruction: str
    mcp_servers: list[McpServerConfig] | None
    otel: OtelConfig


def load_config_yaml() -> AgentConfig:
    """Load and return the agent configuration from a YAML file."""
    config_path = os.environ.get("CONFIG_PATH", "/app/config.yaml")

    if not os.path.exists(config_path):
        runtime_dir = os.path.dirname(os.path.abspath(__file__))
        backend_dir = os.path.dirname(runtime_dir)
        config_path = os.path.join(backend_dir, "config.yaml")

    with open(config_path, "r", encoding="utf-8") as config_file:
        return yaml.safe_load(config_file)  # type: ignore[no-any-return]
