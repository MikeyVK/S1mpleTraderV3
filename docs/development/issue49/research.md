# Epic #49: MCP Platform Configurability - Research

**Status:** COMPLETE
**Phase:** Discovery/Research
**Date:** 2025-12-26
**Epic:** #49 (MCP Platform Configurability)

---

## 1. Problem Statement

The MCP server has accumulated significant technical debt by hardcoding business logic, workflow rules, and validation policies in Python code instead of configuration files.

**Observation:** Violation of "Config Over Code" principle identified during Issue #42 analysis.

**Research Question:** What configuration approaches and technologies exist to migrate hardcoded rules to declarative configuration?

---

## 2. Current State Analysis

### 2.1 Hardcoded Configuration Inventory

**Methodology:** Code scanning for dict definitions, constants, and validation rules.

**Findings:**

| Category | Location | Lines | Instances | Details |
|----------|----------|-------|-----------|---------|
| **Workflow Templates** | `project_manager.py:13-37` | 35 | 5 issue types | PHASE_TEMPLATES dict |
| **Document Templates** | `doc_manager.py:18-30` | 13 | 9 mappings | TEMPLATES dict + SCOPE_DIRS dict |
| **Commit Conventions** | `git_manager.py:49,56-60` | 6 | 7 items | TDD phase validation + prefix_map |
| **Branch Types** | `git_manager.py:16-18` | 3 | 4 types | feature/fix/refactor/docs validation |
| **Protected Branches** | `git_manager.py:138` | 1 | 3 names | main/master/develop |
| **Quality Gates** | `qa_manager.py` | ~150 | 3 gates | Pylint/Mypy/Pyright commands + timeouts |
| **Validation Rules** | `template_validator.py:12-41` | 30 | 5 templates | RULES dict (worker/tool/dto/adapter/base) |
| **Scaffold Rules** | `scaffold_tool.py:117-127` | 11 | 10 types | Component type validation |
| **File Policies** | `policy_engine.py:114,133,153-157,170-171` | ~15 | 8 policies | TDD prefixes, scaffold rules, allowed extensions |
| **Label Definitions** | `issue_tools.py` (implied) | N/A | ~15 labels | type:/priority:/status:/phase: patterns |
| **Regex Patterns** | Multiple files | ~50 | 15 patterns | Branch names, output parsing, validation |
| **Magic Numbers** | Multiple files | ~30 | 25+ values | Timeouts, limits, thresholds, defaults |
| **File Paths** | Multiple files | ~10 | 6 paths | .st3/state.json, .st3/projects.json, etc. |
| **Default Field Values** | All tool files | ~60 | 30+ defaults | Pydantic Field() defaults |

**Total:** ~400+ lines of hardcoded configuration across 15+ files, 150+ distinct config items.

### 2.2 Detailed Configuration Breakdown

#### 2.2.1 Workflow Templates (`project_manager.py:13-37`)

**Purpose:** Define phase sequences per issue type

```python
PHASE_TEMPLATES = {
    "feature": {
        "required_phases": ("discovery", "planning", "design", "component", "tdd", "integration", "documentation"),
        "description": "Full 7-phase workflow for new features"
    },
    "bug": {
        "required_phases": ("discovery", "planning", "component", "tdd", "integration", "documentation"),
        "description": "6-phase workflow (skip design)"
    },
    "docs": {
        "required_phases": ("discovery", "planning", "component", "documentation"),
        "description": "4-phase workflow (skip tdd + integration)"
    },
    "refactor": {
        "required_phases": ("discovery", "planning", "tdd", "integration", "documentation"),
        "description": "5-phase workflow (skip design + component)"
    },
    "hotfix": {
        "required_phases": ("component", "tdd", "integration"),
        "description": "Minimal 3-phase workflow (requires approval for all operations)"
    }
}
```

**Issues:**
- No execution mode support (autonomous vs interactive)
- No phase transition rules
- Uses old phase names (tdd vs red/green/refactor)
- No support for custom workflows

