MAKEFLAGS += --warn-undefined-variables
SHELL := /bin/bash -o pipefail

AGENTS := $(patsubst %/,%,$(wildcard */))

.PHONY: lint containers push $(AGENTS)

lint containers push: $(AGENTS)

$(AGENTS):
	$(MAKE) -C $@ $(MAKECMDGOALS)
