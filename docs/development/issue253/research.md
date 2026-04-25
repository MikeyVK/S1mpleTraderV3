<!-- docs\development\issue253\research.md -->
<!-- template=research version=8b7bb3ab created=2026-04-24T20:14Z updated=2026-04-26 -->
# Issue #253: run_tests Daily-Use Blockers

**Status:** DRAFT  
**Version:** 1.2  
**Last Updated:** 2026-04-26

---

## Purpose

Capture the research findings for issue #253 (`RunTestsTool` reliability gaps), record the two additional workflow-facing findings discovered during branch setup (`create_branch` encoding defect and `get_project_plan` operator hint), confirm the already-resolved status of issue #237, and document the integration-test safety contract that makes marker-based exclusion unnecessary.

## Scope

**In Scope:**
`RunTestsTool` daily-use gaps from issue #253, `create_branch` success-response encoding defect, `get_project_plan` missing operator hint, and the status of `.st3/projects.json` versus current runtime state files

**Out of Scope:**
Detailed implementation design, TDD cycle breakdown, complete test-suite isolation work from issue #282, and removal of `.st3/projects.json` in this research phase, and issue #237 (the pytest integration marker is already abolished — confirmed during this research session)

---

## Problem Statement

The current MCP-based test workflow still creates enough friction that developers fall back to direct terminal pytest usage for reliable feedback. Issue #253 covers the primary `run_tests` correctness gaps. Issue #237 was opened to address a perceived risk that integration-marked tests could run as part of the standard suite — but during this research session, investigation confirmed that #237 is already resolved: the `integration` marker was abolished (not excluded) as part of prerequisite work merged before this branch. During branch setup for issue #253, two additional workflow-facing issues were observed: `create_branch` returns a misencoded success indicator, and `get_project_plan` returns a bare not-found error without guiding the caller to run `initialize_project` first.

## Research Goals

- Confirm the scope of issue #253 and determine which findings remain in this branch
- Record the rationale and impact of the two smaller workflow-facing findings discovered during branch setup
- Determine whether `.st3/projects.json` is still part of the active runtime contract or is now stale
- Provide an `Expected Results` section that design and planning can build on without turning this document into a design or planning artifact
- Confirm the resolved status of issue #237 and document the current integration-test safety contract

---

## Background

Issue #253 describes three unresolved `RunTestsTool` gaps: summary synchronization, incorrect handling of pytest invocation/startup failures, and missing coverage support even though Gate 6 is assigned to `run_tests`. Issue #237 was opened to address integration-marked tests running implicitly in the standard suite. Research during this session confirmed that #237 is already resolved: the `integration` marker was abolished entirely (not filtered out) as part of prerequisite work merged before this branch opened. See Finding 3 for the full resolution context.

The remaining focus of this branch is issue #253: making `run_tests` trustworthy enough that terminal fallback is no longer the default response when a test run produces unexpected output.

---

## Findings

### Finding 1 — `create_branch` had a real output encoding defect

The branch creation flow itself works, but the success response contained a misencoded success marker (`âœ…`) instead of a cleanly renderable indicator. This is a small and localized defect, but it appears in a high-frequency tool path and reduces confidence in tool output quality. The branch-level impact is low-risk and highly visible.

### Finding 2 — `get_project_plan` needs a structured operator hint, not an inline text patch

When no project plan exists, `get_project_plan` currently returns only a diagnostic error message. The missing information is not additional diagnosis but workflow guidance: the caller should run `initialize_project` first for the issue/branch context.

The correct direction is to use the internal note bus (`NoteContext`) and emit a typed `SuggestionNote`, keeping the main error diagnostic short while attaching a machine-readable and user-visible follow-up action. This matches the newer internal context-communication architecture better than appending an ad-hoc hint directly into the primary error string.

### Finding 3 — Issue #237 is resolved: the integration marker is abolished, not excluded

The original risk described in issue #237 (integration-marked tests running implicitly in the default suite and potentially calling the GitHub API) was addressed before this branch opened. The resolution was merged with the #239 prerequisite work.

