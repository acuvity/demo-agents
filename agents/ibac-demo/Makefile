MAKEFLAGS += --warn-undefined-variables
SHELL := /bin/bash -o pipefail

AGENT := src/agent
# Omit tests/ and docs/ (research + generator scripts); same idea as fast-agent omitting tests.
PYLINT_SOURCES := $(patsubst $(AGENT)/%,%,$(shell find $(AGENT) -name '*.py' \
	-not -path '$(AGENT)/.venv/*' \
	-not -path '$(AGENT)/tests/*' \
	-not -path '$(AGENT)/docs/*'))

.PHONY: lint deptry

lint:
	@uv run --directory $(AGENT) --with pylint pylint $(PYLINT_SOURCES)
	@uv run --directory $(AGENT) --with pyright pyright
	@cd src/ui/chat_ui && npm install && npm run lint

deptry:
	@uv run --directory $(AGENT) --with deptry deptry .
