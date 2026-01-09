# Issue #54 Research: Scaffold Rules Configuration

**Date:** 2026-01-09  
**Author:** GitHub Copilot (Claude Sonnet 4.5)  
**Status:** DRAFT  
**Issue:** #54 - Config: Scaffold Rules Configuration (scaffold.yaml)  
**Parent:** Epic #49 - MCP Platform Configurability

---

## Executive Summary

Research phase for migrating hardcoded scaffold rules and file policies from `scaffold_tools.py` and `policy_engine.py` to `.st3/scaffold.yaml` configuration file.

**Key Findings:**
- 9 component types hardcoded in ScaffoldComponentTool
- 2 scaffold phases hardcoded in PolicyEngine (design, tdd)
- 3 blocked patterns for Python files
- 8 allowed file extensions  
- 5 allowed directories

**Location:** `.st3/scaffold.yaml` (corrected from `config/` per user guidance)

---

## Epic Context

**Parent Issue:** Epic #49 - MCP Platform Configurability  
**Related Issues:** #50 (workflows.yaml ✅), #51 (labels.yaml ✅), #52 (validation.yaml ✅), #53 (quality.yaml ✅)

### Epic #49 Goal
Externalize all hardcoded configuration to YAML files in `.st3/` directory, enabling:
- Runtime configurability without code changes
- Clear separation of policy from implementation
- Easier customization for different projects
- Centralized configuration management

### Completed Sibling Issues
1. **#50 - workflows.yaml** ✅ Closed
2. **#51 - labels.yaml** ✅ Closed  
3. **#52 - validation.yaml** ✅ Closed
4. **#53 - quality.yaml** ✅ Closed

---

## Lessons Learned from Sibling Issues

### From Issue #51 (labels.yaml)
**Pattern Established:**
- Singleton pattern with `_instance` ClassVar
- Pydantic models for validation
- `load()` classmethod for lazy initialization
- GitHub sync mechanism for external systems
- Clear separation: config model + loader + consumer

**Key Insight:** "Following WorkflowConfig pattern from Issue #50"
- Reuse established patterns for consistency
- Pydantic validation catches config errors early
- Singleton ensures single source of truth
- 100% test coverage requirement

