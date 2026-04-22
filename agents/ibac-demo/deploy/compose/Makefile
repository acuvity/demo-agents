COMPOSE = docker compose --env-file .env
MCP_SVC = mcp

.PHONY: start stop reset logs status help

## Start all services (build images first)
start:
	$(COMPOSE) up --build -d
	@echo ""
	@echo "Services starting. URLs:"
	@echo "  Demo UI      ->  http://localhost:5174"
	@echo "  MailHog      ->  http://localhost:8025"
	@echo "  Webhook log  ->  http://localhost:9000/events"
	@echo ""
	@echo "Run 'make logs' to follow output, or 'make status' to check health."

## Stop and remove all containers
stop:
	$(COMPOSE) down

## Follow logs for all services (Ctrl-C to exit)
logs:
	$(COMPOSE) logs -f

## Show running containers and service URLs
status:
	$(COMPOSE) ps
	@echo ""
	@echo "URLs:"
	@echo "  Demo UI      ->  http://localhost:5174"
	@echo "  MailHog      ->  http://localhost:8025"
	@echo "  Webhook log  ->  http://localhost:9000/events"

## Recreate MCP container between demo scenarios
reset:
	$(COMPOSE) up -d --force-recreate $(MCP_SVC)
	@echo "MCP recreated."

## Show available targets
help:
	@echo "make start   - build and start all services"
	@echo "make stop    - stop and remove all containers"
	@echo "make logs    - follow all service logs"
	@echo "make status  - show containers and URLs"
	@echo "make reset   - restart MCP container between demo scenarios"
