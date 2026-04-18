# Simple LangGraph Agent

A minimal LangGraph agent with optional chat UI. Traffic can go through the **Acuvity AI Security Gateway (Apex)** for governance and TLS to LLM and MCP providers.

## Start here

Pick **one** path first (each links to the full steps):


| Goal                                              | Where to go                                                                                                    |
| ------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| **Run locally** (batch or chat UI on your laptop) | [Layout](#layout) below, then [Run](#run) and [Interactive UI](#interactive-ui-chat-mode)                      |
| **Run on Kubernetes** (Helm, Docker Hub, Apex)    | **[deploy/k8s/README.md](deploy/k8s/README.md)** section **Full procedure: first install** (steps 1 through 8) |
| **Run with Docker Compose** (no cluster)          | **[deploy/compose/README.md](deploy/compose/README.md)** (optional; still needs Apex + LLM env)                |


## Layout

Unless a command says otherwise, use `**agents/ibac-demo`** as your current directory (this folder).

- `**src/agent/**` - Python app (`main.py`, `server.py`, `utils/`, `tools/`, …), `pyproject.toml`, and `**run.sh**` / `**run_ui.sh**` (from repo root: `./src/agent/run.sh` or `cd src/agent && ./run.sh`).
- `**src/ui/chat_ui/**` - Vite + React UI; production-style image from `src/ui/Dockerfile`.
- `**deploy/**` - Helm chart, Acuvity manifest, optional Compose. Index: **[deploy/README.md](deploy/README.md)**.
- `**assets/`** - Sample PDFs and diagrams for manual testing.

### Kubernetes (in-cluster)

To run **UI**, **agent**, and **CRM MCP** on any Kubernetes cluster (same idea as [langgraph](../langgraph/README.md) / [google_adk](../google_adk/README.md)), follow **[deploy/k8s/README.md](deploy/k8s/README.md)** end to end. After workloads are healthy, import **[deploy/config/providers-openrouter.yaml](deploy/config/providers-openrouter.yaml)** then **[deploy/config/manifest.yaml](deploy/config/manifest.yaml)** (`@org=${APP_ORG}` in the manifest: use **`envsubst`** or edit; full **`acuctl`** commands are in that doc). There is no separate `k3s/` tree: one Helm chart, your kubeconfig.

**Kubernetes quick start** (details and copy-paste commands are in **deploy/k8s/README.md** steps 1 through 8):

1. **Cluster:** Kubernetes running; `kubectl get nodes` shows **Ready** (e.g. [Rancher Desktop](https://rancherdesktop.io/) with Kubernetes on).
2. **Images:** `docker login` to Docker Hub. Set your Hub username once: `export DOCKER_HUB_USER=YOUR_DOCKER_ID` (replace with your real Docker ID; do not commit it). Then from this folder: `make docker-build` and `make docker-push` (or pass `DOCKER_HUB_USER=...` on each `make` line). Raw `docker build` / `docker push` commands are in the k8s README **step 2**.
3. **Install:** Export `ACUVITY_TOKEN`, `APEX_URL`, and your LLM secret (default chart uses OpenRouter). Run `**helm upgrade --install`** as in k8s README **step 5**, or from `**deploy/k8s`**: `./deploy.sh "${APEX_URL}"` (same as `deploy-ibac-demo.sh`) with `**DOCKER_HUB_USER**` set if images live on Hub. Full flags and CA ConfigMap are in that doc.
4. **UI:** `kubectl -n ibac-demo port-forward svc/ibac-demo-ui 3000:80` then open **[http://localhost:3000/](http://localhost:3000/)**.
5. **Governance:** Import the manifest per your process ([infra/cli](../../infra/cli/README.md) if your org uses it).

Do **not** put real Docker IDs or tokens in git; use placeholders in docs and secrets only in your shell.

## Accounts and tools (local development)

- Python 3.12+
- [uv](https://github.com/astral-sh/uv)
- An [Acuvity](https://console.acuvity.ai) account (for using the AI Security Gateway)
- An [OpenRouter](https://openrouter.ai/) account (default LLM for this demo)
- An [Arcade](https://www.arcade.dev/) account (when using `MCP_SERVER=arcade`)
- An [Anthropic](https://console.anthropic.com/) account (when using `LLM_PROVIDER=anthropic`)

## Environment variables


| Variable                        | Description                                                                                               |
| ------------------------------- | --------------------------------------------------------------------------------------------------------- |
| `ACUVITY_TOKEN`                 | Acuvity app token - always required                                                                       |
| `APEX_URL`                      | Acuvity gateway URL - always required                                                                     |
| `LLM_PROVIDER`                  | `openrouter` (default), `openai`, or `anthropic`                                                          |
| `OPENROUTER_API_KEY`            | Required when `LLM_PROVIDER=openrouter` (default)                                                         |
| `ANTHROPIC_API_KEY`             | Required when `LLM_PROVIDER=anthropic`                                                                    |
| `OPENAI_API_KEY`                | Required when `LLM_PROVIDER=openai`                                                                       |
| `MCP_SERVER`                    | `arcade` (default) or `local`                                                                             |
| `ARCADE_API_KEY`                | Required when `MCP_SERVER=arcade`                                                                         |
| `ARCADE_USER_ID`                | Required when `MCP_SERVER=arcade`                                                                         |
| `ARCADE_MCP_URL`                | Required when `MCP_SERVER=arcade`                                                                         |
| `LOCAL_MCP_SSE_URL`             | When set with `MCP_SERVER=local`, connect to remote MCP over **SSE** (Kubernetes/Docker) instead of stdio |
| `LOCAL_MCP_TRANSPORT`           | On the MCP process only: `stdio` (default) or `sse` (see `tools/mcp_tools.py`)                            |
| `FASTMCP_HOST` / `FASTMCP_PORT` | Bind address for SSE MCP server (use `0.0.0.0` in containers)                                             |
| `PROMPTS_TYPE`                  | `simple` (default), `scenario`, or `demo`                                                                 |


Advanced overrides (optional):


| Variable               | Description                                                                                                                                                                                                                                                            |
| ---------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `LLM_MODEL`            | Model name override. Defaults: `claude-opus-4-6` (Anthropic), `gpt-4o` (OpenAI)                                                                                                                                                                                        |
| `OPENROUTER_MODEL`     | OpenRouter model override (default: `stepfun/step-3.5-flash`)                                                                                                                                                                                                          |
| `LLM_BASE_URL`         | Override the API endpoint - enables any third-party compatible API                                                                                                                                                                                                     |
| `LLM_API_KEY`          | Override the API key - takes precedence over the provider-specific key                                                                                                                                                                                                 |
| `DEBUG_LLM`            | Set to `1` to print a non-secret LLM key fingerprint (`key_source`, last 4 chars of key, model) to stderr when `build_llm` runs. Use the same value when running `./src/agent/run.sh` / `./src/agent/run_ui.sh` to confirm both use the same key.                      |
| `DEBUG_PROXY_UPSTREAM` | Set to `1` when `HTTPS_PROXY` is set (e.g. `run_ui.sh`) to log full upstream HTTP details on agent errors: exception chain, `request_url`, `http_status`, and `response_body` (may be Acuvity gateway or LLM vendor). Do not share these logs if they contain secrets. |
| `IBAC_AGENT_ROOT`      | Optional absolute path to the agent package (folder with `main.py`, `tools/`, `prompt-scenarios/`). Defaults to resolving from `utils/paths.py`. Use if you run Python from an unusual working directory without `cd src/agent`.                                       |
| `IBAC_UPLOAD_DIR`      | Optional absolute path for PDF uploads. Defaults to `{agent root}/uploads`. Must match between the API server and `parse_file` when overridden.                                                                                                                        |


## Getting Acuvity App Token

- Access your [Acuvity](https://console.acuvity.ai) account
- Navigate to `Access > App Tokens`
- Create a token with an appropriate name and description.

## Getting your AI Security Gateway (Apex) URL

- Go to [https://console.acuvity.ai/me](https://console.acuvity.ai/me)
- Copy the `Apex` URL under `General` section

## Run

`LLM_PROVIDER` and `MCP_SERVER` are independent - any combination works.

`src/agent/run.sh` does the following:

- Validates required environment variables based on selected providers
- Sets up `ca.pem` from the Acuvity gateway
- Sets up the Acuvity AI Security Gateway as a proxy for all interactions to LLMs and MCP Servers via `HTTPS_PROXY`
- Runs `main.py` via `uv`

### Step 1 - Always required

```bash
export ACUVITY_TOKEN=...
export APEX_URL=https://...
```

### Step 2 - Pick your LLM

```bash
export LLM_PROVIDER=openrouter
export OPENROUTER_API_KEY=...        # openrouter (default)
export OPENROUTER_MODEL=stepfun/step-3.5-flash         # optional; find models at openrouter.ai/models

# OR

export LLM_PROVIDER=anthropic
export ANTHROPIC_API_KEY=...

# OR

export LLM_PROVIDER=openai
export OPENAI_API_KEY=...           # also works with Together AI, Groq, etc. via LLM_BASE_URL
```

### Step 3 - Pick your MCP server

```bash
export MCP_SERVER=local             # local tools with embedded attack patterns

# OR (arcade is the default - set all three)

export ARCADE_API_KEY=...
export ARCADE_USER_ID=...
export ARCADE_MCP_URL=...
```

### Step 4 - Pick your prompts (optional, default: simple)

```bash
export PROMPTS_TYPE=simple      # basic queries, tool usage, simple injection examples (default)

# OR

export PROMPTS_TYPE=scenario    # detailed multi-step attack scenarios (see src/agent/docs/test-scenarios.md)

# OR

export PROMPTS_TYPE=demo        # simplified scenarios for demos (see src/agent/prompt-scenarios/demo-prompts.txt)
```

### Step 5 - Run

From the `**ibac-demo**` directory:

```bash
./src/agent/run.sh
```

Output is automatically saved to `src/agent/docs/results.md`.

---

## Interactive UI (Chat Mode)

A live chat UI lets you send prompts interactively instead of running the batch demo.
It uses the same FastAPI + Vite React stack as the other agents in this repo.

### Stack

- **Backend**: FastAPI on `http://localhost:8300` (`src/agent/server.py`)
- **Frontend**: Vite + React + Tailwind in `src/ui/chat_ui/` on `http://localhost:5174`

### Step 1 - Start the backend

**With Acuvity AI Security Gateway (same as `./src/agent/run.sh`)**: use `./src/agent/run_ui.sh`. It validates required env vars, downloads `ca.pem` from your Apex URL, sets `HTTPS_PROXY`, `HTTP_PROXY`, and `SSL_CERT_FILE`, then starts the API server so LLM and MCP traffic is proxied through the gateway.

```bash
./src/agent/run_ui.sh
```

**Without the gateway** (local testing only): set only your LLM and MCP vars, then:

```bash
cd src/agent && uv run python3 server.py
```

The server initializes tools on the first request and stays warm for subsequent ones.

### Step 2 - Start the frontend

```bash
cd src/ui/chat_ui
npm install
npm run dev
```

Open [http://localhost:5174](http://localhost:5174) in your browser.

The Vite dev server proxies `/api/*` to the backend at `http://localhost:8300`, so no CORS config is needed.

The home screen loads demo scenarios from `GET /scenarios`, which reads `src/agent/prompt-scenarios/demo-prompts.txt` on the server (same content as before, no duplicate list in the frontend). Each card shows title and a one-line preview; clicking sends the **full** scenario text to the agent. Use **New chat** in the header or a full browser refresh to return to that home screen.

**PDF attachments**: Use the paperclip in the composer to attach a `.pdf` file. The API stores it under the agent `uploads/` directory (default `{agent root}/uploads`, gitignored) and appends the saved path to your message so the agent can call `parse_file` on that path. The `parse_file` tool reads the real PDF text from disk (via `pypdf`); only files under `uploads/` are allowed. You can send text only, PDF only, or both. Use a PDF from `assets/` at repo root if you want a fixed file for testing.

To point the frontend at a different backend host:

```bash
BACKEND_URL=http://your-host:8300 npm run dev
```

