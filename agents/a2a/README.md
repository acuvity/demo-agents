# A2A Agents

Examples of [A2A protocol](https://github.com/a2aproject/A2A) agents — a multi-agent travel planner.

---

## Multi-Agent Travel Planner (`multi-agent/`)

A travel planning system built with [Google ADK](https://github.com/google/adk-python) and the A2A protocol. Four agents communicate over A2A:

```
CLI → travel_planner (port 41241)
         ├── flights_agent (port 41242) → pricing_agent (port 41244)
         └── hotels_agent  (port 41243)
```

- **travel_planner** — orchestrator, calls flights and hotels agents
- **flights_agent** — finds flight options, calls pricing agent to evaluate prices
- **hotels_agent** — finds hotel options
- **pricing_agent** — evaluates whether a flight price is a good deal

All agents call Anthropic Claude through the LiteLLM library (via ADK's `LiteLlm`), optionally routed via the Acuvity AI Security Gateway. Agent-to-agent A2A calls route through the same gateway when one is configured, or directly via Kubernetes service DNS when it isn't — see [Configuration](#configuration) below.

## Prerequisites

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | [console.anthropic.com](https://console.anthropic.com) |
| `A2A_TRAVEL_PLANNER_TOKEN` | No | Component token from [console.acuvity.ai](https://console.acuvity.ai) |
| `A2A_FLIGHTS_AGENT_TOKEN` | No | Component token from [console.acuvity.ai](https://console.acuvity.ai) |
| `A2A_HOTELS_AGENT_TOKEN` | No | Component token from [console.acuvity.ai](https://console.acuvity.ai) |
| `A2A_PRICING_AGENT_TOKEN` | No | Component token from [console.acuvity.ai](https://console.acuvity.ai) |
| `CA_BUNDLE_PATH` | No | Path to your CA bundle PEM file |

Import the [manifest file](./multi-agent/deploy/config/manifest.yaml) into [console.acuvity.ai](https://console.acuvity.ai), then issue a component token for each agent component. The tokens and CA bundle are optional: `deploy.sh` prints a warning if they are unset and deploys without them.

For full instructions see the [Acuvity agentic security docs](https://docs.acuvity.ai/wURWAaVt0FMiS39eKrS9/appsec).

## Kubernetes Deployment

<details><summary>Click to expand</summary>

```bash
export ANTHROPIC_API_KEY=<your_anthropic_key>
# optional
export A2A_TRAVEL_PLANNER_TOKEN=<token>
export A2A_FLIGHTS_AGENT_TOKEN=<token>
export A2A_HOTELS_AGENT_TOKEN=<token>
export A2A_PRICING_AGENT_TOKEN=<token>
export CA_BUNDLE_PATH=<path/to/ca.pem>

./multi-agent/deploy/k8s/deploy.sh
```

This script creates the `a2a-multi-agent` namespace, applies the CA bundle, and installs the Helm chart.


### Configuration

Each agent reads its configuration from `/app/config.yaml`, mounted into the pod from the `a2a-secrets` Secret. Helm renders this file from `deploy/k8s/charts/a2a-multi-agent/values.yaml` — the same values each agent reads locally from `multi-agent/src/backend/config.yaml`, just with Kubernetes service URLs and your tokens filled in.

To route agent-to-agent A2A traffic through the Acuvity AI Security Gateway, set `gateway.url`:

```bash
helm upgrade a2a-multi-agent ./multi-agent/deploy/k8s/charts/a2a-multi-agent \
  --namespace a2a-multi-agent \
  --reuse-values \
  --set gateway.url="https://<your-gateway-host>" \
  --set gateway.paths.flights="/<flights-path>" \
  --set gateway.paths.hotels="/<hotels-path>" \
  --set gateway.paths.pricing="/<pricing-path>"
```

Leave `gateway.url` empty (`--set gateway.url=""`) to have agents call each other directly via Kubernetes service DNS instead. Google ADK refuses to fetch agent cards over plain `http` from non-loopback hosts, so callers build the sub-agent card from the bundled `agents/cards/*.json` (pointing at the service URL) instead of fetching it live.

By default `gateway.url` and `litellm.apiBase` are empty: agents call each other directly via Kubernetes service DNS, and LLM calls go to the Anthropic API directly. To send LLM traffic through the gateway as well, set `litellm.apiBase` (e.g. `--set litellm.apiBase="https://<your-gateway-host>/<org>/<project>/anthropic-api"`).

### Running the agent from Kubernetes

Port-forward the travel planner service:

```bash
kubectl port-forward -n a2a-multi-agent svc/a2a-travel-planner-svc 41241:80
```

In another terminal, fetch the agent card and send a message (JSON-RPC):

```bash
curl http://localhost:41241/.well-known/agent-card.json

curl -X POST http://localhost:41241/ \
  -H "Content-Type: application/json" \
  -H "A2A-Version: 1.0" \
  -d '{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "SendMessage",
  "params": {
    "message": {
      "messageId": "msg-1",
      "role": "ROLE_USER",
      "parts": [
        {
          "text": "Plan a 3-day trip from SFO to Tokyo next month"
        }
      ]
    }
  }
}'
```

The agent card advertises the in-cluster service URL, so use `curl` against the forwarded port as above; `cli.py` follows the card's URL and won't work through a port-forward.

</details>

## Local Development

<details><summary>Click to expand</summary>

```bash
cd multi-agent/src/backend
uv sync
```

Edit `config.yaml` with your tokens and (optionally) a gateway URL:

```yaml
gateway:
  url: ""   # leave empty to call sub-agents directly, or set to route through a gateway

ca_cert_path: ""

litellm:
  api_base: "http://localhost:4500"

agents:
  travel_planner:
    agent_token: "<travel-planner-token>"
    ...
  flights_agent:
    agent_token: "<flights-agent-token>"
    ...
```

Start each agent in a separate terminal:

```bash
uv run python agents/pricing_agent.py      # Terminal 1
uv run python agents/flights_agent.py      # Terminal 2
uv run python agents/hotels_agent.py       # Terminal 3
uv run python agents/travel_planner_agent.py  # Terminal 4
```

Talk to the travel planner:

```bash
# From the a2a/ directory
uv run python cli.py --url http://localhost:41241

# Via gateway (if gateway.url is set in config.yaml)
uv run python cli.py \
  --url https://<gateway-host>/<org>/<project>/a2a-travel-planner \
  --token <travel-planner-token> \
  --ca-cert /path/to/ca-chain.pem
```

</details>
