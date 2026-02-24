# Revive AI Backend Test Automation Makefile

.PHONY: help install setup clean lint test test-unit test-integration test-property test-api test-security test-performance test-all test-ci test-report test-watch test-debug

# Default target
help:
	@echo "Revive AI Backend Test Automation"
	@echo "================================="
	@echo ""
	@echo "Available targets:"
	@echo "  install          - Install test dependencies"
	@echo "  setup           - Set up test environment"
	@echo "  clean           - Clean test artifacts"
	@echo "  lint            - Run code linting"
	@echo "  format          - Format code with black and isort"
	@echo "  format-check    - Check code formatting without fixing"
	@echo "  quality         - Run all code quality checks"
	@echo "  quality-fix     - Fix code quality issues"
	@echo "  test            - Run all tests"
	@echo "  test-unit       - Run unit tests only"
	@echo "  test-integration - Run integration tests only"
	@echo "  test-property   - Run property-based tests only"
	@echo "  test-api        - Run API tests only"
	@echo "  test-security   - Run security tests only"
	@echo "  test-performance - Run performance tests only"
	@echo "  test-all        - Run all test categories"
	@echo "  test-ci         - Run CI pipeline"
	@echo "  test-report     - Generate comprehensive test report"
	@echo "  test-watch      - Run tests in watch mode"
	@echo "  test-debug      - Run tests with debugging"
	@echo ""

# Installation and setup
install:
	@echo "Installing test dependencies..."
	python run_tests.py install

setup:
	@echo "Setting up test environment..."
	python run_tests.py setup

clean:
	@echo "Cleaning test artifacts..."
	python run_tests.py clean

# Code quality
lint:
	@echo "Running code linting..."
	python run_tests.py lint

format:
	@echo "Formatting code..."
	black app/
	isort app/

format-check:
	@echo "Checking code formatting..."
	black --check app/
	isort --check-only app/

quality:
	@echo "Running all code quality checks..."
	python scripts/quality_check.py

quality-fix:
	@echo "Fixing code quality issues..."
	python scripts/quality_check.py --fix

# Basic testing
test:
	@echo "Running tests..."
	python run_tests.py test --verbose

test-fast:
	@echo "Running tests (fast mode)..."
	python run_tests.py test --fail-fast --no-coverage

test-parallel:
	@echo "Running tests in parallel..."
	python run_tests.py test --parallel --verbose

# Test categories
test-unit:
	@echo "Running unit tests..."
	python run_tests.py test --category unit --verbose

test-integration:
	@echo "Running integration tests..."
	python run_tests.py test --category integration --verbose

test-property:
	@echo "Running property-based tests..."
	python run_tests.py property --verbose

test-api:
	@echo "Running API tests..."
	python run_tests.py test --category api --verbose

test-security:
	@echo "Running security tests..."
	python run_tests.py security

test-performance:
	@echo "Running performance tests..."
	python run_tests.py performance

test-external:
	@echo "Running external service tests..."
	python run_tests.py test --category external --verbose

test-e2e:
	@echo "Running end-to-end tests..."
	python run_tests.py test --category e2e --verbose

# Comprehensive testing
test-all:
	@echo "Running all test categories..."
	python run_tests.py test --verbose --html --json

test-ci:
	@echo "Running CI pipeline..."
	python run_tests.py ci

test-report:
	@echo "Generating comprehensive test report..."
	python run_tests.py report

# Development helpers
test-watch:
	@echo "Running tests in watch mode..."
	pytest-watch -- --verbose

test-debug:
	@echo "Running tests with debugging..."
	python run_tests.py test --verbose --fail-fast -s

test-coverage:
	@echo "Running tests with coverage report..."
	python run_tests.py test --html
	@echo "Coverage report available at: htmlcov/index.html"

# Specific test markers
test-slow:
	@echo "Running slow tests..."
	python run_tests.py test --markers "slow" --verbose

test-database:
	@echo "Running database tests..."
	python run_tests.py test --markers "database" --verbose

test-auth:
	@echo "Running authentication tests..."
	python run_tests.py test --markers "auth" --verbose

test-llm:
	@echo "Running LLM tests..."
	python run_tests.py test --markers "llm" --verbose

# Quality gates
quality-gate:
	@echo "Running quality gate checks..."
	$(MAKE) quality
	$(MAKE) test-unit
	$(MAKE) test-integration
	$(MAKE) test-security

pre-commit:
	@echo "Running pre-commit checks..."
	$(MAKE) quality-fix
	$(MAKE) test-fast

pre-push:
	@echo "Running pre-push checks..."
	$(MAKE) quality-gate
	$(MAKE) test-property

# Docker testing
test-docker:
	@echo "Running tests in Docker..."
	docker-compose -f ../docker-compose.yml run --rm backend python run_tests.py ci

# Benchmarking
benchmark:
	@echo "Running performance benchmarks..."
	python -m pytest tests/test_performance.py --benchmark-only --benchmark-sort=mean

# Test data management
test-data-setup:
	@echo "Setting up test data..."
	python -c "from tests.fixtures import setup_test_data; setup_test_data()"

test-data-cleanup:
	@echo "Cleaning up test data..."
	python -c "from tests.fixtures import cleanup_test_data; cleanup_test_data()"

# Documentation
test-docs:
	@echo "Testing documentation examples..."
	python -m doctest app/**/*.py

# Continuous testing
test-continuous:
	@echo "Starting continuous testing..."
	while true; do \
		$(MAKE) test-fast; \
		sleep 30; \
	done

# Environment-specific testing
test-local:
	@echo "Running tests for local development..."
	DATABASE_URL=sqlite+aiosqlite:///./test.db $(MAKE) test

test-staging:
	@echo "Running tests against staging environment..."
	ENVIRONMENT=staging $(MAKE) test-integration

# Debugging helpers
test-pdb:
	@echo "Running tests with PDB debugger..."
	python -m pytest --pdb --pdbcls=IPython.terminal.debugger:Pdb

test-profile:
	@echo "Running tests with profiling..."
	python -m pytest --profile --profile-svg

# Reporting
test-junit:
	@echo "Generating JUnit XML report..."
	python -m pytest --junitxml=test-results.xml

test-html-report:
	@echo "Generating HTML test report..."
	python -m pytest --html=test-report.html --self-contained-html

# Maintenance
update-deps:
	@echo "Updating test dependencies..."
	pip install --upgrade pytest pytest-asyncio pytest-cov hypothesis

check-deps:
	@echo "Checking dependency security..."
	safety check -r requirements.txt

# Help for specific categories
help-markers:
	@echo "Available test markers:"
	@echo "  unit         - Unit tests"
	@echo "  integration  - Integration tests"
	@echo "  property     - Property-based tests"
	@echo "  slow         - Slow running tests"
	@echo "  external     - Tests requiring external services"
	@echo "  database     - Tests requiring database"
	@echo "  redis        - Tests requiring Redis"
	@echo "  llm          - Tests requiring LLM services"
	@echo "  auth         - Authentication tests"
	@echo "  api          - API endpoint tests"
	@echo "  security     - Security tests"
	@echo "  performance  - Performance tests"

help-examples:
	@echo "Example usage:"
	@echo "  make test                    # Run all tests"
	@echo "  make test-unit              # Run only unit tests"
	@echo "  make test-property          # Run property-based tests"
	@echo "  make test-ci                # Run full CI pipeline"
	@echo "  make test-coverage          # Run tests with HTML coverage"
	@echo "  make quality-gate           # Run quality checks"