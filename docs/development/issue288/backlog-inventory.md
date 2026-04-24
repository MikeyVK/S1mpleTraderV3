# Backlog Inventory — Issue #288
**Date:** 2026-04-24  
**Trigger:** Merge of PR #283 (atomic submit_pr, BranchMutatingTool ABC, PRStatusCache, LoD fix)

---

## 1. Inventory: All 79 Open Issues

### Group A — Recent analysis findings (high issue numbers, from analysis rounds)

| # | Title | Assessment |
|---|-------|-----------|
| #286 | generic template: methods schema (list[str]) vs template (object access) | Bug → bundle into template issue |
| #285 | Separate MCPServer composition root from runtime dispatch | Architecture → bundle into wheel epic |
| #282 | Isolate test suite from real workflows.yaml | Test infra bug, active pain point |
| #278 | Fix critical gaps and stale claims in agent.md | Partially resolved in #283 |
| #274 | Enforce terminal-phase exit gates via create_pr hook | **CLOSE** — create_pr deleted in #283 |
| #271 | Make phase_contracts.yaml SSOT for workflow-phase membership | Config improvement |
| #269 | Align phase and cycle transition tool base class and API contracts | Technical debt |
| #268 | MCP-tool-first orchestration: get_work_context + create_handover | Workflow improvement |
| #262 | Config layer: GitConfig/QualityConfig are constants, not YAML-backed | Bundle into wheel epic |
| #261 | Add SHA-256 tamper detection for deliverables.json | Low priority / gold-plating |
| #260 | Configureerbare MCP root directory: .st3 → instelbaar pad | **Core blocker for distribution** |
| #259 | ArtifactManager sections injection + workflow-aware template rendering | Future / depends on #258 |
| #258 | sections.yaml + workflow phase_contracts + PSE content_contract gate | Future |
| #255 | Unify scope-aware rerun optimization for quality gates and tests | Future epic |
| #254 | Centralize .st3 config root via MCP setting | **CLOSE** — duplicate of #260 |
| #253 | run_tests: summary_line sync bug + no fail-fast + missing coverage | Bundle into run_tests issue |
| #250 | Test suite clean-up: SOLID audit, deprecated tests, setup-duplicaten | Technical debt |
| #245 | Shared ArtifactBodyRenderer: auto-render PR body and commit message | Future feature |
| #242 | save_planning_deliverables validates TDD deliverables on planning exit | Future gate |
| #238 | Implement three-unity architecture for create_issue tool | Large refactor |
| #237 | Exclude integration marker from default pytest run | Bundle into run_tests issue |
| #236 | Backfill existing issues: clean titles, add labels, re-scaffold bodies | Maintenance |
| #231 | State reconciliation for get_state: cycle/subphase awareness | Bug/enhancement |
| #230 | TDD cycle counter resets to 1 on TDD phase re-entry | Active bug |
| #228 | Add issue number to commit message encoding | Small enhancement |
| #225 | Refactor: remove V1 pipeline, consolidate to single Pydantic scaffold path | Bundle into template issue |

### Group B — Active bugs (real, daily pain points)

| # | Title | Assessment |
|---|-------|-----------|
| #253 | run_tests: sync bug + no fail-fast + missing coverage | Bundle into run_tests issue |
| #237 | Exclude integration marker from default pytest run | Bundle into run_tests issue |
| #230 | TDD cycle counter reset on phase re-entry | Keep open |
| #231 | get_state cycle/subphase awareness | Keep open |
| #139 | get_project_plan does not return current_phase | Daily pain point, keep open |
| #117 | get_work_context detects only TDD phase | Daily pain point, keep open |
| #89 | Copilot Chat disables MCP tools per session | **CLOSE** — VS Code limitation, not fixable by us |
| #58 | scaffold_design_doc: sections parameter type mismatch | Bundle into template issue |

### Group C — Concrete features/refactors (scoped, relevant)

