"""
Bug Condition Exploration Test for Missing Test Runner

**Property 1: Fault Condition** - Test Runner File Missing

This test MUST FAIL on unfixed code - failure confirms the bug exists.
DO NOT attempt to fix the test or the code when it fails.

This test encodes the expected behavior - it will validate the fix when it passes after implementation.

**Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9, 2.10, 2.11**
"""

import subprocess
import sys
import os
from pathlib import Path
import pytest


# Get the backend directory path
BACKEND_DIR = Path(__file__).parent.parent


def test_run_tests_script_exists():
    """
    Test that the run_tests.py script exists in the backend directory.
    
    This test will FAIL on unfixed code (file doesn't exist).
    This test will PASS after the fix is implemented (file exists).
    """
    run_tests_path = BACKEND_DIR / "run_tests.py"
    assert run_tests_path.exists(), f"run_tests.py not found at {run_tests_path}"


def test_run_tests_ci_command_executes():
    """
    Test that 'python run_tests.py ci' can be executed without FileNotFoundError.
    
    This test will FAIL on unfixed code (FileNotFoundError or "can't open file").
    This test will PASS after the fix (command executes, may fail on test results but not on file missing).
    
    **Validates: Requirement 2.1**
    """
    result = subprocess.run(
        [sys.executable, "run_tests.py", "ci"],
        cwd=BACKEND_DIR,
        capture_output=True,
        text=True,
        timeout=60
    )
    
    # Check if the error indicates the file doesn't exist
    if result.returncode != 0:
        error_output = result.stderr.lower()
        if "can't open file" in error_output or "no such file" in error_output:
            pytest.fail(f"run_tests.py file not found. stderr: {result.stderr}")
    
    # If we get here, the file exists and was executed (even if tests failed)
    assert True, "Command executed successfully (file exists)"


def test_run_tests_install_command_executes():
    """
    Test that 'python run_tests.py install' can be executed without FileNotFoundError.
    
    This test will FAIL on unfixed code (FileNotFoundError or "can't open file").
    This test will PASS after the fix (command executes).
    
    **Validates: Requirement 2.2**
    """
    result = subprocess.run(
        [sys.executable, "run_tests.py", "install"],
        cwd=BACKEND_DIR,
        capture_output=True,
        text=True,
        timeout=120
    )
    
    # Check if the error indicates the file doesn't exist
    if result.returncode != 0:
        error_output = result.stderr.lower()
        if "can't open file" in error_output or "no such file" in error_output:
            pytest.fail(f"run_tests.py file not found. stderr: {result.stderr}")
    
    # If we get here, the file exists and was executed
    assert True, "Command executed successfully (file exists)"


def test_run_tests_test_command_with_flags_executes():
    """
    Test that 'python run_tests.py test --verbose --category unit' can be executed.
    
    This test will FAIL on unfixed code (FileNotFoundError or "can't open file").
    This test will PASS after the fix (command executes).
    
    **Validates: Requirement 2.6**
    """
    result = subprocess.run(
        [sys.executable, "run_tests.py", "test", "--verbose", "--category", "unit"],
        cwd=BACKEND_DIR,
        capture_output=True,
        text=True,
        timeout=60
    )
    
    # Check if the error indicates the file doesn't exist
    if result.returncode != 0:
        error_output = result.stderr.lower()
        if "can't open file" in error_output or "no such file" in error_output:
            pytest.fail(f"run_tests.py file not found. stderr: {result.stderr}")
    
    # If we get here, the file exists and was executed
    assert True, "Command executed successfully (file exists)"


def test_run_tests_help_command_executes():
    """
    Test that 'python run_tests.py --help' can be executed.
    
    This is a lightweight test that should complete quickly.
    
    This test will FAIL on unfixed code (FileNotFoundError or "can't open file").
    This test will PASS after the fix (command executes and shows help).
    """
    result = subprocess.run(
        [sys.executable, "run_tests.py", "--help"],
        cwd=BACKEND_DIR,
        capture_output=True,
        text=True,
        timeout=10
    )
    
    # Check if the error indicates the file doesn't exist
    if result.returncode != 0:
        error_output = result.stderr.lower()
        if "can't open file" in error_output or "no such file" in error_output:
            pytest.fail(f"run_tests.py file not found. stderr: {result.stderr}")
    
    # If we get here, the file exists and was executed
    assert True, "Command executed successfully (file exists)"


def test_run_tests_clean_command_executes():
    """
    Test that 'python run_tests.py clean' can be executed.
    
    This test will FAIL on unfixed code (FileNotFoundError or "can't open file").
    This test will PASS after the fix (command executes).
    
    **Validates: Requirement 2.4**
    """
    result = subprocess.run(
        [sys.executable, "run_tests.py", "clean"],
        cwd=BACKEND_DIR,
        capture_output=True,
        text=True,
        timeout=30
    )
    
    # Check if the error indicates the file doesn't exist
    if result.returncode != 0:
        error_output = result.stderr.lower()
        if "can't open file" in error_output or "no such file" in error_output:
            pytest.fail(f"run_tests.py file not found. stderr: {result.stderr}")
    
    # If we get here, the file exists and was executed
    assert True, "Command executed successfully (file exists)"
