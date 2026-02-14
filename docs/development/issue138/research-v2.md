<!-- D:\dev\SimpleTraderV3\docs\development\issue138\research-v2.md -->
<!-- template=research version=8b7bb3ab created=2026-02-14T17:30:00+00:00 updated=2026-02-14T17:45:00+00:00 -->
# Issue #138: Workflow-First Commit Convention Architecture (v2.0)

**Status:** COMPLETE  
**Version:** 2.0  
**Last Updated:** 2026-02-14T17:45:00+00:00

---

## Purpose

Design a workflow-first commit convention that uses Conventional Commits format with workflow phases as scopes, establishing workphases.yaml as SSOT and ensuring DRY principles through shared utilities

## Scope

**In Scope:**
Tool dependency analysis (GitManager, GitConfig, get_work_context), Configuration hierarchy (workphases.yaml → workflows.yaml → git.yaml), Scope format encoder/decoder utility design, Conventional Commits compliance, DRY architecture patterns from coding standards

**Out of Scope:**
Implementation details, test design, UI/UX concerns, performance optimization, migration tooling for existing commits

## Prerequisites

Read these first:
1. Issue #138 v1.0 research.md completed (two phase systems analysis)
2. User architectural vision: workflow phases should drive commit messages
3. Coding standards understood (DRY, type hints, PEP8, scaffolding patterns)
4. Tool inventory completed (GitManager, GitConfig, GitAdapter identified)

---

## Problem Statement

Current architecture splits phase definitions across git.yaml (TDD phases) and workflows.yaml (workflow phases) without integration. User vision: workflow phases should be primary, encoded in Conventional Commits scope field, with workphases.yaml as SSOT. Need architectural design that respects DRY principles and coding standards.

## Research Goals

- Establish workphases.yaml as Single Source of Truth for all workflow phases
- Design Conventional Commits compliant format: type(P_PHASE_SP_SUBPHASE): message
- Identify all tools consuming commit message conventions (dependency graph)
- Design DRY scope encoder/decoder utility following coding standards
- Define configuration hierarchy and data flow between config files
- Document architectural decision rationale and trade-offs

## Related Documentation

