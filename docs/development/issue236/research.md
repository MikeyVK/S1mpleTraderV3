<!-- docs\development\issue236\research.md -->
<!-- template=research version=8b7bb3ab created=2026-02-21T13:48Z updated=2026-02-21T15:00Z -->
# Issue #236 Research: Backfill existing issues and create_issue redesign

**Status:** DRAFT  
**Version:** 1.0  
**Last Updated:** 2026-02-21

---

## Purpose

Establish the technical approach for three interdependent problems before executing the backfill of ~60 open issues. Issue #236 also serves as the test case for the three-unity config-schema-template architecture before rolling it out to other templates.

## Scope

**In Scope:**
pyproject.toml integration marker fix; issue.md.jinja2 title duplication fix; issues.yaml body_fields extension; IssueBody Pydantic schema dynamic input_schema injection; startup validation contract; backfill strategy for open issues; technical debt tracking for v2 template SRP violations

**Out of Scope:**
Backfilling closed issues; changes to non-issue artifact templates; performance optimisation; GitHub API rate limiting strategy

## Prerequisites

Read these first:
1. Research discussion completed (session 2026-02-21)
2. issues.yaml structure reviewed (.st3/issues.yaml)
3. issue.md.jinja2 and IssueBody Pydantic model reviewed (mcp_server/tools/issue_tools.py)
4. scaffold_artifact hints-system reviewed (mcp_server/scaffolders/template_scaffolder.py)
---

## Problem Statement

