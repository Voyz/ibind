.PHONY: help lint scan clean test test-unit test-cov test-unit-cov

# Default target when just running 'make'
.DEFAULT_GOAL := help

# Python interpreter to use
PYTHON := python3

.PHONY: install
install: ## Install python dependencies
	pip install -r requirements.txt
	pip install -r requirements-oauth.txt
	pip install -r requirements-dev.txt

.PHONY: lint
lint:  ## Run code linting
	ruff check --fix

.PHONY: scan
scan:  ## Run security checks
	bandit -r . -ll -x site-packages

.PHONY: clean
clean:  ## Clean up python cache files
	find . -type f -name "*.py[co]" -delete
	find . -type d -name "__pycache__" -delete

.PHONY: test
test:  ## Run unit and integration tests (excludes e2e)
ifeq ($(OS),Windows_NT)
	set PYTHONPATH=.;test && $(PYTHON) -m pytest test/unit/ test/integration/ -v
else
	PYTHONPATH=.:test $(PYTHON) -m pytest test/unit/ test/integration/ -v
endif

.PHONY: test-unit  
test-unit:  ## Run only unit tests
ifeq ($(OS),Windows_NT)
	set PYTHONPATH=.;test && $(PYTHON) -m pytest test/unit/ -v
else
	PYTHONPATH=.:test $(PYTHON) -m pytest test/unit/ -v
endif

.PHONY: test-cov
test-cov:  ## Run unit and integration tests with coverage report
ifeq ($(OS),Windows_NT)
	set PYTHONPATH=.;test && $(PYTHON) -m pytest test/unit/ test/integration/ --cov=ibind --cov-report=term-missing --cov-report=html
else
	PYTHONPATH=.:test $(PYTHON) -m pytest test/unit/ test/integration/ --cov=ibind --cov-report=term-missing --cov-report=html
endif

.PHONY: test-unit-cov
test-unit-cov:  ## Run unit tests with coverage report
ifeq ($(OS),Windows_NT)
	set PYTHONPATH=.;test && $(PYTHON) -m pytest test/unit/ --cov=ibind --cov-report=term-missing --cov-report=html
else
	PYTHONPATH=.:test $(PYTHON) -m pytest test/unit/ --cov=ibind --cov-report=term-missing --cov-report=html
endif

.PHONY: check-all
check-all: lint scan format test  ## Run all checks (lint, scan, format, test)

.PHONY: help
help: # Show help for each of the Makefile recipes.
	@grep -E '^[a-zA-Z0-9 -]+:.*#'  Makefile | sort | while read -r l; do printf "\033[1;32m$$(echo $$l | cut -f 1 -d':')\033[00m:$$(echo $$l | cut -f 2- -d'#')\n"; done

