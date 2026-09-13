.DEFAULT_GOAL := help
SHELL := /bin/bash

help:            ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

inspect:         ## Inspect the three workbooks and write docs/DATA_INSPECTION.md inputs
	python3 scripts/inspect_workbooks.py

ingest:          ## Parse all three workbooks into the canonical factor table
	PYTHONPATH=ai-service python3 -m app.ingestion.build_canonical

policy:          ## Regenerate the factor source policy migration
	python3 scripts/gen_source_policy.py

test:            ## Run the deterministic core test suite
	python3 scripts/run_tests.py

verify-schema:   ## Apply every migration to a throwaway database
	./scripts/verify_schema_local.sh

up:              ## Start the whole stack
	docker compose up --build

down:            ## Stop the stack
	docker compose down

logs:            ## Tail all service logs
	docker compose logs -f

.PHONY: help inspect ingest policy test verify-schema up down logs
