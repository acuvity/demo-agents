# Google ADK Demo

An agent built with Google Agent Development Kit (ADK).

## Overview

This demo provides a conversational AI Agent with the following capabilities:

- **Web Search** — Query the internet for real-time information via Brave Search
- **Sequential Thinking** — Advanced reasoning through structured thought processes
- **Extensible Architecture** — Add custom MCP servers to expand functionality

## Architecture

### Frameworks & Libraries

- [Google ADK](https://github.com/google/adk-python) — Google Agent Development Kit for building AI agents

### Acuvity Secure MCP Servers

| Server | Purpose | Resources |
|--------|---------|-----------|
| mcp-server-sequential-thinking | Structured reasoning and analysis | [Dockerfile](https://github.com/acuvity/mcp-servers-registry/tree/main/mcp-server-sequential-thinking) · [Container](https://hub.docker.com/r/acuvity/mcp-server-sequential-thinking) |
| mcp-server-brave-search | Web search capabilities | [Dockerfile](https://github.com/acuvity/mcp-servers-registry/tree/main/mcp-server-brave-search) · [Container](https://hub.docker.com/r/acuvity/mcp-server-brave-search) |

For additional MCP servers and capabilities, visit the [Acuvity MCP Servers Registry](https://mcp.acuvity.ai) or [Github](https://github.com/acuvity/mcp-servers-registry).

### API Keys

Obtain the following API keys before proceeding:

| Provider | Environment Variable | Obtain From |
|----------|---------------------|-------------|
| Anthropic | `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com) |
| Brave Search | `BRAVE_API_KEY` | [brave.com/search/api](https://brave.com/search/api) |


## Kubernetes Deployment

<details>

The deployment script handles the complete setup including MCP servers:

```bash
# Set required environment variables
export ANTHROPIC_API_KEY=<your_anthropic_key>
export BRAVE_API_KEY=<your_brave_key>

# Run the deployment script
./deploy/k8s/deploy-app.sh
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

## Configuration

The agent is configured via `src/agent/config.yaml` for local development.

For Kubernetes deployments, configuration is managed through Helm values in `deploy/k8s/charts/google-adk-demo/values.yaml`.

### Custom Deployment

Override values during installation:

```bash
helm install google-adk-demo ./deploy/k8s/charts/google-adk-demo \
  --namespace google-adk-demo \
  --set secrets.anthropicApiKey=$ANTHROPIC_API_KEY \
  --set secrets.braveApiKey=$BRAVE_API_KEY \
  --set agent.replicas=3 \
  --set agent.config.agentModel="anthropic/claude-sonnet-4-6"
```

</details>

## Local Development

<details>

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

The agent API will be available at `http://localhost:8300`.

### Web UI

1. Navigate to the UI directory and install dependencies:

```bash
cd src/ui/chat_ui
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

## Container Build

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

### Helm Chart Operations

```bash
# Package the Helm chart
make charts
```

</details>