# Google ADK Demo

A conversational AI agent built with [Google Agent Development Kit (ADK)](https://github.com/google/adk-python).

## Overview

This demo provides a conversational AI agent with the following capabilities:

- **Web Search** — Query the internet for real-time information via Brave Search
- **Sequential Thinking** — Advanced reasoning through structured thought processes
- **Extensible Architecture** — Add custom MCP servers to expand functionality

NOTE: This demo agent has a [manifest file](./deploy/config/manifest.yaml) which describes the components in the agent as well as access policies in there.

## Architecture

### Frameworks & Libraries

- [Google ADK](https://github.com/google/adk-python) — Google Agent Development Kit for building AI agents

### Acuvity Secure MCP Servers

| Server | Purpose | Resources |
|--------|---------|-----------|
| mcp-server-sequential-thinking | Structured reasoning and analysis | [Dockerfile](https://github.com/acuvity/mcp-servers-registry/tree/main/mcp-server-sequential-thinking) · [Container](https://hub.docker.com/r/acuvity/mcp-server-sequential-thinking) |
| mcp-server-brave-search | Web search capabilities | [Dockerfile](https://github.com/acuvity/mcp-servers-registry/tree/main/mcp-server-brave-search) · [Container](https://hub.docker.com/r/acuvity/mcp-server-brave-search) |

For additional MCP servers and capabilities, visit the [Acuvity MCP Servers Registry](https://mcp.acuvity.ai) or [GitHub](https://github.com/acuvity/mcp-servers-registry).

## Connectivity Modes

The deployment supports two independent connectivity modes — one for the agent workload and one for LiteLLM — so you can mix and match based on what credentials you have.

### Agent

| Condition | Behaviour | Extra requirements |
|-----------|-----------|-------------------|
| `GOOGLE_ADK_AGENT_TOKEN` provided | Outbound traffic is routed through the AI Security Gateway via an authenticated HTTP/S proxy (`http://token:<token>@<host>:<port>`). | `PROXY_HOST`, `CA_BUNDLE_PATH` |
| Token absent | No proxy; agent connects directly. | — |

### LiteLLM

| Condition | Behaviour | Extra requirements |
|-----------|-----------|-------------------|
| `GATEWAY_URL` provided | LiteLLM calls the Acuvity gateway as `api_base`, authenticated with `GOOGLE_ADK_LITELLM_TOKEN`. No CA bundle or transport proxy needed. | `GOOGLE_ADK_LITELLM_TOKEN` |
| `GATEWAY_URL` absent | LiteLLM calls the Anthropic API via transport proxy, authenticated with `GOOGLE_ADK_LITELLM_TOKEN`. | `GOOGLE_ADK_LITELLM_TOKEN`, `ANTHROPIC_API_KEY`, `PROXY_HOST`, `CA_BUNDLE_PATH` |

> **`PROXY_HOST` and `CA_BUNDLE_PATH`** are only required when at least one component runs in proxy mode (LiteLLM without a gateway URL, or the agent with a component token).

## Prerequisites

Obtain the following credentials before proceeding:

| Variable | Required when | Obtain From |
|----------|--------------|-------------|
| `BRAVE_API_KEY` | Always | [brave.com/search/api](https://brave.com/search/api) |
| `LITELLM_MASTER_KEY` | Always | Choose any secret string |
| `GOOGLE_ADK_LITELLM_TOKEN` | Always | Component token — issue at [console.acuvity.ai](https://console.acuvity.ai) after manifest import |
| `GATEWAY_URL` | LiteLLM gateway mode | URL of your Acuvity gateway endpoint |
| `ANTHROPIC_API_KEY` | LiteLLM proxy mode (no `GATEWAY_URL`) | [console.anthropic.com](https://console.anthropic.com) |
| `GOOGLE_ADK_AGENT_TOKEN` | Agent proxy mode (optional) | Component token — issue at [console.acuvity.ai](https://console.acuvity.ai) after manifest import |
| `PROXY_HOST` | Any proxy mode | Host of your AI Security Gateway (e.g. `ais-demo-gw.<namespace>.svc.cluster.local`) |
| `CA_BUNDLE_PATH` | Any proxy mode | Path to your CA bundle PEM file for TLS verification |

### Component Tokens

The agent and LiteLLM tokens are **component tokens** issued by the Acuvity platform to authenticate each workload through the AI Security Gateway:

1. Import the [manifest file](./deploy/config/manifest.yaml) into [console.acuvity.ai](https://console.acuvity.ai)
2. Once imported, issue a component token for each component (`agent`, `litellm`) from the console
3. Set `PROXY_HOST` to the host of your AI Security Gateway deployment

For full instructions see the [Acuvity AppSec docs](https://docs.acuvity.ai/wURWAaVt0FMiS39eKrS9/appsec).

## Kubernetes Deployment

<details><summary>Click to expand</summary>

The deployment script handles the complete setup including MCP servers.

**Gateway mode** — LiteLLM calls the Acuvity gateway; agent also uses authenticated proxy:

```bash
export BRAVE_API_KEY=<your_brave_key>
export LITELLM_MASTER_KEY=<secret>
export GATEWAY_URL=<your_acuvity_gateway_url>
export GOOGLE_ADK_LITELLM_TOKEN=<your_litellm_component_token>
export GOOGLE_ADK_AGENT_TOKEN=<your_agent_component_token>  # enables agent proxy
export PROXY_HOST=<your_ai_security_gateway_host>           # required with agent token
export CA_BUNDLE_PATH=<path/to/ca.pem>                      # required with agent token

./deploy/k8s/deploy.sh
```

**Proxy mode** — LiteLLM calls Anthropic directly via transport proxy:

```bash
export BRAVE_API_KEY=<your_brave_key>
export LITELLM_MASTER_KEY=<secret>
export ANTHROPIC_API_KEY=<your_anthropic_key>
export PROXY_HOST=<your_ai_security_gateway_host>
export CA_BUNDLE_PATH=<path/to/ca.pem>
export GOOGLE_ADK_AGENT_TOKEN=<your_agent_component_token>  # optional, enables agent proxy

./deploy/k8s/deploy.sh
```

This script will:

1. Create the `google-adk-demo` namespace
2. Install the Sequential Thinking MCP server
3. Install the Brave Search MCP server
4. Deploy the agent and UI components

### Accessing the Application

Once deployed, forward the UI service to your local machine:

```bash
kubectl -n google-adk-demo port-forward svc/google-adk-demo-ui-svc 5174:80
```

Open your browser and navigate to `http://localhost:5174`.

To visualize this agent, import the [manifest file](./deploy/config/manifest.yaml) into Acuvity console using [instructions provided here](../../infra/cli/README.md).


</details>

## Configuration

For Kubernetes deployments, configuration is managed through Helm values in `deploy/k8s/charts/google-adk-demo/values.yaml`.

### Custom Deployment

Override values during Helm installation:

```bash
helm install google-adk-demo ./deploy/k8s/charts/google-adk-demo \
  --namespace google-adk-demo \
  --set secrets.anthropicApiKey=$ANTHROPIC_API_KEY \
  --set secrets.braveApiKey=$BRAVE_API_KEY \
  --set agent.replicas=3 \
  --set agent.config.agentModel="anthropic/claude-sonnet-4-6"
```

## Local Development

<details><summary>Click to expand</summary>

### Agent Backend

1. Navigate to the agent directory and install dependencies:

```bash
cd src/agent
uv sync
```

2. Create a `.env` file with your API credentials:

```bash
cat > .env << EOF
ANTHROPIC_API_KEY=<your_anthropic_key>
BRAVE_API_KEY=<your_brave_key>
EOF
```

3. Start the agent server:

```bash
uv run python main.py
```

4. The agent is configured via `src/agent/config.yaml` for local development.


The agent API will be available at `http://localhost:8300`.

### Web UI

1. Navigate to the UI directory and install dependencies:

```bash
cd src/ui
npm install
```

2. Start the development server:

```bash
npm run dev
```

The web interface will be available at `http://localhost:5174`.

To connect to a different backend URL:

```bash
BACKEND_URL=http://your-backend-host:8300 npm run dev
```

</details>

## Container Build

<details><summary>Click to expand</summary>

The project includes a `Makefile` for streamlined container operations.

### Build Containers Locally

```bash
# Build both agent and UI containers
make containers
```

### Build and Push to Registry

```bash
# Set your registry (default: acuvity)
export OCI_REGISTRY=<your_container_registry>

# Build and push containers
make push
```

### Package the Helm Chart

```bash
make charts
```

</details>
