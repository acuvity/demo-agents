MAKEFLAGS += --warn-undefined-variables
SHELL := /bin/bash -o pipefail
CONTAINER_ENGINE ?= docker
CONTAINER_TAG ?= "latest"
PACKAGES_VERSION ?= 1.0.0
PACKAGES_RELEASE ?= 1

# Default to linux x86 build for now
ARCH ?= x86

OCI_REGISTRY ?= "acuvity"

HOST_OS := $(shell uname -s)
HOST_ARCH := $(shell uname -m)
ifeq ($(HOST_ARCH),x86_64)
	HOST_ARCH = amd64
endif
ifeq ($(HOST_ARCH),aarch64)
	HOST_ARCH = arm64
endif

ifeq ($(ARCH), x86)
	DOCKER_DEFAULT_PLATFORM = linux/amd64
else ifeq ($(ARCH), arm)
	DOCKER_DEFAULT_PLATFORM = linux/arm64
else ifeq ($(ARCH), native)
	# let the os decide
endif

export DOCKER_DEFAULT_PLATFORM CONTAINER_ENGINE

default: charts containers

mcp-demo-container:
	@cd src/agent && ${CONTAINER_ENGINE} buildx build --attest type=sbom --attest type=provenance --load --platform linux/arm64/v8,linux/amd64 --tag ${OCI_REGISTRY}/acuvity-chatbot-agent:${CONTAINER_TAG} .
	@cd src/ui && ${CONTAINER_ENGINE} buildx build --attest type=sbom --attest type=provenance --load --platform linux/arm64/v8,linux/amd64 --tag ${OCI_REGISTRY}/acuvity-chatbot-ui:${CONTAINER_TAG} .

mcp-demo-container-push:
	@cd src/agent && $(CONTAINER_ENGINE) buildx build --attest type=sbom --attest type=provenance --push --platform linux/arm64/v8,linux/amd64 --tag $(OCI_REGISTRY)/acuvity-chatbot-agent:$(CONTAINER_TAG) .
	@cd src/ui && $(CONTAINER_ENGINE) buildx build --attest type=sbom --attest type=provenance --push --platform linux/arm64/v8,linux/amd64 --tag $(OCI_REGISTRY)/acuvity-chatbot-ui:$(CONTAINER_TAG) .

containers: mcp-demo-container

%-chart-lint:
	@helm lint deploy/k8s/charts/$*

.charts-clean:
	@rm -rf deploy/k8s/charts/repo

deploy/k8s/charts/%: .charts-clean %-chart-lint
	helm package deploy/k8s/charts/$* -d deploy/k8s/charts/repo --version $(PACKAGES_VERSION) --app-version $(CONTAINER_TAG)

.PHONY: charts lint deptry
charts: $(filter-out deploy/k8s/charts/repo%, $(patsubst %/,%, $(filter %/, $(wildcard deploy/k8s/charts/*/))))

PYLINT_SOURCES := $(patsubst src/agent/%,%,$(shell find src/agent -name '*.py' -not -path 'src/agent/.venv/*'))

lint:
	@echo "TODO: add linting for fast-agent"
# 	@uv run --directory src/agent --with pylint pylint $(PYLINT_SOURCES)
# 	@uv run --directory src/agent --with pyright pyright
# 	@cd src/ui/chat_ui && npm run lint

PYTHON_PROJECTS := src/agent

deptry:
	@echo "TODO: add deptry for fast-agent"
#	@$(foreach project,$(PYTHON_PROJECTS),uv run --directory $(project) --with deptry deptry .;)

push: mcp-demo-container-push
