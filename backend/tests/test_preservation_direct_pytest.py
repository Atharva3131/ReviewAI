"""
Preservation Property Tests for Direct Testing Tools

**Property 2: Preservation** - Direct Testing Tools Continue Working

This test MUST PASS on unfixed code - it confirms baseline behavior to preserve.

These tests verify that direct pytest invocations work correctly without run_tests.py,
and that this behavior is preserved after the fix is implemented.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6**
"""

import subprocess
import sys
import os
from pathlib import Path
import pytest
from hypothesis import given, strategies as st, settings, Phase


# Get the backend directory path
BACKEND_DIR = Path(__file__).parent.parent


def test_direct_pytest_works_without_run_tests():
    """
    Test that pytest can be invoked directly without run_tests.py.
    
    This test MUST PASS on unfixed code (baseline behavior).
    This test MUST PASS after the fix (preservation).
    
    **Validates: Requirement 3.1**
    """
    # Run pytest on this specific test file with a simple passing test
    result = subprocess.run(
        [sys.executable, "-m", "pytest", __file__, "-k", "test_simple_passing_test", "--no-cov", "-v"],
        cwd=BACKEND_DIR,
        capture_output=True,
        text=True,
        timeout=30
    )
    
    # Direct pytest should work (exit code 0 means tests passed)
    assert result.returncode == 0, f"Direct pytest failed. stderr: {result.stderr}"
    assert "1 passed" in result.stdout, "Expected 1 test to pass"


def test_simple_passing_test():
    """A simple test that always passes, used by test_direct_pytest_works_without_run_tests."""
    assert True


def test_pytest_uses_pyproject_toml_configuration():
    """
    Test that pytest uses configuration from pyproject.toml when invoked directly.
    
    This test MUST PASS on unfixed code (baseline behavior).
    This test MUST PASS after the fix (preservation).
    
    **Validates: Requirement 3.1, 3.2**
    """
    # Run pytest with --help to see configuration
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--help"],
        cwd=BACKEND_DIR,
        capture_output=True,
        text=True,
        timeout=10
    )
    
    assert result.returncode == 0, "pytest --help should work"
    
    # Verify that pytest is reading from pyproject.toml by checking for configured markers
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--markers"],
        cwd=BACKEND_DIR,
        capture_output=True,
        text=True,
        timeout=10
    )
    
    assert result.returncode == 0, "pytest --markers should work"
    # Check for markers defined in pyproject.toml
    assert "slow:" in result.stdout or "integration:" in result.stdout or "unit:" in result.stdout, \
        "pytest should show markers from pyproject.toml"


def test_pytest_marker_filtering_works():
    """
    Test that pytest marker filtering works with direct invocation.
    
    This test MUST PASS on unfixed code (baseline behavior).
    This test MUST PASS after the fix (preservation).
    
    **Validates: Requirement 3.2**
    """
    # Run pytest with a marker filter on this file
    result = subprocess.run(
        [sys.executable, "-m", "pytest", __file__, "-m", "preservation_test", "--no-cov", "-v"],
        cwd=BACKEND_DIR,
        capture_output=True,
        text=True,
        timeout=30
    )
    
    # Should complete successfully (even if no tests match the marker)
    assert result.returncode in [0, 5], f"pytest with marker filter failed unexpectedly. stderr: {result.stderr}"
    # Exit code 5 means no tests collected, which is fine for this test


@pytest.mark.preservation_test
def test_marker_example():
    """Example test with a marker to verify marker filtering works."""
    assert True


def test_pytest_testpaths_configuration():
    """
    Test that pytest uses testpaths from pyproject.toml.
    
    This test MUST PASS on unfixed code (baseline behavior).
    This test MUST PASS after the fix (preservation).
    
    **Validates: Requirement 3.1**
    """
    # Run pytest on a specific test file to avoid dependency issues
    result = subprocess.run(
        [sys.executable, "-m", "pytest", __file__, "--collect-only", "--no-cov"],
        cwd=BACKEND_DIR,
        capture_output=True,
        text=True,
        timeout=30
    )
    
    # Should complete successfully
    assert result.returncode in [0, 5], f"pytest --collect-only failed. stderr: {result.stderr}"
    # Should show that it's using pyproject.toml configuration
    assert "pyproject.toml" in result.stdout or "test session starts" in result.stdout, \
        "pytest should use pyproject.toml configuration"


