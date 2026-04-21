MAKEFLAGS += --warn-undefined-variables
SHELL := /bin/bash -o pipefail
CONTAINER_ENGINE ?= docker
CONTAINER_TAG ?= latest
OCI_REGISTRY ?= kanavg004
UI_IMAGE ?= agent-demo-ui

.PHONY: lint demo-ui-container demo-ui-container-push deptry pip-check-reqs containers push

lint:
	@cd chat_ui && npm install && npm run lint

demo-ui-container:
	@$(CONTAINER_ENGINE) buildx build --attest type=sbom --attest type=provenance --load --platform linux/arm64/v8,linux/amd64 --tag $(OCI_REGISTRY)/$(UI_IMAGE):$(CONTAINER_TAG) .

demo-ui-container-push:
	@$(CONTAINER_ENGINE) buildx build --attest type=sbom --attest type=provenance --push --platform linux/arm64/v8,linux/amd64 --tag $(OCI_REGISTRY)/$(UI_IMAGE):$(CONTAINER_TAG) .

deptry pip-check-reqs:
	@:

containers: demo-ui-container
push: demo-ui-container-push