---

#### 2.2.2 Document Templates (`doc_manager.py:18-30`)

**Purpose:** Map doc types to template files and directories

```python
TEMPLATES = {
    "architecture": "ARCHITECTURE_TEMPLATE.md",
    "design": "DESIGN_TEMPLATE.md",
    "reference": "REFERENCE_TEMPLATE.md",
    "tracking": "TRACKING_TEMPLATE.md"
}

SCOPE_DIRS = {
    "architecture": "architecture",
    "coding_standards": "coding_standards",
    "development": "development",
    "reference": "reference",
    "implementation": "implementation",
}
```

**Issues:**
- Template paths hardcoded
- No custom template support
- No validation of template existence

---

#### 2.2.3 Git Conventions (`git_manager.py` + `policy_engine.py`)

**Purpose:** Branch types, TDD phase mapping, commit prefixes

```python
# Branch types (git_manager.py:16-18)
VALID_BRANCH_TYPES = ["feature", "fix", "refactor", "docs"]

# TDD phases (git_manager.py:49)
VALID_TDD_PHASES = ["red", "green", "refactor"]

# Prefix mapping (git_manager.py:56-60)
prefix_map = {
    "red": "test",
    "green": "feat",
    "refactor": "refactor"
}

# TDD prefixes (policy_engine.py:114)
TDD_COMMIT_PREFIXES = ("red:", "green:", "refactor:", "docs:")

# Protected branches (git_manager.py:138)
protected_branches = ["main", "master", "develop"]
```

**Issues:**
- Duplicated logic across files
- No support for org-specific branch naming
- Protected branch list not configurable

---

#### 2.2.4 Quality Gates (`qa_manager.py`)

**Purpose:** Static analysis tool configurations

```python
# Pylint (lines 100-113)
["--enable=all", "--max-line-length=100", "--output-format=text"]
timeout: 300 seconds

# Mypy (lines 167-174)
["--strict", "--no-error-summary"]
timeout: 300 seconds

# Pyright (lines 258-265)
["--outputjson"]
timeout: 300 seconds

# Regex patterns
pylint_pattern = r"^(.+?):(\d+):(\d+): ([A-Z]\d+): (.+)$"
mypy_pattern = r"^(.+?):(\d+): (error|warning): (.+)$"
```

**Issues:**
- Tool paths not configurable
- Timeouts hardcoded
- Cannot add custom quality gates
- Regex patterns embedded in code

---

#### 2.2.5 Validation Rules (`template_validator.py:12-41`)

**Purpose:** Define required patterns for component types

```python
RULES = {
    "worker": {
        "required_class_suffix": "Worker",
        "required_methods": ["execute"],
        "required_imports": ["BaseWorker", "TaskResult"],
        "description": "Worker components"
    },
    "tool": {
        "required_class_suffix": "Tool",
        "required_methods": ["execute"],
        "required_attrs": ["name", "description", "input_schema"],
        "description": "MCP Tools"
    },
    "dto": {
        "required_class_suffix": "DTO",
        "required_decorators": ["@dataclass"],
        "description": "Data Transfer Objects"
    },
    "adapter": {
        "required_class_suffix": "Adapter",
        "description": "External System Adapters"
    },
    "base": {
        "description": "Base Python Component",
        "required_imports": ["typing"]
    }
}
```

**Issues:**
- Cannot customize validation per project
- No support for custom component types
- Rules cannot be disabled

---

#### 2.2.6 Scaffold Rules (`scaffold_tool.py:117-127`)

**Purpose:** Validate component types for scaffolding

```python
VALID_COMPONENT_TYPES = [
    "worker", "tool", "dto", "adapter", 
    "manager", "interface", "resource", 
    "schema", "service", "generic"
]
```

**Issues:**
- Cannot add custom component types
- No per-project scaffold rules

---

#### 2.2.7 File Policies (`policy_engine.py`)

**Purpose:** Enforce file creation rules (scaffold vs manual)

