<!-- docs/development/issue456/tool-presentation-field-audit.md -->
<!-- template=generic_doc version=ad8498ef created=2026-08-21 updated=2026-08-21 -->
# Tool Presentation Field Audit

**Status:** REVIEW REQUIRED  
**Version:** 1.2  
**Last Updated:** 2026-08-21

---

## Purpose

Provide a complete field-level target audit for every registered MCP tool before issue #456 implementation.

## Scope

**In Scope:** All 50 tool names in presentation.yaml, their registered output models, inherited tool-specific DTO fields, current templates, and the proposed issue #456 target presentation to be reviewed jointly with the human owner.

**Out of Scope:** Redesign of DTOs or cache payloads, failure DTO internals outside the common output envelope, and the deferred design of structured quality-gate findings.

## Interpretation

This is the proposed normal-success presentation target after issue #456, not a claim about code already implemented. A row becomes an implementation deliverable only after its functional review batch receives explicit human approval.

- **Inline fields** names every tool-specific DTO field intended to appear in chat. Nested paths use collection[].field notation.
- **Mechanism** identifies ordinary scalar interpolation, inline bounded scalar sequences, configured collections, or the resource-only exception.
- **Cache-only fields** remain present in the complete DTO resource but are not included in the normal success text.
- Every result still receives the universal 8,000 UTF-8-byte ceiling and cache reference.
- A dash means that no tool-specific DTO field remains cache-only.
- Presentation headings, emojis, fixed prose, omission notices, and cache URIs are not DTO fields and therefore do not appear in the field columns.

### Common Output Envelope

Every listed output model inherits these fields; they are not repeated in each row:

| Field | Presentation behavior |
|---|---|
| success | Selects success/failure presentation; not normally interpolated as a success field. |
| error_message | Shown through configured failure presentation when relevant; normally null/cache-only on success. |
| post_tool_instruction | Remains cache-only unless a template explicitly adopts it; no target template currently does. |

---

## Interactive Review Decisions

### Batch 1 — Server and Workflow Tools

| Decision | Disposition | Rationale |
|---|---|---|
| `health_check.reason` remains absent from the normal healthy-server template. | APPROVED | The normal presenter path produces `None`. In degraded mode the server has `presenter=None` and no cache publisher, so `str(HealthCheckOutput)` already exposes `status=unhealthy` and the populated reason directly; adding `Reason: -` to the healthy template provides no failure-path value. |
| Complete `passing_gates[]` remains cache-only; `passing_gates_count` stays inline. | APPROVED | Successful gate identities are diagnostic/audit detail, not routine next-action data. |
| Bounded `skipped_gates[]` is inline when non-empty. | APPROVED | Skipped gates identify deliberately bypassed blockers and require attention; configured collection rendering already omits empty collections. |
| `phase_source` remains cache-only. | APPROVED | Normal initialized state always reports `state.json`; the value is diagnostic provenance rather than action data. |
| `phase_confidence` remains cache-only after explicit state status is implemented. | APPROVED | `workflow_state_status` becomes the actionable inline contract; confidence is redundant diagnostic metadata on both normal and abnormal paths. |
| `get_work_context` emits `WorkflowStateStatus` plus structured supporting data; presentation.yaml owns all warning and recovery text. | APPROVED | Explicit human decision aligned with the Presentation Boundary; OperationNotes and tool-owned human text are excluded. |

Batch 1 is CLOSED by explicit human approval. The four-value `WorkflowStateStatus` contract (`available`, `missing`, `unreadable`, `invalid_phase`) is confirmed; remaining server/workflow row decisions follow the approved matrix and are no longer delegated to Implementation.

## Server and Workflow Tools

| Tool | Inline DTO fields after #456 | Presentation mechanism | Tool-specific cache-only fields |
|---|---|---|---|
| health_check | status, version, pid, platform, uptime_seconds | Scalar template, unchanged | reason |
| restart_server | reason | Scalar template, unchanged | pid, timestamp, iso_time |
| transition_cycle | to_cycle, total_cycles, cycle_name, branch, passing_gates_count, skipped_gates_count | Scalar template, unchanged | from_cycle, passing_gates[], skipped_gates[] |
| force_cycle_transition | to_cycle, total_cycles, cycle_name, branch, passing_gates_count, skipped_gates_count | Scalar template, unchanged | from_cycle, passing_gates[], skipped_gates[], skip_reason, human_approval_message |
| get_work_context | current_branch, workflow_name, issue_number, phase, sub_role_hint, parent_branch, current_cycle, sub_phase, phase_instructions, handover_template, workflow_state_status; valid_phases for invalid_phase | Scalar orientation plus enum-selected warning/recovery block; valid_phases use bounded inline scalar-sequence formatting | phase_source, phase_confidence |
| initialize_project | issue_number, branch, initial_phase | Scalar template, unchanged | workflow_name, parent_branch, required_phases[], execution_mode, files_created[] |
| get_project_plan | issue_number, workflow_name, phases[].name, phases[].status, phases[].tasks[].id, phases[].tasks[].title, phases[].tasks[].status | Scalar header plus configured nested model collections | — |
| save_planning_deliverables | issue_number, total_cycles, total_deliverables | Scalar template, unchanged | cycles[].cycle_number, cycles[].deliverables_count |
| update_planning_deliverables | issue_number, total_cycles, total_deliverables | Scalar template, unchanged | cycles[].cycle_number, cycles[].deliverables_count |
| transition_phase | to_phase, branch, passing_gates_count, skipped_gates_count | Scalar template, unchanged | from_phase, passing_gates[], skipped_gates[], skipped_gates_warning, passing_gates_info |
| force_phase_transition | to_phase, branch, passing_gates_count, skipped_gates_count | Scalar template, unchanged | from_phase, passing_gates[], skipped_gates[], skipped_gates_warning, passing_gates_info, skip_reason, human_approval_message |

