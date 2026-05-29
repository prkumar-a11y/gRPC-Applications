.PHONY: help generate install server cli-submit cli-status cli-watch cli-shell cli-logs tui clean

help:
	@echo "Job Orchestrator gRPC Service - Makefile"
	@echo ""
	@echo "Available targets:"
	@echo "  make install      - Install dependencies"
	@echo "  make generate     - Generate gRPC code from proto files"
	@echo "  make server       - Start the gRPC server"
	@echo "  make tui          - Start the TUI client"
	@echo "  make cli-submit   - Submit a test job"
	@echo "  make cli-status   - Get job status (requires JOB_ID=...)"
	@echo "  make cli-watch    - Watch job updates (requires JOB_ID=...)"
	@echo "  make cli-shell    - Interactive shell (requires JOB_ID=...)"
	@echo "  make cli-logs     - Push logs (requires JOB_ID=... FILE=...)"
	@echo "  make clean        - Clean generated files"

install:
	pip install -r requirements.txt

generate:
	@chmod +x generate.sh
	@./generate.sh

server: generate
	python -m server.main

tui: generate
	@chmod +x run_tui.sh
	@./run_tui.sh

cli-submit: generate
	python -m client.cli submit --name smoke-tests --param env=qa --param suite=smoke

cli-status: generate
	@if [ -z "$(JOB_ID)" ]; then \
		echo "Error: Please specify JOB_ID=<job-id>"; \
		exit 1; \
	fi
	python -m client.cli status --job-id $(JOB_ID)

cli-watch: generate
	@if [ -z "$(JOB_ID)" ]; then \
		echo "Error: Please specify JOB_ID=<job-id>"; \
		exit 1; \
	fi
	python -m client.cli watch --job-id $(JOB_ID)

cli-shell: generate
	@if [ -z "$(JOB_ID)" ]; then \
		echo "Error: Please specify JOB_ID=<job-id>"; \
		exit 1; \
	fi
	python -m client.cli shell --job-id $(JOB_ID)

cli-logs: generate
	@if [ -z "$(JOB_ID)" ] || [ -z "$(FILE)" ]; then \
		echo "Error: Please specify JOB_ID=<job-id> FILE=<path>"; \
		exit 1; \
	fi
	python -m client.cli push-logs --job-id $(JOB_ID) $(FILE)

clean:
	rm -rf generated/*.py
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
