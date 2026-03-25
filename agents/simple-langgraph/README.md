# Simple LangGraph Agent

A minimal LangGraph agent that uses the Acuvity AI Security Gateway.

![AI Security Gateway](./images/agent.png)


## Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv)
- An [Acuvity](https://console.acuvity.ai) account (for using the AI Security Gateway)
- An [Arcade](https://www.arcade.dev/) account

## Environment variables

| Variable | Description |
|---|---|
| `ACUVITY_TOKEN` | Acuvity Application Token to authenticate with Acuvity AI Security Gateway |
| `APEX_URL` | The URL for Acuvity AI Security Gateway. Get your Apex URL from `console.acuvity.ai/me` |
|||
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `ARCADE_API_KEY` | Arcade API key |
| `ARCADE_USER_ID` | Arcade user ID |
| `ARCADE_MCP_URL` | Arcade MCP server URL |

## Run

```bash
export ACUVITY_TOKEN=...
export APEX_URL=https://...

export ANTHROPIC_API_KEY=...
export ARCADE_API_KEY=...
export ARCADE_USER_ID=...
export ARCADE_MCP_URL=...

./run.sh
```

`run.sh` does the following:
- Sets up the ca.pem
- Sets up the Acuvity AI Security Gateway as a proxy for all interactions to LLMs and MCP Servers using (`HTTPS_PROXY`) and
- Runs `main.py` via `uv`.
