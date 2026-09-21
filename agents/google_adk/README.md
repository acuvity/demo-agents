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

## Prerequisites

Obtain the following API keys before proceeding:

| Provider | Environment Variable | Obtain From |
|----------|---------------------|-------------|
| Anthropic | `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com) |
| Brave Search | `BRAVE_API_KEY` | [brave.com/search/api](https://brave.com/search/api) |
| Acuvity | `GOOGLE_ADK_AGENT_TOKEN` | Component token — issue at [console.acuvity.ai](https://console.acuvity.ai) after manifest import (see below) |
| Acuvity | `GOOGLE_ADK_LITELLM_TOKEN` | Component token — issue at [console.acuvity.ai](https://console.acuvity.ai) after manifest import (see below) |
| Acuvity | `PROXY_HOST` | Host of your AI Security Gateway deployment (e.g. `ais-demo-gw.<namespace>.svc.cluster.local`) |
| — | `CA_BUNDLE_PATH` | Path to your CA bundle PEM file for TLS verification |

### Component Tokens

The agent and LiteLLM tokens are **component tokens** issued by the Acuvity platform to authenticate each workload through the AI Security Gateway:

1. Import the [manifest file](./deploy/config/manifest.yaml) into [console.acuvity.ai](https://console.acuvity.ai)
2. Once imported, issue a component token for each component (`agent`, `litellm`) from the console
3. Set `PROXY_HOST` to the host of your AI Security Gateway deployment

For full instructions see the [Acuvity AppSec docs](https://docs.acuvity.ai/wURWAaVt0FMiS39eKrS9/appsec).

### Proxy Mode vs AI Gateway Mode

The agent can route its LLM and MCP traffic through Acuvity in one of two ways, selected via `mode` (`proxy` by default):

- **Proxy mode** (`mode=proxy`) — the agent and its self-hosted LiteLLM sidecar make requests transparently via `HTTPS_PROXY`/`HTTP_PROXY`, trusting Acuvity's dynamic CA, with the component token embedded as Basic-auth userinfo in the proxy URL. This is the default and matches the setup described above.
- **Gateway mode** (`mode=gateway`) — the agent instead calls Acuvity's `AIGatewayConnector` endpoints directly: `<gateway_base_url>/<gateway_llm_route>` for the LLM (litellm appends `/v1/messages`) and `<gateway_base_url>/mcp` for all configured MCP servers (a single shared endpoint, with tool names returned prefixed by provider). Auth is a plain `Authorization: Bearer <token>` header — no CA trust required, no self-hosted LiteLLM deployment. Arcade (`arcade-mcp-gateway`) is a third-party MCP integration and is never routed through Acuvity in either mode.

Gateway mode requires these on the **Acuvity/apex side** before it will work, independent of any change in this repo:

1. `APEX_PROVIDER_TOKEN_KEYS` set on the apex deployment, so it can decrypt the `ProviderTokenPool` holding the real upstream provider credentials.
2. A reachable Redis instance configured via `APEX_REDIS_ADDRESS` (and `APEX_REDIS_DISABLE_TLS` if applicable), used to track `Mcp-Session-Id` state for MCP traffic.
3. Each MCP-type `Provider` behind the gateway needs a non-empty `tools` baseline before `toolswatch` will report a snapshot for it.
4. Each MCP `AIGatewayConnector` needs an explicit `upstreamURL` (with `/mcp` suffix) rather than relying on the provider-derived default.
5. The token used as `GOOGLE_ADK_AGENT_TOKEN` in gateway mode must be a real **app component token** (not a plain deployment apptoken) — issue/renew it from the imported app's `agent` component.

To deploy in gateway mode, set `MODE=gateway` and `GATEWAY_BASE_URL` to the gateway's root URL (e.g. `https://<apex-host>/<org>/<gateway-name>`, without a trailing route) — see the [Kubernetes Deployment](#kubernetes-deployment) section below.

## Kubernetes Deployment

<details><summary>Click to expand</summary>

The deployment script handles the complete setup including MCP servers:

```bash
# Proxy mode (default)
export ANTHROPIC_API_KEY=<your_anthropic_key>
export BRAVE_API_KEY=<your_brave_key>
export GOOGLE_ADK_AGENT_TOKEN=<your_agent_component_token>
export GOOGLE_ADK_LITELLM_TOKEN=<your_litellm_component_token>
export PROXY_HOST=<your_ai_security_gateway_host>
export CA_BUNDLE_PATH=<path/to/ca.pem>

# Run the deployment script
./deploy/k8s/deploy.sh
```

```bash
# Gateway mode
export MODE=gateway
export ANTHROPIC_API_KEY=<your_anthropic_key>
export BRAVE_API_KEY=<your_brave_key>
export GOOGLE_ADK_AGENT_TOKEN=<your_agent_component_token>
export GATEWAY_BASE_URL=<https://apex-host/org/gateway-name>
export CA_BUNDLE_PATH=<path/to/ca.pem>

# Run the deployment script
./deploy/k8s/deploy.sh
```

See [Proxy Mode vs AI Gateway Mode](#proxy-mode-vs-ai-gateway-mode) above for the Acuvity-side prerequisites gateway mode needs.

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
