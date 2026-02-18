"""End-to-end test for full workflow cycle (Issue #138 Cycle 3.6).

Tests complete workflow cycle: research → planning → design → tdd → integration → documentation
with commit-scope encoding and ScopeDecoder validation.
"""

import subprocess
from pathlib import Path

import pytest
import yaml

from backend.core.phase_detection import ScopeDecoder
from mcp_server.adapters.git_adapter import GitAdapter
from mcp_server.managers.git_manager import GitManager
from mcp_server.managers.phase_state_engine import PhaseStateEngine
from mcp_server.managers.project_manager import ProjectManager


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    """Create temporary git repository with ST3 configuration."""
    # Initialize git repo
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )

    # Create .st3 directory structure
    st3_dir = tmp_path / ".st3"
    st3_dir.mkdir()

    # Create workphases.yaml
    workphases = {
        "version": "1.0",
        "phases": {
            "research": {
                "display_name": "Research",
                "description": "Research phase",
                "commit_type_hint": "docs",
                "subphases": [],
            },
            "planning": {
                "display_name": "Planning",
                "description": "Planning phase",
                "commit_type_hint": "docs",
                "subphases": [],
            },
            "design": {
                "display_name": "Design",
                "description": "Design phase",
                "commit_type_hint": "docs",
                "subphases": [],
            },
            "tdd": {
                "display_name": "TDD",
                "description": "TDD cycle",
                "commit_type_hint": None,
                "subphases": ["red", "green", "refactor"],
            },
            "integration": {
                "display_name": "Integration",
                "description": "Integration phase",
                "commit_type_hint": "test",
                "subphases": [],
            },
            "documentation": {
                "display_name": "Documentation",
                "description": "Documentation phase",
                "commit_type_hint": "docs",
                "subphases": [],
            },
        },
    }
    (st3_dir / "workphases.yaml").write_text(yaml.dump(workphases))

    # Create workflows.yaml (feature workflow)
    workflows = {
        "version": "1.0",
        "phase_source": ".st3/workphases.yaml",
        "workflows": {
            "feature": {
                "name": "feature",
                "description": "Feature workflow",
                "default_execution_mode": "interactive",
                "phases": ["research", "planning", "design", "tdd", "integration", "documentation"],
            }
        },
    }
    (st3_dir / "workflows.yaml").write_text(yaml.dump(workflows))

    # Create git.yaml (minimal config)
    git_config = {
        "branch_types": ["feature"],
        "tdd_phases": ["red", "green", "refactor"],
        "commit_prefix_map": {"red": "test", "green": "feat", "refactor": "refactor"},
        "protected_branches": ["main"],
        "branch_name_pattern": "^[a-z0-9-]+$",
        "commit_types": ["feat", "fix", "docs", "test", "refactor", "chore"],
        "default_base_branch": "main",
    }
    (st3_dir / "git.yaml").write_text(yaml.dump(git_config))

    # Initial commit (required for branch operations)
    readme = tmp_path / "README.md"
    readme.write_text("# Test Project\n")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )

    return tmp_path