```python
# Scaffold required (line 153-157)
BLOCKED_PATTERNS = [
    ("backend", ".py"),
    ("tests", ".py"),
    ("mcp_server", ".py"),
]

# Allowed extensions (line 170)
ALLOWED_EXTENSIONS = {".yml", ".yaml", ".json", ".toml", ".ini", ".txt", ".md", ".lock"}

# Allowed directories (line 171)
ALLOWED_DIRS = {"scripts", "proof_of_concepts", "docs", "config", ".st3"}

# Scaffold phases (line 133)
SCAFFOLD_PHASES = {"component", "tdd"}
```

**Issues:**
- Per-directory policies not flexible
- Cannot disable scaffold enforcement for certain files
- Allowed extensions not user-configurable

---

#### 2.2.8 Label Definitions (Scattered)

**Purpose:** Define GitHub label structure

**Observation:** Labels are MENTIONED but NOT DEFINED in code:
- `issue_tools.py` validates labels exist but doesn't define them
- Label patterns implied: `type:`, `priority:`, `status:`, `phase:`
- No centralized label registry
- No sync mechanism with GitHub

**Expected labels (from code references):**
```yaml
type:feature, type:bug, type:refactor, type:docs, type:hotfix
priority:critical, priority:high, priority:medium, priority:low
status:blocked, status:in-progress, status:completed
phase:discovery, phase:planning, phase:design, etc.
```

**Issues:**
- CRITICAL: No single source of truth for label structure
- Labels must be manually created in GitHub
- No validation that required labels exist
- No mechanism to sync label definitions to GitHub

---

#### 2.2.9 Magic Numbers (Throughout Codebase)

**Purpose:** Timeouts, limits, thresholds

```python
# qa_manager.py
pylint_timeout = 300  # 5 minutes
mypy_timeout = 300
pyright_timeout = 300
max_line_length = 100

# test_tools.py
default_timeout = 300
default_path = "tests/"

# doc_manager.py
max_search_results = 10
max_contribution_per_term = 3
phrase_match_boost = 1.5
context_lines_before = 2
context_lines_after = 2
snippet_length = 150

# discovery_tools.py
max_results = 10
recent_commits_limit = 10
issue_body_preview = 500
checklist_limit = 10
```

**Issues:**
- No way to tune performance vs accuracy
- Cannot adjust for slower/faster machines
- No per-project customization

---

#### 2.2.10 Regex Patterns (15+ patterns)

**Purpose:** Validation, parsing, extraction

```python
# Branch name validation
r"^[a-z0-9-]+$"

# Pylint output parsing
r"^(.+?):(\d+):(\d+): ([A-Z]\d+): (.+)$"

# Mypy output parsing
r"^(.+?):(\d+): (error|warning): (.+)$"

# Issue number extraction (3 patterns)
r"(?:feature|fix|refactor|docs)/(\d+)-"
r"issue-(\d+)"
r"#(\d+)"

# Link parsing
r"\[([^\]]+)\]\(([^)]+)\)"

# Heading parsing
r"^(#{1,6})\s+(.+)$"

# Class name validation (dynamic)
rf"class \w+{suffix}\b"

# PascalCase validation
r'^[A-Z][a-zA-Z0-9]*$'
```

**Issues:**
- Patterns buried in code
- Cannot customize without code changes
- No testing infrastructure for pattern validation

---

### 2.3 Configuration Dependencies

**Findings:**

