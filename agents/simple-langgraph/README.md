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
| `LLM_PROVIDER` | `anthropic` (default) or `openrouter` |
| `LLM_MODEL` | Model name override. Defaults: `claude-opus-4-6` (Anthropic), ignored for OpenRouter |
| `ANTHROPIC_API_KEY` | Anthropic API key - required when `LLM_PROVIDER=anthropic` |
| `OPENROUTER_API_KEY` | OpenRouter API key - required when `LLM_PROVIDER=openrouter` |
| `OPENROUTER_MODEL` | OpenRouter model name (default: `qwen/qwen3.6-plus-preview:free`) |

### MCP server selection

| Variable | Description |
|---|---|
| `MCP_SERVER` | `arcade` (default) or `local` |
| `ARCADE_API_KEY` | Arcade API key - required when `MCP_SERVER=arcade` |
| `ARCADE_USER_ID` | Arcade user ID - required when `MCP_SERVER=arcade` |
| `ARCADE_MCP_URL` | Arcade MCP server URL - required when `MCP_SERVER=arcade` |

When `MCP_SERVER=local`, the agent connects to `tools/local_tools.py` via stdio.
This server exposes CRM tools with an embedded tool poisoning attack, useful for
demonstrating Acuvity's tool poisoning detection.

## Getting Acuvity App Token

 - Access your [Acuvity](https://console.acuvity.ai) account
 - Navigate to `Access > App Tokens`
 - Create a token with an appropriate name and description.

## Getting your AI Security Gateway (Apex) URL

 - Go to [https://console.acuvity.ai/me](https://console.acuvity.ai/me)
 - Copy the `Apex` URL under `General` section

## Run

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

### OpenRouter + Local MCP (tool poisoning demo)

```bash
export ACUVITY_TOKEN=...
export APEX_URL=https://...

export LLM_PROVIDER=openrouter
export OPENROUTER_API_KEY=...
export OPENROUTER_MODEL=stepfun/step-3.5-flash:free  # optional, this is the default

export MCP_SERVER=local

./run.sh
```

`run.sh` does the following:
- Validates required environment variables based on selected providers
- Sets up the ca.pem from the Acuvity gateway
- Sets up the Acuvity AI Security Gateway as a proxy for all LLM and MCP traffic via `HTTPS_PROXY`
- Runs `main.py` via `uv`
