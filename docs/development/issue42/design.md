# Issue #42: Technical Design - 8-Phase Model Implementation

**Issue:** #42 - Phase workflow contradicts TDD principles  
**Date:** 2025-12-25  
**Phase:** Design  
**Status:** IN PROGRESS

## Overview

Technical design for implementing 8-phase flat model. This document specifies exact data structures, transition logic, and validation rules.

## Design Principles

1. **Backward Compatibility:** Old phase names deprecated but not breaking
2. **Type Safety:** Use tuples for immutable phase lists
3. **Explicit Validation:** Clear error messages for invalid transitions
4. **Extensibility:** Easy to add new issue types or phases

## Component Designs

### 1. PHASE_TEMPLATES Design (WP1)

**File:** `mcp_server/managers/project_manager.py`

#### New Phase Definition

```python
# Phase names (8-phase model)
PHASE_NAMES = {
    "research": "Investigation and alternatives analysis",
    "planning": "Implementation strategy and work breakdown",
    "design": "Technical architecture and design documentation",
    "red": "Write failing tests (TDD: RED phase)",
    "green": "Implement code to pass tests (TDD: GREEN phase)",
    "refactor": "Improve code quality while keeping tests green (TDD: REFACTOR phase)",
    "integration": "System integration and end-to-end testing",
    "documentation": "User-facing documentation and API reference"
}

# Issue type templates
PHASE_TEMPLATES = {
    "feature": {
        "required_phases": (
            "research", "planning", "design", 
            "red", "green", "refactor", 
            "integration", "documentation"
        ),
        "description": "Full 8-phase workflow for new features",
        "rationale": "Complete lifecycle with research, design, and TDD cycles"
    },
    "bug": {
        "required_phases": (
            "research", "planning", 
            "red", "green", "refactor", 
            "integration", "documentation"
        ),
        "description": "7-phase workflow (skip design)",
        "rationale": "Bug fixes typically don't require architecture changes"
    },
    "refactor": {
        "required_phases": (
            "research", "planning", 
            "red", "green", "refactor", 
            "integration", "documentation"
        ),
        "description": "7-phase workflow (skip design)",
        "rationale": "Refactoring maintains behavior, no new architecture needed"
    },
    "docs": {
        "required_phases": (
            "research", "planning", "design", "documentation"
        ),
        "description": "4-phase workflow (skip TDD phases)",
        "rationale": "Documentation-only changes, no code implementation"
    },
    "hotfix": {
        "required_phases": (
            "red", "green", "refactor"
        ),
        "description": "Minimal 3-phase workflow (emergency fixes)",
        "rationale": "Urgent fixes skip research/planning but maintain TDD discipline"
    }
}
```

#### Validation Logic

```python
def _validate_phase_name(phase: str) -> None:
    """Validate phase name is valid in 8-phase model.
    
    Args:
        phase: Phase name to validate
        
    Raises:
        ValueError: If phase name is invalid or deprecated
    """
    valid_phases = set(PHASE_NAMES.keys())
    deprecated_phases = {"discovery", "component", "tdd"}
    
    if phase in deprecated_phases:
        # Map old names to new names
        mapping = {
            "discovery": "research",
            "component": "green",
            "tdd": "Use red/green/refactor instead"
        }
        raise ValueError(
            f"Phase '{phase}' is deprecated. Use '{mapping[phase]}' instead."
        )
    
    if phase not in valid_phases:
        raise ValueError(
            f"Invalid phase: {phase}. Valid phases: {', '.join(sorted(valid_phases))}"
        )
```

#### Migration Strategy

```python
# Optional: Support reading old phase names temporarily
PHASE_MIGRATION_MAP = {
    "discovery": "research",
    "component": "green",  # Best effort mapping
    "tdd": "green",  # Best effort mapping
}

def migrate_phase_name(old_phase: str) -> str:
    """Migrate old phase name to new 8-phase model.
    
    For backward compatibility during transition period.
    """
    return PHASE_MIGRATION_MAP.get(old_phase, old_phase)
```

---

### 2. PhaseStateEngine Design (WP2)

**File:** `mcp_server/core/phase_state_engine.py`

#### Transition State Machine