def test_full_workflow_cycle_with_scope_detection(git_repo: Path) -> None:
    """Test complete workflow cycle with commit-scope encoding and detection.

    Cycle 3.6: End-to-end test validating:
    1. Workflow initialization (issue #999, feature workflow)
    2. Phase transitions through complete cycle
    3. Commit-scope encoding at each phase
    4. ScopeDecoder detection at each phase
    5. TDD subcycle (red → green → refactor)
    """
    # GIVEN: Initialized project with feature workflow
    pm = ProjectManager(workspace_root=git_repo)
    pm.initialize_project(
        issue_number=999,
        issue_title="End-to-end workflow test",
        workflow_name="feature",
    )

    # Create feature branch
    subprocess.run(
        ["git", "checkout", "-b", "feature/999-e2e-test"],
        cwd=git_repo,
        check=True,
        capture_output=True,
    )

    # Initialize PhaseStateEngine
    state_engine = PhaseStateEngine(workspace_root=git_repo, project_manager=pm)
    state_engine.initialize_branch(
        branch="feature/999-e2e-test",
        issue_number=999,
        initial_phase="research",
        parent_branch="main",
    )

    # Initialize GitManager with tmp_path and ScopeDecoder
    git_adapter = GitAdapter(repo_path=str(git_repo))
    git_manager = GitManager(adapter=git_adapter)
    decoder = ScopeDecoder()

    # Phase 1: RESEARCH
    test_file = git_repo / "test.txt"
    test_file.write_text("research phase\n")
    commit_hash = git_manager.commit_with_scope(
        workflow_phase="research",
        message="complete research",
        files=[str(test_file)],
    )
    assert commit_hash is not None

    # Validate commit scope detection
    commits = git_manager.get_recent_commits(limit=1)
    result = decoder.detect_phase(commit_message=commits[0], fallback_to_state=False)
    assert result["workflow_phase"] == "research"
    assert result["source"] == "commit-scope"

    # Transition to PLANNING
    state_engine.transition(branch="feature/999-e2e-test", to_phase="planning")

    # Phase 2: PLANNING
    test_file.write_text("planning phase\n")
    git_manager.commit_with_scope(
        workflow_phase="planning",
        message="create plan",
        files=[str(test_file)],
    )

    commits = git_manager.get_recent_commits(limit=1)
    result = decoder.detect_phase(commit_message=commits[0], fallback_to_state=False)
    assert result["workflow_phase"] == "planning"
    assert result["source"] == "commit-scope"

    # Transition to DESIGN
    state_engine.transition(branch="feature/999-e2e-test", to_phase="design")

    # Phase 3: DESIGN
    test_file.write_text("design phase\n")
    git_manager.commit_with_scope(
        workflow_phase="design",
        message="create design",
        files=[str(test_file)],
    )

    commits = git_manager.get_recent_commits(limit=1)
    result = decoder.detect_phase(commit_message=commits[0], fallback_to_state=False)
    assert result["workflow_phase"] == "design"
    assert result["source"] == "commit-scope"

    # Save planning deliverables (required by on_enter_tdd_phase hook, Issue #146)
    pm.save_planning_deliverables(
        999,
        {
            "tdd_cycles": {
                "total": 1,
                "cycles": [
                    {
                        "cycle_number": 1,
                        "name": "End-to-end TDD cycle",
                        "deliverables": ["test_workflow_cycle_e2e"],
                        "exit_criteria": "E2E test passes",
                    }
                ],
            }
        },
    )

    # Transition to TDD
    state_engine.transition(branch="feature/999-e2e-test", to_phase="tdd")

    # Phase 4: TDD CYCLE (red → green → refactor)

    # TDD: RED
    test_file.write_text("red phase\n")
    git_manager.commit_with_scope(
        workflow_phase="tdd",
        sub_phase="red",
        message="add failing test",
        files=[str(test_file)],
    )

    commits = git_manager.get_recent_commits(limit=1)
    result = decoder.detect_phase(commit_message=commits[0], fallback_to_state=False)
    assert result["workflow_phase"] == "tdd"
    assert result["sub_phase"] == "red"
    assert result["source"] == "commit-scope"

    # TDD: GREEN
    test_file.write_text("green phase\n")
    git_manager.commit_with_scope(
        workflow_phase="tdd",
        sub_phase="green",
        message="implement feature",
        files=[str(test_file)],
    )

    commits = git_manager.get_recent_commits(limit=1)
    result = decoder.detect_phase(commit_message=commits[0], fallback_to_state=False)
    assert result["workflow_phase"] == "tdd"
    assert result["sub_phase"] == "green"
    assert result["source"] == "commit-scope"

    # TDD: REFACTOR
    test_file.write_text("refactor phase\n")
    git_manager.commit_with_scope(
        workflow_phase="tdd",
        sub_phase="refactor",
        message="refactor code",
        files=[str(test_file)],
    )

    commits = git_manager.get_recent_commits(limit=1)
    result = decoder.detect_phase(commit_message=commits[0], fallback_to_state=False)
    assert result["workflow_phase"] == "tdd"
    assert result["sub_phase"] == "refactor"
    assert result["source"] == "commit-scope"

    # Transition to INTEGRATION
    state_engine.transition(branch="feature/999-e2e-test", to_phase="integration")

    # Phase 5: INTEGRATION
    test_file.write_text("integration phase\n")
    git_manager.commit_with_scope(
        workflow_phase="integration",
        message="add integration tests",
        files=[str(test_file)],
    )

    commits = git_manager.get_recent_commits(limit=1)
    result = decoder.detect_phase(commit_message=commits[0], fallback_to_state=False)
    assert result["workflow_phase"] == "integration"
    assert result["source"] == "commit-scope"

    # Transition to DOCUMENTATION
    state_engine.transition(branch="feature/999-e2e-test", to_phase="documentation")

    # Phase 6: DOCUMENTATION
    test_file.write_text("documentation phase\n")
    git_manager.commit_with_scope(
        workflow_phase="documentation",
        message="update docs",
        files=[str(test_file)],
    )

    commits = git_manager.get_recent_commits(limit=1)
    result = decoder.detect_phase(commit_message=commits[0], fallback_to_state=False)
    assert result["workflow_phase"] == "documentation"
    assert result["source"] == "commit-scope"

    # THEN: Full cycle complete, all phases detected correctly from commit-scope
    # Final validation: verify state.json has correct current_phase
    final_state = state_engine.get_state(branch="feature/999-e2e-test")
    assert final_state["current_phase"] == "documentation"

    # Verify last commit scope detection
    commits = git_manager.get_recent_commits(limit=1)
    result = decoder.detect_phase(commit_message=commits[0], fallback_to_state=False)
    assert result["workflow_phase"] == "documentation"
    assert result["source"] == "commit-scope"
