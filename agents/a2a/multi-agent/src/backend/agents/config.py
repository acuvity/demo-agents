"""Configuration loader for the A2A multi-agent demo."""

import json
import os
import tempfile
from pathlib import Path

import yaml


def load_config_yaml() -> dict:
    """Load and return the full agent configuration from a YAML file."""
    config_path = os.environ.get("CONFIG_PATH", "/app/config.yaml")

    if not os.path.exists(config_path):
        config_path = Path(__file__).parent.parent / "config.yaml"

    with open(config_path, "r", encoding="utf-8") as config_file:
        return yaml.safe_load(config_file)


def load_agent_config(agent_name: str, card_filename: str, default_port: int) -> dict:
    """Load config for one agent, resolving sub-agent URLs through the gateway if configured."""
    config = load_config_yaml()
    agent_cfg = config.get("agents", {}).get(agent_name, {})
    litellm_cfg = config.get("litellm", {})
    gateway_url = config.get("gateway", {}).get("url", "")

    port = agent_cfg.get("port", default_port)
    agent_url = agent_cfg.get("agent_url", f"http://127.0.0.1:{port}")

    card_path = Path(__file__).parent / "cards" / card_filename
    card_data = json.loads(card_path.read_text())
    if agent_name != "travel_planner":
        card_data["supported_interfaces"][0]["url"] = f"{agent_url}/"

    card_file = tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", prefix=f"{agent_name}-card-", delete=False
    )
    json.dump(card_data, card_file)
    card_file.close()

    def sub_agent_url(url_key: str, gateway_path_key: str) -> str:
        if gateway_url and agent_cfg.get(gateway_path_key):
            return gateway_url.rstrip("/") + agent_cfg[gateway_path_key]
        return agent_cfg.get(url_key, "")

    return {
        "port": port,
        "agent_url": agent_url,
        "agent_card": card_file.name,
        "agent_token": agent_cfg.get("agent_token", ""),
        "ca_cert_path": config.get("ca_cert_path", ""),
        "litellm_api_key": agent_cfg.get("agent_token", ""),
        "litellm_api_base": litellm_cfg.get("api_base", ""),
        "flights_agent_url": sub_agent_url("flights_agent_url", "flights_agent_gateway_path"),
        "hotels_agent_url": sub_agent_url("hotels_agent_url", "hotels_agent_gateway_path"),
        "pricing_agent_url": sub_agent_url("pricing_agent_url", "pricing_agent_gateway_path"),
    }
