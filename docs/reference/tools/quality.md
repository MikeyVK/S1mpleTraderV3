<!-- docs/reference/tools/quality.md -->
<!-- template=reference version=064954ea created=2026-02-08T12:00:00+01:00 updated=2026-08-22 -->
# Quality and Validation Tools

**Status:** DEFINITIVE  
**Version:** 5.1  
**Last Updated:** 2026-08-22

**Source:** [quality_tools.py](../../../mcp_server/tools/quality_tools.py),
[test_tools.py](../../../mcp_server/tools/test_tools.py), and
[template_validation_tool.py](../../../mcp_server/tools/template_validation_tool.py)

---

## Purpose

Contract-first reference for running configured quality gates, pytest, fixers, and
artifact-template validation. These tools return bounded decision-oriented text while
preserving complete structured results and verbose diagnostics in the MCP Resource
cache.

## Tool Set

| Tool | Purpose | Output DTO |
|---|---|---|
| `run_quality_gates` | Run config-driven quality gates over an explicit scope | `RunQualityGatesOutput` |
| `run_tests` | Run pytest and report structured counts/failures | `RunTestsOutput` |
| `auto_fix` | Execute configured fixer commands | `AutoFixOutput` |
| `validate_template` | Validate one file against an artifact template | `TemplateValidationOutput` |

Every response is limited by the global 8,000 UTF-8-byte presentation ceiling and
contains the cache URI when publication succeeds.

## run_quality_gates

### Input

| Field | Type | Required | Rule |
|---|---|---|---|
| `scope` | `auto` \| `branch` \| `project` \| `files` | No | Defaults to `auto` |
| `files` | `list[string]` \| `null` | Conditional | Required and non-empty only for `scope="files"`; omit otherwise |
| `verbose` | `bool` | No | Captures failing-gate stdout/stderr in cached `details`; defaults to `false` |

### Scope Semantics

| Scope | Target resolution |
|---|---|
| `auto` | Changed files plus persisted failed files; falls back to project scope when no baseline exists |
| `branch` | Files changed between the branch parent and `HEAD` |
| `project` | Files matching configured `project_scope.include_globs` |
| `files` | Explicit paths; directories expand to supported files |

Only effective `auto` runs mutate the quality baseline lifecycle. An all-pass run advances
the baseline and clears failed files; a failed run persists the failing subset. Other
scopes do not mutate those lifecycle fields.

### Presented Output

The text always reports execution completion, effective scope, file count, and
`overall_pass`. It renders at most ten gate records with name, status, passed flag, and
score. Beneath each gate it renders at most ten ordered findings with location, code,
message, severity, and fixability. Missing optional values use the global `-`
placeholder. Generic omission lines report additional gates or findings.

The wording is outcome-neutral: callers must evaluate `overall_pass`, gate records, and
findings rather than infer success from the heading. The final response remains subject
to the universal 8,000 UTF-8-byte ceiling.

The cached `RunQualityGatesOutput` contains:

- `overall_pass: bool`;
- `scope: string`;
- `file_count: int`;
- `gates: list[GateResultDTO]`;
- the common `success`, `error_message`, and `post_tool_instruction` envelope.

Each `GateResultDTO` contains `name`, `passed`, `status`, `score`, `details`,
and `findings: list[GateFindingDTO]`. Existing fields remain compatible and
`findings` defaults to an independent empty list.

### Structured Finding Contract

`GateFindingDTO` is frozen, serializable, and rejects extra fields:

| Field | Type | Meaning |
|---|---|---|
| `gate` | `string` | Required self-identifying gate name |
| `message` | `string` | Required actionable diagnostic or operational failure |
| `file` | `string` \| `null` | Optional affected path |
| `line` | `int` \| `null` | Optional normalized source line when supplied by the checker |
| `column` | `int` \| `null` | Optional source column |
| `code` | `string` \| `null` | Optional checker rule or diagnostic code |
| `severity` | `string` \| `null` | Optional normalized severity |
| `fixable` | `bool` | Whether the source marked the finding automatically fixable; defaults to `false` |
| `details` | `string` \| `null` | Optional cache-only diagnostic evidence |

`QAManager` and `ViolationParser` remain normalization authorities.
`RunQualityGatesTool` only maps their structured records into the public DTO:
`col -> column`, `rule -> code`, and the enclosing gate name into `gate`. It does
not parse messages or raw process output, infer fields, sort, or deduplicate. Missing
required `message` data fails explicitly instead of receiving fabricated text.

Gate order and finding order match the manager result. The configured
`max_items=10` applies independently to the gate collection and to each nested finding
collection. Inline omission never mutates the DTO: every finding, finding `details`,
and gate `details` remains in the cached resource. With `verbose=true`, gate
`details` can additionally contain raw checker stdout/stderr; neither gate nor finding
`details` is rendered inline.

