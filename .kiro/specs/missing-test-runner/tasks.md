# Implementation Plan

- [x] 1. Write bug condition exploration test
  - **Property 1: Fault Condition** - Test Runner File Missing
  - **CRITICAL**: This test MUST FAIL on unfixed code - failure confirms the bug exists
  - **DO NOT attempt to fix the test or the code when it fails**
  - **NOTE**: This test encodes the expected behavior - it will validate the fix when it passes after implementation
  - **GOAL**: Surface counterexamples that demonstrate the bug exists
  - **Scoped PBT Approach**: Scope the property to concrete failing cases - commands that invoke run_tests.py
  - Test that `python run_tests.py ci` fails with FileNotFoundError on unfixed code
  - Test that `python run_tests.py install` fails with FileNotFoundError on unfixed code
  - Test that `python run_tests.py test --verbose --category unit` fails with FileNotFoundError on unfixed code
  - Test that `make test` fails because it invokes run_tests.py on unfixed code
  - Run test on UNFIXED code
  - **EXPECTED OUTCOME**: Test FAILS (this is correct - it proves the bug exists)
  - Document counterexamples found (FileNotFoundError messages, CI workflow failures)
  - Mark task complete when test is written, run, and failure is documented
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9, 2.10, 2.11_

- [x] 2. Write preservation property tests (BEFORE implementing fix)
  - **Property 2: Preservation** - Direct Testing Tools Continue Working
  - **IMPORTANT**: Follow observation-first methodology
  - Observe behavior on UNFIXED code for direct pytest invocations (not using run_tests.py)
  - Observe: `pytest tests/` works and uses pyproject.toml configuration
  - Observe: `pytest tests/ -m unit` filters tests correctly using markers
  - Observe: `pytest --cov=app` uses coverage exclusions from pyproject.toml
  - Observe: `bandit -r app/` runs security scans independently
  - Observe: `safety check` runs dependency checks independently
  - Write property-based tests capturing observed behavior patterns from Preservation Requirements
  - Property-based testing generates many test cases for stronger guarantees
  - Run tests on UNFIXED code
  - **EXPECTED OUTCOME**: Tests PASS (this confirms baseline behavior to preserve)
  - Mark task complete when tests are written, run, and passing on unfixed code
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

- [x] 3. Create run_tests.py script

  - [x] 3.1 Implement command parser and main structure
    - Create backend/run_tests.py with argparse-based CLI
    - Implement main commands: ci, install, setup, clean, lint, test, property, security, performance, report
    - Add test command flags: --verbose, --category, --parallel, --fail-fast, --html, --json, --no-coverage, --markers, -s
    - Implement proper exit code handling and error messages
    - _Bug_Condition: isBugCondition(input) where input.command STARTS_WITH "python run_tests.py" AND NOT fileExists("backend/run_tests.py")_
    - _Expected_Behavior: Script exists, accepts commands, executes test operations, returns proper exit codes_
    - _Preservation: Direct pytest, bandit, safety invocations remain unchanged; pyproject.toml configuration remains source of truth_
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9, 2.10, 2.11, 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

  - [x] 3.2 Implement install command
    - Execute: pip install pytest pytest-asyncio pytest-cov pytest-html pytest-json-report hypothesis bandit safety pytest-xdist
    - Verify installation success and return appropriate exit code
    - _Requirements: 2.2_

  - [x] 3.3 Implement setup command
    - Verify Python version >= 3.11
    - Check for required environment variables (DATABASE_URL, REDIS_URL, SECRET_KEY)
    - Create necessary directories (htmlcov, .pytest_cache)
    - Verify pytest is importable
    - _Requirements: 2.3_

  - [x] 3.4 Implement clean command
    - Delete test artifacts: .coverage, coverage.xml, htmlcov/, .pytest_cache/, test_results.json, pytest_html_report.html
    - Remove __pycache__ directories recursively
    - Remove *.pyc files
    - _Requirements: 2.4_

  - [x] 3.5 Implement lint command
    - Execute: black --check app/ tests/
    - Execute: isort --check app/ tests/
    - Execute: flake8 app/ tests/
    - Aggregate exit codes (fail if any linter fails)
    - _Requirements: 2.5_

  - [x] 3.6 Implement test command
    - Build pytest command from arguments
    - Map --category to -m marker (e.g., --category unit → -m unit)
    - Map --parallel to -n auto (pytest-xdist)
    - Map --fail-fast to -x
    - Map --html to --html=pytest_html_report.html --self-contained-html
    - Map --json to --json-report --json-report-file=test_results.json
    - Map --no-coverage to remove --cov flags
    - Map --markers to -m (custom marker expression)
    - Map -s to -s (no output capture)
    - Default: pytest tests/ with coverage
    - _Requirements: 2.6_

  - [x] 3.7 Implement property command
    - Execute: pytest tests/ -m property --verbose
    - Use hypothesis settings for extended testing
    - _Requirements: 2.7_

  - [x] 3.8 Implement security command
    - Execute: bandit -r app/ -f json -o bandit_report.json
    - Execute: safety check --json > safety_report.json
    - Report findings and exit with non-zero if issues found
    - _Requirements: 2.8_

  - [x] 3.9 Implement performance command
    - Execute: pytest tests/ -m performance --verbose
    - Generate performance report
    - _Requirements: 2.9_

  - [x] 3.10 Implement report command
    - Execute tests with all report formats enabled
    - Generate: HTML report, JSON report, coverage XML, coverage HTML
    - Print summary of report locations
    - _Requirements: 2.10_

  - [x] 3.11 Implement ci command
    - Run linting (black --check, isort --check, flake8)
    - Run unit tests with coverage
    - Run integration tests
    - Generate HTML and JSON reports
    - Generate coverage reports (XML, HTML)
    - Exit with non-zero code if any step fails
    - _Requirements: 2.1_

  - [x] 3.12 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - Test Runner Executes Commands
    - **IMPORTANT**: Re-run the SAME test from task 1 - do NOT write a new test
    - The test from task 1 encodes the expected behavior
    - When this test passes, it confirms the expected behavior is satisfied
    - Run bug condition exploration test from step 1
    - Verify `python run_tests.py ci` executes successfully
    - Verify `python run_tests.py install` executes successfully
    - Verify `python run_tests.py test --verbose --category unit` executes successfully
    - Verify `make test` executes successfully
    - **EXPECTED OUTCOME**: Test PASSES (confirms bug is fixed)
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9, 2.10, 2.11_

  - [x] 3.13 Verify preservation tests still pass
    - **Property 2: Preservation** - Direct Testing Tools Continue Working
    - **IMPORTANT**: Re-run the SAME tests from task 2 - do NOT write new tests
    - Run preservation property tests from step 2
    - Verify direct pytest invocations work identically
    - Verify test markers filter correctly
    - Verify coverage configuration is preserved
    - Verify direct bandit and safety commands work identically
    - Verify artifact paths remain unchanged
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)
    - Confirm all tests still pass after fix (no regressions)

- [x] 4. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.
