<!-- docs\development\issue251\design.md -->
<!-- template=design version=5827e841 created=2026-02-22T20:54Z updated= -->
# run_quality_gates Refactor — Scope-Driven Architecture, Config-Driven Parsing, ViolationDTO

**Status:** DRAFT  
**Version:** 1.0  
**Last Updated:** 2026-02-22

---

## Purpose

Define finalized interface contracts for all architectural changes in issue #251 so that TDD implementation can proceed without design ambiguity.

## Scope

**In Scope:**
`quality_config.py` (new types), `qa_manager.py` (parser dispatch, scope resolution, state machine), `quality_tools.py` (scope API), `.st3/quality.yaml` (gate config migration), `.st3/state.json` (quality_gates section), `test_tools.py` (content order)

**Out of Scope:**
CI/CD pipeline, non-Python gates, pyproject.toml migration, frontend, `QUALITY_GATES.md` (documentation phase)

## Prerequisites

1. `research.md` v1.6 complete — all 15 findings documented
2. `planning.md` v1.2 complete — 32 TDD cycles defined with exit criteria
3. All 7 design decisions locked (no backward compatibility)

---

## 1. Context & Requirements

### 1.1. Problem Statement

`run_quality_gates` has 15 identified bugs and architectural problems across five clusters:
1. Gate 5/6 invoke system pytest, causing exit code 4 failures on every run
2. Output contains double JSON and no human-readable summary line
3. Execution is bifurcated on a `files=[]` / `files=[...]` mode switch instead of a declarative scope
4. All parser logic is tool-specific and hardcoded in Python rather than declared in config
5. No baseline state machine — every run re-scans the full project regardless of what changed

### 1.2. Requirements

**Functional:**
- [ ] Remove Gate 5 (pytest) and Gate 6 (coverage) from active quality gates — test execution belongs exclusively to `run_tests`
- [ ] Replace `files: list[str]` API with `scope: Literal["auto", "branch", "project"] = "auto"`
- [ ] Introduce `ViolationDTO` as the uniform violation contract returned by every gate parser
- [ ] Introduce `JsonViolationsParsing` and `TextViolationsParsing` as the only two parsing strategy types; eliminate all tool-name-based dispatcher logic
- [ ] Implement baseline state machine: `baseline_sha` + `failed_files` persisted in `state.json` under `quality_gates` section
- [ ] `scope=auto` returns union of git-diff files (`baseline_sha..HEAD`) and persisted `failed_files`
- [ ] `scope=auto` with no baseline falls back to `scope=project`
- [ ] `scope=branch` uses `git diff parent..HEAD`
- [ ] `scope=project` globs from `quality.yaml` `project_scope.include_globs`
- [ ] `ToolResult` must contain exactly two content items in fixed order: item 0 text summary, item 1 JSON payload
- [ ] `run_tests` content order must be inverted to match the same contract (separate cycle)

**Non-Functional:**
- [ ] Zero tool-specific methods in `QAManager` after refactor — all dispatch driven by `parsing_strategy` config field
- [ ] No backward compatibility: `files` parameter is removed without shim or deprecation warning
- [ ] Existing passing tests must remain green after all deletion cycles
- [ ] `state.json` `quality_gates` section must be isolated per-branch and must not overwrite unrelated keys
- [ ] Git subprocess calls must be guarded against errors and empty output

### 1.3. Constraints

- No backward compatibility for removed `files` API
- No tool-name comparisons may remain in `QAManager` parser dispatch after refactor
- Git subprocess calls must not block without a timeout guard
- `state.json` writes must be isolated to the `quality_gates` key — no other keys may be mutated

---

## 2. Design Options

### 2.1. Option A — Keep tool-specific parsers, fix individual bugs

Patch the identified bugs in place: fix the pytest gate entries, add a summary line, fix the JSON duplication. Leave the existing `_parse_ruff_json`, `_parse_json_field_issues` methods and the `files` API in place.

**Pros:**
- Minimal blast radius per bug fix
- No schema changes required

**Cons:**
- Does not address the root cause: parser logic stays coupled to tool names
- Adding a new gate still requires a Python method change
- Dead code clusters remain
- Mode bifurcation remains; no scope resolution

---

### 2.2. Option B — Config-driven strategies with ViolationDTO ✅ CHOSEN

