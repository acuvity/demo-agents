MAKEFLAGS += --warn-undefined-variables
SHELL := /bin/bash -o pipefail

# Docker Hub username (Docker ID) for image tags. Do not commit a real value; pass on CLI or export.
CONTAINER_ENGINE ?= docker
CONTAINER_TAG ?= latest
DOCKER_HUB_USER ?=

AGENT := src/agent
# Omit tests/ and docs/ (research + generator scripts); same idea as fast-agent omitting tests.
PYLINT_SOURCES := $(patsubst $(AGENT)/%,%,$(shell find $(AGENT) -name '*.py' \
	-not -path '$(AGENT)/.venv/*' \
	-not -path '$(AGENT)/tests/*' \
	-not -path '$(AGENT)/docs/*'))

.PHONY: lint deptry docker-build docker-push helm-lint require-docker-hub-user

# Image names match deploy/k8s/README.md (YOUR_DOCKER_ID/ibac-demo-*).
IMAGE_AGENT := $(DOCKER_HUB_USER)/ibac-demo-agent
IMAGE_UI := $(DOCKER_HUB_USER)/ibac-demo-ui

require-docker-hub-user:
	@test -n "$(DOCKER_HUB_USER)" || { echo >&2 "DOCKER_HUB_USER is not set (Docker Hub username). Example: make docker-build DOCKER_HUB_USER=yourid"; exit 1; }

docker-build: require-docker-hub-user
	@cd src/agent && $(CONTAINER_ENGINE) build -t $(IMAGE_AGENT):$(CONTAINER_TAG) -f Dockerfile .
	@cd src/ui && $(CONTAINER_ENGINE) build -t $(IMAGE_UI):$(CONTAINER_TAG) -f Dockerfile .

docker-push: require-docker-hub-user
	@$(CONTAINER_ENGINE) push $(IMAGE_AGENT):$(CONTAINER_TAG)
	@$(CONTAINER_ENGINE) push $(IMAGE_UI):$(CONTAINER_TAG)

helm-lint:
	@helm lint deploy/k8s/charts/ibac-demo

lint:
	@uv run --directory $(AGENT) --with pylint pylint $(PYLINT_SOURCES)
	@uv run --directory $(AGENT) --with pyright pyright
	@cd src/ui/chat_ui && npm install && npm run lint

deptry:
	@uv run --directory $(AGENT) --with deptry deptry .
