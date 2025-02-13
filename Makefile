.PHONY: help lint scan clean

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

.PHONY: format
format:  ## Format code using ruff
	ruff format

.PHONY: scan
scan:  ## Run security checks
	bandit -r . -ll -x site-packages

.PHONY: clean
clean:  ## Clean up python cache files
	find . -type f -name "*.py[co]" -delete
	find . -type d -name "__pycache__" -delete

.PHONY: check-all
check-all: lint scan format  ## Run all checks (lint, scan, format)

.PHONY: help
help: # Show help for each of the Makefile recipes.
	@grep -E '^[a-zA-Z0-9 -]+:.*#'  Makefile | sort | while read -r l; do printf "\033[1;32m$$(echo $$l | cut -f 1 -d':')\033[00m:$$(echo $$l | cut -f 2- -d'#')\n"; done

