<!-- docs/reference/mcp/tools/quality.md -->
<!-- template=reference version=064954ea created=2026-02-08T12:00:00+01:00 updated=2026-03-01 -->
# Quality & Validation Tools

**Status:** DEFINITIVE  
**Version:** 3.0  
**Last Updated:** 2026-03-01

**Source:** [mcp_server/tools/quality_tools.py](../../../../mcp_server/tools/quality_tools.py), [mcp_server/managers/qa_manager.py](../../../../mcp_server/managers/qa_manager.py), [mcp_server/tools/test_tools.py](../../../../mcp_server/tools/test_tools.py), [mcp_server/tools/validation_tools.py](../../../../mcp_server/tools/validation_tools.py), [mcp_server/tools/template_validation_tool.py](../../../../mcp_server/tools/template_validation_tool.py)

---

## Purpose

Contract-first reference for quality and validation tool usage.

This page is optimized for agents: exact input contracts, copy/paste call patterns, and failure-safe execution order.

---

## Tool Set

| Tool | Purpose | Contract Anchor |
|------|---------|-----------------|
| `run_quality_gates` | Config-driven quality gates over explicit scope | `RunQualityGatesInput` in `quality_tools.py` |
| `run_tests` | Pytest execution and failure reporting | `RunTestsInput` in `test_tools.py` |
| `validate_architecture` | Architecture-level checks by scope | `ValidationInput` in `validation_tools.py` |
| `validate_dto` | DTO-specific validation | `ValidateDTOInput` in `validation_tools.py` |
| `validate_template` | Template conformance checks | `TemplateValidationInput` in `template_validation_tool.py` |

---

## run_quality_gates (authoritative contract)

### Input

| Field | Type | Required | Allowed values | Rule |
|------|------|----------|----------------|------|
| `scope` | `string` | No | `auto`, `branch`, `project`, `files` | Default is `auto` |
| `files` | `list[string] \| null` | Conditional | Any workspace-relative paths | Required and non-empty **only** when `scope="files"`; must be omitted otherwise |

### Validation rules

- `scope="files"` and `files` is missing or `[]` → validation error.
- `scope!="files"` and `files` is provided → validation error.

### Scope semantics

| Scope | Target resolution |
|------|--------------------|
| `auto` | `git diff baseline_sha..HEAD` union persisted `failed_files`; if no baseline → project scope fallback |
| `branch` | `git diff parent_branch..HEAD` (`parent_branch` from `.st3/state.json`, fallback `main`) |
| `project` | `.st3/quality.yaml` `project_scope.include_globs` |
| `files` | Explicit user list; directories expanded to `.py` files |

### Output contract

`run_quality_gates` returns `ToolResult.content` with exactly two items:

1. `content[0]`: `{"type":"text","text":"...summary line..."}`
2. `content[1]`: `{"type":"json","json": {"overall_pass": bool, "gates": [...]}}`

Compact JSON root keys are:
- `overall_pass`
- `gates`

### Baseline lifecycle behavior

Baseline mutation is allowed only for effective `scope="auto"` runs.

- Auto all-pass: advance `baseline_sha` to `HEAD`, clear `failed_files`.
- Auto fail: update `failed_files` to failing subset.
- Non-auto (`files`, `branch`, `project`): do not mutate auto lifecycle fields.

---

## Agent Call Patterns (copy/paste)

### Minimal changed-files check during TDD refactor

```json
{"scope": "files", "files": ["mcp_server/managers/qa_manager.py", "tests/mcp_server/unit/managers/test_baseline_advance.py"]}
```

### Branch-wide quality gate check

```json
{"scope": "branch"}
```

### Baseline-aware rerun behavior

```json
{"scope": "auto"}
```

### Project-wide sweep

```json
{"scope": "project"}
```

---

## Execution order for reliable agent runs

1. Run targeted tests via `run_tests(path=...)`.
2. Run `run_quality_gates(scope="files", files=[...changed files...])`.
3. Before acceptance closure, run switch-path checks (`auto↔files`, `branch↔files`, `project→auto`).
4. Use `restart_server`, then wait 3 seconds, before live behavior validation after server/tool code changes.

---

## Common mistakes to avoid

- Do **not** call `run_quality_gates(files=[...])` without `scope="files"`.
- Do **not** use `scope="project"` with a `files` payload.
- Do **not** treat `run_quality_gates` as test runner replacement; use `run_tests` for pytest execution.
- Do **not** infer compact payload from legacy `json_data` examples; use `content[0]/content[1]` contract.

---

## Quick checks for documentation consumers

Use this checklist when writing prompts/instructions for agents:

- [ ] `run_quality_gates` examples include explicit `scope`
- [ ] `files` appears only with `scope="files"`
- [ ] No references to Gate 5/6 test/coverage under quality gates
- [ ] Output examples show `content[0]=text` and `content[1]=json`
- [ ] Lifecycle notes mention auto-only state mutation

---

## Related

- [docs/reference/mcp/tools/README.md](README.md)
- [docs/reference/mcp/MCP_TOOLS.md](../MCP_TOOLS.md)
- [docs/development/issue251/live-validation-plan-v2.md](../../development/issue251/live-validation-plan-v2.md)
- [docs/development/issue251/live-validation-blocked-scenarios-20260301.md](../../development/issue251/live-validation-blocked-scenarios-20260301.md)
