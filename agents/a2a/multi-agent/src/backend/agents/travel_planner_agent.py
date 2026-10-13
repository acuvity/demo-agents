"""Travel planner orchestrator: uses LLM to call flights + hotels sub-agents and compose a response."""

import uvicorn
import httpx
from google.adk.agents import LlmAgent
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.agent_tool import AgentTool
from agents.config import load_agent_config

_cfg = load_agent_config("travel_planner", "travel_planner_agent.json", 41241)
PORT = _cfg["port"]
AGENT_CARD = _cfg["agent_card"]
AGENT_TOKEN = _cfg["agent_token"]
CA_CERT = _cfg["ca_cert_path"]
litellm_api_key = _cfg["litellm_api_key"]
litellm_api_base = _cfg["litellm_api_base"]
flights_agent_url = _cfg["flights_agent_url"]
hotels_agent_url = _cfg["hotels_agent_url"]

http_client = httpx.AsyncClient(
    headers={"Authorization": f"Bearer {AGENT_TOKEN}"} if AGENT_TOKEN else {},
    verify=CA_CERT if CA_CERT else True,
    timeout=httpx.Timeout(connect=10.0, read=120.0, write=10.0, pool=10.0),
)

flights_agent = RemoteA2aAgent(
    name="flights_agent",
    description="Finds flight options for a destination and travel dates.",
    agent_card=f"{flights_agent_url}/.well-known/agent-card.json",
    httpx_client=http_client if AGENT_TOKEN and CA_CERT else None,
)

hotels_agent = RemoteA2aAgent(
    name="hotels_agent",
    description="Finds hotel options for a destination and travel dates.",
    agent_card=f"{hotels_agent_url}/.well-known/agent-card.json",
    httpx_client=http_client if AGENT_TOKEN and CA_CERT else None,
)

root_agent = LlmAgent(
    model=LiteLlm(
        model="anthropic/claude-sonnet-4-6",
        api_key=litellm_api_key if litellm_api_key else None,
        api_base=litellm_api_base,
    ),
    name="travel_planner",
    description="Plans a trip by finding flights and hotels, then presenting a combined travel plan.",
    instruction=(
        "You are a travel planner. When the user gives you a travel request, "
        "call the flights_agent tool to get flight options AND call the hotels_agent tool "
        "to get hotel options. Then combine both results into a single clear travel plan "
        "with a Flights section and a Hotels section. "
        "Only call both tools when needed."
    ),
    tools=[
        AgentTool(agent=flights_agent),
        AgentTool(agent=hotels_agent),
    ],
)

a2a_app = to_a2a(root_agent, port=PORT, agent_card=AGENT_CARD)

if __name__ == "__main__":
    uvicorn.run(a2a_app, host="0.0.0.0", port=PORT)