All ~60 open issues predate the create_issue redesign (issue #149) and have inconsistent titles, incomplete labels, and free-form bodies. Before backfilling, three structural problems must be resolved: (A) the integration test suite creates real GitHub issues on every full test run because the 'integration' pytest marker is never excluded by default; (B) issue.md.jinja2 renders a duplicate H1 title in the body (GitHub already shows the title above the body), and the template has implicit bug-report bias with no per-type field guidance; (C) the create_issue tool schema gives agents no type-aware guidance about which IssueBody fields are relevant for a given issue_type, and validation errors lack the structured hints format that scaffold_artifact already provides.

## Research Goals

- Confirm the minimal pyproject.toml fix to exclude integration tests from the default pytest run
- Define the three-unity architecture: issues.yaml (config/intent) + IssueBody Pydantic (validation/contract) + issue.md.jinja2 (presentation/rendering), each with strict SRP
- Design the body_fields extension for issues.yaml: which per-type field guidance levels are needed (required, recommended, optional) vs. over-engineering
- Design the dynamic input_schema injection: how CreateIssueTool.input_schema combines Pydantic schema with issues.yaml body_fields into x-relevant-for annotations
- Design the runtime model_validator for type-aware IssueBody hints, matching the scaffold_artifact hints format
- Design the startup validation contract that enforces issues.yaml body_fields names match IssueBody.model_fields keys
- Define the backfill strategy: which steps can be scripted vs. require agent judgment, and in what order
- Record the technical debt item: SRP violations in v2 template architecture to be tracked as a separate issue after decision 4 is implemented

---

## Background

Issue #149 redesigned create_issue with structured IssueBody, Jinja2 rendering, and label assembly. Per-type body_fields guidance was explicitly deferred as out of scope. The scaffold_artifact tool already has a working hints-response pattern (ValidationError with Required/Optional/Missing lines driven from template introspection). The create_issue tool should reach parity with this pattern. The three-unity principle emerged from the research discussion: issues.yaml owns config/intent, Pydantic owns validation/contract, Jinja2 owns presentation — each with strict SRP. The startup validation contract closes the DRY loop by asserting that body_fields names in issues.yaml match IssueBody.model_fields keys.

---

## Findings

### F1 — Three-unity architecture (DECIDED)

`issues.yaml`, `IssueBody` (Pydantic), and `issue.md.jinja2` form a strict SRP triad. Each owns one dimension:

| Layer | File | Responsibility |
|---|---|---|
| Config/Intent | `.st3/issues.yaml` | Which issue types exist; which body fields are relevant per type |
| Validation/Contract | `IssueBody` (Pydantic) | Which fields exist; type safety; cross-field validation |
| Presentation | `issue.md.jinja2` + tier3 patterns | How the rendered body looks |

Overlap in field names across layers is an **interface contract**, not a DRY violation. A startup validation asserts that every `body_fields` name in `issues.yaml` exists as a key in `IssueBody.model_fields`, closing the loop without coupling.

Adding a new issue type = `issues.yaml` only. `IssueBody` and the template are generic and do not need to change.

### F2 — Guidance levels: four levels are justified (DECIDED)

Two levels (`required` / `optional`) cover validation. Four levels (`required` / `recommended` / `optional` / `discouraged`) cover agentic use. The distinction:

- `required` → hard error at validation time
- `recommended` → soft signal in schema and hints; agent is prompted to consider the field even though omitting it is allowed
- `optional` → no signal; agent decides autonomously
- `discouraged` → prevents semantic misuse (e.g. `actual` on a `feature`) without a hard error; agent receives a warning hint

The tier3 markdown pattern catalog (`tier3_pattern_markdown_*.jinja2`) provides the concrete vocabulary: each pattern that the `issue.md.jinja2` template *could* use but currently does not (e.g. `pattern_prerequisites_section`, `pattern_open_questions_section`) is a candidate `optional` or `recommended` field for specific issue types.

### F3 — Dynamic input_schema strategy: description append (DECIDED)

Maximum agent compatibility requires that guidance is carried in the `description` field of each `IssueBody` property, as that is what every agent reads natively. The `x-*` JSON Schema extension strategy is unreliable across MCP clients.

`CreateIssueTool.input_schema` already returns a dynamically constructed schema (via `_resolve_schema_refs`). The property will be extended to read `issues.yaml` `body_fields` at runtime and append guidance to each field's `description`:

```
"actual": "Actual behavior observed. [bug, hotfix: recommended] [other types: discouraged]"
```

This makes the schema self-documenting without relying on client-side extension support.

### F4 — Runtime type-aware IssueBody validation (DECIDED)

A `model_validator` on `CreateIssueInput` (mode `after`, cross-field) will:
1. Read `body_fields` from `issues.yaml` for the given `issue_type`
2. Emit hint warnings for `discouraged` fields that are populated
3. Emit hint suggestions for `recommended` fields that are absent

This matches the hints format already used by `scaffold_artifact` (Required / Recommended / Discouraged lines in the response). Soft signals — no hard error for `discouraged` fields — preserving flexibility. The `update_issue` tool does not have this constraint; drift prevention there is a separate concern and explicitly out of scope for #236.

### F5 — Backfill strategy (DECIDED)

| Task | Approach |
|---|---|
| Title cleanup (remove prefixes) | Semi-automated script; rule-based transformations are deterministic |
| Label completion (add missing type/priority/scope) | Semi-automated script; priority and scope require agent judgment per issue |
| Body re-scaffolding (~60 issues) | Manual; ~60 is tractable, automation overhead disproportionate |

The title + label script will be a standalone Python script in `scripts/`. It is a one-off tool but will be retained (not deleted). It will **not** be registered in `server.py`. Body re-scaffolding happens only after F1–F4 are implemented, using the improved template.

### F6 — issue.md.jinja2 structural fixes (DECIDED)

Two fixes required before backfill:
1. Remove the `# {{ title }}` H1 block — GitHub renders the issue title as H1 above the body natively; the template duplicates it
2. The template currently only imports `tier3_pattern_markdown_related_docs`. Additional tier3 patterns should be imported as candidates for new body fields (driven by F7 decisions)

### F7 — IssueBody field catalog (DECIDED)

One field added beyond the current set: `prerequisites`. Rationale: an issue without prerequisites can be picked up at the wrong moment — by an agent or a developer — causing wasted effort or incorrect sequencing. Absence of this information meaningfully impedes execution.

All three candidate fields evaluated against the principle *"does absence meaningfully impede future execution?"*:

| Candidate | Decision | Rationale |
|---|---|---|
| `scope_in` / `scope_out` | ❌ Not added | Scope is the *result* of research/planning, not input to the backlog item. Belongs in `planning.md`. |
| `prerequisites` | ✅ Added | Ordering constraint that must be known before picking up the issue. Universal across all types. |
| `open_questions` | ❌ Not added | Open questions signal an incomplete issue. If questions exist at creation time, they belong in `research.md`, not the issue body. |

Final `IssueBody` field set: `problem`, `expected`, `context`, `actual`, `steps_to_reproduce`, `related_docs`, `prerequisites`.

### F8 — SCAFFOLD metadata header for issue bodies (DECIDED)

The current `_render_body` call in `CreateIssueTool` bypasses the scaffolding pipeline and passes empty strings for `version_hash`, `output_path`, and `timestamp`. This renders a meaningless two-line header:

```html
<!--  -->
<!-- template= version= created= updated= -->
```

**Desired output for issue bodies** — one line, template fingerprint only:
```html
<!-- template=issue version=8b7bb3ab -->
```

Rationale: GitHub issues are stored in GitHub, not in the filesystem. Git tracks created/updated timestamps natively. The filepath is not meaningful for a GitHub resource. Only the template version fingerprint has value — it enables future detection of "this body was generated from template version X, which is now outdated".

**Implementation approach for #236:**
- `_render_body` computes `version_hash` via `compute_version_hash()` from the `issue.md.jinja2` template file
- `tier0_base_artifact.jinja2` is **not changed** in this issue — the cascade impact on all four tier1 branches (code, document, tracking, config) and all 20+ concrete templates requires a dedicated analysis. This is recorded as technical debt (see F10).
- Interim: `_render_body` passes `output_path=""` and `timestamp=""` as today, but with `version_hash` properly computed. The created/updated fields render as empty, which is acceptable until the tier0 tech debt is resolved.

### F9 — Impact scope: three-unity implementation (DECIDED)

Seven files are affected, across four layers:

**`.st3/issues.yaml`**
- Add `body_fields` block per issue type with guidance levels (required / recommended / optional / discouraged)

**`mcp_server/config/issue_config.py`**
- Extend `IssueTypeEntry` with `body_fields: dict`
- Add `get_body_fields(issue_type)` helper method to `IssueConfig`

**`mcp_server/tools/issue_tools.py`** — three changes in one file:
1. `IssueBody` — add `prerequisites` field; update field descriptions with type-guidance via description-append
2. `CreateIssueInput` — add `model_validator(mode="after")` for cross-field discouraged/recommended hints
3. `CreateIssueTool.input_schema` — extend to read `issues.yaml` `body_fields` and append guidance to field descriptions dynamically

**`mcp_server/scaffolding/templates/concrete/issue.md.jinja2`**
- Remove `# {{ title }}` H1 block
- Import `tier3_pattern_markdown_prerequisites` and render conditionally

**Tests — existing (regression check):**
- `tests/unit/tools/test_create_issue_errors.py` — verify no regressions from the new validator
- `tests/unit/tools/test_create_issue_label_assembly.py` — expected unaffected
- `tests/integration/test_create_issue_e2e.py` — Scenario 2 (bug fields on feature) may now emit hint warnings; assertions stay valid

**Tests — new:**
- `tests/unit/tools/test_create_issue_input.py` — new tests for `model_validator`: discouraged-field warnings and recommended-field suggestions per issue type

**Startup validation — new location TBD in planning:**
- Assert that all field names in `body_fields` entries in `issues.yaml` exist as keys in `IssueBody.model_fields`
- Fires at server startup, preventing silent config/code drift

### F10 — Technical debt: tier0 cascade (NOTED, separate issue)

`tier0_base_artifact.jinja2` is the root of the entire template hierarchy:
- Direct children: `tier1_base_code`, `tier1_base_document`, `tier1_base_tracking`, `tier1_base_config`
- Downstream: all 20+ concrete templates via their respective tier1/tier2 parents

Making `created=`, `updated=`, and the filepath line conditional in tier0 is architecturally desirable — not all artifact types are files on disk — but requires:
1. Auditing all concrete templates and their test baselines for expected header changes
2. Deciding the conditional variable name and default behaviour
3. Updating `template_scaffolder.py` to inject the condition flag

This work is explicitly out of scope for #236 and must be tracked as a separate issue after the three-unity changes are complete.

---

## Open Questions

**Q1 — Guidance levels** ✅ Resolved → F2: four levels (required, recommended, optional, discouraged) are architecturally justified and necessary for agentic use.

**Q2 — input_schema injection strategy** ✅ Resolved → F3: description append is the primary strategy; maximises agent compatibility across all MCP clients.

**Q3 — model_validator scope** ✅ Resolved → F4: validator covers both discouraged-field warnings and recommended-field suggestions. Soft signals only; no hard error on discouraged. `update_issue` drift is out of scope for #236.

**Q4 — IssueBody field catalog** ✅ Resolved → F7: `prerequisites` added; `scope_in/out` and `open_questions` rejected. Guiding principle: *an issue captures the minimally required context to be maximally useful for future execution.*

**Q5 — Backfill script: one-off or reusable tool** ✅ Resolved → F5: one-off, retained in `scripts/`, not registered in `server.py`.


## Related Documentation
- **[docs/development/issue149/planning.md][related-1]**
- **[docs/development/issue149/design.md][related-2]**
- **[.st3/issues.yaml][related-3]**
- **[mcp_server/tools/issue_tools.py][related-4]**
- **[mcp_server/scaffolding/templates/concrete/issue.md.jinja2][related-5]**
- **[mcp_server/scaffolders/template_scaffolder.py][related-6]**
- **[pyproject.toml][related-7]**

<!-- Link definitions -->

[related-1]: docs/development/issue149/planning.md
[related-2]: docs/development/issue149/design.md
[related-3]: .st3/issues.yaml
[related-4]: mcp_server/tools/issue_tools.py
[related-5]: mcp_server/scaffolding/templates/concrete/issue.md.jinja2
[related-6]: mcp_server/scaffolders/template_scaffolder.py
[related-7]: pyproject.toml

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 |  | Agent | Initial draft |