**Branch Strategy:**
- Initially branched from epic branch (refactor/49)
- Later child issues branch from main (epic completed)
- This issue (#54): branch from main

### From Issue #52 (validation.yaml)
**Pattern Established:**
- Nested Pydantic models (TemplateRule → ValidationConfig)
- Dict[str, Model] for type-specific rules
- Removed RULES dict from code completely
- Config loader in separate module

**Key Insight:** "RULES dict removed from code"
- Complete migration, no fallback to hardcoded values
- All validation customizable via YAML
- Tests ensure config loading works before deployment

### Common Patterns Across All Issues
1. **File Location:** `.st3/` directory (not `config/`)
2. **Pydantic Validation:** Always use Pydantic models
3. **Singleton Pattern:** ClassVar + load() classmethod
4. **Test Coverage:** 100% requirement
5. **Documentation:** Reference docs in main documentation
6. **No Fallbacks:** Remove hardcoded values completely

---

## Current Implementation Analysis

### scaffold_tools.py (Lines 100-150)

**Hardcoded Component Types (9 types):**
```python
self.scaffolders: dict[str, ComponentScaffolder] = {
    "dto": DTOScaffolder(self.renderer),
    "worker": WorkerScaffolder(self.renderer),
    "adapter": AdapterScaffolder(self.renderer),
    "tool": ToolScaffolder(self.renderer),
    "resource": ResourceScaffolder(self.renderer),
    "schema": SchemaScaffolder(self.renderer),
    "interface": InterfaceScaffolder(self.renderer),
    "service": ServiceScaffolder(self.renderer),
    "generic": GenericScaffolder(self.renderer),
}
```

**Handler Mapping (Lines 125-145):**
```python
handlers: dict[str, Callable] = {
    "dto": self._scaffold_dto,
    "worker": self._scaffold_worker,
    # ... etc (9 handlers total)
}
```

**Current Validation (Line 147):**
```python
if not handler:
    raise ValidationError(
        f"Unknown component type: {params.component_type}",
        hints=["Use dto, worker, adapter, tool, resource, schema, interface, service, generic"]
    )
```

**Problem:** Component types are hardcoded in three places:
1. Scaffolders dict initialization
2. Handlers dict
3. Error message hints

### policy_engine.py (Lines 120-200)

**Scaffold Phases (Lines 142-157):**
```python
def _decide_scaffold(self, ctx: DecisionContext) -> PolicyDecision:
    allowed_phases = {"design", "tdd"}  # HARDCODED
    
    if ctx.phase in allowed_phases:
        return PolicyDecision(allowed=True, ...)
    return PolicyDecision(allowed=False, ...)
```

**File Creation Blocked Patterns (Lines 165-172):**
```python
blocked_patterns = [
    ("backend", ".py"),      # backend/**/*.py must use scaffold
    ("tests", ".py"),        # tests/**/*.py must use scaffold  
    ("mcp_server", ".py"),   # mcp_server/**/*.py must use scaffold
]
```

**Allowed Extensions (Line 184):**
```python
allowed_extensions = {".yml", ".yaml", ".json", ".toml", ".ini", ".txt", ".md", ".lock"}  # 8 extensions
```

**Allowed Directories (Line 185):**
```python
allowed_dirs = {"scripts", "proof_of_concepts", "docs", "config", ".st3"}  # 5 directories
```

**Problem:** File policies scattered across PolicyEngine with no external configuration.

---

## Hardcoded Rules Inventory

### Component Types (9 total)
1. `dto` - Data Transfer Objects
2. `worker` - Background workers
3. `adapter` - External service adapters
4. `tool` - MCP tools
5. `resource` - MCP resources
6. `schema` - Pydantic schemas
7. `interface` - Protocol definitions
8. `service` - Service layer (query/command/orchestrator subtypes)
9. `generic` - Generic Python files from templates

### Scaffold Policies

**Allowed Phases (2):**
- `design` - Architecture and planning phase
- `tdd` - Test-driven development phase

**Rationale:** Scaffolding generates new code structure, should only happen during design/implementation, not during research or documentation phases.

### File Creation Policies

**Blocked Patterns (3 rules):**
1. `backend/**/*.py` → Must use scaffold tool
2. `tests/**/*.py` → Must use scaffold tool
3. `mcp_server/**/*.py` → Must use scaffold tool

**Allowed Extensions (8 types):**
- Configuration: `.yml`, `.yaml`, `.json`, `.toml`, `.ini`
- Documentation: `.md`, `.txt`
- Dependency: `.lock`

**Allowed Directories (5 paths):**
- `scripts/` - Utility scripts
- `proof_of_concepts/` - POC code
- `docs/` - Documentation
- `config/` - Configuration (legacy)
- `.st3/` - Platform configuration (current standard)

---

## Configuration Requirements

### Proposed .st3/scaffold.yaml Structure

```yaml
# Scaffold configuration
version: "1.0"

# Component types supported by scaffold tool
component_types:
  - dto
  - worker
  - adapter
  - tool
  - resource
  - schema
  - interface
  - service
  - generic

# Phases where scaffolding is allowed
allowed_phases:
  - design
  - tdd

# File creation policies
file_policies:
  # Python files in these directories must use scaffold tool
  blocked_patterns:
    - directory: backend
      extension: .py
      reason: "Backend code must follow architecture patterns"
    - directory: tests
      extension: .py
      reason: "Test files must follow testing conventions"
    - directory: mcp_server
      extension: .py
      reason: "MCP server code must follow platform patterns"
  
  # File extensions allowed for direct creation (create_file tool)
  allowed_extensions:
    - .yml
    - .yaml
    - .json
    - .toml
    - .ini
    - .txt
    - .md
    - .lock
  
  # Directories where files can be created directly
  allowed_directories:
    - scripts
    - proof_of_concepts
    - docs
    - config
    - .st3
```

### Pydantic Model Structure

```python
# mcp_server/config/scaffold_config.py

from pydantic import BaseModel, Field
from typing import ClassVar

class BlockedPattern(BaseModel):
    """Pattern for files that must use scaffold tool."""
    directory: str
    extension: str
    reason: str = ""

class FilePolicies(BaseModel):
    """File creation policies."""
    blocked_patterns: list[BlockedPattern]
    allowed_extensions: set[str]
    allowed_directories: set[str]

class ScaffoldConfig(BaseModel):
    """Scaffold configuration from .st3/scaffold.yaml."""
    version: str = "1.0"
    component_types: list[str]
    allowed_phases: set[str]
    file_policies: FilePolicies
    
    _instance: ClassVar["ScaffoldConfig | None"] = None
    
    @classmethod
    def load(cls, config_path: Path | None = None) -> "ScaffoldConfig":
        """Load scaffold.yaml with Pydantic validation."""
        # Singleton pattern from Issue #51
        if cls._instance is None:
            # Load YAML + validate with Pydantic
            cls._instance = ...
        return cls._instance
```

### Integration Points

**1. ScaffoldComponentTool (scaffold_tools.py)**
- Replace hardcoded component types with `ScaffoldConfig.load().component_types`
- Update error hints dynamically from config
- Validate component_type against config

**2. PolicyEngine (policy_engine.py)**
- Replace `allowed_phases = {"design", "tdd"}` with `ScaffoldConfig.load().allowed_phases`
- Replace `blocked_patterns` list with `config.file_policies.blocked_patterns`
- Replace `allowed_extensions` set with `config.file_policies.allowed_extensions`
- Replace `allowed_dirs` set with `config.file_policies.allowed_directories`

**3. Tests**
- Test config loading from YAML
- Test policy enforcement with custom config
- Test error handling for invalid config
- Test migration from hardcoded to config-based

---

## Safe_Edit Tool Evaluation

### Evaluation Summary

**Attempt #1: Search/Replace Mode**
- ❌ Failed - Pattern not found
- Issue: Expected template structure didn't match actual scaffolded template
- Root Cause: Generic template includes extensive HTML comments, metadata sections, and different structure than expected

**Attempt #2: Content Mode (Full Replacement)**
- ✅ Success (this document)
- Used `mode="strict"` with full `content` parameter (no search)
- Completely replaced file with research findings

### Observations

**✅ What Worked:**
1. **Content mode for full rewrites** - Clean, single-operation replacement
2. **Scaffolding tool** - Created proper directory structure and template
3. **Diff preview** - Shows changes clearly (when working)

**❌ Challenges Identified:**
1. **Search pattern matching** - Whitespace/formatting must match exactly
2. **Template structure complexity** - Generic templates have extensive boilerplate
3. **No incremental editing** - Search/replace requires perfect pattern match

**Root Cause Analysis:**
- Agents don't see the actual file content before attempting edits
- Templates have more structure than expected (HTML comments, metadata)
- Search/replace mode requires exact string matching (whitespace-sensitive)
- No fuzzy matching or smart pattern detection

**Recommendations for Improving safe_edit:**
1. **Add `read_first` parameter** - Tool should optionally read file before edit to show agent actual content
2. **Improve search matching** - Consider fuzzy/regex matching for patterns
3. **Better error messages** - Show portion of file where pattern was expected
4. **Template-aware mode** - Special handling for scaffolded templates
5. **Section-based editing** - Edit by markdown heading instead of raw text search

**Agent Workflow Improvement:**
- Always read file first with `read_file` before complex edits
- Use content mode for full rewrites instead of search/replace
- For incremental edits, read exact text first to match pattern precisely

### Impact on Issue #54

**For this research phase:**
- ✅ Research document completed successfully
- ✅ Two attempts total (one failed, one succeeded)
- ✅ Workaround: Use content mode for full replacement

**For future phases:**
- Will use content mode for document creation
- Will read files first before attempting edits
- Will prefer full replacements over incremental edits when practical

---

## Next Steps

1. **Research Complete** ✅
   - Hardcoded rules identified and documented
   - Lessons learned from sibling issues applied
   - Requirements clearly defined
   - Safe_edit tool evaluated with findings

2. **Transition to Planning Phase**
   - Use `transition_phase` tool to move to planning
   - Design detailed .st3/scaffold.yaml schema
   - Design ScaffoldConfig Pydantic model structure
   - Plan migration strategy from hardcoded to config
   - Define comprehensive test coverage requirements

3. **Commit Research Work**
   - Commit research.md with TDD phase (docs)
   - Document safe_edit evaluation findings
   - Prepare for planning phase

---

**End of Research Phase - Ready for Phase Transition**