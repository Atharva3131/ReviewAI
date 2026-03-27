"""
Property-based tests for CI/CD Pipeline Artifact Actions Bug Condition
**Validates: Requirements 2.1, 2.2, 2.3, 2.4**

This test explores the bug condition where workflows using deprecated v3 artifact actions
fail during the preparation phase. This test encodes the EXPECTED BEHAVIOR and will:
- FAIL on unfixed code (confirming the bug exists)
- PASS after the fix is applied (confirming the bug is resolved)
"""

from pathlib import Path
from typing import Any, Dict, List, Tuple

import pytest
import yaml
from hypothesis import given, settings
from hypothesis import strategies as st


class TestArtifactActionsBugCondition:
    """Property-based tests for artifact actions v3 bug condition exploration"""

    # List of all 19 workflow files that use v3 artifact actions
    AFFECTED_WORKFLOWS = [
        ".github/workflows/ci.yml",
        ".github/workflows/code-quality.yml",
        ".github/workflows/deployment-orchestrator.yml",
        ".github/workflows/dependency-update.yml",
        ".github/workflows/monitoring.yml",
        ".github/workflows/performance-test.yml",
        ".github/workflows/release.yml",
        ".github/workflows/rollback.yml",
        ".github/workflows/security-scan.yml",
        ".github/workflows/staging-deploy.yml",
    ]

    def setup_method(self):
        """Set up test fixtures"""
        self.project_root = Path(__file__).parent.parent.parent
        self.workflows_dir = self.project_root / ".github" / "workflows"

    def load_workflow(self, workflow_path: str) -> Dict[str, Any]:
        """Load and parse a GitHub Actions workflow YAML file"""
        full_path = self.project_root / workflow_path
        with open(full_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def find_artifact_actions(self, workflow: Dict[str, Any]) -> List[Tuple[str, str]]:
        """
        Find all artifact action usages in a workflow.
        Returns list of tuples: (action_type, version)
        where action_type is 'upload' or 'download'
        """
        actions = []

        if "jobs" not in workflow:
            return actions

        for job_name, job_config in workflow["jobs"].items():
            if "steps" not in job_config:
                continue

            for step in job_config["steps"]:
                if "uses" not in step:
                    continue

                uses = step["uses"]
                if "actions/upload-artifact@" in uses:
                    version = uses.split("@")[1]
                    actions.append(("upload", version))
                elif "actions/download-artifact@" in uses:
                    version = uses.split("@")[1]
                    actions.append(("download", version))

        return actions

    def is_bug_condition(self, workflow_path: str) -> bool:
        """
        Check if workflow has the bug condition (uses v3 artifact actions).
        This is the fault condition that triggers the bug.
        """
        workflow = self.load_workflow(workflow_path)
        actions = self.find_artifact_actions(workflow)

        # Bug condition: workflow uses v3 artifact actions
        return any(version == "v3" for _, version in actions)

    @pytest.mark.parametrize("workflow_path", AFFECTED_WORKFLOWS)
    def test_workflow_uses_correct_artifact_version(self, workflow_path: str):
        """
        Property 1: Fault Condition - Artifact Actions Execute Successfully

        EXPECTED BEHAVIOR: Workflows should use v4 artifact actions and execute successfully.

        CRITICAL: This test MUST FAIL on unfixed code where workflows use v3.
        When this test fails, it confirms the bug exists (workflows use deprecated v3).
        When this test passes, it confirms the fix works (workflows use v4).

        **Validates: Requirements 2.1, 2.2, 2.3, 2.4**
        """
        workflow = self.load_workflow(workflow_path)
        actions = self.find_artifact_actions(workflow)

        # Assert that NO v3 artifact actions are present
        v3_actions = [
            (action_type, version)
            for action_type, version in actions
            if version == "v3"
        ]

        # This assertion will FAIL on unfixed code, documenting the counterexamples
        assert len(v3_actions) == 0, (
            f"COUNTEREXAMPLE FOUND: {workflow_path} uses deprecated v3 artifact actions: {v3_actions}. "
            f"This workflow will fail during GitHub Actions preparation phase with error: "
            f"'This request has been automatically failed because it uses a deprecated version of actions/upload-artifact: v3'. "
            f"Expected: All artifact actions should use v4 for successful execution."
        )

    @given(st.sampled_from(AFFECTED_WORKFLOWS))
    @settings(max_examples=len(AFFECTED_WORKFLOWS))
    def test_property_all_workflows_use_v4_artifacts(self, workflow_path: str):
        """
        Property-based test: For ALL affected workflows, artifact actions should be v4.

        This property-based test generates test cases for all 19 workflow files to verify
        that they use v4 artifact actions (expected behavior).

        CRITICAL: This test MUST FAIL on unfixed code.
        Failure confirms the bug exists and surfaces counterexamples.

        **Validates: Requirements 2.1, 2.2, 2.3, 2.4**
        """
        workflow = self.load_workflow(workflow_path)
        actions = self.find_artifact_actions(workflow)

        # Property: All artifact actions should use v4
        for action_type, version in actions:
            assert version == "v4", (
                f"COUNTEREXAMPLE: {workflow_path} uses {action_type}-artifact@{version}. "
                f"Expected v4 for successful workflow execution. "
                f"Bug condition detected: deprecated v3 will cause preparation phase failure."
            )

    def test_document_bug_condition_counterexamples(self):
        """
        Document all counterexamples where the bug condition exists.

        This test systematically checks all workflows and documents which ones
        have the bug condition (use v3 artifact actions).

        EXPECTED OUTCOME: This test FAILS and documents all affected workflows.
        """
        counterexamples = []

        for workflow_path in self.AFFECTED_WORKFLOWS:
            if self.is_bug_condition(workflow_path):
                workflow = self.load_workflow(workflow_path)
                actions = self.find_artifact_actions(workflow)
                v3_actions = [
                    (action_type, version)
                    for action_type, version in actions
                    if version == "v3"
                ]
                counterexamples.append(
                    {
                        "workflow": workflow_path,
                        "v3_actions_count": len(v3_actions),
                        "actions": v3_actions,
                    }
                )

        # Document the counterexamples
        counterexample_summary = "\n".join(
            [
                f"  - {ce['workflow']}: {ce['v3_actions_count']} v3 artifact actions"
                for ce in counterexamples
            ]
        )

        # This assertion will FAIL on unfixed code, documenting all counterexamples
        assert len(counterexamples) == 0, (
            f"BUG CONDITION CONFIRMED: Found {len(counterexamples)} workflows with deprecated v3 artifact actions:\n"
            f"{counterexample_summary}\n\n"
            f"These workflows will fail during GitHub Actions preparation phase with error:\n"
            f"'This request has been automatically failed because it uses a deprecated version of actions/upload-artifact: v3'\n\n"
            f"Expected behavior: All workflows should use v4 artifact actions for successful execution.\n"
            f"Impact: CI/CD pipeline is blocked - no tests, security scans, or deployments can execute."
        )
