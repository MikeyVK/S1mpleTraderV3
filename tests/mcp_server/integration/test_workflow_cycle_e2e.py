"""End-to-end test for full workflow cycle (Issue #138 Cycle 3.6).

Tests complete workflow cycle: research -> planning -> design -> implementation -> validation
-> documentation with commit-scope encoding and ScopeDecoder validation.

@layer: Tests (Integration)
@dependencies: [pytest, subprocess, mcp_server.managers.git_manager]
"""

import subprocess
from pathlib import Path

import pytest
import yaml

from mcp_server.adapters.git_adapter import GitAdapter
from mcp_server.config.loader import ConfigLoader
from mcp_server.core.operation_notes import NoteContext
from mcp_server.core.phase_detection import ScopeDecoder
from mcp_server.managers.git_manager import GitManager
from tests.mcp_server.test_support import make_phase_state_engine, make_project_manager


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
    config_dir = st3_dir / "config"
    config_dir.mkdir(parents=True)

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
            "implementation": {
                "display_name": "Implementation",
                "description": "Implementation cycle",
                "commit_type_hint": None,
                "subphases": ["red", "green", "refactor"],
            },
            "validation": {
                "display_name": "Validation",
                "description": "Validation phase",
                "commit_type_hint": "test",
                "subphases": [],
            },
            "documentation": {
                "display_name": "Documentation",
                "description": "Documentation phase",
                "commit_type_hint": "docs",
                "subphases": [],
            },
            "ready": {
                "display_name": "Ready",
                "description": "Terminal phase — merge readiness verified",
                "commit_type_hint": None,
                "subphases": [],
                "terminal": True,
            },
        },
    }
    (config_dir / "workphases.yaml").write_text(yaml.dump(workphases), encoding="utf-8")

    # Create workflows.yaml (feature workflow)
    workflows = {
        "version": "1.0",
        "phase_source": ".st3/workphases.yaml",
        "workflows": {
            "feature": {
                "name": "feature",
                "description": "Feature workflow",
                "default_execution_mode": "interactive",
                "phases": [
                    "research",
                    "planning",
                    "design",
                    "implementation",
                    "validation",
                    "documentation",
                ],
            }
        },
    }
    (config_dir / "workflows.yaml").write_text(yaml.dump(workflows), encoding="utf-8")

    # Create git.yaml (minimal config)
    git_config = {
        "branch_types": ["feature"],
        "protected_branches": ["main"],
        "branch_name_pattern": "^[a-z0-9-]+$",
        "commit_types": ["feat", "fix", "docs", "test", "refactor", "chore"],
        "default_base_branch": "main",
        "issue_title_max_length": 72,
    }
    (config_dir / "git.yaml").write_text(yaml.dump(git_config), encoding="utf-8")

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
    5. Implementation subcycle (red -> green -> refactor)
    """
    # GIVEN: Initialized project with feature workflow
    pm = make_project_manager(git_repo)
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
    state_engine = make_phase_state_engine(git_repo, project_manager=pm)
    state_engine.initialize_branch(
        branch="feature/999-e2e-test",
        issue_number=999,
        initial_phase="research",
        parent_branch="main",
    )

    # Initialize GitManager with tmp_path and ScopeDecoder
    git_adapter = GitAdapter(repo_path=str(git_repo))
    git_config = ConfigLoader(git_repo / ".st3" / "config").load_git_config(
        config_path=git_repo / ".st3" / "config" / "git.yaml"
    )
    _workphases_config = ConfigLoader(git_repo / ".st3" / "config").load_workphases_config(
        config_path=git_repo / ".st3" / "config" / "workphases.yaml"
    )
    git_manager = GitManager(
        git_config=git_config,
        adapter=git_adapter,
        workphases_config=_workphases_config,
    )
    decoder = ScopeDecoder(_workphases_config)

    # Phase 1: RESEARCH
    test_file = git_repo / "test.txt"
    test_file.write_text("research phase\n")
    commit_hash = git_manager.commit_with_scope(
        workflow_phase="research",
        message="complete research",
        note_context=NoteContext(),
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
        note_context=NoteContext(),
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
        note_context=NoteContext(),
        files=[str(test_file)],
    )

    commits = git_manager.get_recent_commits(limit=1)
    result = decoder.detect_phase(commit_message=commits[0], fallback_to_state=False)
    assert result["workflow_phase"] == "design"
    assert result["source"] == "commit-scope"

    # Save planning deliverables (required by implementation-cycle hooks, Issue #146)
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

    # Transition to IMPLEMENTATION
    state_engine.transition(branch="feature/999-e2e-test", to_phase="implementation")

    # Phase 4: IMPLEMENTATION CYCLE (red -> green -> refactor)

    # IMPLEMENTATION: RED
    test_file.write_text("red phase\n")
    git_manager.commit_with_scope(
        workflow_phase="implementation",
        sub_phase="red",
        cycle_number=1,
        commit_type="test",
        message="add failing test",
        note_context=NoteContext(),
        files=[str(test_file)],
    )

    commits = git_manager.get_recent_commits(limit=1)
    result = decoder.detect_phase(commit_message=commits[0], fallback_to_state=False)
    assert result["workflow_phase"] == "implementation"
    assert result["sub_phase"] == "c1_red"
    assert result["source"] == "commit-scope"

    # IMPLEMENTATION: GREEN
    test_file.write_text("green phase\n")
    git_manager.commit_with_scope(
        workflow_phase="implementation",
        sub_phase="green",
        cycle_number=1,
        commit_type="feat",
        message="implement feature",
        note_context=NoteContext(),
        files=[str(test_file)],
    )

    commits = git_manager.get_recent_commits(limit=1)
    result = decoder.detect_phase(commit_message=commits[0], fallback_to_state=False)
    assert result["workflow_phase"] == "implementation"
    assert result["sub_phase"] == "c1_green"
    assert result["source"] == "commit-scope"

    # IMPLEMENTATION: REFACTOR
    test_file.write_text("refactor phase\n")
    git_manager.commit_with_scope(
        workflow_phase="implementation",
        sub_phase="refactor",
        cycle_number=1,
        commit_type="refactor",
        message="refactor code",
        note_context=NoteContext(),
        files=[str(test_file)],
    )

    commits = git_manager.get_recent_commits(limit=1)
    result = decoder.detect_phase(commit_message=commits[0], fallback_to_state=False)
    assert result["workflow_phase"] == "implementation"
    assert result["sub_phase"] == "c1_refactor"
    assert result["source"] == "commit-scope"

    # Transition to VALIDATION
    state_engine.transition(branch="feature/999-e2e-test", to_phase="validation")

    # Phase 5: VALIDATION
    test_file.write_text("validation phase\n")
    git_manager.commit_with_scope(
        workflow_phase="validation",
        message="add validation tests",
        note_context=NoteContext(),
        files=[str(test_file)],
    )

    commits = git_manager.get_recent_commits(limit=1)
    result = decoder.detect_phase(commit_message=commits[0], fallback_to_state=False)
    assert result["workflow_phase"] == "validation"
    assert result["source"] == "commit-scope"

    # Transition to DOCUMENTATION
    state_engine.transition(branch="feature/999-e2e-test", to_phase="documentation")

    # Phase 6: DOCUMENTATION
    test_file.write_text("documentation phase\n")
    git_manager.commit_with_scope(
        workflow_phase="documentation",
        message="update docs",
        note_context=NoteContext(),
        files=[str(test_file)],
    )

    commits = git_manager.get_recent_commits(limit=1)
    result = decoder.detect_phase(commit_message=commits[0], fallback_to_state=False)
    assert result["workflow_phase"] == "documentation"
    assert result["source"] == "commit-scope"

    # THEN: Full cycle complete, all phases detected correctly from commit-scope
    # Final validation: verify state.json has correct current_phase
    final_state = state_engine.get_state(branch="feature/999-e2e-test")
    assert final_state.current_phase == "documentation"

    # Verify last commit scope detection
    commits = git_manager.get_recent_commits(limit=1)
    result = decoder.detect_phase(commit_message=commits[0], fallback_to_state=False)
    assert result["workflow_phase"] == "documentation"
    assert result["source"] == "commit-scope"
