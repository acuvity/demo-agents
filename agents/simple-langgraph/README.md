# Simple LangGraph Agent

A minimal LangGraph agent that uses the Apex proxy without needing the Apex-Agent.

## Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv)
- An [Acuvity](https://console.acuvity.ai) account (for the Apex proxy)
- An [Arcade](https://www.arcade.dev/) account

## Environment variables

| Variable | Description |
|---|---|
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `ARCADE_API_KEY` | Arcade API key |
| `ARCADE_USER_ID` | Arcade user ID |
| `ARCADE_MCP_URL` | Arcade MCP server URL |
| `ACUVITY_TOKEN` | Acuvity app token (for Apex proxy) |
| `APEX_URL` | Your Apex URL from `console.acuvity.ai/me` |

## Run

```bash
export ANTHROPIC_API_KEY=...
export ARCADE_API_KEY=...
export ARCADE_USER_ID=...
export ARCADE_MCP_URL=...
export ACUVITY_TOKEN=...
export APEX_URL=https://...

./run.sh
```

`run.sh` sets up the Acuvity Apex proxy (routes traffic through `HTTPS_PROXY`) and then runs `main.py` via `uv`.