```python
class PhaseStateEngine:
    """Phase state management with 8-phase model."""
    
    # Valid phase transitions (state machine)
    VALID_TRANSITIONS: dict[str, list[str]] = {
        # Linear workflow phases
        "research": ["planning"],
        "planning": ["design"],
        "design": ["red"],  # Enter TDD cycle
        
        # TDD cycle phases
        "red": ["green"],  # RED → GREEN (tests written, implement code)
        "green": ["refactor"],  # GREEN → REFACTOR (tests passing, improve code)
        "refactor": [
            "red",  # Next TDD cycle (add more features)
            "integration"  # Exit TDD (all features complete)
        ],
        
        # Final phases
        "integration": ["documentation"],
        "documentation": ["done"],
        
        # Terminal state
        "done": []
    }
    
    def _is_valid_transition(self, from_phase: str, to_phase: str) -> bool:
        """Validate phase transition against state machine.
        
        Args:
            from_phase: Current phase
            to_phase: Target phase
            
        Returns:
            True if transition is valid
        """
        allowed = self.VALID_TRANSITIONS.get(from_phase, [])
        return to_phase in allowed
    
    def get_next_phases(self, current_phase: str) -> list[str]:
        """Get list of valid next phases.
        
        Args:
            current_phase: Current phase name
            
        Returns:
            List of valid next phase names
        """
        return self.VALID_TRANSITIONS.get(current_phase, [])
```

#### Enhanced Transition Logic

```python
def transition(
    self, 
    branch: str, 
    from_phase: str, 
    to_phase: str,
    human_approval: str | None = None
) -> TransitionResult:
    """Execute phase transition with validation.
    
    Args:
        branch: Branch name
        from_phase: Expected current phase
        to_phase: Target phase
        human_approval: Optional approval message
        
    Returns:
        TransitionResult with success/failure and reason
    """
    # Check branch exists
    if branch not in self._state:
        return TransitionResult(
            success=False,
            reason=f"Branch '{branch}' not initialized. "
                   f"Call initialize_branch() first."
        )
    
    # Verify current phase matches
    current = self._state[branch].current_phase
    if current != from_phase:
        return TransitionResult(
            success=False,
            reason=f"Phase mismatch: branch is in '{current}', "
                   f"but transition expects '{from_phase}'"
        )
    
    # Validate transition
    if not self._is_valid_transition(from_phase, to_phase):
        valid_next = self.get_next_phases(from_phase)
        return TransitionResult(
            success=False,
            reason=f"Invalid transition: {from_phase} → {to_phase}. "
                   f"Valid next phases: {', '.join(valid_next)}"
        )
    
    # Special validations for TDD cycle
    if to_phase in ["green", "refactor"] and from_phase == "refactor":
        # Entering next TDD cycle from refactor
        if from_phase == "refactor" and to_phase == "red":
            # This is valid: starting next feature cycle
            pass
    
    # Execute transition
    self._state[branch].current_phase = to_phase
    self._state[branch].transitions.append({
        "from_phase": from_phase,
        "to_phase": to_phase,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "human_approval": human_approval
    })
    
    self._save_state()
    
    return TransitionResult(
        success=True,
        new_phase=to_phase,
        reason=f"Transitioned {from_phase} → {to_phase}"
    )
```

#### Transition History

```python
def get_transition_history(self, branch: str) -> list[dict[str, Any]]:
    """Get complete transition history for a branch.
    
    Useful for auditing and understanding phase progression.
    
    Args:
        branch: Branch name
        
    Returns:
        List of transition records
    """
    if branch not in self._state:
        return []
    
    return self._state[branch].transitions.copy()

def count_tdd_cycles(self, branch: str) -> int:
    """Count how many TDD cycles (red→green→refactor) were executed.
    
    Args:
        branch: Branch name
        
    Returns:
        Number of complete TDD cycles
    """
    history = self.get_transition_history(branch)
    
    # Count refactor → red transitions (indicates new cycle start)
    cycles = 1  # First cycle
    for transition in history:
        if (transition["from_phase"] == "refactor" and 
            transition["to_phase"] == "red"):
            cycles += 1
    
    return cycles
```

---

### 3. Test Design (WP3)

**File:** `tests/unit/mcp_server/test_8_phase_model.py`

#### Test Structure

