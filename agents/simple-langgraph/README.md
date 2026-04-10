# Simple LangGraph Agent

A minimal LangGraph agent that uses the Acuvity AI Security Gateway.

![AI Security Gateway](./images/agent.png)


## Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv)
- An [Acuvity](https://console.acuvity.ai) account (for using the AI Security Gateway)
- An [Arcade](https://www.arcade.dev/) account (when using `MCP_SERVER=arcade`)
- An [OpenRouter](https://openrouter.ai/) account (when using `LLM_PROVIDER=openrouter`)

## Environment variables

| Variable | Description |
|---|---|
| `ACUVITY_TOKEN` | Acuvity app token - always required |
| `APEX_URL` | Acuvity gateway URL - always required |
| `LLM_PROVIDER` | `anthropic` (default), `openai`, or `openrouter` |
| `ANTHROPIC_API_KEY` | Required when `LLM_PROVIDER=anthropic` |
| `OPENAI_API_KEY` | Required when `LLM_PROVIDER=openai` |
| `OPENROUTER_API_KEY` | Required when `LLM_PROVIDER=openrouter` |
| `MCP_SERVER` | `arcade` (default) or `local` |
| `ARCADE_API_KEY` | Required when `MCP_SERVER=arcade` |
| `ARCADE_USER_ID` | Required when `MCP_SERVER=arcade` |
| `ARCADE_MCP_URL` | Required when `MCP_SERVER=arcade` |
| `PROMPTS_TYPE` | `simple` (default), `scenario`, or `demo` |

Advanced overrides (optional):

| Variable | Description |
|---|---|
| `LLM_MODEL` | Model name override. Defaults: `claude-opus-4-6` (Anthropic), `gpt-4o` (OpenAI) |
| `OPENROUTER_MODEL` | OpenRouter model override (default: `stepfun/step-3.5-flash:free`) |
| `LLM_BASE_URL` | Override the API endpoint - enables any third-party compatible API |
| `LLM_API_KEY` | Override the API key - takes precedence over the provider-specific key |

## Getting Acuvity App Token

 - Access your [Acuvity](https://console.acuvity.ai) account
 - Navigate to `Access > App Tokens`
 - Create a token with an appropriate name and description.

## Getting your AI Security Gateway (Apex) URL

 - Go to [https://console.acuvity.ai/me](https://console.acuvity.ai/me)
 - Copy the `Apex` URL under `General` section

## Run

`LLM_PROVIDER` and `MCP_SERVER` are independent - any combination works.

`run.sh` does the following:
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
export LLM_MODEL= stepfun/step-3.5-flash                  # find models at openrouter.ai/models, eg: stepfun/step-3.5-flash

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

export PROMPTS_TYPE=scenario    # detailed multi-step attack scenarios (see docs/test-scenarios.md)

# OR

export PROMPTS_TYPE=demo        # simplified scenarios for demos (see prompt-scenarios/demo-prompts.txt)
```

### Step 5 - Run

```bash
./run.sh
```

Output is automatically saved to `docs/results.md`.

---

## Interactive UI (Chat Mode)

A live chat UI lets you send prompts interactively instead of running the batch demo.
It uses the same FastAPI + Vite React stack as the other agents in this repo.

### Stack

- **Backend**: FastAPI on `http://localhost:8300` (`server.py`)
- **Frontend**: Vite + React + Tailwind in `ui/chat_ui/` on `http://localhost:5174`

### Step 1 - Start the backend

**With Acuvity AI Security Gateway (same as `./run.sh`)**: use `run_ui.sh`. It validates required env vars, downloads `ca.pem` from your Apex URL, sets `HTTPS_PROXY`, `HTTP_PROXY`, and `SSL_CERT_FILE`, then starts the API server so LLM and MCP traffic is proxied through the gateway.

```bash
./run_ui.sh
```

**Without the gateway** (local testing only): set only your LLM and MCP vars, then:

```bash
uv run python3 server.py
```

The server initializes tools on the first request and stays warm for subsequent ones.

### Step 2 - Start the frontend

```bash
cd ui/chat_ui
npm install
npm run dev
```

Open [http://localhost:5174](http://localhost:5174) in your browser.

The Vite dev server proxies `/api/*` to the backend at `http://localhost:8300`, so no CORS config is needed.

The home screen lists all demo scenarios from `prompt-scenarios/demo-prompts.txt`. Each card shows a short title and preview; clicking sends the **full** scenario text to the agent (same wording as the file, not truncated). Use **New chat** in the header or a full browser refresh to return to that home screen.

**PDF attachments**: Use the paperclip in the composer to attach a `.pdf` file. The API stores it under `uploads/` (gitignored) and appends the saved path to your message so the agent can call `parse_file` on that path. You can send text only, PDF only, or both.

To point the frontend at a different backend host:

```bash
BACKEND_URL=http://your-host:8300 npm run dev
```

---

## Client Demo

A self-contained HTML demo page can be generated for presenting the attack scenarios to non-technical audiences.

### What it shows

- Agent architecture diagram and tool inventory (which tools are POISONED vs CLEAN)
- Plain-English explanation of indirect prompt injection
- Per-scenario cards: the user request, the exact injection text highlighted inside the tool definition, the actual tool calls made (UNAUTHORIZED vs LEGITIMATE), and a one-line client takeaway
- How Acuvity detects misalignment

### Pre-demo workflow

```bash
# 1. Run the agent with demo prompts to get fresh tool-call traces
export PROMPTS_TYPE=demo
./run.sh

# 2. Generate the HTML page
uv run docs/generate_demo.py

# 3. Open in browser
open docs/demo.html
```

### Updating scenarios

The generator reads source files directly - no manual HTML editing:

| What changes | File to edit | Action |
|---|---|---|
| Prompt wording or title | `prompt-scenarios/demo-prompts.txt` | Re-run generator |
| PREREQ injection text or target tool | `tools/local_tools.py` | Re-run generator |
| Which tool the prompt triggers | `prompt-scenarios/demo-scenarios.json` (`intended_tool`) | Re-run generator |
| Attack type label or story text | `prompt-scenarios/demo-scenarios.json` | Re-run generator |