## Git Tools

| Tool | Inline DTO fields after #456 | Presentation mechanism | Tool-specific cache-only fields |
|---|---|---|---|
| git_list_branches | branches_count, current_branch, branches[].name, branches[].is_current, branches[].upstream | Scalar header plus bounded model collection | branches[].commit_hash |
| git_diff_stat | source_branch, target_branch, files_changed, insertions, deletions | Scalar template, unchanged | stats |
| get_parent_branch | branch, parent_branch | Scalar template, unchanged | — |
| check_merge | merge_sha | Scalar success/failure template, unchanged | is_ancestor |
| git_status | branch, is_clean, modified_count, untracked_count, modified_files[], untracked_files[] | Scalar header plus two bounded scalar collections | — |
| create_branch | branch_name, branch_type, base_branch | Scalar template, unchanged | — |
| git_add_or_commit | branch, commit_hash, workflow_phase, sub_phase, cycle_number, commit_type, files[] | Expanded scalar template plus bounded scalar file collection | — |
| git_restore | files_count, source, files[] | Scalar confirmation plus bounded scalar file collection | — |
| git_checkout | previous_branch, branch, current_phase, parent_branch | Expanded scalar orientation template | — |
| git_push | branch, new_upstream_created | Scalar template, unchanged | set_upstream |
| git_merge | source_branch, target_branch | Scalar template, unchanged | — |
| git_delete_branch | branch, local_status, remote_status | Scalar template, unchanged | — |
| git_stash | action, stashes[] | Scalar header plus bounded scalar collection | message |
| git_fetch | remote | Scalar template, unchanged | raw_output, prune |
| git_pull | remote | Scalar template, unchanged | raw_output, rebase |

### Batch 2 — Git Tools

**Disposition:** CLOSED by explicit human approval.

- All fifteen Git rows below are approved as the implementation target.
- `git_add_or_commit.files[]`, commit sub-phase/cycle, `git_restore.files[]`, and `git_checkout.parent_branch` are promoted inline for direct mutation verification and orientation.
- `git_diff_stat.stats`, fetch/pull raw output, and redundant caller-input flags remain cache-only because they are unstructured diagnostics or repeat requested inputs.
- Collection projections remain bounded and preserve Git/DTO order.

## GitHub Tools

| Tool | Inline DTO fields after #456 | Presentation mechanism | Tool-specific cache-only fields |
|---|---|---|---|
| create_issue | number, title, html_url | Scalar template, unchanged | state, milestone_title, assignees_summary, body, labels[], created_at, updated_at, closed_at, author |
| update_issue | number, title, html_url | Scalar template, unchanged | state, milestone_title, assignees_summary, body, labels[], created_at, updated_at, closed_at, author |
| get_issue | number, title, state, milestone_title, assignees_summary, html_url, body, labels[] | Expanded scalar template; labels use bounded inline scalar-sequence formatting | created_at, updated_at, closed_at, author |
| close_issue | issue_number | Scalar template, unchanged | — |
| list_issues | issues_count, issues[].number, issues[].title, issues[].state, issues[].html_url, issues[].labels[] | Scalar header plus bounded model collection; labels use bounded inline scalar-sequence formatting per item | issues[].assignees_summary, issues[].created_at |
| get_pr | number, title, html_url, state, base_ref, head_ref, body | Expanded scalar template | merged_at, merge_sha |
| submit_pr | number, title, html_url, base_ref, head_ref | Scalar template, unchanged | state, merged_at, merge_sha, body |
| merge_pr | pr_number, merge_method, merge_sha | Scalar template, unchanged | — |
| list_prs | prs_count, pull_requests[].number, pull_requests[].title, pull_requests[].state, pull_requests[].html_url, pull_requests[].base_ref, pull_requests[].head_ref | Scalar header plus bounded model collection | — |
| list_labels | total_labels, labels[].name, labels[].color, labels[].description | Scalar header plus bounded model collection | — |
| create_label | label_name, color | Scalar template, unchanged | — |
| delete_label | label_name | Scalar template, unchanged | — |
| add_labels | formatted_labels, issue_number | Scalar template, unchanged | labels[] |
| remove_labels | formatted_labels, issue_number | Scalar template, unchanged | labels[] |
| list_milestones | total_milestones, milestones[].number, milestones[].title, milestones[].state | Scalar header plus bounded model collection | — |
| create_milestone | number, title | Scalar template, unchanged | state |
| close_milestone | number, title | Scalar template, unchanged | state |

