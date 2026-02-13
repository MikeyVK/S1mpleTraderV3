"""Baseline capture tests for Issue #108 (Cycle 0).

Captures scaffolding output BEFORE JinjaRenderer extraction to enable
byte-identical regression validation in Cycle 4.

RED Phase: These tests expect baseline files that don't exist yet.
GREEN Phase: Run scaffolding and save outputs to tests/baselines/
REFACTOR Phase: Document baseline regeneration process
"""

from pathlib import Path

import pytest


BASELINE_DIR = Path("tests/baselines")


def test_capture_baseline_dto():
    """Baseline: DTO scaffolding output."""
    baseline_file = BASELINE_DIR / "baseline_dto.py"
    
    assert baseline_file.exists(), (
        f"Baseline file missing: {baseline_file}\n"
        "Run scaffolding in GREEN phase to capture baseline."
    )
    
    content = baseline_file.read_text(encoding="utf-8")
    assert len(content) > 0, "Baseline file should not be empty"
    assert "class" in content, "DTO baseline should contain class definition"


def test_capture_baseline_worker():
    """Baseline: Worker scaffolding output."""
    baseline_file = BASELINE_DIR / "baseline_worker.py"
    
    assert baseline_file.exists(), (
        f"Baseline file missing: {baseline_file}\n"
        "Run scaffolding in GREEN phase to capture baseline."
    )
    
    content = baseline_file.read_text(encoding="utf-8")
    assert len(content) > 0, "Baseline file should not be empty"
    assert "class" in content, "Worker baseline should contain class definition"


def test_capture_baseline_tool():
    """Baseline: Tool (markdown) scaffolding output."""
    baseline_file = BASELINE_DIR / "baseline_tool.md"
    
    assert baseline_file.exists(), (
        f"Baseline file missing: {baseline_file}\n"
        "Run scaffolding in GREEN phase to capture baseline."
    )
    
    content = baseline_file.read_text(encoding="utf-8")
    assert len(content) > 0, "Baseline file should not be empty"
    assert "#" in content, "Tool baseline should contain markdown headers"


def test_capture_baseline_research():
    """Baseline: Research document scaffolding output."""
    baseline_file = BASELINE_DIR / "baseline_research.md"
    
    assert baseline_file.exists(), (
        f"Baseline file missing: {baseline_file}\n"
        "Run scaffolding in GREEN phase to capture baseline."
    )
    
    content = baseline_file.read_text(encoding="utf-8")
    assert len(content) > 0, "Baseline file should not be empty"
    assert "# Baseline Test Research" in content, "Research baseline should contain title"
    assert "## Purpose" in content, "Research baseline should have Purpose section"


def test_capture_baseline_planning():
    """Baseline: Planning document scaffolding output."""
    baseline_file = BASELINE_DIR / "baseline_planning.md"
    
    assert baseline_file.exists(), (
        f"Baseline file missing: {baseline_file}\n"
        "Run scaffolding in GREEN phase to capture baseline."
    )
    
    content = baseline_file.read_text(encoding="utf-8")
    assert len(content) > 0, "Baseline file should not be empty"
    assert "# Baseline Test Planning" in content, "Planning baseline should contain title"
    assert "## Purpose" in content, "Planning baseline should have Purpose section"


def test_baselines_directory_exists():
    """Baseline directory exists and is committed to git."""
    assert BASELINE_DIR.exists(), (
        f"Baselines directory missing: {BASELINE_DIR}\n"
        "Create in GREEN phase."
    )
    
    assert BASELINE_DIR.is_dir(), f"{BASELINE_DIR} should be a directory"
    
    # Check for README documenting regeneration process
    readme = BASELINE_DIR / "README.md"
    assert readme.exists(), (
        f"Baseline README missing: {readme}\n"
        "Add documentation in REFACTOR phase."
    )