```python
import pytest
from mcp_server.managers.project_manager import (
    PHASE_TEMPLATES, PHASE_NAMES, ProjectManager
)
from mcp_server.core.phase_state_engine import PhaseStateEngine

class TestPhaseTemplates:
    """Test PHASE_TEMPLATES structure and content."""
    
    def test_all_templates_use_8_phase_names(self):
        """All phase names in templates are valid 8-phase names."""
        valid_phases = set(PHASE_NAMES.keys())
        
        for issue_type, template in PHASE_TEMPLATES.items():
            phases = template["required_phases"]
            for phase in phases:
                assert phase in valid_phases, (
                    f"{issue_type} template uses invalid phase: {phase}"
                )
    
    def test_feature_template_has_8_phases(self):
        """Feature template includes all 8 phases."""
        phases = PHASE_TEMPLATES["feature"]["required_phases"]
        assert phases == (
            "research", "planning", "design",
            "red", "green", "refactor",
            "integration", "documentation"
        )
    
    def test_bug_template_skips_design(self):
        """Bug template skips design phase (7 phases total)."""
        phases = PHASE_TEMPLATES["bug"]["required_phases"]
        assert "design" not in phases
        assert len(phases) == 7
    
    def test_docs_template_skips_tdd_phases(self):
        """Docs template skips all TDD phases."""
        phases = PHASE_TEMPLATES["docs"]["required_phases"]
        assert "red" not in phases
        assert "green" not in phases
        assert "refactor" not in phases
        assert "integration" not in phases
    
    def test_hotfix_template_minimal(self):
        """Hotfix template is minimal (3 TDD phases only)."""
        phases = PHASE_TEMPLATES["hotfix"]["required_phases"]
        assert phases == ("red", "green", "refactor")


class TestPhaseTransitions:
    """Test PhaseStateEngine transition validation."""
    
    @pytest.fixture
    def engine(self, tmp_path):
        """Create PhaseStateEngine instance."""
        return PhaseStateEngine(workspace_root=tmp_path)
    
    def test_linear_workflow_transitions(self, engine):
        """Test valid linear phase transitions."""
        engine.initialize_branch("test", "research", 1)
        
        # research → planning
        result = engine.transition("test", "research", "planning")
        assert result.success
        
        # planning → design
        result = engine.transition("test", "planning", "design")
        assert result.success
        
        # design → red (enter TDD)
        result = engine.transition("test", "design", "red")
        assert result.success
    
    def test_tdd_cycle_transitions(self, engine):
        """Test TDD cycle: red → green → refactor."""
        engine.initialize_branch("test", "red", 1)
        
        # red → green
        result = engine.transition("test", "red", "green")
        assert result.success
        
        # green → refactor
        result = engine.transition("test", "green", "refactor")
        assert result.success
    
    def test_multiple_tdd_cycles(self, engine):
        """Test refactor → red for next TDD cycle."""
        engine.initialize_branch("test", "refactor", 1)
        
        # refactor → red (next cycle)
        result = engine.transition("test", "refactor", "red")
        assert result.success
        
        # Complete second cycle
        result = engine.transition("test", "red", "green")
        assert result.success
        result = engine.transition("test", "green", "refactor")
        assert result.success
        
        # Verify cycle count
        assert engine.count_tdd_cycles("test") == 2
    
    def test_exit_tdd_to_integration(self, engine):
        """Test refactor → integration to exit TDD."""
        engine.initialize_branch("test", "refactor", 1)
        
        # refactor → integration (done with TDD)
        result = engine.transition("test", "refactor", "integration")
        assert result.success
    
    def test_invalid_transitions_rejected(self, engine):
        """Test invalid transitions are rejected."""
        engine.initialize_branch("test", "green", 1)
        
        # green → integration (skipping refactor) - INVALID
        result = engine.transition("test", "green", "integration")
        assert not result.success
        assert "Invalid transition" in result.reason
        assert "refactor" in result.reason  # Suggests valid option
    
    def test_get_next_phases(self, engine):
        """Test getting valid next phases."""
        # From refactor, can go to red OR integration
        next_phases = engine.get_next_phases("refactor")
        assert set(next_phases) == {"red", "integration"}
        
        # From green, can only go to refactor
        next_phases = engine.get_next_phases("green")
        assert next_phases == ["refactor"]


class TestInitializeProjectTool:
    """Test project initialization with 8-phase model."""
    
    @pytest.fixture
    def manager(self, tmp_path):
        """Create ProjectManager instance."""
        return ProjectManager(workspace_root=tmp_path)
    
    def test_initialize_feature_project(self, manager):
        """Initialize feature project with 8 phases."""
        result = manager.initialize_project(
            issue_number=1,
            issue_title="Test Feature",
            issue_type="feature"
        )
        
        assert result["success"]
        assert result["required_phases"] == [
            "research", "planning", "design",
            "red", "green", "refactor",
            "integration", "documentation"
        ]
    
    def test_first_phase_is_research(self, manager):
        """All issue types start with research (except hotfix)."""
        for issue_type in ["feature", "bug", "refactor", "docs"]:
            result = manager.initialize_project(
                issue_number=1,
                issue_title="Test",
                issue_type=issue_type
            )
            assert result["required_phases"][0] == "research"
    
    def test_hotfix_starts_with_red(self, manager):
        """Hotfix starts directly with TDD (red phase)."""
        result = manager.initialize_project(
            issue_number=1,
            issue_title="Emergency Fix",
            issue_type="hotfix"
        )
        assert result["required_phases"][0] == "red"
```