### Examples

```json
{"scope": "files", "files": ["mcp_server/presenters/text_presenter.py"]}
```

```json
{"scope": "branch", "verbose": false}
```

## run_tests

### Input

| Field | Type | Required | Default | Rule |
|---|---|---|---|---|
| `path` | `string` \| `null` | Conditional | `null` | One or more space-separated pytest paths; mutually exclusive with `scope` |
| `scope` | `"full"` \| `null` | Conditional | `null` | Selects the entire workspace suite; mutually exclusive with `path` |
| `markers` | `string` \| `null` | No | `null` | Pytest `-m` expression |
| `last_failed_only` | `bool` | No | `false` | Use pytest's last-failed selection |
| `timeout` | `int` | No | `300` | Hard timeout in seconds |
| `coverage` | `bool` | No | `false` | Enable branch coverage and enforce the configured threshold |
| `collect_only` | `bool` | No | `false` | Collect tests without executing them |
| `verbose` | `bool` | No | `false` | Allowed only for path-based execution targeting specific files |

Exactly one of `path` or `scope="full"` is required. `verbose=true` is rejected for
directories and full-suite execution.

### Presented Output

The text reports exit code, passed/failed/skipped/error counts, numeric duration, and
coverage when available. It renders at most five structured failures with test ID,
location, concise reason, and collection-error flag. Tracebacks and stderr are never
inlined by the collection template.

The cached `RunTestsOutput` contains:

- `exit_code: int`;
- `passed_count`, `failed_count`, `skipped_count`, and `errors_count`;
- `duration_seconds: float | null`;
- `coverage_pct: float | null`;
- `failures: list[TestFailureDTO]`, including cache-only `traceback`;
- `lf_cache_was_empty: bool`;
- `stderr: string`;
- the common output envelope.

There is no `summary_line` field. Counts and duration are structured data, and the
presenter owns their wording.

### Examples

```json
{"path": "tests/mcp_server/unit/presenters/test_text_budget_limiter.py"}
```

```json
{"scope": "full", "timeout": 900}
```

```json
{"path": "tests/mcp_server/unit/presenters/test_text_presenter_composition.py", "verbose": true}
```

## auto_fix

### Input

`auto_fix` uses the same `scope` and conditional `files` contract as
`run_quality_gates`; it has no `verbose` parameter.

### Presented and Cached Output

The text reports executed-gate and modified-file counts and lists up to 20 gate names and
modified paths. The cached `AutoFixOutput` contains `gates_executed`,
`gates_executed_count`, `modified_files`, and `modified_files_count`. There is no
preformatted duplicate modified-files field.

```json
{"scope": "auto"}
```

## validate_template

### Input

| Field | Type | Required | Description |
|---|---|---|---|
| `path` | `string` | Yes | Absolute path to the file |
| `template_type` | `worker` \| `tool` \| `dto` \| `adapter` \| `base` | Yes | Supported code-template family to validate against |

### Presented and Cached Output

The text reports `passed` and `errors_count`, followed by at most ten errors with severity
and message. The complete `errors: list[TemplateValidationErrorDTO]` remains in the cached
`TemplateValidationOutput`.

`validate_template` does not validate documentation templates. Documentation structure
and links require documentation-specific checks.

## Agent Call Guidance

- Use the narrowest scope that proves the current change; phase contracts own when
  branch- or workspace-wide checks run.
- Do not pass `files` unless `scope="files"`.
- Do not use `path` and `scope` together for `run_tests`.
- Use the presented response for routine counts, bounded failures, gate summaries, and
  actionable findings.
- Read the cached resource for complete collections, tracebacks, stderr, raw checker
  output, or other cache-only fields.
- Do not parse presented Markdown into structured evidence.
- Do not treat quality gates as a replacement for tests.
- When `last_failed_only=true`, inspect `lf_cache_was_empty` in the cache if selection
  behavior matters.

## Related Documentation

- [MCP tools navigation](README.md)
- [Presentation architecture](../presentation_architecture.md)
- [Quality gate standards](../../coding_standards/QUALITY_GATES.md)

---

## Version History

| Version | Date | Author | Changes |
|---|---|---|---|
| 5.1 | 2026-08-22 | Agent | Document structured quality-gate findings, nested bounds, ordering, and cache authority |
| 5.0 | 2026-08-22 | Agent | Align bounded quality/test presentation, structured DTO fields, and deferred finding boundary |
| 4.0 | 2026-06-15 | Agent | Document scoped quality and test execution contracts |
