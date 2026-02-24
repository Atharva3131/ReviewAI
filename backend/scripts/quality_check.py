#!/usr/bin/env python3
"""
Backend Code Quality Check Script
Runs all code quality checks for the backend codebase.
"""

import subprocess
import sys
from pathlib import Path
from typing import List, Tuple

# Set UTF-8 encoding for Windows console
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())

# Color codes for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"

# Symbols (fallback for Windows)
CHECK_MARK = "✓" if sys.platform != "win32" else "+"
CROSS_MARK = "✗" if sys.platform != "win32" else "x"
WARNING_MARK = "⚠" if sys.platform != "win32" else "!"


def print_header(message: str) -> None:
    """Print a formatted header."""
    print(f"\n{BLUE}{'=' * 80}{RESET}")
    print(f"{BLUE}{message.center(80)}{RESET}")
    print(f"{BLUE}{'=' * 80}{RESET}\n")


def print_success(message: str) -> None:
    """Print a success message."""
    print(f"{GREEN}{CHECK_MARK} {message}{RESET}")


def print_error(message: str) -> None:
    """Print an error message."""
    print(f"{RED}{CROSS_MARK} {message}{RESET}")


def print_warning(message: str) -> None:
    """Print a warning message."""
    print(f"{YELLOW}{WARNING_MARK} {message}{RESET}")


def run_command(
    command: List[str], description: str, allow_failure: bool = False
) -> Tuple[bool, str]:
    """
    Run a shell command and return success status.
    
    Args:
        command: Command to run as list of strings
        description: Description of what the command does
        allow_failure: If True, don't fail the entire script on error
        
    Returns:
        Tuple of (success, output)
    """
    print(f"\n{YELLOW}Running: {description}{RESET}")
    print(f"Command: {' '.join(command)}")
    
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            encoding='utf-8',
            errors='replace',
        )
        
        if result.returncode == 0:
            print_success(f"{description} passed")
            return True, result.stdout
        else:
            if allow_failure:
                print_warning(f"{description} failed (non-blocking)")
                print(result.stdout)
                print(result.stderr)
                return False, result.stderr
            else:
                print_error(f"{description} failed")
                print(result.stdout)
                print(result.stderr)
                return False, result.stderr
    except Exception as e:
        print_error(f"Error running {description}: {str(e)}")
        return False, str(e)


def check_black() -> bool:
    """Check code formatting with Black."""
    return run_command(
        ["black", "--check", "--diff", "app/", "--config", "pyproject.toml"],
        "Black formatting check",
    )[0]


def check_isort() -> bool:
    """Check import sorting with isort."""
    return run_command(
        ["isort", "--check-only", "--diff", "app/", "--settings-path", "pyproject.toml"],
        "isort import sorting check",
    )[0]


def check_flake8() -> bool:
    """Run flake8 linting."""
    return run_command(
        ["flake8", "app/", "--count", "--statistics", "--config", ".flake8"],
        "Flake8 linting",
    )[0]


def check_mypy() -> bool:
    """Run mypy type checking."""
    return run_command(
        ["mypy", "app/", "--config-file", "pyproject.toml"],
        "MyPy type checking",
        allow_failure=True,
    )[0]


def check_pylint() -> bool:
    """Run pylint code analysis."""
    return run_command(
        ["pylint", "app/", "--exit-zero"],
        "Pylint code analysis",
        allow_failure=True,
    )[0]


def check_bandit() -> bool:
    """Run bandit security checks."""
    return run_command(
        ["bandit", "-r", "app/", "-f", "txt"],
        "Bandit security check",
        allow_failure=True,
    )[0]


def check_safety() -> bool:
    """Check dependencies for security vulnerabilities."""
    return run_command(
        ["safety", "check", "-r", "requirements.txt"],
        "Safety dependency check",
        allow_failure=True,
    )[0]


def check_complexity() -> bool:
    """Check code complexity with radon."""
    success = True
    
    # Cyclomatic complexity
    result = run_command(
        ["radon", "cc", "app/", "-a", "-nc"],
        "Radon cyclomatic complexity",
        allow_failure=True,
    )
    
    # Maintainability index
    run_command(
        ["radon", "mi", "app/", "-nc"],
        "Radon maintainability index",
        allow_failure=True,
    )
    
    return result[0]


def fix_formatting() -> bool:
    """Auto-fix formatting issues."""
    print_header("Auto-fixing Code Formatting")
    
    black_success = run_command(
        ["black", "app/", "--config", "pyproject.toml"],
        "Black auto-formatting",
    )[0]
    
    isort_success = run_command(
        ["isort", "app/", "--settings-path", "pyproject.toml"],
        "isort auto-sorting",
    )[0]
    
    return black_success and isort_success


def main() -> int:
    """Main entry point."""
    # Change to backend directory
    backend_dir = Path(__file__).parent.parent
    import os
    os.chdir(backend_dir)
    
    # Parse command line arguments
    fix_mode = "--fix" in sys.argv
    
    if fix_mode:
        print_header("Backend Code Quality - Fix Mode")
        if fix_formatting():
            print_success("\nFormatting fixes applied successfully!")
            return 0
        else:
            print_error("\nSome formatting fixes failed")
            return 1
    
    print_header("Backend Code Quality Checks")
    
    results = {}
    
    # Run all checks
    print_header("Code Formatting")
    results["black"] = check_black()
    results["isort"] = check_isort()
    
    print_header("Code Linting")
    results["flake8"] = check_flake8()
    
    print_header("Type Checking")
    results["mypy"] = check_mypy()
    
    print_header("Code Analysis")
    results["pylint"] = check_pylint()
    
    print_header("Security Checks")
    results["bandit"] = check_bandit()
    results["safety"] = check_safety()
    
    print_header("Complexity Analysis")
    results["complexity"] = check_complexity()
    
    # Print summary
    print_header("Quality Check Summary")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for check, success in results.items():
        if success:
            print_success(f"{check.capitalize()}: PASSED")
        else:
            print_error(f"{check.capitalize()}: FAILED")
    
    print(f"\n{BLUE}Results: {passed}/{total} checks passed{RESET}")
    
    if passed == total:
        print_success(f"\n{CHECK_MARK} All quality checks passed!")
        return 0
    else:
        print_error(f"\n{CROSS_MARK} {total - passed} quality check(s) failed")
        print_warning("\nRun with --fix to auto-fix formatting issues")
        return 1


if __name__ == "__main__":
    sys.exit(main())