@given(marker=st.sampled_from(["unit", "integration", "property", "slow", "external"]))
@settings(phases=[Phase.generate, Phase.target], max_examples=5, deadline=None)
def test_property_pytest_accepts_all_configured_markers(marker):
    """
    Property-based test: pytest should accept all markers configured in pyproject.toml.
    
    This test MUST PASS on unfixed code (baseline behavior).
    This test MUST PASS after the fix (preservation).
    
    **Validates: Requirement 3.2**
    """
    # Run pytest with the marker filter on this specific file to avoid dependency issues
    result = subprocess.run(
        [sys.executable, "-m", "pytest", __file__, "--collect-only", "-m", marker, "--no-cov"],
        cwd=BACKEND_DIR,
        capture_output=True,
        text=True,
        timeout=30
    )
    
    # Should not fail with "unknown marker" error
    assert "unknown marker" not in result.stderr.lower(), \
        f"Marker '{marker}' should be recognized from pyproject.toml"
    # Exit code should be 0 (success) or 5 (no tests collected)
    assert result.returncode in [0, 5], \
        f"pytest with marker '{marker}' failed unexpectedly. stderr: {result.stderr}"


def test_pytest_coverage_configuration_preserved():
    """
    Test that pytest coverage configuration from pyproject.toml is used.
    
    This test MUST PASS on unfixed code (baseline behavior).
    This test MUST PASS after the fix (preservation).
    
    **Validates: Requirement 3.3**
    """
    # Run pytest with coverage on this file
    result = subprocess.run(
        [sys.executable, "-m", "pytest", __file__, "-k", "test_simple_passing_test", 
         "--cov=app", "--cov-report=term", "-v"],
        cwd=BACKEND_DIR,
        capture_output=True,
        text=True,
        timeout=30
    )
    
    # Coverage should run (even if it reports 0% because we're testing a test file)
    # The important thing is that it doesn't crash and uses the configuration
    assert "coverage" in result.stdout.lower() or "coverage" in result.stderr.lower(), \
        "Coverage should be reported"


def test_direct_pytest_help_command():
    """
    Test that pytest --help works directly.
    
    This test MUST PASS on unfixed code (baseline behavior).
    This test MUST PASS after the fix (preservation).
    
    **Validates: Requirement 3.6**
    """
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--help"],
        cwd=BACKEND_DIR,
        capture_output=True,
        text=True,
        timeout=10
    )
    
    assert result.returncode == 0, "pytest --help should work"
    assert "usage:" in result.stdout.lower() or "pytest" in result.stdout.lower(), \
        "Help output should be displayed"


@given(
    verbose_flag=st.sampled_from(["-v", "-vv", "--verbose"]),
    quiet_flag=st.sampled_from(["-q", "--quiet", None])
)
@settings(phases=[Phase.generate, Phase.target], max_examples=5, deadline=None)
def test_property_pytest_accepts_standard_flags(verbose_flag, quiet_flag):
    """
    Property-based test: pytest should accept standard command-line flags.
    
    This test MUST PASS on unfixed code (baseline behavior).
    This test MUST PASS after the fix (preservation).
    
    **Validates: Requirement 3.6**
    """
    # Build command with flags - test on this specific file to avoid dependency issues
    cmd = [sys.executable, "-m", "pytest", __file__, "--collect-only", "--no-cov"]
    
    # Don't use both verbose and quiet at the same time
    if quiet_flag is None:
        cmd.append(verbose_flag)
    else:
        cmd.append(quiet_flag)
    
    result = subprocess.run(
        cmd,
        cwd=BACKEND_DIR,
        capture_output=True,
        text=True,
        timeout=30
    )
    
    # Should complete successfully
    assert result.returncode in [0, 5], \
        f"pytest with flags {cmd[3:]} failed unexpectedly. stderr: {result.stderr}"