| # | Title | Assessment |
|---|-------|-----------|
| #285 | Separate MCPServer composition root | Bundle into wheel epic |
| #269 | Align phase/cycle transition base class + API | Keep open |
| #268 | get_work_context + create_handover | Keep open |
| #250 | Test suite clean-up | Keep open |
| #237 | Exclude integration marker | Bundle into run_tests issue |
| #228 | Issue number in commit encoding | Keep open |
| #225 | Remove V1 scaffold pipeline | Bundle into template issue |
| #187 | Decouple create_issue from Jinja2 field contract | Keep open |
| #150 | Align get_issue/list_issues with new conventions | Keep open |
| #140 | Test coverage 82% → 90% | Bundle into wheel epic |
| #136 | Normalise error handling | Keep open |
| #118 | Post-#56: restore test discovery + lint suppressions | Keep open |
| #116 | create_branch accepts issue_number parameter | Keep open |
| #107 | DRY violations in scaffolding | Bundle into template issue (optional) |
| #74 | Fix DTO and Tool template validation failures | Bundle into template issue |
| #62 | Make phase workflow tests phase-agnostic | Keep open |
| #47 | Audit over-broad exception handling + lint suppressions | Keep open |

### Group D — Epics

| # | Title | Assessment |
|---|-------|-----------|
| #91 | Epic: Restore clean tests + consistent ToolResult error contract | Partially done, keep open |
| #73 | Epic: Template Governance | **CLOSE** — process doc, not code; governance emerges from practice |
| #72 | Epic: Template Library Management | Keep open as parent |
| #49 | Epic: MCP Platform Configurability (8 config files) | Keep open as parent |

### Group E — Old sequential phase implementation issues (superseded)

| # | Title | Assessment |
|---|-------|-----------|
| #36 | Phase G: End-to-end integration testing + docs | **CLOSE** — superseded by actual implementation |
| #35 | Phase F: Extend SafeEdit validators (YAML/JSON/TOML) | **CLOSE** — partially done, low priority |
| #34 | Phase D: Path-based file creation enforcement | **CLOSE** — realised |
| #33 | Phase C: Retrofit GitManager with PolicyEngine | **CLOSE** — realised in #283 |
| #32 | Phase B: TransitionPhaseTool implementation | **CLOSE** — realised |
| #31 | Phase A.2: PhaseStateEngine for transition management | **CLOSE** — realised |
| #30 | Phase A.1: PolicyEngine core with strict validation | **CLOSE** — realised |
| #24 | [Tooling Debt] Missing Git operations in ST3 workflow tools | **CLOSE** — mostly realised |

### Group F — Old / low priority / stale

| # | Title | Assessment |
|---|-------|-----------|
| #274 | Enforce terminal-phase exit gates via create_pr | **CLOSE** — create_pr deleted |
| #261 | SHA-256 tamper detection deliverables.json | Low priority, defer |
| #260 | Configureerbare MCP root (.st3) | Core distribution blocker → bundle into wheel epic |
| #254 | Centralize .st3 config root | **CLOSE** — duplicate of #260 |
| #242 | save_planning_deliverables validates TDD deliverables | Future |
| #238 | Three-unity architecture create_issue | Large refactor, defer |
| #236 | Backfill existing issues | Maintenance, defer |
| #122 | Refactor: path resolution ArtifactManager → tool layer | Keep as debt |
| #121 | Content-Aware Edit Tool: VS Code Position/Range API | Defer |
| #110 | Project Scaffolding Tool (Empty Dir → Full Project) | Future |
| #109 | File Operations Consolidation (PathResolver Utility) | Debt |
| #106 | ScaffoldComponentTool SRP Refactoring | Debt |
| #102 | TEST: Project Initialization Tool Validation | Possibly stale |
| #59 | Enforce Git Branching & Merging Strategy | Mostly realised |
| #57 | Config: Constants Configuration (constants.yaml) | Low priority |
| #48 | Research: Git as SSOT for phase tracking | **CLOSE** — replaced by state.json |
| #46 | Enforce pre-push/post-pull validation | Partially done |
| #42 | Phase workflow vs TDD: component→tdd sequence | Conceptual, low prio |
| #41 | TransitionPhaseTool with phase-specific guidance | Enhancement |
| #40 | Enforce hierarchical issue-specific docs structure | Partially realised |
| #37 | Design test_*.py Jinja2 template | Template work |
| #22 | Analyze SRP Compliance | **CLOSE** — research done |
| #18 | Enforce TDD & Coverage via Hard Tooling | Partially realised |
| #16 | Inventory of Test Coverage & TDD Compliance | **CLOSE** — done |
| #15 | Enhanced Template Validation & Standardization | **CLOSE** — superseded |
| #14 | Automated 'Close Feature' Workflow | **CLOSE** — superseded |