## Scaffolding Tools

| Tool | Inline DTO fields after #456 | Presentation mechanism | Tool-specific cache-only fields |
|---|---|---|---|
| scaffold_artifact | artifact_type, name, files_created[] | Scalar header plus bounded scalar collection | formatted_files_created, schema_info, validation_schema, missing_fields[], provided_fields[] |
| scaffold_schema | artifact_type | Scalar locator; schema remains deliberately resource-only | schema_data |

## Quality, Testing, and Editing Tools

| Tool | Inline DTO fields after #456 | Presentation mechanism | Tool-specific cache-only fields |
|---|---|---|---|
| auto_fix | gates_executed_count, gates_executed[], modified_files_count, modified_files[] | Scalar header plus two bounded scalar collections | formatted_modified_files |
| run_quality_gates | overall_pass, scope, file_count, gates[].name, gates[].passed, gates[].status, gates[].score | Outcome-neutral scalar header plus bounded model collection | gates[].details |
| run_tests | passed_count, failed_count, skipped_count, errors_count, summary_line, failures[].test_id, failures[].location, failures[].short_reason | Scalar summary plus bounded failure collection | exit_code, failures[].traceback, failures[].is_collection_error, coverage_pct, lf_cache_was_empty, stderr |
| safe_edit_file | path, passed, written, issues | Expanded scalar template | mode, diff, has_diff |
| validate_template | passed, errors_count, errors[].severity, errors[].message | Outcome-neutral scalar header plus bounded model collection | — |

---

## Full-Optimization Decision

The field audit disproves the earlier shorthand that the 32 compact templates have no additional cached data. They often do. All 50 rows are proposed implementation scope, but their inline/cache-only splits remain proposals until the interactive Design review closes.

A cache-only classification is intentional only under one of these actionability rules:

| Rationale | Representative fields |
|---|---|
| Redundant confirmation or caller-supplied input | create/update issue body and labels, commit/restore file lists, transition gate lists after a successful transition |
| Internal or low-value operational metadata | timestamps, process identifiers, author metadata, prior phase/cycle values |
| Raw or deep inspection evidence | raw Git output, diffs, tracebacks, stderr, validation schemas, opaque gate details |
| Duplicate convenience representation | formatted file or label strings when the underlying bounded collection is inline |
| Semantically unreliable without a richer DTO contract | `gates[].details` until structured findings exist |

Optimization requires implementing and reviewing every row, not forcing every DTO field inline. The current compact scalar result remains optimal where extra fields are redundant, operational metadata, or deep-inspection evidence. The complete cache continues to expose all omitted fields.

The deferred quality-gate gap remains unchanged: `gates[].details` is an opaque string. Showing bounded concrete diagnostics requires a future structured finding contract rather than gate-specific presentation parsing.

## Evidence and Reproducibility

The inventory was derived from:

- all 50 keys in [presentation.yaml](../../../.pgmcp/config/presentation.yaml);
- the tool classes assembled by [ServerBootstrapper](../../../mcp_server/bootstrap.py);
- their ICoreTool output model type arguments or explicit output_model declarations;
- Pydantic model fields in [tool outputs](../../../mcp_server/schemas/tool_outputs.py);
- current scalar placeholders parsed from [presentation.yaml](../../../.pgmcp/config/presentation.yaml);
- the approved target behavior in [Research](research.md) and [Design](design.md).

## Validation Checklist

- [ ] Exactly 50 unique tools are present.
- [ ] Every tool maps to a registered output model.
- [ ] Every tool-specific DTO field is classified as inline or cache-only.
- [ ] Nested DTO fields use explicit path notation.
- [ ] Every functional batch has an explicit human disposition.
- [ ] Every row is approved or changed against its proposed inline/cache-only target before implementation.
- [ ] Registered public tool names and presentation keys have exact bidirectional parity.
- [ ] Any change to the approved inline/cache-only split is reflected in Research, Design, Planning, and structured deliverables.

## Related Documentation

- [Research](research.md)
- [Design](design.md)
- [Planning](planning.md)
- [Presentation configuration](../../../.pgmcp/config/presentation.yaml)
- [Tool output DTOs](../../../mcp_server/schemas/tool_outputs.py)
- [TextPresenter](../../../mcp_server/presenters/text_presenter.py)

---

## Version History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-08-21 | Agent | Complete 50-tool target presentation and cache-field audit |
| 1.1 | 2026-08-21 | Agent | Approve the 50-tool implementation target and explicit cache-only rationale categories |
| 1.2 | 2026-08-21 | Agent | Reopen the matrix for mandatory interactive human review before Planning |
