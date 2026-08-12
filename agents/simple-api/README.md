# Simple API

A minimal OpenAI API that uses the Scan/Police API.

## Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv)
- An [Acuvity](https://console.acuvity.ai) account (for using the API)

## Environment variables

| Variable | Description |
|---|---|
| `APP_COMP_TOKEN` | An App Component Token to authenticate with the API |
| `APEX_URL` | The URL for API. Get your Apex URL from `console.acuvity.ai/me` |
|||
| `OPENAI_API_KEY` | OpenAI API key |

## Import the app manifest

- Follow the steps [here](https://docs.acuvity.ai/wURWAaVt0FMiS39eKrS9/appsec/product-guides/app-definitions/app-definition-as-code) to import the ./manifest.yaml

## Getting App Component Token

 - Access your [Acuvity](https://console.acuvity.ai) account
 - Navigate to `Applications > App Definitions`
 - Click on 'simple-api' > Issue a token for the component

## Getting your API URL

 - Goto [https://console.acuvity.ai/me](https://console.acuvity.ai/me) information page
 - Copy the `Apex` URL under `General` section


## Run

```bash
export APP_COMP_TOKEN=...
export APEX_URL=https://...

export OPENAI_API_KEY=...

uv run main.py
```