```
PHASE_TEMPLATES (project_manager.py)
Ôö£ÔöÇÔöÇ ProjectManager.initialize_project() ÔåÆ reads templates
Ôö£ÔöÇÔöÇ InitializeProjectTool ÔåÆ validates issue_type keys
ÔööÔöÇÔöÇ PhaseStateEngine ÔåÆ validates phase names (indirect)

RULES (template_validator.py)
Ôö£ÔöÇÔöÇ TemplateValidator.validate() ÔåÆ applies rules
Ôö£ÔöÇÔöÇ SafeEditTool ÔåÆ registers validators
ÔööÔöÇÔöÇ validate_template tool ÔåÆ exposes validation

Quality Gates (qa_manager.py)
Ôö£ÔöÇÔöÇ run_quality_gates tool ÔåÆ executes gates
ÔööÔöÇÔöÇ PolicyEngine ÔåÆ enforces gate results

Git Conventions (git_manager.py + policy_engine.py)
Ôö£ÔöÇÔöÇ create_feature_branch tool ÔåÆ validates branch types
Ôö£ÔöÇÔöÇ git_add_or_commit tool ÔåÆ validates TDD phases
ÔööÔöÇÔöÇ PolicyEngine ÔåÆ enforces commit prefixes

Labels (issue_tools.py + GitHub API)
Ôö£ÔöÇÔöÇ create_issue tool ÔåÆ applies labels
Ôö£ÔöÇÔöÇ add_labels tool ÔåÆ validates label format
ÔööÔöÇÔöÇ GitHub ÔåÆ stores actual labels (NOT synced)
```

---

## 3. Technology Research

### 3.1 Configuration Format Options

**Research Question:** What formats are suitable for declarative configuration?

#### Option A: YAML
**Examples in wild:**
- Kubernetes (deployment configs)
- Ansible (playbooks)
- Docker Compose
- GitHub Actions

**Pros:**
- Ô£à Human-readable
- Ô£à Supports comments
- Ô£à Widely adopted
- Ô£à Python: `pyyaml` library (mature)

**Cons:**
- ÔÜá´©Å Indentation-sensitive (can cause errors)
- ÔÜá´©Å No schema enforcement without external validation

**Python Support:**
```python
import yaml
config = yaml.safe_load(Path("config.yaml").read_text())
```

#### Option B: TOML
**Examples in wild:**
- Python `pyproject.toml` (PEP 518)
- Rust `Cargo.toml`
- Hugo static site generator

**Pros:**
- Ô£à Human-readable
- Ô£à Less indentation issues than YAML
- Ô£à Python: `tomli` (standard in 3.11+)

**Cons:**
- ÔÜá´©Å Less widely adopted than YAML
- ÔÜá´©Å Verbose for nested structures

**Python Support:**
```python
import tomli
config = tomli.loads(Path("config.toml").read_text())
```

#### Option C: JSON
**Examples in wild:**
- VSCode settings
- NPM package.json
- REST APIs

**Pros:**
- Ô£à Strict syntax (catches errors)
- Ô£à JSON Schema validation
- Ô£à Python: built-in `json` module

**Cons:**
- ÔØî No comments
- ÔØî Less human-readable (quotes, commas)
- ÔØî No trailing commas allowed

#### Option D: Python Files (settings.py)
**Examples in wild:**
- Django settings
- Flask config

**Pros:**
- Ô£à Full Python language features
- Ô£à Can compute values dynamically

**Cons:**
- ÔØî Still code, not config
- ÔØî Requires Python knowledge
- ÔØî Security risk (arbitrary code execution)

#### Option E: Database
**Examples in wild:**
- WordPress (options table)
- CMS systems

**Pros:**
- Ô£à Can change without file edits
- Ô£à Audit trail possible

**Cons:**
- ÔØî Overkill for static config
- ÔØî Adds database dependency
- ÔØî Harder to version control

### 3.2 Schema Validation Options

**Research Question:** How to ensure config file correctness?

#### Option A: Pydantic (Python)
**Used by:**
- FastAPI
- LangChain
- Prefect

**Example:**
```python
from pydantic import BaseModel

class WorkflowConfig(BaseModel):
    version: str
    issue_types: dict[str, IssueTypeConfig]
    
    @field_validator("version")
    def check_version(cls, v):
        if not v.startswith("1."):
            raise ValueError("Unsupported version")
        return v
```

**Pros:**
- Ô£à Type safety
- Ô£à Runtime validation
- Ô£à Clear error messages
- Ô£à Auto-generated JSON Schema

