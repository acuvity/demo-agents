MAKEFLAGS += --warn-undefined-variables
SHELL := /bin/bash -o pipefail

AGENTS := $(patsubst %/,%,$(wildcard */))

.PHONY: lint deptry pip-check-reqs containers push $(AGENTS)

lint deptry pip-check-reqs containers push: $(AGENTS)

$(AGENTS):
	$(MAKE) -C $@ $(MAKECMDGOALS)
