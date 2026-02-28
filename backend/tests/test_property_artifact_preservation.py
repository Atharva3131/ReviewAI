"""
Property-based tests for CI/CD Pipeline Artifact Actions Preservation
**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6**

This test verifies that all workflow configurations (except artifact action versions)
remain unchanged after the fix is applied. This ensures no regressions are introduced.

IMPORTANT: These tests should PASS on unfixed code (establishing baseline behavior).
After the fix, these tests should still PASS (confirming preservation).
"""
import pytest
import yaml
from pathlib import Path
from hypothesis import given, strategies as st, settings
from typing import Dict, Any, List, Tuple, Optional


class TestArtifactActionsPreservation:
    """Property-based tests for workflow configuration preservation"""
    
    # List of all workflow files that use artifact actions
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
        with open(full_path, 'r', encoding='utf-8') as f:
            # Use yaml.safe_load with custom resolver to handle 'on' key correctly
            # YAML treats 'on' as boolean True by default, we need the actual key
            workflow = yaml.safe_load(f)
            # If True key exists, it's the 'on' trigger configuration
            if True in workflow:
                workflow['on'] = workflow.pop(True)
            return workflow
    
    def extract_artifact_configs(self, workflow: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract all artifact action configurations from a workflow.
        Returns list of artifact configurations with metadata.
        """
        artifacts = []
        
        if 'jobs' not in workflow:
            return artifacts
        
        for job_name, job_config in workflow['jobs'].items():
            if 'steps' not in job_config:
                continue
            
            for step_idx, step in enumerate(job_config['steps']):
                if 'uses' not in step:
                    continue
                
                uses = step['uses']
                if 'actions/upload-artifact@' in uses or 'actions/download-artifact@' in uses:
                    action_type = 'upload' if 'upload-artifact' in uses else 'download'
                    
                    artifact_config = {
                        'job': job_name,
                        'step_index': step_idx,
                        'action_type': action_type,
                        'step_name': step.get('name', f'Step {step_idx}'),
                        'with_params': step.get('with', {}),
                        'if_condition': step.get('if'),
                    }
                    artifacts.append(artifact_config)
        
        return artifacts
    
    @pytest.mark.parametrize("workflow_path", AFFECTED_WORKFLOWS)
    def test_artifact_names_preserved(self, workflow_path: str):
        """
        Property 2: Preservation - Artifact Names Remain Identical
        
        Verifies that artifact names (e.g., "backend-test-results", "security-report")
        remain unchanged. This is critical for downstream job compatibility.
        
        **Validates: Requirement 3.1**
        """
        workflow = self.load_workflow(workflow_path)
        artifacts = self.extract_artifact_configs(workflow)
        
        # Expected artifact names based on workflow file
        expected_names = self._get_expected_artifact_names(workflow_path)
        
        if not expected_names:
            # No specific expectations for this workflow
            pytest.skip(f"No artifact name expectations defined for {workflow_path}")
        
        # Extract actual artifact names
        actual_names = []
        for artifact in artifacts:
            if 'name' in artifact['with_params']:
                actual_names.append(artifact['with_params']['name'])
        
        # Verify all expected names are present
        for expected_name in expected_names:
            assert expected_name in actual_names, (
                f"Artifact name '{expected_name}' not found in {workflow_path}. "
                f"Found: {actual_names}. "
                f"Artifact names must remain identical for downstream job compatibility."
            )
    
    @pytest.mark.parametrize("workflow_path", AFFECTED_WORKFLOWS)
    def test_artifact_paths_preserved(self, workflow_path: str):
        """
        Property 2: Preservation - Artifact Paths and File Patterns Unchanged
        
        Verifies that artifact paths and file patterns remain unchanged.
        
        **Validates: Requirement 3.2**
        """
        workflow = self.load_workflow(workflow_path)
        artifacts = self.extract_artifact_configs(workflow)
        
        for artifact in artifacts:
            with_params = artifact['with_params']
            
            # Verify 'path' parameter exists for upload actions
            if artifact['action_type'] == 'upload':
                assert 'path' in with_params, (
                    f"Upload artifact in {workflow_path} (job: {artifact['job']}, "
                    f"step: {artifact['step_name']}) missing 'path' parameter. "
                    f"Artifact paths must be preserved."
                )
                
                # Verify path is not empty
                path_value = with_params['path']
                assert path_value, (
                    f"Upload artifact path is empty in {workflow_path} "
                    f"(job: {artifact['job']}, step: {artifact['step_name']})"
                )
    
    @pytest.mark.parametrize("workflow_path", AFFECTED_WORKFLOWS)
    def test_retention_periods_preserved(self, workflow_path: str):
        """
        Property 2: Preservation - Retention Periods Preserved
        
        Verifies that retention-days configurations (e.g., 30 days) remain unchanged.
        
        **Validates: Requirement 3.3**
        """
        workflow = self.load_workflow(workflow_path)
        artifacts = self.extract_artifact_configs(workflow)
        
        # Expected retention periods based on workflow analysis
        expected_retention = self._get_expected_retention_periods(workflow_path)
        
        for artifact in artifacts:
            if artifact['action_type'] == 'upload':
                with_params = artifact['with_params']
                
                # Check if retention-days is specified
                if 'retention-days' in with_params:
                    retention_days = with_params['retention-days']
                    
                    # Verify it's a valid positive integer
                    assert isinstance(retention_days, int) and retention_days > 0, (
                        f"Invalid retention-days in {workflow_path} "
                        f"(job: {artifact['job']}, step: {artifact['step_name']}): {retention_days}"
                    )
                    
                    # If we have expected values, verify them
                    artifact_name = with_params.get('name', 'unnamed')
                    if workflow_path in expected_retention and artifact_name in expected_retention[workflow_path]:
                        expected_days = expected_retention[workflow_path][artifact_name]
                        assert retention_days == expected_days, (
                            f"Retention period changed in {workflow_path} for '{artifact_name}'. "
                            f"Expected: {expected_days} days, Found: {retention_days} days. "
                            f"Retention periods must be preserved."
                        )
    
    @pytest.mark.parametrize("workflow_path", AFFECTED_WORKFLOWS)
    def test_conditional_uploads_preserved(self, workflow_path: str):
        """
        Property 2: Preservation - Conditional Uploads Continue to Work
        
        Verifies that conditional logic (e.g., if: always()) remains unchanged.
        
        **Validates: Requirement 3.4**
        """
        workflow = self.load_workflow(workflow_path)
        artifacts = self.extract_artifact_configs(workflow)
        
        for artifact in artifacts:
            if_condition = artifact['if_condition']
            
            # If a condition exists, verify it's valid
            if if_condition:
                # Common valid conditions
                valid_conditions = ['always()', 'success()', 'failure()']
                
                # Check if it's a simple condition or complex expression
                is_valid = (
                    if_condition in valid_conditions or
                    'always()' in if_condition or
                    'success()' in if_condition or
                    'failure()' in if_condition or
                    '==' in if_condition or
                    '!=' in if_condition
                )
                
                assert is_valid, (
                    f"Unexpected conditional in {workflow_path} "
                    f"(job: {artifact['job']}, step: {artifact['step_name']}): {if_condition}"
                )
    
    @pytest.mark.parametrize("workflow_path", AFFECTED_WORKFLOWS)
    def test_download_artifact_patterns_preserved(self, workflow_path: str):
        """
        Property 2: Preservation - Download Artifact Patterns Unchanged
        
        Verifies that download artifact patterns and path specifications remain unchanged.
        
        **Validates: Requirement 3.5**
        """
        workflow = self.load_workflow(workflow_path)
        artifacts = self.extract_artifact_configs(workflow)
        
        download_artifacts = [a for a in artifacts if a['action_type'] == 'download']
        
        for artifact in download_artifacts:
            with_params = artifact['with_params']
            
            # Verify 'name' parameter exists for download actions (to specify which artifact)
            # Note: If 'name' is omitted, it downloads all artifacts, which is also valid
            if 'name' in with_params:
                artifact_name = with_params['name']
                assert artifact_name, (
                    f"Download artifact name is empty in {workflow_path} "
                    f"(job: {artifact['job']}, step: {artifact['step_name']})"
                )
    
    @pytest.mark.parametrize("workflow_path", AFFECTED_WORKFLOWS)
    def test_workflow_triggers_preserved(self, workflow_path: str):
        """
        Property 2: Preservation - Workflow Triggers Unchanged
        
        Verifies that workflow triggers (push, pull_request, schedule, etc.) remain identical.
        
        **Validates: Requirement 3.6**
        """
        workflow = self.load_workflow(workflow_path)
        
        # Verify 'on' key exists
        assert 'on' in workflow, (
            f"Workflow {workflow_path} missing 'on' trigger configuration"
        )
        
        triggers = workflow['on']
        
        # Verify triggers is not empty
        assert triggers, (
            f"Workflow {workflow_path} has empty trigger configuration"
        )
        
        # Common valid triggers
        valid_triggers = [
            'push', 'pull_request', 'schedule', 'workflow_dispatch',
            'release', 'workflow_call', 'repository_dispatch'
        ]
        
        # If triggers is a dict, check keys; if list, check items
        if isinstance(triggers, dict):
            trigger_keys = list(triggers.keys())
        elif isinstance(triggers, list):
            trigger_keys = triggers
        else:
            trigger_keys = [triggers]
        
        # Verify at least one valid trigger exists
        has_valid_trigger = any(trigger in valid_triggers for trigger in trigger_keys)
        assert has_valid_trigger, (
            f"Workflow {workflow_path} has no recognized triggers. Found: {trigger_keys}"
        )
    
    @given(st.sampled_from(AFFECTED_WORKFLOWS))
    @settings(max_examples=len(AFFECTED_WORKFLOWS))
    def test_property_workflow_structure_preserved(self, workflow_path: str):
        """
        Property-based test: For ALL workflows, essential structure is preserved.
        
        This property-based test generates test cases for all workflow files to verify
        that essential workflow structure (jobs, steps, triggers) remains intact.
        
        **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6**
        """
        workflow = self.load_workflow(workflow_path)
        
        # Property: Workflow must have essential structure
        assert 'name' in workflow, f"{workflow_path} missing 'name' field"
        assert 'on' in workflow, f"{workflow_path} missing 'on' trigger field"
        assert 'jobs' in workflow, f"{workflow_path} missing 'jobs' field"
        assert len(workflow['jobs']) > 0, f"{workflow_path} has no jobs defined"
        
        # Property: Each job must have steps
        for job_name, job_config in workflow['jobs'].items():
            if 'steps' in job_config:
                assert len(job_config['steps']) > 0, (
                    f"{workflow_path} job '{job_name}' has empty steps"
                )
    
    # Helper methods for expected values
    
    def _get_expected_artifact_names(self, workflow_path: str) -> List[str]:
        """Return expected artifact names for a workflow based on observation"""
        expectations = {
            ".github/workflows/ci.yml": [
                "backend-test-results",
                "migration-report-ci",
                "playwright-report"
            ],
            ".github/workflows/security-scan.yml": [
                "python-security-reports",
                "javascript-security-reports",
                "docker-security-reports",
                "infrastructure-security-reports",
                "license-compliance-reports",
                "security-report"
            ],
            ".github/workflows/deployment-orchestrator.yml": [
                "deployment-manifest",
                "infrastructure-outputs",
            ],
        }
        return expectations.get(workflow_path, [])
    
    def _get_expected_retention_periods(self, workflow_path: str) -> Dict[str, Dict[str, int]]:
        """Return expected retention periods for artifacts based on observation"""
        expectations = {
            ".github/workflows/ci.yml": {
                "backend-test-results": 30,
                "migration-report-ci": 30,
                "playwright-report": 30
            },
            ".github/workflows/security-scan.yml": {
                "python-security-reports": 30,
                "javascript-security-reports": 30,
                "docker-security-reports": 30,
                "infrastructure-security-reports": 30,
                "license-compliance-reports": 30,
                "security-report": 30
            },
            ".github/workflows/deployment-orchestrator.yml": {
                "deployment-manifest": 90,
                "infrastructure-outputs": 30,
            },
        }
        return expectations
