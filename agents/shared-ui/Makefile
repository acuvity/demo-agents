MAKEFLAGS += --warn-undefined-variables
SHELL := /bin/bash -o pipefail

.PHONY: lint deptry pip-check-reqs containers push

lint:
	@cd chat_ui && npm install && npm run lint

deptry pip-check-reqs containers push:
	@:
