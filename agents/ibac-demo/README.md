# Simple LangGraph Agent

A minimal LangGraph agent that uses the Acuvity AI Security Gateway.

AI Security Gateway

## Layout

Unless a command says otherwise, run it with your **current directory set to `ibac-demo`** (this folder).

- `**src/agent/**` - Python app (`main.py`, `server.py`, `utils/`, `tools/`, `prompt-scenarios/`, `docs/`, `tests/`), `pyproject.toml`, and Acuvity `**run.sh**` / `**run_ui.sh**` (run as `./src/agent/run.sh` or `cd src/agent && ./run.sh`).
- `**src/ui/chat_ui/**` - Vite + React chat UI (container image builds from `**src/ui/Dockerfile**` with context `src/ui`, same pattern as langgraph/google_adk)
- `**deploy/**` - Kubernetes Helm chart, Acuvity **manifest** import, optional Docker Compose ([deploy/k8s/README.md](deploy/k8s/README.md))
- `**assets/`** (repo root) - Diagram for this README and sample PDFs for manual UI upload testing (e.g. `Q4_Operations_Report.pdf`)

### Remote deployment (Kubernetes + Acuvity manifest)

To run the **UI**, **agent**, and **CRM MCP** in-cluster (same pattern as [fast-agent](../fast-agent)), see [deploy/k8s/README.md](deploy/k8s/README.md). Build images from `src/agent/Dockerfile` and `src/ui/Dockerfile`, install the Helm chart, then import [deploy/config/manifest.yaml](deploy/config/manifest.yaml) after replacing placeholders. Local laptop workflows stay the same: `MCP_SERVER=local` without `LOCAL_MCP_SSE_URL` still uses **stdio** to `tools/mcp_tools.py`.

## Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv)
- An [Acuvity](https://console.acuvity.ai) account (for using the AI Security Gateway)
- An [Arcade](https://www.arcade.dev/) account (when using `MCP_SERVER=arcade`)
- An [OpenRouter](https://openrouter.ai/) account (when using `LLM_PROVIDER=openrouter`)

## Environment variables


| Variable                        | Description                                                                                               |
| ------------------------------- | --------------------------------------------------------------------------------------------------------- |
| `ACUVITY_TOKEN`                 | Acuvity app token - always required                                                                       |
| `APEX_URL`                      | Acuvity gateway URL - always required                                                                     |
| `LLM_PROVIDER`                  | `anthropic` (default), `openai`, or `openrouter`                                                          |
| `ANTHROPIC_API_KEY`             | Required when `LLM_PROVIDER=anthropic`                                                                    |
| `OPENAI_API_KEY`                | Required when `LLM_PROVIDER=openai`                                                                       |
| `OPENROUTER_API_KEY`            | Required when `LLM_PROVIDER=openrouter`                                                                   |
| `MCP_SERVER`                    | `arcade` (default) or `local`                                                                             |
| `ARCADE_API_KEY`                | Required when `MCP_SERVER=arcade`                                                                         |
| `ARCADE_USER_ID`                | Required when `MCP_SERVER=arcade`                                                                         |
| `ARCADE_MCP_URL`                | Required when `MCP_SERVER=arcade`                                                                         |
| `LOCAL_MCP_SSE_URL`             | When set with `MCP_SERVER=local`, connect to remote MCP over **SSE** (Kubernetes/Docker) instead of stdio |
| `LOCAL_MCP_TRANSPORT`           | On the MCP process only: `stdio` (default) or `sse` (see `tools/mcp_tools.py`)                          |
| `FASTMCP_HOST` / `FASTMCP_PORT` | Bind address for SSE MCP server (use `0.0.0.0` in containers)                                             |
| `PROMPTS_TYPE`                  | `simple` (default), `scenario`, or `demo`                                                                 |


Advanced overrides (optional):


| Variable           | Description                                                                                                                                                                                                                                                                       |
| ------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `LLM_MODEL`        | Model name override. Defaults: `claude-opus-4-6` (Anthropic), `gpt-4o` (OpenAI)                                                                                                                                                                                                   |
| `OPENROUTER_MODEL` | OpenRouter model override (default: `stepfun/step-3.5-flash`)                                                                                                                                                                                                                     |
| `LLM_BASE_URL`     | Override the API endpoint - enables any third-party compatible API                                                                                                                                                                                                                |
| `LLM_API_KEY`      | Override the API key - takes precedence over the provider-specific key                                                                                                                                                                                                            |
| `DEBUG_LLM`        | Set to `1` to print a non-secret LLM key fingerprint (`key_source`, last 4 chars of key, model) to stderr when `build_llm` runs. Use the same value when running `./src/agent/run.sh` / `./src/agent/run_ui.sh` to confirm both use the same key. |
| `IBAC_AGENT_ROOT`  | Optional absolute path to the agent package (folder with `main.py`, `tools/`, `prompt-scenarios/`). Defaults to resolving from `utils/paths.py`. Use if you run Python from an unusual working directory without `cd src/agent`.                                                  |
| `IBAC_UPLOAD_DIR`  | Optional absolute path for PDF uploads. Defaults to `{agent root}/uploads`. Must match between the API server and `parse_file` when overridden.                                                                                                                                   |


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
export ANTHROPIC_API_KEY=...        # anthropic (default)

# OR

export LLM_PROVIDER=openrouter
export OPENROUTER_API_KEY=...
export OPENROUTER_MODEL=stepfun/step-3.5-flash         # find models at openrouter.ai/models

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

---

## HTML summary

A self-contained HTML demo page can be generated for presenting the attack scenarios to non-technical audiences.

### What it shows

- Agent architecture diagram and tool inventory (which tools are POISONED vs CLEAN)
- Plain-English explanation of indirect prompt injection
- Per-scenario cards: the user request, the exact injection text highlighted inside the tool definition, the actual tool calls made (UNAUTHORIZED vs LEGITIMATE), and a one-line client takeaway
- How Acuvity detects misalignment

### Workflow

```bash
# 1. Run the agent with demo prompts to get fresh tool-call traces
export PROMPTS_TYPE=demo
./src/agent/run.sh

# 2. Generate the HTML page
cd src/agent && uv run python3 docs/generate_demo.py

# 3. Open in browser (from ibac-demo root)
open src/agent/docs/demo.html
```

### Updating scenarios

The generator reads source files directly - no manual HTML editing:


| What changes                         | File to edit                                                       | Action           |
| ------------------------------------ | ------------------------------------------------------------------ | ---------------- |
| Prompt wording or title              | `src/agent/prompt-scenarios/demo-prompts.txt`                      | Re-run generator |
| PREREQ injection text or target tool | `src/agent/tools/mcp_tools.py`                                   | Re-run generator |
| Which tool the prompt triggers       | `src/agent/prompt-scenarios/demo-scenarios.json` (`intended_tool`) | Re-run generator |
| Attack type label or story text      | `src/agent/prompt-scenarios/demo-scenarios.json`                   | Re-run generator |


