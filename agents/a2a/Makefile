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

demo-container: demo-travel-planner-container demo-flights-agent-container demo-hotels-agent-container demo-pricing-agent-container

demo-travel-planner-container:
	@cd multi-agent/src/backend && ${CONTAINER_ENGINE} buildx build --attest type=sbom --attest type=provenance --load --platform linux/arm64/v8,linux/amd64 --build-arg AGENT_MODULE=agents.travel_planner_agent --build-arg AGENT_PORT=41241 --tag ${OCI_REGISTRY}/a2a-travel-planner:${CONTAINER_TAG} .

demo-flights-agent-container:
	@cd multi-agent/src/backend && ${CONTAINER_ENGINE} buildx build --attest type=sbom --attest type=provenance --load --platform linux/arm64/v8,linux/amd64 --build-arg AGENT_MODULE=agents.flights_agent --build-arg AGENT_PORT=41242 --tag ${OCI_REGISTRY}/a2a-flights-agent:${CONTAINER_TAG} .

demo-hotels-agent-container:
	@cd multi-agent/src/backend && ${CONTAINER_ENGINE} buildx build --attest type=sbom --attest type=provenance --load --platform linux/arm64/v8,linux/amd64 --build-arg AGENT_MODULE=agents.hotels_agent --build-arg AGENT_PORT=41243 --tag ${OCI_REGISTRY}/a2a-hotels-agent:${CONTAINER_TAG} .

demo-pricing-agent-container:
	@cd multi-agent/src/backend && ${CONTAINER_ENGINE} buildx build --attest type=sbom --attest type=provenance --load --platform linux/arm64/v8,linux/amd64 --build-arg AGENT_MODULE=agents.pricing_agent --build-arg AGENT_PORT=41244 --tag ${OCI_REGISTRY}/a2a-pricing-agent:${CONTAINER_TAG} .

demo-container-push:
	@cd multi-agent/src/backend && $(CONTAINER_ENGINE) buildx build --attest type=sbom --attest type=provenance --push --platform linux/arm64/v8,linux/amd64 --build-arg AGENT_MODULE=agents.travel_planner_agent --build-arg AGENT_PORT=41241 --tag $(OCI_REGISTRY)/a2a-travel-planner:$(CONTAINER_TAG) .
	@cd multi-agent/src/backend && $(CONTAINER_ENGINE) buildx build --attest type=sbom --attest type=provenance --push --platform linux/arm64/v8,linux/amd64 --build-arg AGENT_MODULE=agents.flights_agent --build-arg AGENT_PORT=41242 --tag $(OCI_REGISTRY)/a2a-flights-agent:$(CONTAINER_TAG) .
	@cd multi-agent/src/backend && $(CONTAINER_ENGINE) buildx build --attest type=sbom --attest type=provenance --push --platform linux/arm64/v8,linux/amd64 --build-arg AGENT_MODULE=agents.hotels_agent --build-arg AGENT_PORT=41243 --tag $(OCI_REGISTRY)/a2a-hotels-agent:$(CONTAINER_TAG) .
	@cd multi-agent/src/backend && $(CONTAINER_ENGINE) buildx build --attest type=sbom --attest type=provenance --push --platform linux/arm64/v8,linux/amd64 --build-arg AGENT_MODULE=agents.pricing_agent --build-arg AGENT_PORT=41244 --tag $(OCI_REGISTRY)/a2a-pricing-agent:$(CONTAINER_TAG) .

containers: demo-container

%-chart-lint:
	@helm lint multi-agent/deploy/k8s/charts/$*

.charts-clean:
	@rm -rf multi-agent/deploy/k8s/charts/repo

multi-agent/deploy/k8s/charts/%: .charts-clean %-chart-lint
	helm package multi-agent/deploy/k8s/charts/$* -d multi-agent/deploy/k8s/charts/repo --version $(PACKAGES_VERSION) --app-version $(CONTAINER_TAG)

.PHONY: charts lint deptry
charts: $(filter-out multi-agent/deploy/k8s/charts/repo%, $(patsubst %/,%, $(filter %/, $(wildcard multi-agent/deploy/k8s/charts/*/))))

PYTHON_PROJECTS := multi-agent/src/backend single-agent

lint:
	@$(foreach project,$(PYTHON_PROJECTS),uv run --directory $(project) --with pylint pylint $$(find $(project) -name '*.py' -not -path '$(project)/.venv/*' | sed 's#$(project)/##');)
	@$(foreach project,$(PYTHON_PROJECTS),uv run --directory $(project) --with pyright pyright;)

deptry:
	@$(foreach project,$(PYTHON_PROJECTS),uv run --directory $(project) --with deptry deptry .;)

push: demo-container-push
