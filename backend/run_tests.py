#!/usr/bin/env python3
"""
Test Runner Script for Revive AI Backend

This script orchestrates the entire test automation pipeline including:
- Dependency installation
- Environment setup
- Test execution (unit, integration, property-based)
- Code quality checks (linting)
- Security scanning
- Performance testing
- Report generation

Usage:
    python run_tests.py <command> [options]

Commands:
    ci          Run complete CI pipeline
    install     Install test dependencies
    setup       Configure test environment
    clean       Remove test artifacts
    lint        Run code quality checks
    test        Execute pytest with options
    property    Run property-based tests
    security    Run security scans
    performance Run performance tests
    report      Generate comprehensive reports
"""

import argparse
import subprocess
import sys
import os
import shutil
from pathlib import Path
from typing import List, Optional


def run_command(cmd: List[str], check: bool = True, cwd: Optional[str] = None) -> subprocess.CompletedProcess:
    """
    Execute a shell command and return the result.
    
    Args:
        cmd: Command and arguments as a list
        check: If True, raise exception on non-zero exit code
        cwd: Working directory for the command
    
    Returns:
        CompletedProcess instance with result
    """
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, capture_output=False)
    if check and result.returncode != 0:
        sys.exit(result.returncode)
    return result


def cmd_install(args):
    """Install test dependencies."""
    print("Installing test dependencies...")
    dependencies = [
        "pytest",
        "pytest-asyncio",
        "pytest-cov",
        "pytest-html",
        "pytest-json-report",
        "hypothesis",
        "bandit",
        "safety",
        "pytest-xdist",
    ]
    
    cmd = [sys.executable, "-m", "pip", "install"] + dependencies
    result = run_command(cmd, check=False)
    
    if result.returncode == 0:
        print("✓ Test dependencies installed successfully")
    else:
        print("✗ Failed to install test dependencies")
        sys.exit(1)


def cmd_setup(args):
    """Configure test environment."""
    print("Setting up test environment...")
    
    # Check Python version
    if sys.version_info < (3, 11):
        print(f"✗ Python 3.11+ required, found {sys.version_info.major}.{sys.version_info.minor}")
        sys.exit(1)
    print(f"✓ Python version: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    
    # Check for required environment variables (optional - warn if missing)
    env_vars = ["DATABASE_URL", "REDIS_URL", "SECRET_KEY"]
    missing_vars = [var for var in env_vars if not os.getenv(var)]
    if missing_vars:
        print(f"⚠ Warning: Missing environment variables: {', '.join(missing_vars)}")
        print("  Some tests may fail without proper configuration")
    else:
        print("✓ Required environment variables present")
    
    # Create necessary directories
    dirs = ["htmlcov", ".pytest_cache"]
    for dir_name in dirs:
        Path(dir_name).mkdir(exist_ok=True)
    print(f"✓ Created directories: {', '.join(dirs)}")
    
    # Verify pytest is importable
    try:
        import pytest
        print(f"✓ pytest is importable (version {pytest.__version__})")
    except ImportError:
        print("✗ pytest is not installed")
        sys.exit(1)
    
    print("✓ Test environment setup complete")


def cmd_clean(args):
    """Remove test artifacts."""
    print("Cleaning test artifacts...")
    
    # Files to remove
    files_to_remove = [
        ".coverage",
        "coverage.xml",
        "test_results.json",
        "pytest_html_report.html",
        "bandit_report.json",
        "safety_report.json",
    ]
    
    # Directories to remove
    dirs_to_remove = [
        "htmlcov",
        ".pytest_cache",
        "__pycache__",
    ]
    
    # Remove files
    for file_name in files_to_remove:
        file_path = Path(file_name)
        if file_path.exists():
            file_path.unlink()
            print(f"  Removed: {file_name}")
    
    # Remove directories
    for dir_name in dirs_to_remove:
        dir_path = Path(dir_name)
        if dir_path.exists():
            shutil.rmtree(dir_path)
            print(f"  Removed: {dir_name}/")
    
    # Remove __pycache__ directories recursively
    for pycache in Path(".").rglob("__pycache__"):
        shutil.rmtree(pycache)
        print(f"  Removed: {pycache}/")
    
    # Remove .pyc files
    for pyc_file in Path(".").rglob("*.pyc"):
        pyc_file.unlink()
        print(f"  Removed: {pyc_file}")
    
    print("✓ Cleanup complete")


def cmd_lint(args):
    """Run code quality checks."""
    print("Running code quality checks...")
    
    exit_code = 0
    
    # Run black
    print("\n--- Black (code formatting) ---")
    result = run_command(
        [sys.executable, "-m", "black", "--check", "app/", "tests/"],
        check=False
    )
    if result.returncode != 0:
        print("✗ Black found formatting issues")
        exit_code = 1
    else:
        print("✓ Black check passed")
    
    # Run isort
    print("\n--- isort (import sorting) ---")
    result = run_command(
        [sys.executable, "-m", "isort", "--check", "app/", "tests/"],
        check=False
    )
    if result.returncode != 0:
        print("✗ isort found import sorting issues")
        exit_code = 1
    else:
        print("✓ isort check passed")
    
    # Run flake8
    print("\n--- flake8 (linting) ---")
    result = run_command(
        [sys.executable, "-m", "flake8", "app/", "tests/"],
        check=False
    )
    if result.returncode != 0:
        print("✗ flake8 found linting issues")
        exit_code = 1
    else:
        print("✓ flake8 check passed")
    
    if exit_code == 0:
        print("\n✓ All linting checks passed")
    else:
        print("\n✗ Some linting checks failed")
    
    sys.exit(exit_code)


def cmd_test(args):
    """Execute pytest with options."""
    print("Running tests...")
    
    # Build pytest command
    cmd = [sys.executable, "-m", "pytest", "tests/"]
    
    # Add verbosity
    if args.verbose:
        cmd.append("-v")
    
    # Add category (marker) filter
    if args.category:
        cmd.extend(["-m", args.category])
    
    # Add custom marker expression
    if args.markers:
        cmd.extend(["-m", args.markers])
    
    # Add parallel execution
    if args.parallel:
        cmd.extend(["-n", "auto"])
    
    # Add fail-fast
    if args.fail_fast:
        cmd.append("-x")
    
    # Add HTML report
    if args.html:
        cmd.extend(["--html=pytest_html_report.html", "--self-contained-html"])
    
    # Add JSON report
    if args.json:
        cmd.extend(["--json-report", "--json-report-file=test_results.json"])
    
    # Add coverage (default unless --no-coverage)
    if not args.no_coverage:
        cmd.extend(["--cov=app", "--cov-report=term-missing", "--cov-report=html", "--cov-report=xml"])
    
    # Add -s flag (no output capture)
    if args.s:
        cmd.append("-s")
    
    # Run pytest
    result = run_command(cmd, check=False)
    sys.exit(result.returncode)


def cmd_property(args):
    """Run property-based tests."""
    print("Running property-based tests...")
    
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/",
        "-m", "property",
        "--verbose",
        "--hypothesis-show-statistics",
    ]
    
    result = run_command(cmd, check=False)
    sys.exit(result.returncode)


