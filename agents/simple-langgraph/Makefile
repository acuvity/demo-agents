MAKEFLAGS += --warn-undefined-variables
SHELL := /bin/bash -o pipefail

PYLINT_SOURCES := $(patsubst ./%,%,$(shell find . -name '*.py' -not -path './.venv/*'))

.PHONY: lint deptry

lint:
	@uv run --with pylint pylint $(PYLINT_SOURCES)
	@uv run --with pyright pyright

deptry:
	@uv run --with deptry deptry .
