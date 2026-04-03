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

### Acuvity AI Security Gateway (always required)

| Variable | Description |
|---|---|
| `ACUVITY_TOKEN` | Acuvity Application Token to authenticate with Acuvity AI Security Gateway |
| `APEX_URL` | The URL for Acuvity AI Security Gateway. Get your Apex URL from `console.acuvity.ai/me` |

### LLM provider selection

| Variable | Description |
|---|---|
| `LLM_PROVIDER` | `anthropic` (default), `openai`, or `openrouter` |
| `LLM_MODEL` | Model name override. Defaults: `claude-opus-4-6` (Anthropic), `gpt-4o` (OpenAI) |
| `ANTHROPIC_API_KEY` | Required when `LLM_PROVIDER=anthropic` |
| `OPENAI_API_KEY` | Required when `LLM_PROVIDER=openai` |
| `OPENROUTER_API_KEY` | Required when `LLM_PROVIDER=openrouter` |
| `OPENROUTER_MODEL` | OpenRouter model name (default: `stepfun/step-3.5-flash:free`) |
| `LLM_BASE_URL` | Override the API endpoint (any provider - enables third-party compatible APIs) |
| `LLM_API_KEY` | Override the API key (any provider - takes precedence over the provider-specific key) |

### MCP server selection

| Variable | Description |
|---|---|
| `MCP_SERVER` | `arcade` (default) or `local` |
| `ARCADE_API_KEY` | Arcade API key - required when `MCP_SERVER=arcade` |
| `ARCADE_USER_ID` | Arcade user ID - required when `MCP_SERVER=arcade` |
| `ARCADE_MCP_URL` | Arcade MCP server URL - required when `MCP_SERVER=arcade` |

When `MCP_SERVER=local`, the agent connects to `tools/local_tools.py` via stdio.
This server exposes CRM tools with embedded attack patterns for demonstrating
Acuvity's detection capabilities.

### Prompts

| Variable | Description |
|---|---|
| `PROMPTS_TYPE` | `simple` (default) or `scenario` |

Two prompt files are provided:
- `simple` → `prompt-scenarios/simple-prompts.txt` - basic queries, tool usage, and simple injection examples
- `scenario` → `prompt-scenarios/scenario-prompts.txt` - detailed multi-step attack scenarios (see `docs/test-scenarios.md`)

## Getting Acuvity App Token

 - Access your [Acuvity](https://console.acuvity.ai) account
 - Navigate to `Access > App Tokens`
 - Create a token with an appropriate name and description.

## Getting your AI Security Gateway (Apex) URL

 - Go to [https://console.acuvity.ai/me](https://console.acuvity.ai/me)
 - Copy the `Apex` URL under `General` section

## Run

`LLM_PROVIDER` and `MCP_SERVER` are independent - any combination works. Set the
variables for the provider you want and run `./run.sh`.

`run.sh` does the following:
- Validates required environment variables based on selected providers
- Sets up `ca.pem` from the Acuvity gateway
- Sets up the Acuvity AI Security Gateway as a proxy for all interactions to LLMs and MCP Servers via `HTTPS_PROXY`
- Runs `main.py` via `uv`

### Default: Anthropic + Arcade

```bash
export ACUVITY_TOKEN=...
export APEX_URL=https://...

export ANTHROPIC_API_KEY=...
export ARCADE_API_KEY=...
export ARCADE_USER_ID=...
export ARCADE_MCP_URL=...

./run.sh
```

### Local MCP - pick any LLM provider

Local MCP (`MCP_SERVER=local`) runs `tools/local_tools.py` via stdio and exposes CRM
tools with embedded attack patterns for demonstrating detection capabilities.

**Anthropic**
```bash
export ACUVITY_TOKEN=...
export APEX_URL=https://...

export ANTHROPIC_API_KEY=...
export MCP_SERVER=local

./run.sh
```

**OpenRouter** - find a model at [openrouter.ai/models](https://openrouter.ai/models)
```bash
export ACUVITY_TOKEN=...
export APEX_URL=https://...

export LLM_PROVIDER=openrouter
export OPENROUTER_API_KEY=...
export OPENROUTER_MODEL=stepfun/step-3.5-flash:free  # optional, this is the default
export MCP_SERVER=local

./run.sh
```

**OpenAI or any OpenAI-compatible provider** (Together AI, Groq, etc.)
```bash
export ACUVITY_TOKEN=...
export APEX_URL=https://...

export LLM_PROVIDER=openai
export OPENAI_API_KEY=...
export LLM_MODEL=gpt-4o                          # optional
export LLM_BASE_URL=https://api.together.xyz/v1  # optional, for third-party endpoints
export MCP_SERVER=local

./run.sh
```

### Attack Scenario Testing

Runs the scenarios from `docs/test-scenarios.md` one at a time. Add scenarios to
`prompt-scenarios/scenario-prompts.txt` as they are validated.

Works with any LLM provider - set `PROMPTS_TYPE=scenario` alongside your chosen provider variables:

```bash
export ACUVITY_TOKEN=...
export APEX_URL=https://...

# pick one: Anthropic / OpenAI / OpenRouter (see above for variables)
export ANTHROPIC_API_KEY=...

export MCP_SERVER=local
export PROMPTS_TYPE=scenario

./run.sh
```
