"""Hotels sub-agent: returns mocked hotel options for a destination."""

import uvicorn
from google.adk.agents import LlmAgent
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from google.adk.models.lite_llm import LiteLlm
from agents.config import load_agent_config

_cfg = load_agent_config("hotels_agent", "hotels_agent.json", 41243)
PORT = _cfg["port"]
AGENT_CARD = _cfg["agent_card"]
litellm_api_key = _cfg["litellm_api_key"]
litellm_api_base = _cfg["litellm_api_base"]

root_agent = LlmAgent(
    model=LiteLlm(
        model="anthropic/claude-sonnet-4-6",
        api_key=litellm_api_key if litellm_api_key else None,
        api_base=litellm_api_base if litellm_api_base else None,
    ),
    name="hotels_agent",
    description="Finds hotel options for a travel destination and dates.",
    instruction=(
        "You are a hotels specialist. When given any travel request, immediately respond "
        "with 3 mocked hotel options. Do not ask clarifying questions. "
        "If dates or guest count are missing, invent plausible ones. "
        "Format: Hotel Name | Price/night | Description. Keep it brief."
    ),
)

a2a_app = to_a2a(root_agent, port=PORT, agent_card=AGENT_CARD)

if __name__ == "__main__":
    uvicorn.run(a2a_app, host="0.0.0.0", port=PORT)