The key implementation distinction: the fix was not to add a `-m not integration` exclusion filter. The `integration` marker itself was abolished. `pyproject.toml` no longer defines an `integration` marker, and `addopts` contains no `-m not integration` clause. This is a structural fix, not a procedural one.

The active enforcement lives in `test_pytest_config.py`:
- `test_addopts_does_not_exclude_integration`: asserts `-m not integration` is absent from `addopts`
- `test_integration_marker_not_defined`: asserts `integration:` is not in the markers list

Issue #237 is out of scope for this branch. The scope is #253 only.

### Finding 4 — The impact of issue #253 is immediate and operator-facing

Issue #253 has direct daily impact because it undermines trust in `run_tests` output:

- failed or malformed pytest runs can still look like an empty successful summary
- invocation/setup failures are not surfaced clearly enough as hard tool errors
- coverage remains unreachable through the MCP tool path even though the architecture assigns that responsibility to `run_tests`

This pushes users back to direct terminal pytest usage whenever they need reliable failure details or coverage information.

### Finding 5 — Integration tests are architecturally hermetic: the adapter boundary is the safety layer

Tests that touch an external GitHub boundary (for example `test_create_issue_e2e.py`) replace the GitHub API adapter with a `MagicMock`. Tests that operate exclusively on a local filesystem (for example `test_search_integration.py`) have no external adapter to mock; they still use `tmp_path` for all writes. The contractual rule is therefore adapter-boundary-scoped: **every test that reaches an external service must mock that service's adapter**. No test in the suite uses an environment variable guard (`GITHUB_TOKEN`, `pytest.mark.skipif` env check) to make itself opt-in. This was verified by inspecting the full integration test directory during this research session.

The integration tests exercise multiple real layers simultaneously (tool + manager + config) but always mock or avoid the external boundary. They are hermetic tests with a wider internal scope. The safety guarantee is structural: it does not depend on a marker filter or an environment variable.

The `test_pytest_config.py` suite enforces the configuration contract that makes this safe at scale. See Finding 3 and `docs/coding_standards/QUALITY_GATES.md` § Integration Test Boundary Contract for the full checklist.

### Finding 6 — `.st3/projects.json` appears stale relative to the current runtime

Current runtime persistence in the active Python implementation points to `.st3/deliverables.json` and `.st3/state.json`, not `.st3/projects.json`:

- `ProjectManager` persists project plans to `deliverables.json`
- `InitializeProjectTool` reports `deliverables.json` and `state.json` as the created files
- current runtime-oriented documentation and several older docs still mention `projects.json`

The targeted code search found no active Python runtime reads/writes of `.st3/projects.json`; the remaining references are in documentation and stale test names/descriptions. This strongly suggests that `projects.json` is no longer part of the live runtime contract and should be treated as cleanup debt or documentation debt, not as an active state file. It should **not** be removed during this research phase, but the mismatch should be considered a tracked finding.

**Exact stale references found in runtime/reference docs:**

- `docs/reference/mcp/tools/project.md:37` — lists `.st3/projects.json` as the historical project registry alongside active runtime files
- `docs/reference/mcp/tools/project.md:124` — states that `initialize_project` writes to `.st3/state.json` and `.st3/projects.json`
- `docs/reference/mcp/tools/project.md:183` — states that `get_project_plan` reads from `.st3/projects.json`
- `docs/reference/mcp/tools/project.md:242` — states that `transition_phase` records audit trail data in `.st3/projects.json`
- `docs/reference/mcp/tools/project.md:314` — states that `force_phase_transition` records audit trail data in `.st3/projects.json`
- `docs/reference/mcp/tools/project.md:346` — includes a full `.st3/projects.json` state-management section
- `docs/reference/mcp/tools/project.md:492` — lists `.st3/projects.json` again in the related files summary

**Additional non-reference architecture note:**

- `docs/mcp_server/architectural_diagrams/05_config_layer.md:83` — flags `.st3/projects.json` as a residual file that should have been removed earlier