---

### 4. Integration Test Design (WP5)

**Scenario:** Complete feature development with multiple TDD cycles

```python
class TestEndToEndWorkflow:
    """Test complete workflow from research to documentation."""
    
    @pytest.fixture
    def workspace(self, tmp_path):
        """Set up complete workspace."""
        manager = ProjectManager(tmp_path)
        engine = PhaseStateEngine(tmp_path)
        return {"manager": manager, "engine": engine, "root": tmp_path}
    
    def test_feature_workflow_with_multiple_tdd_cycles(self, workspace):
        """Test complete feature workflow with 2 TDD cycles."""
        manager = workspace["manager"]
        engine = workspace["engine"]
        
        # 1. Initialize project
        result = manager.initialize_project(
            issue_number=42,
            issue_title="New Feature",
            issue_type="feature"
        )
        assert result["success"]
        
        # 2. Initialize branch state
        engine.initialize_branch("feature/42-test", "research", 42)
        
        # 3. Progress through pre-TDD phases
        assert engine.transition("feature/42-test", "research", "planning").success
        assert engine.transition("feature/42-test", "planning", "design").success
        assert engine.transition("feature/42-test", "design", "red").success
        
        # 4. First TDD cycle
        assert engine.transition("feature/42-test", "red", "green").success
        assert engine.transition("feature/42-test", "green", "refactor").success
        
        # 5. Second TDD cycle (add more features)
        assert engine.transition("feature/42-test", "refactor", "red").success
        assert engine.transition("feature/42-test", "red", "green").success
        assert engine.transition("feature/42-test", "green", "refactor").success
        
        # 6. Exit TDD and complete
        assert engine.transition("feature/42-test", "refactor", "integration").success
        assert engine.transition("feature/42-test", "integration", "documentation").success
        
        # 7. Verify history
        history = engine.get_transition_history("feature/42-test")
        assert len(history) == 10  # 10 transitions total
        
        # 8. Verify TDD cycle count
        assert engine.count_tdd_cycles("feature/42-test") == 2
```

---

## State File Format Design

**File:** `.st3/state.json`

### Current Format (Flat)
```json
{
  "feature/42-test": {
    "current_phase": "green",
    "issue_number": 42,
    "transitions": [
      {
        "from_phase": "research",
        "to_phase": "planning",
        "timestamp": "2025-12-25T10:00:00Z",
        "human_approval": null
      }
    ]
  }
}
```

### Proposed Format (Versioned) - Future Enhancement
```json
{
  "version": "2.0",
  "branches": {
    "feature/42-test": {
      "current_phase": "green",
      "issue_number": 42,
      "transitions": [...],
      "metadata": {
        "tdd_cycles": 1,
        "created_at": "2025-12-25T09:00:00Z",
        "last_transition": "2025-12-25T10:30:00Z"
      }
    }
  }
}
```