Introduce two parsing strategy types in Pydantic: `json_violations` and `text_violations`. Each gate declares its strategy in `quality.yaml`. `QAManager` dispatches generically on `parsing_strategy` and returns `list[ViolationDTO]`. Scope resolution is decoupled into `_resolve_scope()`. Baseline state machine is added to `state.json`.

**Pros:**
- Adding a new gate requires only a YAML entry, no Python change (OCP)
- Zero tool-specific code in `QAManager` after refactor
- `ViolationDTO` gives uniform contract to all downstream consumers
- Scope and baseline features are cleanly layered on top

**Cons:**
- Larger initial refactor surface (32 cycles)
- Requires careful sequencing (contracts before parsers, state machine before auto-scope)

---

## 3. Chosen Design

**Option B — Config-driven strategies with ViolationDTO**

**Rationale:** All 15 research findings share one root cause: behaviour is encoded in Python methods tied to tool names rather than declared in config. The chosen design makes the config the single authority for parsing shape, scope discovery, and gate activation. `QAManager` becomes a generic executor: it reads a strategy, calls one of two parsing functions, and updates state. Adding a new gate or changing its output format requires only a YAML edit, not a Python change. This satisfies OCP and eliminates the four dead-code clusters identified in research.

### 3.1. Key Design Decisions

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | Gate 5/6 removed from `active_gates` entirely | Pytest belongs in `run_tests`; quality gates are for static analysis only |
| 2 | `files` → `scope` enum, no backward compat | Declarative scope is the correct abstraction; migration shim would perpetuate the mode bifurcation |
| 3 | Global baseline (all-green advances SHA) | Branch-level baseline minimizes re-scan scope without requiring per-file timestamps |
| 4 | Re-run = `diff(baseline..HEAD)` ∪ `failed_files` | Guarantees no regressions slip through while keeping scan surface minimal |
| 5 | `summary_line` as first content item | Callers get actionable status without parsing JSON |
| 6 | `json_violations` + `text_violations` only | Two shapes cover all real gate outputs; a third shape would require a third parser — use config, not code |
| 7 | `ViolationDTO` uniform contract | Downstream consumers need one type, not per-gate dicts |

---

## 4. Interface Contracts

### 4.1. ViolationDTO

**Location:** `mcp_server/config/quality_config.py`

```python
@dataclass
class ViolationDTO:
    file: str
    message: str
    line: int | None = None
    col: int | None = None
    rule: str | None = None
    fixable: bool = False
    severity: str = "error"
```

All gate parsers return `list[ViolationDTO]`. No parser may return a plain dict or tool-specific type.

---

### 4.2. Parsing Strategy Models

**Location:** `mcp_server/config/quality_config.py`

**JsonViolationsParsing** — for gates that emit JSON (ruff, pyright):
```python
class JsonViolationsParsing(BaseModel):
    field_map: dict[str, str]           # violation key → ViolationDTO field name
    violations_path: str | None = None  # dotted path to array (e.g. "generalDiagnostics")
    line_offset: int = 0                # applied to mapped line value (pyright is 0-based)
    fixable_when: str | None = None     # field name whose truthiness sets fixable=True
```

**TextViolationsParsing** — for gates that emit text (mypy, ruff format):
```python
class TextViolationsParsing(BaseModel):
    pattern: str                        # regex with named capture groups
    defaults: dict[str, str] = {}       # static or {field}-interpolated fallback values
    severity_default: str = "error"

    # Validator: every {name} in defaults must be a named group in pattern or "file"
```

**Removed:** `JsonFieldParsing`, `TextRegexParsing`, `produces_json` flag.

---

### 4.3. QualityConfig Changes

**Location:** `mcp_server/config/quality_config.py`

```python
class QualityConfig(BaseModel):
    # existing fields...
    project_scope: GateScope | None = None   # NEW: globs for scope=project
```

```python
class CapabilitiesMetadata(BaseModel):
    file_types: list[str] = []
    parsing_strategy: Literal["json_violations", "text_violations"] | None = None
    json_violations: JsonViolationsParsing | None = None
    text_violations: TextViolationsParsing | None = None
    # REMOVED: produces_json, json_field, text_regex
```

---

### 4.4. quality.yaml Schema