**Cons:**
- ÔÜá´©Å Python-specific
- ÔÜá´©Å Validation at runtime (not pre-deployment)

#### Option B: JSON Schema
**Used by:**
- VSCode (settings.json validation)
- OpenAPI
- AsyncAPI

**Example:**
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "issue_types": {
      "type": "object"
    }
  },
  "required": ["issue_types"]
}
```

**Pros:**
- Ô£à Language-agnostic
- Ô£à Editor support (autocomplete, validation)
- Ô£à Pre-deployment validation possible

**Cons:**
- ÔÜá´©Å Verbose
- ÔÜá´©Å Less intuitive than Pydantic

#### Option C: Cerberus
**Used by:**
- Eve REST framework

**Pros:**
- Ô£à Lightweight
- Ô£à Python dict-based rules

**Cons:**
- ÔÜá´©Å Less popular than Pydantic
- ÔÜá´©Å Manual schema definition

### 3.3 Best Practices Research

**Sources:**
- "The Twelve-Factor App" (config in environment)
- "Release It!" by Michael Nygard (externalized config)
- Python Packaging User Guide (pyproject.toml)

**Key Principles Found:**

1. **Config Over Code**
   - Business rules should be data, not logic
   - Changes shouldn't require code deployment

2. **Fail Fast**
   - Validate config at startup
   - Don't discover errors at runtime

3. **Sensible Defaults**
   - System should work out-of-box
   - Advanced users can override

4. **Version Config**
   - Track config changes in git
   - Rollback capability

5. **Environment-Specific**
   - Dev/test/prod configs
   - Not applicable here (workflow is universal)

---

## 4. Alternative Approaches

### Alternative A: Keep Hardcoded + Override API
**Example:**
```python
PHASE_TEMPLATES = {...}  # Defaults

def register_custom_workflow(issue_type, phases):
    PHASE_TEMPLATES[issue_type] = phases
```

**Pros:** Backward compatible, simple

**Cons:** Doesn't solve config-over-code, no persistence

### Alternative B: Hybrid (Defaults + Optional Overrides)
**Example:**
```python
# Built-in defaults
DEFAULT_TEMPLATES = {...}

# Load overrides if present
if Path("config/workflows.yaml").exists():
    custom = yaml.safe_load(...)
    PHASE_TEMPLATES = {**DEFAULT_TEMPLATES, **custom}