def cmd_security(args):
    """Run security scans."""
    print("Running security scans...")
    
    exit_code = 0
    
    # Run bandit
    print("\n--- Bandit (security linter) ---")
    result = run_command(
        [sys.executable, "-m", "bandit", "-r", "app/", "-f", "json", "-o", "bandit_report.json"],
        check=False
    )
    if result.returncode != 0:
        print("✗ Bandit found security issues")
        print("  Report saved to: bandit_report.json")
        exit_code = 1
    else:
        print("✓ Bandit scan passed")
    
    # Run safety
    print("\n--- Safety (dependency vulnerability check) ---")
    result = run_command(
        [sys.executable, "-m", "safety", "check", "--json", "--output", "safety_report.json"],
        check=False
    )
    if result.returncode != 0:
        print("✗ Safety found vulnerable dependencies")
        print("  Report saved to: safety_report.json")
        exit_code = 1
    else:
        print("✓ Safety scan passed")
    
    if exit_code == 0:
        print("\n✓ All security scans passed")
    else:
        print("\n✗ Some security scans found issues")
    
    sys.exit(exit_code)


def cmd_performance(args):
    """Run performance tests."""
    print("Running performance tests...")
    
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/",
        "-m", "performance",
        "--verbose",
    ]
    
    result = run_command(cmd, check=False)
    sys.exit(result.returncode)


def cmd_report(args):
    """Generate comprehensive reports."""
    print("Generating comprehensive test reports...")
    
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/",
        "--verbose",
        "--cov=app",
        "--cov-report=term-missing",
        "--cov-report=html",
        "--cov-report=xml",
        "--html=pytest_html_report.html",
        "--self-contained-html",
        "--json-report",
        "--json-report-file=test_results.json",
    ]
    
    result = run_command(cmd, check=False)
    
    print("\n" + "="*60)
    print("Report Generation Summary")
    print("="*60)
    print("Reports generated:")
    print("  - HTML Report:     pytest_html_report.html")
    print("  - JSON Report:     test_results.json")
    print("  - Coverage XML:    coverage.xml")
    print("  - Coverage HTML:   htmlcov/index.html")
    print("="*60)
    
    sys.exit(result.returncode)