- [research.md v1.0](research.md): Two phase systems analysis
- [docs/coding_standards/README.md](../../coding_standards/README.md): DRY principles
- [docs/coding_standards/CODE_STYLE.md](../../coding_standards/CODE_STYLE.md): Type hinting standards
- [mcp_server/managers/git_manager.py](../../../mcp_server/managers/git_manager.py): GitManager implementation
- [mcp_server/config/git_config.py](../../../mcp_server/config/git_config.py): GitConfig implementation
- [.st3/git.yaml](../../../.st3/git.yaml): Current conventions
- [.st3/workflows.yaml](../../../.st3/workflows.yaml): Workflow definitions
- [Conventional Commits](https://www.conventionalcommits.org/): Industry standard

---

## Architectural Vision

### User Requirements

**Core Principle:** Workflow phases are PRIMARY, commit messages ENCODE workflow state.

**Format:** Conventional Commits compliant
```
type(scope): description

Where:
  type  = Git conventional type (feat, test, docs, refactor, fix, chore)
  scope = Workflow state identifier (P_PHASE or P_PHASE_SP_SUBPHASE)
```

**Examples:**
```bash
# Research phase (no subphase)
docs(P_RESEARCH): complete dependency analysis

# TDD phase with subphase (cycle tracking)
test(P_TDD_SP_C1_RED): add user service validation tests
feat(P_TDD_SP_C1_GREEN): implement user service validation
refactor(P_TDD_SP_C1_REFACTOR): extract validation helper
test(P_TDD_SP_C2_RED): add caching tests

# Integration phase
feat(P_INTEGRATION): wire user service to event bus

# Documentation phase  
docs(P_DOCUMENTATION): update API reference
```

**Key Benefits:**

1. **Git history = Complete workflow trace**
   - `git log` shows phase progression without external state files
   - State reconstruction possible from commits alone
   - Eliminates Issue #117 (get_work_context can parse scope, not guess from type)

2. **Conventional Commits compliance**
   - GitHub/GitLab changelog generators still work
   - Third-party tooling compatibility maintained
   - `type` field remains conventional (feat/test/docs)

3. **Workflow-first architecture**
   - Phases defined ONCE in workphases.yaml
   - All tools reference same source (DRY)
   - Adding new phases = config change only, zero code changes

4. **Hierarchical clarity**
   ```
   P_RESEARCH          → Macro (hours/days)
   P_TDD               → Macro (hours/days)
     └─ SP_C1_RED      → Micro (minutes) - Cycle 1, Red
     └─ SP_C1_GREEN    → Micro (minutes) - Cycle 1, Green
     └─ SP_C2_RED      → Micro (minutes) - Cycle 2, Red
   P_INTEGRATION       → Macro (hours/days)
   ```

### Abandoning v1.0 "Hybrid" Approach

**v1.0 research conclusion:**
> "Option C: Hybrid - GitCommitInput accepts BOTH TDD and workflow phases, maps workflow → TDD"

**Why this was wrong:**
- **Treats symptoms:** Patches validation to accept workflow phases
- **Perpetuates dual system:** TDD phases still exist separately
- **State hidden:** Workflow phase not in commit message, only state.json
- **Backwards:** Makes TDD phases primary, workflow phases secondary

**v2.0 correction:**
- **Treats root cause:** Workflow phases ARE the commit scope
- **Unifies system:** Single phase hierarchy (macro → micro)
- **State visible:** Workflow phase encoded in every commit
- **Correct priority:** Workflow phases primary, TDD cycles are subphases

---

## Tool Dependency Analysis

### Current Tool Inventory (Consumers of Commit Conventions)

**1. GitManager (`mcp_server/managers/git_manager.py`)**

**Methods:**
```python
def commit_tdd_phase(self, phase: str, message: str, files: list[str] | None = None) -> str:
    """Commit with TDD phase prefix."""
    # Current: validates phase via GitConfig.has_phase()
    # Current: gets prefix via self._git_config.commit_prefix_map[phase]
    # Maps: phase="red" → prefix="test" → commit="test: message"
    
def commit_docs(self, message: str, files: list[str] | None = None) -> str:
    """Commit with docs prefix."""
    # Current: hardcoded "docs:" prefix
```

**Usage:**
- Called by `GitCommitTool.execute()` in [git_tools.py](../../../mcp_server/tools/git_tools.py)
- 78 test assertions across test suite

**Change Impact:**
- ❌ **REMOVE:** `commit_tdd_phase()` (TDD-centric)
- ❌ **REMOVE:** `commit_docs()` (special case)
- ✅ **ADD:** `commit_with_scope(type: str, scope: str, message: str, files: list[str] | None) -> str`

---

**2. GitConfig (`mcp_server/config/git_config.py`)**

**Fields:**
```python
tdd_phases: list[str] = ["red", "green", "refactor", "docs"]  # Convention #2
commit_prefix_map: dict[str, str] = {  # Convention #3
    "red": "test",
    "green": "feat", 
    "refactor": "refactor",
    "docs": "docs"
}
```

**Methods:**
```python
def has_phase(self, phase: str) -> bool:
    """Check if phase is valid TDD phase."""
    return phase in self.tdd_phases

def get_prefix(self, phase: str) -> str:
    """Get commit prefix for TDD phase."""
    return self.commit_prefix_map[phase]
```

**Usage:**
- Singleton loaded from `.st3/git.yaml`
- Referenced by GitManager validation
- 54 test assertions

**Change Impact:**
- ❌ **DEPRECATE:** `tdd_phases` (replaced by workphases.yaml)
- ❌ **DEPRECATE:** `commit_prefix_map` (becomes type → commit type mapping)
- ❌ **DEPRECATE:** `has_phase()` (replaced by WorkflowConfig.has_phase())
- ❌ **DEPRECATE:** `get_prefix()` (replaced by ScopeEncoder utility)
- ✅ **ADD:** `commit_types` list (feat, test, docs, refactor, fix, chore)
- ✅ **RETAIN:** `branch_types`, `protected_branches`, `branch_name_pattern` (unchanged)

---

**3. GitCommitInput (`mcp_server/tools/git_tools.py`)**

**Current Schema:**
```python
class GitCommitInput(BaseModel):
    phase: str = Field(..., description="TDD phase (red/green/refactor/docs)")
    message: str
    files: list[str] | None = None
    
    @field_validator("phase")
    @classmethod
    def validate_phase(cls, value: str) -> str:
        git_config = GitConfig.from_file()
        if not git_config.has_phase(value):
            raise ValueError(f"Invalid phase: {value}")
        return value
```

**Change Impact:**
- ❌ **REMOVE:** `phase` field (TDD-centric)
- ✅ **ADD:** `workflow_phase: str` - validated against workphases.yaml
- ✅ **ADD:** `sub_phase: str | None = None` - optional (e.g., "C1_RED")
- ✅ **ADD:** `commit_type: str` - validated against git.yaml commit_types
- ✅ **KEEP:** `message`, `files` (unchanged)

---

**4. get_work_context (`mcp_server/tools/context_tools.py`)**

**Current Behavior:**
```python
def _detect_tdd_phase(self) -> str:
    """Detect TDD phase from last commit prefix."""
    last_commit = git_adapter.get_last_commit_message()
    if last_commit.startswith("test:"):
        return "red"
    elif last_commit.startswith("feat:"):
        return "green"
    # ...
```

**Issue #117:** Ignores state.json, only parses commit prefixes

**Change Impact:**
- ✅ **FIX:** Parse scope from commit message instead of type
- ✅ **EXAMPLE:** `feat(P_TDD_SP_C2_GREEN): ...` → phase="tdd", subphase="C2_GREEN"
- ✅ **USE:** ScopeDecoder utility (DRY)
- ✅ **FALLBACK:** If no scope found, check state.json

---

**5. Other Tools (Minor Impact)**

**PolicyEngine tests:** Reference commit_prefix_map (23 assertions)
**PR creation tools:** May format commit lists, need scope awareness
**Changelog generators:** Should work unchanged (Conventional Commits compliant)

---

## Configuration Hierarchy Design

### New File Structure

```
.st3/
├── workphases.yaml         → SSOT: All workflow phases + metadata
├── workflows.yaml          → Workflow sequences (references workphases)
└── git.yaml                → Commit conventions (references workphases)
```

### 1. workphases.yaml (NEW - Single Source of Truth)

**Purpose:** Define ALL workflow phases with rich metadata

```yaml
# .st3/workphases.yaml
# Single Source of Truth for workflow phases
# Referenced by: workflows.yaml, git.yaml

version: "1.0"

phases:
  research:
    abbrev: P_RESEARCH
    display_name: "Research Phase"
    description: "Dependency analysis, architecture investigation, feasibility research"
    typical_duration_hours: 2
    commit_type_hints:
      - docs  # Research docs, notes, questions
    
  planning:
    abbrev: P_PLANNING
    display_name: "Planning Phase"
    description: "Task breakdown, implementation strategy, design decisions"
    typical_duration_hours: 1
    commit_type_hints:
      - docs  # Planning documents, strategy docs
    
  design:
    abbrev: P_DESIGN
    display_name: "Design Phase"
    description: "Architecture diagrams, interface definitions, data models"
    typical_duration_hours: 2
    commit_type_hints:
      - docs  # Design docs, architecture diagrams
    
  tdd:
    abbrev: P_TDD
    display_name: "Test-Driven Development Phase"
    description: "RED → GREEN → REFACTOR cycles with tests"
    typical_duration_hours: 4
    has_subphases: true
    subphase_pattern: "SP_C{cycle}_{step}"  # e.g., SP_C1_RED, SP_C2_GREEN
    subphases:
      red:
        abbrev: RED
        display_name: "Red (Failing Test)"
        commit_type_hints: [test]
      green:
        abbrev: GREEN
        display_name: "Green (Implementation)"
        commit_type_hints: [feat]
      refactor:
        abbrev: REFACTOR
        display_name: "Refactor (Cleanup)"
        commit_type_hints: [refactor]
    
  integration:
    abbrev: P_INTEGRATION
    display_name: "Integration Phase"
    description: "Wire components, end-to-end tests, system integration"
    typical_duration_hours: 2
    commit_type_hints:
      - feat   # Integration code
      - test   # Integration tests
    
  documentation:
    abbrev: P_DOCUMENTATION
    display_name: "Documentation Phase"
    description: "API docs, README updates, reference documentation"
    typical_duration_hours: 1
    commit_type_hints:
      - docs  # Documentation files
    
  coordination:
    abbrev: P_COORDINATION
    display_name: "Coordination Phase"
    description: "Epic management, multi-issue orchestration"
    typical_duration_hours: 1
    commit_type_hints:
      - docs   # Epic tracking, issue management
      - chore  # Project management tasks

# Conventional Commit types mapping
commit_types:
  feat: "New feature or enhancement"
  test: "Adding or updating tests"
  docs: "Documentation changes"
  refactor: "Code refactoring without behavior change"
  fix: "Bug fixes"
  chore: "Build, CI, or tooling changes"
```

**Key Design Decisions:**

✅ **Rich metadata:** duration hints, commit type suggestions  
✅ **Subphase support:** TDD phase decomposes into RED/GREEN/REFACTOR  
✅ **Self-documenting:** Display names and descriptions for tooling  
✅ **Extensible:** Easy to add new phases (e.g., `peer_review`)

---

### 2. workflows.yaml (UPDATED - References workphases)

**Purpose:** Define workflow sequences using phase references

```yaml
# .st3/workflows.yaml
# Workflow definitions - sequences of phases from workphases.yaml

version: "1.0"

# Reference to phase definitions
phase_source: workphases.yaml

workflows:
  feature:
    phases:
      - research      # references workphases.yaml:phases.research
      - planning
      - design
      - tdd
      - integration
      - documentation
    description: "New functionality (6 phases)"
  
  bug:
    phases:
      - research
      - planning
      - design
      - tdd
      - integration
      - documentation
    description: "Bug fixes (6 phases)"
  
  hotfix:
    phases:
      - tdd
      - integration
      - documentation
    description: "Urgent fixes (3 phases)"
  
  refactor:
    phases:
      - research
      - planning
      - tdd
      - integration
      - documentation
    description: "Code improvements (5 phases, no design)"
  
  docs:
    phases:
      - planning
      - documentation
    description: "Documentation work (2 phases)"
  
  epic:
    phases:
      - research
      - planning
      - design
      - coordination     # references workphases.yaml:phases.coordination
      - documentation
    description: "Large initiatives (5 phases)"
```

**Key Design Decisions:**

✅ **Phase references only:** No duplication of phase metadata  
✅ **Validation:** Workflow loader verifies phase references exist  
✅ **Clear separation:** Workflow = sequence, workphases = definitions

---

### 3. git.yaml (UPDATED - Simplified)

**Purpose:** Git-specific conventions (branch types, protected branches, commit types)

```yaml
# .st3/git.yaml
# Git conventions - branches, protection, commit types

version: "1.0"

# Reference to phase definitions
phase_source: workphases.yaml

# Convention #1: Branch types (UNCHANGED)
branch_types:
  - feature
  - fix
  - refactor
  - docs
  - epic

# Convention #4: Protected branches (UNCHANGED)
protected_branches:
  - main
  - master
  - develop

# Convention #5: Branch name pattern (UNCHANGED)
branch_name_pattern: "^[a-z0-9-]+$"

# Convention #9-11: Default base branch (UNCHANGED)
default_base_branch: main

# NEW: Commit type validation
# (Conventional Commits types - duplicated from workphases for git-specific context)
commit_types:
  - feat
  - test
  - docs
  - refactor
  - fix
  - chore

# NEW: Scope format specification
commit_format:
  pattern: "type(scope): description"
  scope_format: "P_{PHASE}" or "P_{PHASE}_SP_{SUBPHASE}"
  examples:
    - "docs(P_RESEARCH): complete analysis"
    - "test(P_TDD_SP_C1_RED): add validation tests"
    - "feat(P_TDD_SP_C1_GREEN): implement validation"

# REMOVED (migrated to workphases.yaml):
# - tdd_phases
# - commit_prefix_map
```

**Key Design Decisions:**

✅ **Git-specific only:** Branch rules, protection, commit format  
✅ **References workphases:** Doesn't redefine phases  
✅ **Conventional Commits:** Explicit format specification

---

### Configuration Data Flow

```
User action: git_add_or_commit(workflow_phase="tdd", sub_phase="C1_RED", commit_type="test", message="...")
                ↓
ScopeEncoder.encode(phase="tdd", subphase="C1_RED")
                ↓
        workphases.yaml (SSOT)
        phases.tdd.abbrev = "P_TDD"
        phases.tdd.subphases.red.abbrev = "RED"
                ↓
        Returns: "P_TDD_SP_C1_RED"
                ↓
GitManager.commit_with_scope(type="test", scope="P_TDD_SP_C1_RED", message="...")
                ↓
        Formats: "test(P_TDD_SP_C1_RED): add validation tests"
                ↓
        GitAdapter.commit(message="test(P_TDD_SP_C1_RED): add validation tests")
                ↓
        Git history

Later:
get_work_context() reads last commit
                ↓
ScopeDecoder.decode("P_TDD_SP_C1_RED")
                ↓
        workphases.yaml (SSOT)
        Parses: phase="tdd", subphase="C1_RED", cycle=1
                ↓
        Returns: WorkflowScope(phase="tdd", subphase="C1_RED", cycle=1, step="red")
                ↓
Display: "Workflow Phase: TDD (Cycle 1 - Red)"
```

---

## Scope Format Specification

### Format Grammar

```ebnf
<scope>       ::= <phase_scope> | <subphase_scope>
<phase_scope> ::= "P_" <PHASE_ABBREV>
<subphase_scope> ::= "P_" <PHASE_ABBREV> "_SP_" <SUBPHASE_SPEC>
<SUBPHASE_SPEC> ::= <CYCLE_SPEC> | <SIMPLE_SUBPHASE>
<CYCLE_SPEC>  ::= "C" <DIGIT>+ "_" <STEP_ABBREV>
<SIMPLE_SUBPHASE> ::= <ABBREV>

Examples:
  P_RESEARCH                → Research phase (no subphase)
  P_TDD_SP_C1_RED           → TDD phase, cycle 1, red step
  P_TDD_SP_C3_REFACTOR      → TDD phase, cycle 3, refactor step
  P_INTEGRATION             → Integration phase
```

### Complete Format Examples

```bash
# Research phase
docs(P_RESEARCH): analyze git workflow dependencies
docs(P_RESEARCH): document tool inventory

# Planning phase
docs(P_PLANNING): break down implementation tasks
docs(P_PLANNING): define acceptance criteria

# Design phase
docs(P_DESIGN): create configuration hierarchy diagram
docs(P_DESIGN): specify scope format grammar

# TDD phase - Cycle 1
test(P_TDD_SP_C1_RED): add ScopeEncoder validation tests
feat(P_TDD_SP_C1_GREEN): implement ScopeEncoder.encode()
refactor(P_TDD_SP_C1_REFACTOR): extract validation helper

# TDD phase - Cycle 2
test(P_TDD_SP_C2_RED): add ScopeDecoder parsing tests
feat(P_TDD_SP_C2_GREEN): implement ScopeDecoder.decode()
refactor(P_TDD_SP_C2_REFACTOR): consolidate regex patterns

# Integration phase
feat(P_INTEGRATION): integrate ScopeEncoder with GitManager
test(P_INTEGRATION): add end-to-end commit workflow tests

# Documentation phase
docs(P_DOCUMENTATION): update git workflow documentation
docs(P_DOCUMENTATION): add scope format examples to agent.md

# Coordination phase (epic-only)
docs(P_COORDINATION): create epic tracking document
chore(P_COORDINATION): update child issue dependencies
```

### Parsing Rules

**Regex Pattern:**
```python
SCOPE_PATTERN = re.compile(
    r"P_(?P<phase>[A-Z_]+)"           # Phase abbreviation
    r"(?:_SP_"                          # Optional subphase
        r"(?:"
            r"C(?P<cycle>\d+)_(?P<step>[A-Z_]+)"   # Cycle + step (e.g., C1_RED)
            r"|"
            r"(?P<simple>[A-Z_]+)"                 # Simple subphase
        r")"
    r")?"
)
```

**Validation:**
1. Parse scope with regex
2. Look up `phase` in workphases.yaml
3. If subphase present, validate against phase.subphases
4. If cycle present, extract cycle number

---

## DRY Utility Design

### Module: `mcp_server/core/scope_formatter.py` (NEW)

**Purpose:** Single source of truth for scope encoding/decoding logic

**File Header (per coding standards):**
```python
# mcp_server/core/scope_formatter.py
"""
Workflow scope formatter utilities.

Encodes and decodes Conventional Commits scope field from workflow phase state.
Ensures DRY principle - all tools use these utilities instead of reimplementing
scope parsing/formatting logic.

@layer: MCP Server (Core)
@dependencies: [re, typing, pydantic, mcp_server.config.workphase_config]
@responsibilities:
    - Encode workflow phase + subphase → scope string (P_PHASE_SP_SUBPHASE)
    - Decode scope string → structured WorkflowScope object
    - Validate scope format against workphases.yaml
    - Provide cycle tracking for TDD subphases
"""

# Standard library
import re
from typing import Literal

# Third-party
from pydantic import BaseModel, Field, field_validator

# Project modules
from mcp_server.config.workphase_config import WorkflowPhaseConfig
```

### Data Models

```python
class WorkflowScope(BaseModel):
    """Parsed workflow scope from commit message."""
    
    phase: str = Field(..., description="Workflow phase (e.g., 'tdd', 'research')")
    subphase: str | None = Field(None, description="Subphase step (e.g., 'red', 'green')")
    cycle: int | None = Field(None, description="TDD cycle number (1-based)", ge=1)
    
    @property
    def display_name(self) -> str:
        """Human-readable phase name from workphases.yaml."""
        config = WorkflowPhaseConfig.from_file()
        phase_def = config.phases[self.phase]
        
        if self.subphase and self.cycle:
            subphase_def = phase_def.subphases[self.subphase]
            return f"{phase_def.display_name} (Cycle {self.cycle} - {subphase_def.display_name})"
        elif self.subphase:
            return f"{phase_def.display_name} - {self.subphase}"
        else:
            return phase_def.display_name
```

### ScopeEncoder

```python
class ScopeEncoder:
    """Encode workflow phase state into scope string."""
    
    SCOPE_PATTERN = re.compile(
        r"P_(?P<phase>[A-Z_]+)"
        r"(?:_SP_"
            r"(?:"
                r"C(?P<cycle>\d+)_(?P<step>[A-Z_]+)"
                r"|"
                r"(?P<simple>[A-Z_]+)"
            r")"
        r")?"
    )
    
    def __init__(self) -> None:
        self._config = WorkflowPhaseConfig.from_file()
    
    def encode(
        self, 
        phase: str, 
        subphase: str | None = None,
        cycle: int | None = None
    ) -> str:
        """Encode workflow phase into scope string.
        
        Args:
            phase: Workflow phase name (e.g., "research", "tdd")
            subphase: Optional subphase step (e.g., "red", "green")
            cycle: Optional TDD cycle number (1-based)
            
        Returns:
            Scope string (e.g., "P_RESEARCH", "P_TDD_SP_C1_RED")
            
        Raises:
            ValueError: If phase/subphase invalid or cycle missing when required
            
        Examples:
            >>> encoder = ScopeEncoder()
            >>> encoder.encode("research")
            'P_RESEARCH'
            >>> encoder.encode("tdd", subphase="red", cycle=1)
            'P_TDD_SP_C1_RED'
        """
        # Validate phase
        if phase not in self._config.phases:
            raise ValueError(
                f"Invalid phase: {phase}. "
                f"Valid phases: {list(self._config.phases.keys())}"
            )
        
        phase_def = self._config.phases[phase]
        phase_abbrev = phase_def.abbrev.replace("P_", "")  # Remove prefix if present
        
        # No subphase - simple case
        if subphase is None:
            return f"P_{phase_abbrev}"
        
        # Validate subphase
        if not phase_def.has_subphases or subphase not in phase_def.subphases:
            raise ValueError(
                f"Phase '{phase}' does not have subphase '{subphase}'. "
                f"Valid subphases: {list(phase_def.subphases.keys()) if phase_def.has_subphases else 'None'}"
            )
        
        subphase_abbrev = phase_def.subphases[subphase].abbrev
        
        # Cycle-based subphase (TDD)
        if phase_def.subphase_pattern and "{cycle}" in phase_def.subphase_pattern:
            if cycle is None:
                raise ValueError(
                    f"Phase '{phase}' with subphase '{subphase}' requires cycle number"
                )
            return f"P_{phase_abbrev}_SP_C{cycle}_{subphase_abbrev}"
        
        # Simple subphase
        return f"P_{phase_abbrev}_SP_{subphase_abbrev}"
    
    def suggest_commit_types(self, phase: str, subphase: str | None = None) -> list[str]:
        """Get suggested commit types for phase/subphase.
        
        Returns list from workphases.yaml commit_type_hints.
        """
        phase_def = self._config.phases[phase]
        
        if subphase and phase_def.has_subphases:
            subphase_def = phase_def.subphases[subphase]
            return subphase_def.commit_type_hints or phase_def.commit_type_hints
        
        return phase_def.commit_type_hints
```

### ScopeDecoder

```python
class ScopeDecoder:
    """Decode scope string into structured workflow phase state."""
    
    def __init__(self) -> None:
        self._config = WorkflowPhaseConfig.from_file()
        self._encoder = ScopeEncoder()  # Reuse pattern
    
    def decode(self, scope: str) -> WorkflowScope:
        """Decode scope string to WorkflowScope.
        
        Args:
            scope: Scope string from commit message
            
        Returns:
            Parsed WorkflowScope object
            
        Raises:
            ValueError: If scope format invalid or phase not found
            
        Examples:
            >>> decoder = ScopeDecoder()
            >>> scope = decoder.decode("P_RESEARCH")
            >>> scope.phase
            'research'
            >>> scope = decoder.decode("P_TDD_SP_C1_RED")
            >>> scope.phase, scope.subphase, scope.cycle
            ('tdd', 'red', 1)
        """
        match = self._encoder.SCOPE_PATTERN.match(scope)
        if not match:
            raise ValueError(
                f"Invalid scope format: {scope}. "
                f"Expected: P_PHASE or P_PHASE_SP_SUBPHASE"
            )
        
        groups = match.groupdict()
        phase_abbrev = groups["phase"]
        
        # Find phase by abbreviation
        phase_name = self._find_phase_by_abbrev(phase_abbrev)
        if not phase_name:
            raise ValueError(
                f"Unknown phase abbreviation: {phase_abbrev}"
            )
        
        # Parse subphase
        cycle = int(groups["cycle"]) if groups["cycle"] else None
        step_abbrev = groups["step"] or groups["simple"]
        
        subphase_name = None
        if step_abbrev:
            subphase_name = self._find_subphase_by_abbrev(phase_name, step_abbrev)
            if not subphase_name:
                raise ValueError(
                    f"Unknown subphase abbreviation: {step_abbrev} for phase {phase_name}"
                )
        
        return WorkflowScope(
            phase=phase_name,
            subphase=subphase_name,
            cycle=cycle
        )
    
    def _find_phase_by_abbrev(self, abbrev: str) -> str | None:
        """Find phase name by abbreviation."""
        for name, definition in self._config.phases.items():
            phase_abbrev = definition.abbrev.replace("P_", "")
            if phase_abbrev == abbrev:
                return name
        return None
    
    def _find_subphase_by_abbrev(self, phase: str, abbrev: str) -> str | None:
        """Find subphase name by abbreviation."""
        phase_def = self._config.phases[phase]
        if not phase_def.has_subphases:
            return None
        
        for name, subphase_def in phase_def.subphases.items():
            if subphase_def.abbrev == abbrev:
                return name
        return None
    
    def extract_from_commit(self, commit_message: str) -> WorkflowScope | None:
        """Extract scope from full Conventional Commits message.
        
        Args:
            commit_message: Full commit message (type(scope): description)
            
        Returns:
            WorkflowScope if scope found and valid, None otherwise
            
        Examples:
            >>> decoder = ScopeDecoder()
            >>> scope = decoder.extract_from_commit("test(P_TDD_SP_C1_RED): add tests")
            >>> scope.phase
            'tdd'
        """
        # Conventional Commits pattern
        commit_pattern = re.compile(r"^[a-z]+\((?P<scope>[^)]+)\):")
        match = commit_pattern.match(commit_message)
        
        if not match:
            return None
        
        try:
            return self.decode(match.group("scope"))
        except ValueError:
            return None
```

### Usage Examples

```python
# Encoding (tools/git_tools.py)
encoder = ScopeEncoder()
scope = encoder.encode(phase="tdd", subphase="red", cycle=1)
# → "P_TDD_SP_C1_RED"

commit_types = encoder.suggest_commit_types("tdd", "red")
# → ["test"]

# Decoding (tools/context_tools.py - get_work_context)
decoder = ScopeDecoder()
last_commit = "test(P_TDD_SP_C2_GREEN): implement validator"

workflow_scope = decoder.extract_from_commit(last_commit)
# → WorkflowScope(phase="tdd", subphase="green", cycle=2)

display = workflow_scope.display_name
# → "Test-Driven Development Phase (Cycle 2 - Green (Implementation))"
```

---

## Migration Impact Assessment

### Files Modified

**Core Config:**
1. ✅ `.st3/workphases.yaml` - NEW (SSOT)
2. 🔄 `.st3/workflows.yaml` - UPDATED (add phase_source reference)
3. 🔄 `.st3/git.yaml` - UPDATED (remove tdd_phases, commit_prefix_map; add commit_types, scope format)

**MCP Server:**
4. ✅ `mcp_server/core/scope_formatter.py` - NEW (DRY utility)
5. ✅ `mcp_server/config/workphase_config.py` - NEW (WorkflowPhaseConfig model)
6. 🔄 `mcp_server/config/git_config.py` - UPDATED (deprecate tdd_phases, commit_prefix_map)
7. 🔄 `mcp_server/managers/git_manager.py` - MAJOR REFACTOR
   - Remove: `commit_tdd_phase()`, `commit_docs()`
   - Add: `commit_with_scope(type, scope, message, files)`
8. 🔄 `mcp_server/tools/git_tools.py` - MAJOR REFACTOR
   - Update: GitCommitInput schema
   - Use: ScopeEncoder for scope generation
9. 🔄 `mcp_server/tools/context_tools.py` - FIX Issue #117
   - Use: ScopeDecoder for phase detection

**Tests:**
10. 🔄 `tests/.../test_git_manager.py` - UPDATE (78+ assertions)
11. 🔄 `tests/.../test_git_tools_config.py` - UPDATE (validation tests)
12. ✅ `tests/.../test_scope_formatter.py` - NEW (encoder/decoder tests)

**Documentation:**
13. 🔄 `agent.md` - UPDATE (Phase 2.3 TDD Cycle, Phase 5 Tool Priority Matrix)
14. 🔄 `docs/coding_standards/GIT_WORKFLOW.md` - UPDATE (commit examples)

### Breaking Changes

**❌ Breaking (tools):**
- `GitManager.commit_tdd_phase()` removed
- `GitManager.commit_docs()` removed
- `GitConfig.has_phase()` deprecated
- `GitConfig.get_prefix()` deprecated
- `GitCommitInput.phase` field removed

**✅ Non-breaking:**
- Branch conventions unchanged
- Protected branches unchanged
- Conventional Commits format preserved (type(scope): message)
- GitHub/GitLab tooling compatibility maintained

### Test Impact

**Estimated test updates:**
- GitManager tests: ~80 assertions (rewrite with new API)
- GitConfig tests: ~50 assertions (deprecate old, add new)
- ScopeFormatter tests: ~60 assertions (new)
- Integration tests: ~20 assertions (update commit messages)

**Total: ~210 test assertions** (mix of updates + new)

---

## Architecture Decision Record

### ADR-001: Workflow-First Commit Convention

**Status:** Proposed  
**Date:** 2026-02-14  
**Deciders:** User (architect), Agent (implementer)

### Context

**Problem:** Two independent phase systems (TDD phases in git.yaml, workflow phases in workflows.yaml) cause confusion, require mental mapping, and hide workflow state in external state.json files.

**User Vision:** Workflow phases should be PRIMARY and VISIBLE in git history. Commit messages should encode workflow state using Conventional Commits format.

### Decision

**We will:**

1. **Establish workphases.yaml as SSOT** for all workflow phase definitions with rich metadata
2. **Encode workflow state in Conventional Commits scope field** using format `type(P_PHASE_SP_SUBPHASE): description`
3. **Deprecate TDD-centric concepts** (commit_tdd_phase, commit_prefix_map) in favor of workflow-first architecture
4. **Build DRY utilities** (ScopeEncoder, ScopeDecoder) following coding standards
5. **Maintain Conventional Commits compliance** to preserve third-party tooling compatibility

### Consequences

**✅ Positive:**
- **Git history = complete audit trail:** `git log` shows full workflow progression
- **State visibility:** No hidden state.json dependency, commits are self-describing
- **DRY architecture:** Single source of truth (workphases.yaml) referenced by all tools
- **Extensibility:** Adding new phases = config change only, zero code changes
- **Tooling compatibility:** Conventional Commits format preserved for GitHub/GitLab

**⚠️ Negative:**
- **Migration effort:** ~14 files modified, ~210 test assertions updated
- **Breaking changes:** GitManager API changes (commit_tdd_phase removed)
- **Learning curve:** Agents must learn new scope format (P_PHASE_SP_SUBPHASE)
- **Verbosity:** Scope strings longer than old prefixes (P_TDD_SP_C1_RED vs test:)

**🔄 Mitigation:**
- **Documentation:** Update agent.md with clear examples and Tool Priority Matrix
- **Validation:** Rich error messages with examples (learned from Issue #121 Root Cause #5)
- **Tooling:** ScopeEncoder suggests commit types, reducing cognitive load
- **Testing:** Comprehensive test coverage ensures correctness

### Alternatives Considered

**Alternative 1: Hybrid validation (v1.0 Option C)**
- Accept both TDD and workflow phases, map workflow → TDD
- **Rejected:** Treats symptoms, perpetuates dual system, state hidden

**Alternative 2: Keep TDD phases primary**
- Add workflow tracking separately (state.json only)
- **Rejected:** Violates user vision (workflow-first), Issue #117 persists

**Alternative 3: Custom commit format (non-Conventional Commits)**
- Use format like `P_RESEARCH - SP_TDD_C1 - CT_GREEN - message`
- **Rejected:** Breaks GitHub/GitLab tooling, poor industry compatibility

### Related Issues

- Issue #138: git_add_or_commit workflow phases (primary)
- Issue #117: get_work_context TDD-only detection (fixed by scope decoding)
- Issue #139: get_project_plan missing current_phase (improved by visible state)
- Issue #121: safe_edit_file error messages (pattern for validation UX)

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 2.0 | 2026-02-14T17:45:00+00:00 | Agent | Complete architectural design with workphases.yaml, scope format, DRY utilities |