---

## 2. Issues to Close (17 confirmed)

| # | Reason |
|---|--------|
| #274 | `create_pr` tool deleted in #283 — enforcement rule is gone |
| #254 | Exact duplicate of #260 |
| #89  | VS Code limitation outside our control |
| #73  | Governance emerges from practice; process doc not actionable |
| #36  | Superseded by actual implementation |
| #35  | Superseded; SafeEdit validators partially done |
| #34  | Realised (path enforcement implemented) |
| #33  | Realised in #283 (GitManager + PolicyEngine/EnforcementRunner) |
| #32  | Realised (TransitionPhaseTool exists and works) |
| #31  | Realised (PhaseStateEngine exists and works) |
| #30  | Realised (EnforcementRunner = PolicyEngine core) |
| #24  | Mostly realised; remaining items tracked in specific issues |
| #48  | Research superseded; state.json is the SSOT |
| #22  | Research complete; findings absorbed into specific issues |
| #16  | Inventory done; tracking ongoing via quality gates |
| #15  | Superseded by V2 template validation infrastructure |
| #14  | Automated close workflow not needed; submit_pr covers it |

---

## 3. Three Consolidated Focus Areas

### Focus A — run_tests: fix all known gaps
**Consolidates:** #237 + #253  
**Scope:**
- Add `-m not integration` to pyproject.toml addopts (one-liner — #237)
- Fix summary_line sync: write fallback back to `parsed["summary_line"]` (#253 Gap 1)
- Detect pytest exit code 4 / startup errors as `ToolResult.error` (#253 Gap 2)
- Add `coverage: bool` parameter + `--cov` flags + Gate 6 output (#253 Gap 3)
- Regression tests for all three code paths

**Estimate:** ~1 sprint

### Focus B — Template system pass
**Consolidates:** #74 + #286 + #58 + #225 (+ optional #107)  
**Scope:**
- Fix `generic` template: align `GenericContext.methods` schema with template object access (#286)
- Fix DTO template: remove unused imports, fix typing issues (#74)
- Fix Tool template: resolve syntax error in triple-quoted string (#74)
- Fix `scaffold_design_doc`: sections parameter type mismatch (#58)
- Remove V1 dict-based pipeline from ArtifactManager; consolidate to single Pydantic path (#225)
- Optional: BaseScaffolder DRY fix (#107) — include if V1 removal reveals good moment

**Estimate:** ~2 sprints

### Focus C — Installable wheel / standalone MCP server (Epic)
**Groups:** #260 + #285 + #262 + #128 + #140  
**New work to add:**
- Entry point declaration in pyproject.toml (`console_scripts: st3-mcp`)
- Bootstrap logic: create default `.st3/` structure on first run if absent
- Replace `start_mcp_server.ps1` with proper CLI entry point

**Child issues to keep active:** #260 (core), #285 (composition root), #262 (config constants), #128 (V2→V3 infra), #140 (coverage 90%)  
**Estimate:** Epic — ~3–4 sprints total across child issues

---

## 4. Decision Log

| Decision | Rationale |
|----------|-----------|
| #254 close (not merge into #260) | Exact duplicate; no unique content to preserve |
| #73 close | Template governance emerges from actual template quality work (#B), not a separate process doc |
| #89 close | VS Code MCP tool lazy-loading is documented in agent.md as a known pattern; not a code fix |
| #107 optional in Focus B | V1 removal (#225) may make the DRY violations less severe; reassess after #225 is done |
| #255 defer | Scope-aware rerun optimization is valid but not blocking; stays as future epic after Focus A ships |