def cmd_ci(args):
    """Run complete CI pipeline."""
    print("="*60)
    print("Running Complete CI Pipeline")
    print("="*60)
    
    exit_code = 0
    
    # Step 1: Linting
    print("\n[1/5] Running linting checks...")
    result = subprocess.run(
        [sys.executable, __file__, "lint"],
        capture_output=False
    )
    if result.returncode != 0:
        print("✗ Linting failed")
        exit_code = 1
    else:
        print("✓ Linting passed")
    
    # Step 2: Unit tests
    print("\n[2/5] Running unit tests...")
    result = subprocess.run(
        [sys.executable, __file__, "test", "--category", "unit", "--verbose"],
        capture_output=False
    )
    if result.returncode != 0:
        print("✗ Unit tests failed")
        exit_code = 1
    else:
        print("✓ Unit tests passed")
    
    # Step 3: Integration tests
    print("\n[3/5] Running integration tests...")
    result = subprocess.run(
        [sys.executable, __file__, "test", "--category", "integration", "--verbose"],
        capture_output=False
    )
    if result.returncode != 0:
        print("✗ Integration tests failed")
        exit_code = 1
    else:
        print("✓ Integration tests passed")
    
    # Step 4: Generate reports
    print("\n[4/5] Generating reports...")
    result = subprocess.run(
        [sys.executable, __file__, "report"],
        capture_output=False
    )
    if result.returncode != 0:
        print("✗ Report generation failed")
        exit_code = 1
    else:
        print("✓ Reports generated")
    
    # Step 5: Security scans
    print("\n[5/5] Running security scans...")
    result = subprocess.run(
        [sys.executable, __file__, "security"],
        capture_output=False
    )
    if result.returncode != 0:
        print("⚠ Security scans found issues (non-blocking)")
        # Don't fail CI on security issues, just warn
    else:
        print("✓ Security scans passed")
    
    print("\n" + "="*60)
    if exit_code == 0:
        print("✓ CI Pipeline Completed Successfully")
    else:
        print("✗ CI Pipeline Failed")
    print("="*60)
    
    sys.exit(exit_code)


def main():
    """Main entry point for the test runner."""
    parser = argparse.ArgumentParser(
        description="Test Runner for Revive AI Backend",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # CI command
    subparsers.add_parser("ci", help="Run complete CI pipeline")
    
    # Install command
    subparsers.add_parser("install", help="Install test dependencies")
    
    # Setup command
    subparsers.add_parser("setup", help="Configure test environment")
    
    # Clean command
    subparsers.add_parser("clean", help="Remove test artifacts")
    
    # Lint command
    subparsers.add_parser("lint", help="Run code quality checks")
    
    # Test command
    test_parser = subparsers.add_parser("test", help="Execute pytest with options")
    test_parser.add_argument("--verbose", action="store_true", help="Verbose output")
    test_parser.add_argument("--category", type=str, help="Test category (marker)")
    test_parser.add_argument("--parallel", action="store_true", help="Run tests in parallel")
    test_parser.add_argument("--fail-fast", action="store_true", help="Stop on first failure")
    test_parser.add_argument("--html", action="store_true", help="Generate HTML report")
    test_parser.add_argument("--json", action="store_true", help="Generate JSON report")
    test_parser.add_argument("--no-coverage", action="store_true", help="Disable coverage")
    test_parser.add_argument("--markers", type=str, help="Custom marker expression")
    test_parser.add_argument("-s", action="store_true", help="No output capture")
    
    # Property command
    subparsers.add_parser("property", help="Run property-based tests")
    
    # Security command
    subparsers.add_parser("security", help="Run security scans")
    
    # Performance command
    subparsers.add_parser("performance", help="Run performance tests")
    
    # Report command
    subparsers.add_parser("report", help="Generate comprehensive reports")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Dispatch to command handler
    command_handlers = {
        "ci": cmd_ci,
        "install": cmd_install,
        "setup": cmd_setup,
        "clean": cmd_clean,
        "lint": cmd_lint,
        "test": cmd_test,
        "property": cmd_property,
        "security": cmd_security,
        "performance": cmd_performance,
        "report": cmd_report,
    }
    
    handler = command_handlers.get(args.command)
    if handler:
        handler(args)
    else:
        print(f"Unknown command: {args.command}")
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
