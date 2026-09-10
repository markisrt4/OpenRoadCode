# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

REPO_ROOT := $(abspath $(dir $(lastword $(MAKEFILE_LIST)))/../..)

.PHONY: image tui validate deploy test

image:
	./scripts/build-image.sh

tui:
	./scripts/run-builder.sh tui

validate:
	./scripts/validate-host.sh

deploy:
	./scripts/deploy-to-srv.sh $(if $(REMOTE),--remote $(REMOTE))

test:
	PYTHONPATH=$(REPO_ROOT) python3 -m unittest discover -s tests -v
