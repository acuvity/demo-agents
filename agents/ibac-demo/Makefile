MAKEFLAGS += --warn-undefined-variables
SHELL := /bin/bash -o pipefail

AGENT := src/agent
PYLINT_SOURCES := $(patsubst $(AGENT)/%,%,$(shell find $(AGENT) -name '*.py' -not -path '$(AGENT)/.venv/*'))

.PHONY: lint deptry

lint:
	@uv run --directory $(AGENT) --with pylint pylint $(PYLINT_SOURCES)
	@uv run --directory $(AGENT) --with pyright pyright

deptry:
	@uv run --directory $(AGENT) --with deptry deptry .
