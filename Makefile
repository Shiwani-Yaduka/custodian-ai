# Makefile — Developer automation shortcuts for Custodian AI
# Run `make help` to inspect all available workflow targets.

.PHONY: help up down test fairness scan clean

# Default target prints available commands
help:
	@echo "=========================================================="
	@echo " Custodian AI — Local Development & CI Commands"
	@echo "=========================================================="
	@echo " make up        Start local development containers (Redis, Postgres)"
	@echo " make down      Stop and clean up local dev containers"
	@echo " make test      Execute automated unit and integration tests"
	@echo " make fairness  Run the fairness & false-flag regression suite"
	@echo " make scan      Execute security scanners (gitleaks, Trivy)"
	@echo " make clean     Remove temporary caches, pycache, build artifacts"
	@echo "=========================================================="

# Start local backing services using Docker Compose
up:
	@echo "--> Starting local development environment..."
	docker compose up -d

# Shut down local containers and network
down:
	@echo "--> Stopping local development environment..."
	docker compose down

# Execute unit and service tests across the workspace
test:
	@echo "--> Running unit and integration tests..."
	pytest services shared -v

# Run the mandatory fairness regression suite (definition of done for all PRs)
fairness:
	@echo "--> Running fairness regression suite..."
	python -m fairness.runner

# Run vulnerability scanning and secret leak detection
scan:
	@echo "--> Scanning workspace for hardcoded secrets and CVE vulnerabilities..."
	@echo "1. Checking for committed secrets..."
	-gitleaks detect --verbose
	@echo "2. Scanning filesystem vulnerabilities with Trivy..."
	-trivy fs --severity HIGH,CRITICAL .

# Housekeeping: clean temporary Python bytecode and test caches
clean:
	@echo "--> Cleaning bytecode and test caches..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
