# Chatbot Example with Google ADK

## Overview

This is a Google ADK Chatbot Demo that uses the Google Agent Development Kit to create a research assistant with MCP server integration.

## Architecture

In this demo, we have the following components:

- A **Web Interface** which presents a chat to the user. This is a Vite + React application making calls to the Agent.
- An **Agent** built with Google ADK using LiteLLM for model flexibility (default: Anthropic Claude).
- Some **[Secure MCP servers](https://mcp.acuvity.ai)** which provide additional capabilities to the Agent.

> [!TIP]
> Add more Secure MCP Servers as needed to make your Chatbot more powerful!

> [!NOTE]
> Understand the benefits of these MCP Secure Server by visiting our [Github mcp-servers-registry repository](https://github.com/acuvity/mcp-servers-registry)

### Framework used:

- [Google ADK](https://github.com/google/adk-python) - Google Agent Development Kit for building AI agents.
- [LiteLLM](https://github.com/BerriAI/litellm) - Unified interface for multiple LLM providers.
- [Minibridge](https://github.com/acuvity/minibridge) makes it secure and production ready in the [secure MCP servers](https://mcp.acuvity.ai).

### Enterprise Ready MCP servers used:

- mcp-server-sequential-thinking [Dockerfile](https://github.com/acuvity/mcp-servers-registry/tree/main/mcp-server-sequential-thinking) [Container](https://hub.docker.com/r/acuvity/mcp-server-sequential-thinking)
- mcp-server-brave-search [Dockerfile](https://github.com/acuvity/mcp-servers-registry/tree/main/mcp-server-brave-search) [Container](https://hub.docker.com/r/acuvity/mcp-server-brave-search)

## Prerequisites

- Python 3.12 or higher
- [uv](https://github.com/astral-sh/uv) package manager
- Node.js 22 or higher (for the UI)
- Docker (for containerized deployment)
- API keys for your chosen LLM provider (e.g., `ANTHROPIC_API_KEY`)

## Installation and Setup

### Getting started

Clone the repository:

```bash
git clone <repository-url>
cd agents/google_adk
```

### Running the Agent Locally

1. Install dependencies:

```bash
cd src/agent
uv sync
```

2. Create a `.env` file in `src/agent/` with your API keys:

```
ANTHROPIC_API_KEY=your_api_key_here
```

3. Run the agent:

```bash
uv run python main.py
```

The agent will start on `http://localhost:8300`.

### Running the UI Locally

1. Install dependencies:

```bash
cd src/ui/chat_ui
npm install
```

2. Run the development server:

```bash
npm run dev
```

The UI will start on `http://localhost:5174`.

Configure the backend URL via environment variable if needed:

```bash
BACKEND_URL=http://127.0.0.1:8300 npm run dev
```

### Deploying on Kubernetes

Set your API keys and run the deployment script:

```bash
export ANTHROPIC_API_KEY=your_anthropic_key
export BRAVE_API_KEY=your_brave_key
./deploy/k8s/deploy-app.yaml
```

This script installs the MCP servers and the application in the `g-adk-demo` namespace.

For configuration options, see `deploy/k8s/charts/g-adk-demo/values.yaml`.

## Configuration

The agent is configured via `src/agent/config.yaml`:

| Field | Description |
|-------|-------------|
| `app_name` | Application identifier |
| `title` | FastAPI title |
| `cors_origins` | Allowed CORS origins |
| `instruction` | System instruction for the agent |
| `mcp_servers` | List of MCP server configurations |
| `otel` | OpenTelemetry configuration |

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/send` | POST | Send a message to the agent |
| `/health` | GET | Health check endpoint |

### Example Request

```bash
curl -X POST http://localhost:8300/send \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, research assistant"}'
```

## Observability

The agent includes OpenTelemetry instrumentation with support for:

- Trace export to OTLP endpoints (default: 127.0.0.1 at `http://127.0.0.1:4317`)
- Console export for debugging
- FastAPI, HTTPX, MCP, GOOGLE-ADK, AIOHTTP, Threading and LiteLLM instrumentation

Configure observability settings in `config.yaml` under the `otel` section.