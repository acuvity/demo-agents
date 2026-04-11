# Simple LangGraph Agent

A minimal LangGraph agent that uses the Acuvity AI Security Gateway.

![AI Security Gateway](./assets/agent.png)

## Layout

Unless a command says otherwise, run it with your **current directory set to `ibac-demo`** (this folder).

- **`src/agent/`** - Python app (`main.py`, `server.py`, `utils/`, `tools/`, `prompt-scenarios/`, `docs/`, `tests/`), `pyproject.toml`, and Acuvity **`run.sh`** / **`run_ui.sh`**. You can also run **`./run.sh`** or **`./run_ui.sh`** at this root; they forward to `src/agent/`.
- **`src/ui/chat_ui/`** - Vite + React chat UI
- **`assets/`** (repo root) - Diagram for this README and sample PDFs for manual UI upload testing (e.g. `Q4_Operations_Report.pdf`)

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
| `OPENROUTER_MODEL` | OpenRouter model override (default: `stepfun/step-3.5-flash`) |
| `LLM_BASE_URL` | Override the API endpoint - enables any third-party compatible API |
| `LLM_API_KEY` | Override the API key - takes precedence over the provider-specific key |
| `DEBUG_LLM` | Set to `1` to print a non-secret LLM key fingerprint (`key_source`, last 4 chars of key, model) to stderr when `build_llm` runs. Use the same value when running `./run.sh` / `./run_ui.sh` (or `./src/agent/run.sh` / `./src/agent/run_ui.sh`) to confirm both use the same key. |

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

From the **`ibac-demo`** directory:

```bash
./run.sh
# equivalent: ./src/agent/run.sh
```

Output is automatically saved to `src/agent/docs/results.md`.

### OpenRouter: UI works but `./run.sh` fails

`./run.sh` and the chat UI both call the same `build_llm()` in `src/agent/utils/config.py` behind the same Acuvity proxy. If the batch script fails while the UI succeeds, check the following.

1. **Same key in both terminals**  
   The UI backend inherits the environment from the shell that started `./run_ui.sh` (or `./src/agent/run_ui.sh`, or `cd src/agent && uv run python3 server.py`). `./run.sh` uses the shell where you invoke it. A different `OPENROUTER_API_KEY`, or only one of them having `LLM_API_KEY` set, explains mismatches.  
   Run with `DEBUG_LLM=1` in both places and compare the printed `key_source`, `key_tail`, and model line. They should match.

2. **Per-key limits on OpenRouter**  
   At [openrouter.ai/keys](https://openrouter.ai/keys), each API key can have its own usage cap. Account credits can look fine while a specific key returns a limit-style error. Raise the cap, remove it, or create a new key and export it in every shell you use.

3. **Batch volume and rate limits**  
   `./run.sh` runs every prompt in the selected file; each run can trigger multiple LLM calls (tool loops). Default `PROMPTS_TYPE=simple` issues many requests in a short time. OpenRouter signals rate limiting with **HTTP 429**. Try `PROMPTS_TYPE=demo` or a smaller custom prompt file to confirm.

4. **Prompt content and moderation**  
   `simple` and `scenario` files include adversarial example lines. The UI home cards use benign CRM-style text. Some models return **HTTP 403** when input is moderation-flagged. If failures line up with specific prompts, try `PROMPTS_TYPE=demo` to compare.

**OpenRouter HTTP codes** (see [errors and debugging](https://openrouter.ai/docs/api/reference/errors-and-debugging)): **402** insufficient credits, **429** rate limited, **403** moderation flagged (for documented cases).

---

## Interactive UI (Chat Mode)

A live chat UI lets you send prompts interactively instead of running the batch demo.
It uses the same FastAPI + Vite React stack as the other agents in this repo.

### Stack

- **Backend**: FastAPI on `http://localhost:8300` (`src/agent/server.py`)
- **Frontend**: Vite + React + Tailwind in `src/ui/chat_ui/` on `http://localhost:5174`

### Step 1 - Start the backend

**With Acuvity AI Security Gateway (same as `./run.sh`)**: use `run_ui.sh`. It validates required env vars, downloads `ca.pem` from your Apex URL, sets `HTTPS_PROXY`, `HTTP_PROXY`, and `SSL_CERT_FILE`, then starts the API server so LLM and MCP traffic is proxied through the gateway.

```bash
./run_ui.sh
# equivalent: ./src/agent/run_ui.sh
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

The home screen lists all demo scenarios from `src/agent/prompt-scenarios/demo-prompts.txt`. Each card shows a short title and preview; clicking sends the **full** scenario text to the agent (same wording as the file, not truncated). Use **New chat** in the header or a full browser refresh to return to that home screen.

**PDF attachments**: Use the paperclip in the composer to attach a `.pdf` file. The API stores it under `src/agent/uploads/` (gitignored) and appends the saved path to your message so the agent can call `parse_file` on that path. The `parse_file` tool reads the real PDF text from disk (via `pypdf`); only files under `uploads/` are allowed. You can send text only, PDF only, or both. Use a PDF from `assets/` at repo root if you want a fixed file for testing.

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
./run.sh

# 2. Generate the HTML page
cd src/agent && uv run python3 docs/generate_demo.py

# 3. Open in browser (from ibac-demo root)
open src/agent/docs/demo.html
```

### Updating scenarios

The generator reads source files directly - no manual HTML editing:

| What changes | File to edit | Action |
|---|---|---|
| Prompt wording or title | `src/agent/prompt-scenarios/demo-prompts.txt` | Re-run generator |
| PREREQ injection text or target tool | `src/agent/tools/local_tools.py` | Re-run generator |
| Which tool the prompt triggers | `src/agent/prompt-scenarios/demo-scenarios.json` (`intended_tool`) | Re-run generator |
| Attack type label or story text | `src/agent/prompt-scenarios/demo-scenarios.json` | Re-run generator |
