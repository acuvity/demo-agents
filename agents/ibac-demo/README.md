# IBAC Demo

A minimal LangGraph agent with optional chat UI. Traffic can go through the **Acuvity AI Security Gateway (Apex)** for governance and TLS to LLM and MCP providers.

## Prerequisites

**Tools**

- [Docker Desktop](https://docs.docker.com/get-docker/) (Mac/Windows) or Rancher Desktop

**Accounts**

- [Acuvity](https://console.acuvity.ai) - get your app token from `Access > App Tokens`; get your Apex URL from [Acuvity Console](https://console.acuvity.dev/)
- [OpenRouter](https://openrouter.ai/) - default LLM provider (or use the keys provided)

## Quick Start

### Step 1 - Clone the repo

```bash
git clone https://github.com/acuvity/demo-agents.git
cd demo-agents/agents/ibac-demo
```

### Step 2 - Set your credentials

Create a file at `deploy/compose/.env` (use any text editor, or run the command below):

```bash
cat > deploy/compose/.env <<EOF
ACUVITY_TOKEN=...
APEX_URL=https://...
OPENROUTER_API_KEY=...
EOF
```

> If using OpenAI instead, add `LLM_PROVIDER=openai` and `OPENAI_API_KEY=...`

### Step 3 - Start everything

```bash
cd deploy/compose
make start
```

This builds and starts the UI, agent, MCP server, email capture, and webhook logger.

### Step 4 - Open in your browser


| What                            | URL                                                          |
| ------------------------------- | ------------------------------------------------------------ |
| Demo UI                         | [http://localhost:5174](http://localhost:5174)               |
| Captured emails (Demo 1)        | [http://localhost:8025](http://localhost:8025)               |
| Captured webhook calls (Demo 2) | [http://localhost:9000/events](http://localhost:9000/events) |


To stop: `make stop`. To view logs: `make logs`.

## Deploy to Kubernetes

Build and push images first (requires a [Docker Hub](https://hub.docker.com/) account). Run these from the repo root (`demo-agents/agents/ibac-demo`):

```bash
export DOCKER_HUB_USER=YOUR_DOCKER_ID
docker login
make docker-build
make docker-push
```

Then follow [deploy/k8s/README.md](deploy/k8s/README.md).

---

## Run without Docker (local dev)

**Tools needed:** Python 3.12+, [uv](https://github.com/astral-sh/uv), Node.js

**Step 1 - Set credentials (Terminal 1)**

```bash
export ACUVITY_TOKEN=...
export APEX_URL=https://...
export OPENROUTER_API_KEY=...
```

**Step 2 - Start the backend (Terminal 1)**

```bash
./src/agent/run_ui.sh
```

**Step 3 - Start the frontend (Terminal 2)**

```bash
cd src/ui/chat_ui
npm install
npm run dev
```

Open [http://localhost:5174](http://localhost:5174) in your browser.

---

## Advanced overrides (optional)


| Variable                        | Description                                                                       |
| ------------------------------- | --------------------------------------------------------------------------------- |
| `OPENROUTER_MODEL`              | OpenRouter model override (default: `stepfun/step-3.5-flash`)                     |
| `LLM_MODEL`                     | Model name override for OpenAI (default: `gpt-4o`)                                |
| `LLM_BASE_URL`                  | Override the API endpoint - enables any third-party compatible API                |
| `LLM_API_KEY`                   | Override the API key - takes precedence over the provider-specific key            |
| `MCP_SERVER`                    | `local` (default) or `arcade` - switches between local tools and Arcade MCP       |
| `LOCAL_MCP_SSE_URL`             | When set with `MCP_SERVER=local`, connect to remote MCP over SSE instead of stdio |
| `LOCAL_MCP_TRANSPORT`           | On the MCP process only: `stdio` (default) or `sse`                               |
| `FASTMCP_HOST` / `FASTMCP_PORT` | Bind address for SSE MCP server (use `0.0.0.0` in containers)                     |
| `IBAC_AGENT_ROOT`               | Absolute path to the agent package. Defaults to resolving from `utils/paths.py`   |
| `IBAC_UPLOAD_DIR`               | Absolute path for PDF uploads. Defaults to `{agent root}/uploads`                 |
| `DEBUG_LLM`                     | Set to `1` to print LLM key fingerprint to stderr                                 |
| `DEBUG_PROXY_UPSTREAM`          | Set to `1` to log full upstream HTTP details on agent errors                      |


