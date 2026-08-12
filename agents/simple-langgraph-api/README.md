# Simple LangGraph Agent

A minimal LangGraph agent that uses the Scan/Police API.

## Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv)
- An [Acuvity](https://console.acuvity.ai) account (for using the API)
- An [Arcade](https://www.arcade.dev/) account (If you want MCP tools)

## Environment variables

| Variable | Description |
|---|---|
| `APP_COMP_TOKEN` | An App Component Token to authenticate with the API |
| `APEX_URL` | The URL for API. Get your Apex URL from `console.acuvity.ai/me` |
|||
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `ARCADE_API_KEY` | Arcade API key |
| `ARCADE_USER_ID` | Arcade user ID |
| `ARCADE_MCP_URL` | Arcade MCP server URL |

## Import the app manifest

- Follow the steps [here](https://docs.acuvity.ai/wURWAaVt0FMiS39eKrS9/appsec/product-guides/app-definitions/app-definition-as-code) to import the manifest.yaml

## Getting App Component Token

 - Access your [Acuvity](https://console.acuvity.ai) account
 - Navigate to `Applications > App Definitions`
 - Click on the App > Issue a token for the component

## Getting you API URL

 - Goto [https://console.acuvity.ai/me](https://console.acuvity.ai/me) information page
 - Copy the `Apex` URL under `General` section

## Run Flags

 - --conversation NAME        Run prompts (prompts.txt) from section NAME (example: 'Basic Queries'); each prompt gets a fresh conversation ID (no memory between turns)
 - --multi-conversation NAME  Run prompts (prompts.txt) from section NAME (example: 'Basic Queries'); all prompts share one conversation ID (memory preserved across turns)
 - --trace [FILE]             Write OpenTelemetry spans to FILE (default: trace.jsonl). NOTE - this write the apps internal traces , not traces from the scan/police API.
 - --secure / --no-secure     Enable or disable SSL verification for API calls (default: enabled)

## Run

```bash
export APP_COMP_TOKEN=...
export APEX_URL=https://...

export ANTHROPIC_API_KEY=...
export ARCADE_API_KEY=...
export ARCADE_USER_ID=...
export ARCADE_MCP_URL=...

uv run main.py [FLAGS]
```