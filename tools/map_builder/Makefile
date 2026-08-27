# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

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
	PYTHONPATH=. python3 -m unittest discover -s tests -v