**Negative finding:**

- No `projects.json` mention was found in `docs/reference/mcp/MCP_TOOLS.md`, which means the stale contract is concentrated in the dedicated project-tool reference page rather than spread across the whole MCP reference surface.

### Finding 7 — Empirical verification of run_tests across modes confirms #253 trust gaps

A direct in-process harness invoked RunTestsTool.execute() against five operational modes. Captured ToolResult.content payloads:

| Mode | Input | text block | summary_line | summary | failures |
|------|-------|------------|--------------|---------|----------|
| A. Targeted unit file | path=tests/mcp_server/unit/tools/test_git_tools.py | 36 passed in 4.51s | 36 passed in 4.51s | passed:36, failed:0 | absent |
| B. Nonexistent path | path=tests/does_not_exist | 0 passed, 0 failed (fallback) | empty string | passed:0, failed:0 | absent |
| C. Unknown marker | path=tests/mcp_server/unit, markers=nonexistent_marker | 0 passed, 0 failed (fallback) | empty string | passed:0, failed:0 | absent |
| D. last_failed_only=True with empty cache | path=test_git_tools.py, last_failed_only=True | 36 passed in 3.61s | 36 passed in 3.61s | passed:36, failed:0 | absent |
| E. Induced failure | tiny sentinel test with assert 1==2 | 1 failed in 1.98s | 1 failed in 1.98s | passed:0, failed:1 | populated correctly |

**What this confirms:**

- **Modes B and C reproduce #253 Gap 1 and Gap 2 directly.** Pytest exits with code 4 (usage error, mode B) or code 5 (no tests collected, mode C). _run_pytest_sync returns the returncode, but RunTestsTool.execute discards it (stdout, stderr, _ = await asyncio.to_thread(...)). The parser then finds no "N passed/failed" line, leaving summary_line empty. The fallback "0 passed, 0 failed" is indistinguishable from a real empty-but-clean run. The caller has no signal that anything went wrong.
- **Mode D surfaces a previously unrecorded surprise behavior of last_failed_only.** When pytest --lf cache is empty, pytest silently falls back to running every test in the path. The tool gives no indication that the LF cache was empty, so the caller asked for "previously failed only" and got a full run. This is a UX trust gap, not a correctness gap, but it falls inside the same #253 reliability envelope.
- **Mode E confirms the failure-path response shape works.** failures[] is populated with test_id, location, short_reason, and traceback. The traceback contains the xdist worker prefix [gw0] win32 ..., which empirically confirms pytest-xdist is active end-to-end and the silent-failure root cause was its absence from [project.optional-dependencies].dev rather than any wiring problem.

### Finding 8 — Tool-response structure analysis: run_tests should adopt the NoteContext interface

**Current response shape (all five modes):** ToolResult.content is a fixed two-entry list — a text block holding the summary line, followed by a json block holding summary, summary_line, and (on failure) failures. The tool signature already accepts NoteContext but explicitly drops it via `del context  # Not used`. No notes are produced in any code path.

**Why migration applies:** Modes B, C, and D all surface conditions where the primary response is technically valid but operationally misleading. These are exactly the cases the typed-note bus was designed for — secondary, machine-readable, user-visible signals layered onto a primary result. Inlining hints into the text block would break the existing parser-friendly contract that the first content entry is always the summary line.

**Mapping to existing note variants (no new types needed):**

