# A2A Agents

Examples of [A2A protocol](https://github.com/a2aproject/A2A) agents — a single-agent hello world and a multi-agent travel planner.

NOTE: This demo has a [manifest file](./multi-agent/deploy/config/manifest.yaml) which describes the components and access policies.

---

## Single Agent (`single-agent/`)

A minimal A2A server demonstrating the full request/response lifecycle: working status update, simulated processing, and response artifact. Bearer token auth is enforced on all endpoints except the agent card.

### Run

```bash
cd single-agent
uv sync
uv run python hello_world_agent.py --host 127.0.0.1 --port 41241
```

```bash
# From the a2a/ directory
uv run python cli.py --url http://localhost:41241 --token <your-token>
```

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

All agents route LLM calls through a LiteLLM proxy, which routes to Anthropic Claude via the Acuvity AI Security Gateway. Agent-to-agent A2A calls route through the same gateway when one is configured, or directly via Kubernetes service DNS when it isn't — see [Configuration](#configuration) below.

## Prerequisites

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com) |
| `A2A_TRAVEL_PLANNER_TOKEN` | Component token from [console.acuvity.ai](https://console.acuvity.ai) |
| `A2A_FLIGHTS_AGENT_TOKEN` | Component token from [console.acuvity.ai](https://console.acuvity.ai) |
| `A2A_HOTELS_AGENT_TOKEN` | Component token from [console.acuvity.ai](https://console.acuvity.ai) |
| `A2A_PRICING_AGENT_TOKEN` | Component token from [console.acuvity.ai](https://console.acuvity.ai) |
| `CA_BUNDLE_PATH` | Path to your CA bundle PEM file |

Import the [manifest file](./multi-agent/deploy/config/manifest.yaml) into [console.acuvity.ai](https://console.acuvity.ai), then issue a component token for each agent component.

For full instructions see the [Acuvity AppSec docs](https://docs.acuvity.ai/wURWAaVt0FMiS39eKrS9/appsec).

## Kubernetes Deployment

<details><summary>Click to expand</summary>

```bash
export ANTHROPIC_API_KEY=<your_anthropic_key>
export A2A_TRAVEL_PLANNER_TOKEN=<token>
export A2A_FLIGHTS_AGENT_TOKEN=<token>
export A2A_HOTELS_AGENT_TOKEN=<token>
export A2A_PRICING_AGENT_TOKEN=<token>
export CA_BUNDLE_PATH=<path/to/ca.pem>

./multi-agent/deploy/k8s/deploy.sh
```

This script creates the `a2a-multi-agent` namespace, applies the CA bundle, and installs the Helm chart.

To visualize this agent, import the [manifest file](./multi-agent/deploy/config/manifest.yaml) into the Acuvity console using [instructions provided here](../../infra/cli/README.md).

### Configuration

Each agent reads its configuration from `/app/config.yaml`, mounted into the pod from the `a2a-secrets` Secret. Helm renders this file from `deploy/k8s/charts/a2a-multi-agent/values.yaml` — the same values each agent reads locally from `multi-agent/src/backend/config.yaml`, just with Kubernetes service URLs and your tokens filled in.

To route agent-to-agent A2A traffic through the Acuvity AI Security Gateway, set `gateway.url`:

```bash
helm upgrade a2a-multi-agent ./multi-agent/deploy/k8s/charts/a2a-multi-agent \
  --namespace a2a-multi-agent \
  --reuse-values \
  --set gateway.url="https://<your-gateway-host>"
```

Leave `gateway.url` empty (`--set gateway.url=""`) to have agents call each other directly via Kubernetes service DNS instead.

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