```

**Pros:** Gradual migration, fallback to defaults

**Cons:** Two sources of truth, migration complexity

### Alternative C: Pure Config (No Defaults in Code)
**Example:**
```python
# No hardcoded templates
config = yaml.safe_load(Path("config/workflows.yaml").read_text())
PHASE_TEMPLATES = config["issue_types"]
```

**Pros:** Clean separation, single source of truth

**Cons:** Requires config file to exist (no defaults)

---

## 5. Related Technologies

### 5.1 Config Management Tools

**Consul / etcd:**
- Distributed key-value stores
- **Assessment:** Overkill for MCP (single-machine deployment)

**Ansible:**
- Configuration management for servers
- **Assessment:** Not applicable (no remote machines)

**Python-dotenv:**
- Environment variable loading
- **Assessment:** Too simple for structured data

### 5.2 Existing MCP Config

**Current:** `mcp_config.yaml` exists!

**Location:** `d:\dev\SimpleTraderV3\mcp_config.yaml`

**Content:** Server settings, GitHub repo, logging levels

**Observation:** Already using YAML, already have PyYAML dependency

**Implication:** Extending existing YAML approach is natural fit

---

## 6. Comparative Analysis

| Aspect | YAML + Pydantic | TOML + Pydantic | JSON Schema | Python files |
|--------|----------------|-----------------|-------------|--------------|
| Human-readable | Ô¡ÉÔ¡ÉÔ¡ÉÔ¡ÉÔ¡É | Ô¡ÉÔ¡ÉÔ¡ÉÔ¡É | Ô¡ÉÔ¡ÉÔ¡É | Ô¡ÉÔ¡ÉÔ¡ÉÔ¡É |
| Type safety | Ô¡ÉÔ¡ÉÔ¡ÉÔ¡ÉÔ¡É | Ô¡ÉÔ¡ÉÔ¡ÉÔ¡ÉÔ¡É | Ô¡ÉÔ¡ÉÔ¡ÉÔ¡É | Ô¡ÉÔ¡ÉÔ¡É |
| Validation | Ô¡ÉÔ¡ÉÔ¡ÉÔ¡ÉÔ¡É | Ô¡ÉÔ¡ÉÔ¡ÉÔ¡ÉÔ¡É | Ô¡ÉÔ¡ÉÔ¡ÉÔ¡ÉÔ¡É | Ô¡ÉÔ¡É |
| Ecosystem fit | Ô¡ÉÔ¡ÉÔ¡ÉÔ¡ÉÔ¡É | Ô¡ÉÔ¡ÉÔ¡É | Ô¡ÉÔ¡ÉÔ¡É | Ô¡ÉÔ¡ÉÔ¡ÉÔ¡É |
| Learning curve | Ô¡ÉÔ¡ÉÔ¡ÉÔ¡É | Ô¡ÉÔ¡ÉÔ¡ÉÔ¡É | Ô¡ÉÔ¡ÉÔ¡É | Ô¡ÉÔ¡ÉÔ¡ÉÔ¡ÉÔ¡É |
| Config-over-code | Ô¡ÉÔ¡ÉÔ¡ÉÔ¡ÉÔ¡É | Ô¡ÉÔ¡ÉÔ¡ÉÔ¡ÉÔ¡É | Ô¡ÉÔ¡ÉÔ¡ÉÔ¡ÉÔ¡É | Ô¡É |

---

## 7. External References

**Documentation Reviewed:**
- PyYAML docs: https://pyyaml.org/wiki/PyYAMLDocumentation
- Pydantic docs: https://docs.pydantic.dev/
- Python TOML: https://docs.python.org/3/library/tomllib.html
- JSON Schema: https://json-schema.org/

**Similar Projects:**
- FastAPI: Uses Pydantic for config validation
- Prefect: YAML workflows with Python validation
- Airflow: Python DAG files (rejected approach)

---

## 8. Research Findings

### Key Observations

1. **MCP already uses YAML** for `mcp_config.yaml`
2. **PyYAML is already a dependency**
3. **YAML is industry standard** for config files
4. **Pydantic provides type safety** and validation
5. **No backward compatibility needed** (no enforced projects yet)

### Technology Recommendations

**Primary:** YAML + Pydantic
- Natural fit with existing codebase
- Best balance of readability and safety
- Strong Python ecosystem support

**Secondary:** TOML + Pydantic
- If YAML indentation becomes problematic
- More explicit syntax

**Not Recommended:**
- JSON (not human-friendly enough)
- Python files (violates config-over-code)
- Database (overkill)

---

## 9. Open Questions for Planning Phase

1. Should config be split into multiple files (`workflows.yaml`, `labels.yaml`, `quality.yaml`) or monolithic?
2. Should there be environment-specific configs (dev/prod)?
3. How to handle config migrations (v1.0 ÔåÆ v2.0)?
4. Should validation happen at import time or on first use?
5. What happens if config file is missing/invalid? (fail fast vs fallback)

---

## 10. Research Conclusion

**Status:** Ô£à Research complete

**Primary Finding:** YAML + Pydantic is the optimal approach for MCP config migration.

**Rationale:**
- Aligns with existing MCP architecture
- Industry best practice
- Strong validation capabilities
- Human-friendly format

**Ready for:** Planning phase to design concrete YAML schema and Pydantic models

**Research artifacts preserved for planning:**
- Hardcoded config inventory (300 lines across 8 files)
- Technology comparison matrix
- Alternative approaches analysis
- Best practices compilation
