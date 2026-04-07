# Aegis Forge Makefile
# Common development and deployment tasks

.PHONY: help install test lint clean run-ganache run-ipfs deploy-all

# Default target
help:
@echo "Aegis Forge - Available Commands"
@echo "================================"
@echo ""
@echo "Setup:"
@echo "  make install        - Install Python dependencies"
@echo "  make setup          - Full setup (install + copy .env)"
@echo ""
@echo "Testing:"
@echo "  make test           - Run all tests with pytest"
@echo "  make test-cov       - Run tests with coverage report"
@echo "  make test-single    - Run a single test file (e.g., make test-single FILE=test_config.py)"
@echo ""
@echo "Code Quality:"
@echo "  make lint           - Run flake8 linter"
@echo "  make format         - Format code with black"
@echo "  make type-check     - Run mypy type checker"
@echo ""
@echo "Services:"
@echo "  make run-ganache    - Start Ganache blockchain"
@echo "  make run-ipfs       - Start IPFS daemon"
@echo "  make stop-services  - Stop all services"
@echo ""
@echo "Deployment:"
@echo "  make compile        - Compile smart contracts"
@echo "  make deploy-did     - Deploy DIDRegistry contract"
@echo "  make deploy-token   - Deploy AegisToken contract"
@echo "  make deploy-all     - Deploy all contracts"
@echo ""
@echo "CLI:"
@echo "  make cli-help       - Show CLI help"
@echo "  make cli-did-list   - List DIDs"
@echo "  make cli-project-list - List projects"
@echo ""
@echo "Cleanup:"
@echo "  make clean          - Remove generated files and caches"
@echo "  make clean-all      - Full cleanup including data files"

# Setup
install:
pip install -r requirements.txt

setup: install
@if [ ! -f .env ]; then \
cp .env.example .env; \
echo "Created .env file from .env.example"; \
else \
echo ".env already exists"; \
fi

# Testing
test:
pytest tests/ -v

test-cov:
pytest tests/ -v --cov=. --cov-report=html

test-single:
pytest tests/$(FILE) -v

# Code Quality
lint:
flake8 --max-line-length=100 --exclude=venv,env,.venv,build,dist *.py tests/

format:
black --line-length=100 *.py tests/

type-check:
mypy *.py tests/ --ignore-missing-imports

# Services
run-ganache:
@echo "Starting Ganache..."
@echo "Note: Run in background or separate terminal"
ganache || echo "Ganache not found. Install with: npm install -g ganache"

run-ipfs:
@echo "Starting IPFS daemon..."
@echo "Note: Run in background or separate terminal"
ipfs daemon || echo "IPFS not found. Install IPFS Desktop or go-ipfs"

stop-services:
@echo "Stopping services..."
pkill -f ganache || true
pkill -f "ipfs daemon" || true
@echo "Services stopped"

# Deployment
compile:
python compile_and_extract.py

deploy-did:
python deploy_did_registry.py

deploy-token:
python deploy_aegis_token.py

deploy-all: compile deploy-did deploy-token
@echo "All contracts deployed!"

# CLI
cli-help:
python aegis_cli.py --help

cli-did-list:
python aegis_cli.py did list

cli-project-list:
python aegis_cli.py project list

# Cleanup
clean:
@echo "Cleaning up..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name ".coverage" -delete 2>/dev/null || true
rm -rf htmlcov/ 2>/dev/null || true
rm -rf build/ dist/ 2>/dev/null || true
@echo "Cleanup complete"

clean-all: clean
@echo "Full cleanup..."
rm -rf project_data/ 2>/dev/null || true
rm -f projects.json contributions.json 2>/dev/null || true
rm -f *.log 2>/dev/null || true
@echo "Full cleanup complete"

# Development shortcuts
dev: clean test lint
@echo "Development cycle complete!"

quick-test:
pytest tests/test_config.py tests/test_security.py -v
