"""Flights sub-agent: returns mocked flight options annotated with pricing analysis."""

import uvicorn
import httpx
from google.adk.agents import LlmAgent
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.agent_tool import AgentTool
from agents.config import load_agent_config

_cfg = load_agent_config("flights_agent", "flights_agent.json", 41242)
PORT = _cfg["port"]
AGENT_CARD = _cfg["agent_card"]
AGENT_TOKEN = _cfg["agent_token"]
CA_CERT = _cfg["ca_cert_path"]
litellm_api_key = _cfg["litellm_api_key"]
litellm_api_base = _cfg["litellm_api_base"]
pricing_agent_url = _cfg["pricing_agent_url"]

http_client = httpx.AsyncClient(
    headers={"Authorization": f"Bearer {AGENT_TOKEN}"} if AGENT_TOKEN else {},
    verify=CA_CERT if CA_CERT else True,
    timeout=httpx.Timeout(connect=10.0, read=120.0, write=10.0, pool=10.0),
)

pricing_agent = RemoteA2aAgent(
    name="pricing_agent",
    description="Evaluates whether flight prices are good deals.",
    agent_card=f"{pricing_agent_url}/.well-known/agent-card.json",
    httpx_client=http_client if AGENT_TOKEN and CA_CERT else None,
)

root_agent = LlmAgent(
    model=LiteLlm(
        model="anthropic/claude-sonnet-4-6",
        api_key=litellm_api_key if litellm_api_key else None,
        api_base=litellm_api_base,
    ),
    name="flights_agent",
    description="Finds flight options for a travel destination and dates.",
    instruction=(
        "You are a flights specialist. When given any travel request:\n"
        "1. Come up with 3 mocked flight options. Do not ask clarifying questions. "
        "If dates or origin are missing, invent plausible ones. "
        "Format each as: Airline | Route | Price | Duration\n"
        "2. Pass the full list to the pricing_agent tool to get a deal assessment.\n"
        "3. Return the annotated list from pricing_agent as your final response."
    ),
    tools=[AgentTool(agent=pricing_agent)],
)

a2a_app = to_a2a(root_agent, port=PORT, agent_card=AGENT_CARD)

if __name__ == "__main__":
    uvicorn.run(a2a_app, host="0.0.0.0", port=PORT)