| Condition | Note variant | Trigger | Example message |
|-----------|--------------|---------|-----------------|
| pytest exit code 4 (usage error / nonexistent path) | RecoveryNote raised via ExecutionError | returncode == 4 | "Pytest could not start. Verify the path exists and is readable." |
| pytest exit code 5 (no tests collected after filtering) | SuggestionNote returned, not raised | returncode == 5 and parsed counts both zero | "No tests matched the filter. Check markers and path." |
| pytest exit code 2 (interrupted / internal error) | RecoveryNote raised | returncode == 2 | "Pytest reported an internal error; inspect stderr." |
| last_failed_only=True but pytest runs everything | InfoNote returned | LF-empty pattern in stdout | "Last-failed cache was empty; ran full selection instead." |
| Coverage requested but pytest-cov missing (future #253 Gap 3) | RecoveryNote raised | plugin missing | "Install pytest-cov to enable coverage reporting." |

**Architectural fit:**

- NoteContext.render_to_response already appends a single text block of all Renderable notes after ToolResult.content. The current two-element text+json contract is preserved — notes are appended, not interleaved.
- Pattern is already established in enforcement_runner.py (SuggestionNote) and discovery_tools.py (RecoveryNote). Migration of run_tests is a like-for-like reuse, not a new architectural commitment.
- Returncode handling becomes the only required structural change. Once the tool inspects exit codes, every other note above is a one-line conditional context.produce(...) call.

**Migration scope (for the design phase, not implemented here):**

1. Capture returncode instead of discarding it (tuple unpacking change in execute).
2. Branch on returncode before parsing: codes 0/1 use the existing parser; 2/4/5 emit notes (or raise) without trusting parser output.
3. Optional: detect the LF-empty-cache message in stdout for InfoNote.
4. No change to the text+json content order — keeps existing client-side consumers working.

This finding scopes the architectural side of #253 cleanly without entering design or implementation territory.

---

## Expected Results

This research supports the following expected outcomes for the next phases:

- `create_branch` returns a cleanly renderable success marker in its primary success response
- `get_project_plan` keeps its diagnostic error concise and adds a structured hint telling the caller to run `initialize_project` first when no plan exists
- reference documentation for project tools reflects the real sequencing contract: `initialize_project` first, `get_project_plan` after project initialization
- the integration test safety contract is documented and enforced (see `docs/coding_standards/QUALITY_GATES.md` § Integration Test Boundary Contract)
- `run_tests` becomes trustworthy enough that terminal fallback is no longer the default behavior for routine failure inspection
- the repository records `.st3/projects.json` as a stale contract artifact pending explicit cleanup or documentation alignment, without removing it in this phase

## Related Documentation
- **[mcp_server/tools/git_tools.py][related-1]**
- **[mcp_server/tools/project_tools.py][related-2]**
- **[mcp_server/tools/test_tools.py][related-3]**
- **[mcp_server/managers/project_manager.py][related-4]**
- **[pyproject.toml][related-5]**
- **[docs/reference/mcp/tools/project.md][related-6]**
- **[docs/reference/mcp/MCP_TOOLS.md][related-7]**
- **[docs/development/archive/issue251/design.md][related-8]**
- **[docs/development/archive/issue251/research.md][related-9]**
- **[docs/development/archive/issue236/research.md][related-10]**
- **[docs/mcp_server/architectural_diagrams/04_enforcement_layer.md][related-11]**

<!-- Link definitions -->

[related-1]: mcp_server/tools/git_tools.py
[related-2]: mcp_server/tools/project_tools.py
[related-3]: mcp_server/tools/test_tools.py
[related-4]: mcp_server/managers/project_manager.py
[related-5]: pyproject.toml
[related-6]: docs/reference/mcp/tools/project.md
[related-7]: docs/reference/mcp/MCP_TOOLS.md
[related-8]: docs/development/archive/issue251/design.md
[related-9]: docs/development/archive/issue251/research.md
[related-10]: docs/development/archive/issue236/research.md
[related-11]: docs/mcp_server/architectural_diagrams/04_enforcement_layer.md

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-04-24 | Agent | Initial research draft covering #253, #237, two branch-setup findings, and the stale `projects.json` finding |
| 1.1 | 2026-04-25 | Agent | Added Finding 7 (empirical run_tests verification across 5 modes) and Finding 8 (NoteContext migration analysis) |
| 1.2 | 2026-04-26 | Agent | QA feedback processed: removed stale #237 framing, replaced Findings 3+5 with confirmed research conclusions, fixed issue251 archive links, added integration-test safety documentation |
