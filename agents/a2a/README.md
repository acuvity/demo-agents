# A2A Agents

Examples of [A2A protocol](https://github.com/a2aproject/A2A) agents — a single-agent hello world and a multi-agent travel planner.

---

## Single Agent (`single-agent/`)

A minimal A2A server built that simulates agentic behavior. It demonstrates the full A2A request/response lifecycle:

- Receives a message and immediately sends a `working` status update
- Simulates processing with a 1-second delay
- Returns a response artifact
- Enforces bearer token auth via middleware (card endpoint is public)
- Logs all incoming requests for visibility



### Setup

```bash
cd single-agent
uv sync
```

The bearer auth middleware logs the incoming token but does not validate it (validation is a TODO). Any token — or no token — is accepted.

### Run

```bash
uv run python hello_world_agent.py --host 127.0.0.1 --port 41241
```

### Talk to it

```bash
# From the a2a/ directory
uv run python cli.py --url http://localhost:41241 --token <your-token>
```

---

## Multi-Agent Travel Planner (`multi-agent/`)

A travel planning multi-agent system built with [Google ADK](https://github.com/google/adk-python) and the A2A protocol.

## Architecture

```
CLI → travel_planner (port 41241)
         ├── flights_agent (direct or via gateway)
         └── hotels_agent  (direct or via gateway)
```

- **travel_planner**: Orchestrator — calls both sub-agents and combines results
- **flights_agent**: Returns flight options for a destination
- **hotels_agent**: Returns hotel options for a destination (routed through gateway)
- **cli.py**: Terminal client for talking to any A2A agent

## Setup

### 1. Install dependencies

```bash
cd multi-agent/src/backend
uv sync
```

Edit `agents/.env`:

```env
ANTHROPIC_API_KEY=your_anthropic_api_key

# Gateway settings (if routing agents through a gateway)
GATEWAY_URL=https://<gateway-host>/<org>/<project>
APP_COMP_TOKEN=your_bearer_token
CA_CERT_PATH=/path/to/ca-chain.pem
```

## Running

Start each agent in a separate terminal from `multi-agent/src/backend/`:

```bash
# Terminal 1 — flights sub-agent
uv run python agents/flights_agent.py

# Terminal 2 — hotels sub-agent (optional if using gateway)
uv run python agents/hotels_agent.py

# Terminal 3 — orchestrator
uv run python agents/travel_planner_agent.py
```

## Talking to the agent

From the `a2a/` directory:

```bash
# Direct (no gateway)
uv run python cli.py --url http://localhost:41241

# Via gateway with TLS and bearer token
uv run python cli.py \
  --url https://<gateway-host>/<org>/<project>/a2a-travel-agent \
  --token $APP_COMP_TOKEN \
  --ca-cert /path/to/ca-chain.pem
```