**Decision:** Keep flat format for now (Issue #45 will add versioning)

---

## Validation Rules Design

### Phase Name Validation

```python
def validate_phase_sequence(phases: tuple[str, ...]) -> None:
    """Validate that phase sequence is logical.
    
    Rules:
    - Must start with research (or red for hotfix)
    - TDD phases must be in order: red → green → refactor
    - Must end with documentation (or refactor for hotfix)
    
    Args:
        phases: Tuple of phase names
        
    Raises:
        ValueError: If sequence is invalid
    """
    if not phases:
        raise ValueError("Phase sequence cannot be empty")
    
    # Check first phase
    if phases[0] not in ["research", "red"]:
        raise ValueError(
            f"Phase sequence must start with 'research' or 'red', "
            f"got '{phases[0]}'"
        )
    
    # Check TDD phase ordering (if present)
    tdd_phases = {"red", "green", "refactor"}
    tdd_found = [p for p in phases if p in tdd_phases]
    
    if tdd_found:
        # Verify TDD phases appear in correct order
        expected_order = ["red", "green", "refactor"]
        tdd_positions = {p: phases.index(p) for p in tdd_found}
        
        for i in range(len(tdd_found) - 1):
            current = tdd_found[i]
            next_phase = tdd_found[i + 1]
            if tdd_positions[current] >= tdd_positions[next_phase]:
                raise ValueError(
                    f"TDD phases must be in order: red → green → refactor. "
                    f"Found: {' → '.join(tdd_found)}"
                )
```

---

## Migration Strategy

### Handling Existing Projects

```python
def migrate_project_phases(project_data: dict[str, Any]) -> dict[str, Any]:
    """Migrate project from old 7-phase to new 8-phase model.
    
    Only needed if old projects exist (currently: none exist).
    
    Args:
        project_data: Old project data with 7-phase names
        
    Returns:
        Migrated project data with 8-phase names
    """
    old_phases = project_data["required_phases"]
    new_phases = []
    
    for phase in old_phases:
        if phase == "discovery":
            new_phases.append("research")
        elif phase == "component":
            # Component maps to green (best effort)
            # Note: This loses the red phase!
            new_phases.append("green")
        elif phase == "tdd":
            # TDD maps to refactor (best effort)
            new_phases.append("refactor")
        else:
            new_phases.append(phase)
    
    project_data["required_phases"] = new_phases
    project_data["migration_note"] = (
        "Migrated from 7-phase to 8-phase model. "
        "Old 'component' and 'tdd' phases collapsed to 'green' and 'refactor'."
    )
    
    return project_data
```

---

## Error Message Design

### Helpful Error Messages

```python
# Example 1: Invalid transition
"Invalid transition: green → integration. 
Valid next phases from 'green': refactor
Hint: You must refactor before integration."

# Example 2: Deprecated phase name
"Phase 'component' is deprecated. Use 'green' instead.
The 8-phase model uses: red (write tests), green (implement), refactor (improve quality)."

# Example 3: Branch not initialized
"Branch 'feature/42-test' not initialized.
Call initialize_project() first, or manually initialize with:
  engine.initialize_branch('feature/42-test', 'research', 42)"
```

---

## Design Decisions Summary

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Phase count** | 8 phases | Explicit TDD phases, clear semantics |
| **Phase names** | research/red/green/refactor | Clear intent, TDD standard terminology |
| **Transitions** | Explicit state machine | Prevents invalid phase jumps |
| **TDD cycles** | refactor → red allowed | Supports iterative development |
| **State format** | Flat (for now) | Keep simple, Issue #45 adds versioning |
| **Backward compat** | Deprecation warnings | Clear migration path for users |
| **Test strategy** | Unit + integration tests | Comprehensive coverage |

---

## Success Criteria

### Functional
- [ ] All 5 issue types defined with correct phase sequences
- [ ] PhaseStateEngine validates all transitions correctly
- [ ] Multiple TDD cycles work (refactor → red → green → refactor)
- [ ] Invalid transitions rejected with helpful messages

### Quality
- [ ] Test coverage ≥ 90%
- [ ] All edge cases covered
- [ ] Error messages are actionable
- [ ] Code is type-safe (mypy passes)

### Documentation
- [ ] Inline code comments explain design decisions
- [ ] Docstrings complete for all public methods
- [ ] State machine diagram created
- [ ] Migration guide written (if needed)

---

## Next Phase: Red (TDD)

**Handover:**
- ✅ Data structures designed (PHASE_TEMPLATES, transitions)
- ✅ Validation rules specified
- ✅ Test cases outlined
- ✅ Error messages designed

**Ready to implement:** Write failing tests that specify exact behavior.

**Status:** Design phase COMPLETE. Ready for Red (test-first) phase.
