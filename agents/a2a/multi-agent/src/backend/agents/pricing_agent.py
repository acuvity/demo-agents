"""Pricing sub-agent: evaluates whether flight prices are good deals."""

import uvicorn
from google.adk.agents import LlmAgent
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from google.adk.models.lite_llm import LiteLlm
from agents.config import load_agent_config

_cfg = load_agent_config("pricing_agent", "pricing_agent.json", 41244)
PORT = _cfg["port"]
AGENT_CARD = _cfg["agent_card"]
litellm_api_key = _cfg["litellm_api_key"]
litellm_api_base = _cfg["litellm_api_base"]

root_agent = LlmAgent(
    model=LiteLlm(
        model="anthropic/claude-sonnet-4-6",
        api_key=litellm_api_key if litellm_api_key else None,
        api_base=litellm_api_base,
    ),
    name="pricing_agent",
    description="Evaluates whether flight prices are good deals based on typical market rates.",
    instruction=(
        "You are a flight pricing analyst. Given a list of flights with prices, "
        "evaluate each one against these hardcoded typical market rates:\n"
        "- Short haul (<3h): typical $150-$300\n"
        "- Medium haul (3-8h): typical $300-$600\n"
        "- Long haul (>8h): typical $600-$1200\n\n"
        "For each flight, append one of: [Good deal], [Fair price], or [Overpriced]. "
        "Return the same flight list with the label appended to each line. "
        "Do not add any other commentary."
    ),
)

a2a_app = to_a2a(root_agent, port=PORT, agent_card=AGENT_CARD)

if __name__ == "__main__":
    uvicorn.run(a2a_app, host="0.0.0.0", port=PORT)
