# MCP Agent

An **OpenAI Agents SDK** powered agent that connects to any number of remote
MCP servers over HTTP, supports both **OpenAI** and **Claude** models, and emits
full **OpenTelemetry** traces for every run.

Everything is driven by a single YAML config file — no code changes needed to
switch models, add servers, or change where traces are sent.

---

## Quick start

```bash
# 1 – install dependencies
pip install -r requirements.txt

# 2 – set credentials
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."   # only needed when provider=claude

# 3 – edit config.yaml to point at your MCP server(s) and choose a model

# 4 – run
python agent.py --config config.yaml --prompt "What tools do you have?"
```

---

## Configuration reference

```yaml
# ── LLM ──────────────────────────────────────────────────────────────────────
llm:
  provider: openai          # openai | claude

  openai:
    model: gpt-4o-mini
    api_key: ${OPENAI_API_KEY}   # env-var expansion supported everywhere
    base_url: ~                  # null = default endpoint

  claude:
    model: claude-sonnet-4-20250514
    api_key: ${ANTHROPIC_API_KEY}

# ── MCP servers ───────────────────────────────────────────────────────────────
# mcp_servers:
#   - name: my-server
#     url: http://localhost:8000/mcp
#     headers:
#       Authorization: "Bearer ${MCP_TOKEN}"
#     timeout: 30           # seconds  (default 30)
#     cache_tools: false    # cache the tools list between calls

# ── OpenTelemetry ─────────────────────────────────────────────────────────────
otel:
  enabled: true
  service_name: mcp-agent

  # exporter: console | otlp_http | otlp_grpc
  exporter: console

  otlp_http:
    endpoint: http://localhost:4318/v1/traces
    headers:
      api-key: "your-key"

  otlp_grpc:
    endpoint: http://localhost:4317
```

### Environment-variable substitution

Any string value in the YAML can reference an environment variable with the
`${VAR_NAME}` syntax. It is expanded at load time. If the variable is not set
you will see a warning and an empty string will be used.

---

## CLI flags

| Flag | Default | Description |
|---|---|---|
| `--config` / `-c` | `config.yaml` | Path to YAML config |
| `--prompt` / `-p` | *(required)* | User prompt |
| `--system` / `-s` | built-in | Override the agent system prompt |
| `--max-turns` | `20` | Max agentic turns before stopping |

---

## OTEL instrumentation included

| Instrumentor | What it covers |
|---|---|
| `HTTPXClientInstrumentor` | Every outbound HTTP call (OpenAI API, MCP servers) |
| `ThreadingInstrumentor` | Propagates trace context across background threads |
| `MCPInstrumentor` | MCP `tools/list` and `tools/call` operations |

All spans are emitted under the `service.name` set in the config and exported
via whichever exporter you configure.

---

## Examples

```bash
# Use Claude, console traces
python agent.py -c config.yaml -p "Summarise what tools are available"

# Override system prompt
python agent.py -c config.yaml \
  -p "List all MCP tools" \
  -s "You are a concise assistant. Respond in bullet points."

# Send traces to a local Jaeger instance (OTLP HTTP)
# (set exporter: otlp_http in config.yaml first)
python agent.py -c config.yaml -p "Hello"
```