```yaml
# Top-level addition
project_scope:
  include_globs:
    - "mcp_server/**/*.py"
    - "tests/mcp_server/**/*.py"

# Gate config structure (per gate)
gates:
  gate1_ruff:
    capabilities:
      parsing_strategy: "json_violations"
      json_violations:
        field_map:
          file: "filename"
          line: "row"
          col: "col"
          rule: "code"
          message: "message"
        fixable_when: "fix"

  gate4_mypy:
    capabilities:
      parsing_strategy: "text_violations"
      text_violations:
        pattern: '(?P<file>[^:]+):(?P<line>\d+): (?P<severity>\w+): (?P<message>.+)'
        defaults: {}

  gate0_ruff_format:
    capabilities:
      parsing_strategy: "text_violations"
      text_violations:
        pattern: '(?P<file>.+)'
        defaults:
          message: "File requires formatting. Fix: python -m ruff format {file}"

  gate4b_pyright:
    capabilities:
      parsing_strategy: "json_violations"
      json_violations:
        violations_path: "generalDiagnostics"
        line_offset: 1
        field_map:
          file: "file"
          line: "range.start.line"
          rule: "rule"
          message: "message"

# Removed from active_gates: gate5_tests, gate6_coverage
```

---

### 4.5. QAManager Dispatch Contract

**Location:** `mcp_server/managers/qa_manager.py`

```python
# execute_gate — after refactor
match gate.capabilities.parsing_strategy:
    case "json_violations":
        raw = json.loads(result.stdout)
        violations = self._parse_json_violations(raw, gate.capabilities.json_violations)
    case "text_violations":
        violations = self._parse_text_violations(result.stdout, gate.capabilities.text_violations)
    case _:
        violations = []
```

No `if gate.name == ...` or `if gate.id == ...` comparisons anywhere in dispatch.

**Removed methods:** `_parse_ruff_json()`, `_parse_json_field_issues()`, `_filter_files()`, `_is_pytest_gate()`, `_maybe_enable_pytest_json_report()`, `_get_skip_reason()`.

**Added methods:** `_parse_json_violations()`, `_parse_text_violations()`, `_extract_path()`, `_files_for_gate()`, `_resolve_scope()`, `_advance_baseline_if_all_pass()`, `_accumulate_failures()`, `_format_summary_line()`, `_build_compact_result()`.

---

### 4.6. Scope Resolution Contract

**Location:** `mcp_server/managers/qa_manager.py`

| scope | Resolution |
|-------|------------|
| `"project"` | Expand `project_scope.include_globs` from config against workspace root |
| `"branch"` | `git diff --name-only <parent>..HEAD` |
| `"auto"` (baseline present) | `set(git diff --name-only baseline_sha..HEAD)` ∪ `set(failed_files)` |
| `"auto"` (no baseline) | Fallback to `"project"` |
| `"auto"` (empty union) | Return `[]` immediately — nothing to check |

---

### 4.7. Baseline State Machine Contract

**Location:** `.st3/state.json` key path: `branches.<branch>.quality_gates`

```json
{
  "branches": {
    "refactor/251-refactor-run-quality-gates": {
      "quality_gates": {
        "baseline_sha": "abc123",
        "failed_files": ["mcp_server/managers/qa_manager.py"]
      }
    }
  }
}
```

**Transitions:**
- All gates pass → `baseline_sha = HEAD`, `failed_files = []`
- Any gate fails → `failed_files = old_failed_files ∪ newly_failed_files` (baseline_sha unchanged)
- `quality_gates` key is absent → treated as no baseline (auto falls back to project)

**Invariant:** Only the `quality_gates` sub-key is written; no other branch state is modified.

---

### 4.8. Output Contract (ToolResult)

Both `run_quality_gates` and `run_tests` must return:
```
content[0] = {"type": "text", "text": <summary_line>}
content[1] = {"type": "json", "json": <payload>}
```

Exactly 2 items, in this order, always.

**summary_line format:**
- Pass:   `"✅ Quality gates: N/N passed (0 violations)"`
- Fail:   `"❌ Quality gates: N/M passed — V violations in gate_id[, gate_id]"`
- Skip+pass: `"⚠️ Quality gates: N/N active (S skipped)"`

**Compact payload schema:**
```json
{
  "gates": [
    {
      "id": "gate1_ruff",
      "passed": true,
      "skipped": false,
      "violations": []
    }
  ]
}
```

No `stdout`, `stderr`, or `raw_output` fields in payload.

**Contract change for run_tests:** Current implementation returns `[json, text]`. C29 inverts this to `[text, json]` to match the above contract. Callers depending on `content[1]` for summary must be updated.

---

## Related Documentation

- [research.md](research.md)
- [planning.md](planning.md)

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-22 | Agent | Initial design — 8 interface contracts, 2 design options, decision rationale |
