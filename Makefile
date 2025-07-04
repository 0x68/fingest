# Makefile for fingest development

.PHONY: help install test lint format type-check clean build publish dev-install

# Default target
help:
	@echo "Available targets:"
	@echo "  install      Install dependencies"
	@echo "  dev-install  Install development dependencies"
	@echo "  test         Run tests"
	@echo "  test-cov     Run tests with coverage"
	@echo "  lint         Run linting (flake8)"
	@echo "  format       Format code (black + isort)"
	@echo "  type-check   Run type checking (mypy)"
	@echo "  clean        Clean build artifacts"
	@echo "  build        Build package"
	@echo "  publish      Publish to PyPI"
	@echo "  pre-commit   Install pre-commit hooks"
	@echo "  check-all    Run all checks (lint, type-check, test)"

# Installation
install:
	poetry install --only=main

dev-install:
	poetry install
	poetry run pre-commit install

# Testing
test:
	poetry run pytest

test-cov:
	poetry run pytest --cov=fingest --cov-report=html --cov-report=term

test-verbose:
	poetry run pytest -v

# Code quality
lint:
	poetry run flake8 src tests

format:
	poetry run black src tests
	poetry run isort src tests

type-check:
	poetry run mypy src

# Pre-commit
pre-commit:
	poetry run pre-commit install

pre-commit-run:
	poetry run pre-commit run --all-files

# Build and publish
clean:
	rm -rf dist/
	rm -rf build/
	rm -rf *.egg-info/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf .pytest_cache/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

build: clean
	poetry build

publish: build
	poetry publish

publish-test: build
	poetry publish --repository testpypi

# Development workflow
check-all: lint type-check test

# Quick development cycle
dev: format lint type-check test

# CI/CD simulation
ci: dev-install check-all

# Documentation
docs-serve:
	@echo "README.md contains the documentation"
	@echo "Open README.md in your browser or markdown viewer"

# Version management
version-patch:
	poetry version patch

version-minor:
	poetry version minor

version-major:
	poetry version major

# Show current version
version:
	poetry version
