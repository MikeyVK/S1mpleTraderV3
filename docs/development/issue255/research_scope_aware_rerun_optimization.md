<!-- docs\development\issue255\research_scope_aware_rerun_optimization.md -->
<!-- template=research version=8b7bb3ab created=2026-02-27T19:05Z updated=2026-02-28 -->
# Scope-aware rerun optimization context fingerprint model

**Status:** DRAFT  
**Version:** 2.0  
**Last Updated:** 2026-02-28

---

## Problem Statement

Current rerun behavior is not robust across scope switches, branch changes, and multi-machine workflows. We need a uniform optimization model across all scopes that safely supports: skip fixed files, rerun known bad files, and rerun newly changed files.

## Research Goals

- Define one uniform rerun optimization model for `auto`, `branch`, `project`, and `files`.
- Define a minimal context-fingerprint concept that determines when optimization is safe.
- Define correctness-first invariants and fallback behavior.
- Establish a shared theoretical baseline before architecture and implementation design.

## Scope of This Document (Current Revision)

This revision captures only the **theoretical target model**.

Out of scope for this revision:
- concrete code changes,
- state-schema migration decisions,
- final architecture decisions,
- test implementation details.

## Scope Boundary Note (Issue Transfer)

This document is rehomed from issue #251 to issue #255.

- Issue #255 owns broad optimization/refactor architecture for both `run_quality_gates` and `run_tests`.
- Issue #251 remains focused on minimal-effort stabilization and safe daily usage across existing scopes.

---

## 1. Theoretical Target Model

### 1.1 Uniform Rerun Rule (all scopes)

For any scope, the optimized rerun set is:

- `known_bad`: files that were previously evaluated in the same valid context and had failed status.
- `newly_changed`: files whose content has changed since last evaluation in the same valid context.

Execution set:

- `rerun_set = known_bad ∪ newly_changed`

Skip rule:

- A file is skippable only if it was previously evaluated as pass **and** its content is unchanged in the same valid context.

### 1.2 Baseline-first Principle

Optimization is only allowed after a valid baseline exists for the active context.

- First run in a context: full evaluation of the resolved scope set.
- Subsequent runs in same context: optimized evaluation via `known_bad ∪ newly_changed`.

### 1.3 Context Validity Principle

Optimization is a cache privilege, not a correctness requirement.

- If context is unknown, stale, or mismatched, the system must fall back to full evaluation.
- Correctness always wins over performance.

---

## 2. Context Fingerprint Specification (Locked v1)

This section defines the strict, deterministic fingerprint contract for optimization safety.

### 2.1 Fingerprint Fields (exact set)

Fingerprint v1 consists of exactly six normalized fields:

1. `repo_id`
2. `branch_id`
3. `scope_mode`
4. `scope_target_hash`
5. `rules_hash`
6. `runtime_hash`

Any field change invalidates optimization context and requires a baseline/full run.

### 2.2 Field Definitions

#### `repo_id`

Purpose: separate optimization state across repositories/forks/workspaces.

Canonical value:

- `repo_id = sha256("remote=<canonical_remote>|root=<workspace_root_canonical>")`

Normalization rules:

- remote URL lowercased host, normalized `.git` suffix handling,
- workspace root normalized to absolute, symlink-resolved, POSIX separator form,
- if remote unavailable, use `remote=none` (still include canonical root).

#### `branch_id`

Purpose: prevent cross-branch cache reuse.

Canonical value:

- current git branch name as exact UTF-8 string,
- detached HEAD represented as `DETACHED:<short_head_sha>`.

#### `scope_mode`

Purpose: separate optimization contexts per scope behavior.

Allowed values:

- `auto`, `branch`, `project`, `files`.

#### `scope_target_hash`

Purpose: detect candidate-set drift within same scope.

Canonical value:

- resolve candidate targets for the run,
- normalize every target to workspace-relative POSIX path,
- sort ascending, deduplicate,
- join with `\n`,
- hash with SHA-256.

Formula:

- `scope_target_hash = sha256("\n".join(sorted_unique_targets))`

#### `rules_hash`

Purpose: invalidate optimization when quality/test rule semantics change.

Canonical value:

- SHA-256 over normalized config payload used for evaluation.

Minimum included inputs:

- active gate list/order,
- gate commands/arguments,
- parser strategy settings,
- scope include/exclude patterns relevant to candidate resolution,
- for tests: pytest option set used by runner mode.

#### `runtime_hash`

Purpose: strict invalidation on runtime/toolchain drift.

Canonical value:

- SHA-256 over normalized runtime manifest:
  - python version (full),
  - tool versions used by run (`ruff`, `mypy`, `pyright`, `pytest` as applicable),
  - platform identifier.

Strict policy:

- any runtime/tool version/platform change invalidates context.

### 2.3 Fingerprint Composition

Normalized payload order is fixed:

1. `repo_id`
2. `branch_id`
3. `scope_mode`
4. `scope_target_hash`
5. `rules_hash`
6. `runtime_hash`

Composite string format:

- `repo_id=<...>|branch_id=<...>|scope_mode=<...>|scope_target_hash=<...>|rules_hash=<...>|runtime_hash=<...>`

Final context fingerprint:

- `context_fingerprint = sha256(composite_string)`

### 2.4 Validation Contract

At run start:

1. Recompute all six fields.
2. Recompute `context_fingerprint`.
3. Compare with stored context entry.

Decision rules:

- match => optimization allowed,
- mismatch/missing/parse-error => optimization forbidden; execute baseline/full run,
- after baseline/full run => persist fresh context snapshot.

### 2.5 Storage Contract

Fingerprint and optimization context state are stored in `.st3/state.json` under `quality_gates`.

Constraints:

- state is local-only (`.gitignore`),
- storage location does not imply trust,
- trust comes only from runtime recomputation + match validation.

### 2.6 Independence Constraint

Fingerprint validity must not depend on workflow helper side-effects.

- No reliance on checkout tool mutations,
- no reliance on "always via tool" assumptions,
- runtime recomputation is the only source of truth for context validity.

---

## 3. Content Identity and Tracking Policy (Locked v1)

Path equality alone is insufficient for safe skipping.

### 3.1 Identity Source Order (Git-first)

Content identity must be resolved in this strict order:

1. git blob/oid identity for tracked files (primary),
2. deterministic file-content hash (fallback only where explicitly allowed).

Git is the primary trust source for repository files; state.json only stores cached observations.

### 3.2 Tracking Scope (Locked v1)

Optimization-state tracking includes:

- tracked, non-gitignored files only.

Optimization-state tracking excludes:

- gitignored files,
- directories/non-file targets,
- unresolved/missing paths.

### 3.3 Untracked File Policy

Untracked files are not part of optimization-state v1 by default.

- They may still be evaluated in a run if explicitly part of resolved scope input.
- Their outcomes do not become stable optimization cache entries unless a future version explicitly enables untracked tracking policy.

### 3.4 Required State Metadata per Target

Each target entry must include:

- `content_id`: resolved identity value,
- `identity_source`: `git_blob` or `file_hash`,
- `last_status`: `passed|failed|skipped`,
- `last_seen_at`,
- `last_run_id`.

Rationale:

- auditability of identity provenance,
- deterministic debugging when identity source changes,
- explicit prevention of implicit fallback drift.

### 3.5 Ambiguity/Fallback Rules

If identity cannot be resolved with policy-compliant source:

- target is treated as non-optimizable for that run,
- execute in full-evaluation path,
- do not record misleading optimization-state entry.

A file can only remain skipped when:

- context remains valid,
- `content_id` is unchanged,
- prior status in that context was pass,
- identity source remains policy-compliant.

---

## 4. Correctness Invariants

The model is correct only if all invariants hold:

1. **No silent skip of unknown files**: files without prior evaluated state in context are evaluated.
2. **No skip on content change**: changed content must be re-evaluated.
3. **No cross-context reuse**: optimization data cannot be reused across invalid context boundaries.
4. **Deterministic fallback**: invalid context always triggers full scope evaluation.
5. **Optimization is optional**: disabling optimization must not change correctness outcomes.

---

## 5. Context Boundary Events (Conceptual)

Events that conceptually force new baseline behavior:

- switching scope,
- switching branch,
- changing quality-gate/rule configuration,
- runtime/toolchain drift,
- repository identity changes,
- missing or unreadable optimization state.

In all such cases: treat as fresh context and run without optimization first.

---

## 6. Architecture Decision (SOLID-first)

This section records the intended architecture choice before implementation mapping.

### 6.1 Decision Summary

Adopt a shared optimization architecture with:

- one reusable rerun planning core,
- strict separation between context resolution, state persistence, execution, and outcome classification,
- tool-specific adapters for `run_quality_gates` and `run_tests`.

### 6.2 Design Principles

- **SRP:** each component owns exactly one responsibility.
- **DRY:** rerun planning logic is implemented once and reused across tools.
- **OCP:** new tools can join via adapters without changing core planner logic.
- **DIP:** orchestration depends on interfaces, not concrete tool implementations.
- **Correctness-first:** optimization is optional and must never alter correctness semantics.

### 6.3 Logical Components

1. **ExecutionContextResolver**
   - Resolves candidate targets for a scope.
   - Produces deterministic context fingerprint inputs.
   - No state mutation.

2. **RunStateRepository**
   - Sole read/write boundary for optimization state.
   - Handles serialization, schema versioning, and safe fallback behavior.

3. **ContentIdentityService**
   - Computes content identity per target (git blob id or hash fallback).
   - Provides deterministic change detection.

4. **RerunPlanner (Shared Core)**
   - Computes rerun set using: `known_bad ∪ newly_changed`.
   - Computes skip set from unchanged previously passing targets.
   - Contains no tool-specific parsing logic.

5. **OutcomeClassifier (Tool Adapter Interface)**
   - Converts tool execution output into target-level pass/fail/skipped status.
   - One implementation per tool family (`quality_gates`, `pytest`).

6. **OptimizationPolicy**
   - Encapsulates invalidation and fallback rules.
   - Decides when full baseline run is required.

7. **OptimizedRunnerOrchestrator**
   - Coordinates resolver, planner, executor, classifier, and repository.
   - Applies identical rerun lifecycle for all scopes and all participating tools.

### 6.4 Uniform Lifecycle (High-Level)

1. Resolve scope candidates.
2. Build/validate execution context.
3. If context invalid or missing baseline: run full scope set.
4. Else run planned set (`known_bad ∪ newly_changed`).
5. Classify outcomes at target level.
6. Persist updated optimization state.

### 6.5 Tool Integration Strategy

- `run_quality_gates` and `run_tests` share the same orchestrator flow.
- They differ only in:
  - target resolution specifics,
  - command execution adapter,
  - outcome classifier.
- No duplication of rerun math, context gating, or state semantics.

### 6.6 Hybrid Test Optimization Pattern (L1/L2)

For test execution optimization, use a two-layer model:

- **L1 (file-level):** mandatory baseline layer, always available, deterministic fallback.
- **L2 (node-level):** optional acceleration layer, active only when strict safety checks pass.

Safety checks for L2 activation:

- strict context fingerprint match,
- stable collection fingerprint match,
- unchanged content-id for involved test files,
- no rename/delete ambiguity in tracked targets.

Fallback rule:

- If any L2 safety check fails, execution degrades automatically to L1 file-level behavior.
- Correctness semantics must remain identical between L1 and L2 paths.

### 6.7 Architecture Boundaries

**Issue boundary (hard constraint):**

- This issue is the umbrella refactor scope for shared optimization architecture across `run_quality_gates` and `run_tests`.
- Implementation remains phased to control risk and preserve correctness-first fallback behavior.
- Stabilization-only fixes that avoid broad refactor stay scoped to issue #251.

### 6.8 Operational Independence Decision

The optimization model must not depend on non-contractual behavior of workflow helpers.

Decision:

- Do **not** rely on git-checkout tool state mutation behavior.
- Do **not** assume users always switch branches through a specific tool path.
- Always validate branch/context compatibility through runtime fingerprint checks.

Rationale:

- Tool/workflow assumptions are fragile over time.
- Runtime fingerprint validation is deterministic and self-contained.
- Correctness remains stable across CLI/tool/manual/CI execution paths.

### 6.9 Shared State Infrastructure Decision

State lifecycle behavior is a shared infrastructure concern, not a domain-manager concern.

Decision:

- Implement shared state infrastructure for JSON artifacts (including `state.json` and `projects.json`).
- Retention/size policies must be loaded from YAML configuration.
- Domain managers (e.g., quality/project managers) must not hardcode retention thresholds or file-size limits.

Scope intent:

- one policy mechanism, multiple state artifacts,
- consistent pruning/compaction behavior,
- SRP + DRY compliance across managers.

In scope for this decision:
- component responsibilities,
- interaction boundaries,
- shared-vs-tool-specific split.

Out of scope for this decision:
- concrete module paths,
- concrete class/method names,
- migration mechanics,
- test-file mapping.

---

## 7. State Snapshot Contract (Proposed v1)

This section defines the proposed storage shape in `.st3/state.json` for optimization state.

### 7.1 Location

All optimization state is stored under:

- `quality_gates.optimization`

This remains local-only and gitignored.

### 7.2 Top-level Shape

```json
{
  "quality_gates": {
    "baseline_sha": "<legacy-auto-field-kept-for-compat>",
    "failed_files": ["<legacy-auto-field-kept-for-compat>"],
    "optimization": {
      "schema_version": 1,
      "contexts": {
        "<context_fingerprint>": {
          "fingerprint": {
            "repo_id": "...",
            "branch_id": "...",
            "scope_mode": "auto|branch|project|files",
            "scope_target_hash": "...",
            "rules_hash": "...",
            "runtime_hash": "...",
            "context_fingerprint": "..."
          },
          "created_at": "2026-02-27T20:00:00Z",
          "updated_at": "2026-02-27T20:05:00Z",
          "baseline_completed": true,
          "run_count": 3,
          "last_full_run_at": "2026-02-27T20:01:00Z",
          "targets": {
            "path/to/file.py": {
              "content_id": "...",
              "identity_source": "git_blob|file_hash",
              "last_status": "passed|failed|skipped",
              "last_seen_at": "2026-02-27T20:05:00Z",
              "last_run_id": "20260227T200500Z"
            }
          }
        }
      }
    }
  }
}
```

### 7.3 Semantic Rules

1. `contexts` key is `context_fingerprint`.
2. `baseline_completed=false` means optimization is disallowed for that context.
3. `targets` contains only normalized workspace-relative POSIX paths.
4. `last_status=passed` is skippable only when `content_id` unchanged.
5. Missing target state implies "unknown" and must be evaluated.

### 7.4 Compatibility Rules

- Keep `baseline_sha` and `failed_files` during transition for backward compatibility.
- New optimization engine must not trust legacy fields without fingerprint match.
- Legacy fields can be deprecated only after migration and rollout validation.

### 7.5 Retention and Size Policy (Config-Driven)

Retention and file-size controls must be policy-driven via YAML configuration.

Locked rules:

- No hardcoded retention counts in domain code.
- No hardcoded file-size thresholds in domain code.
- Policy values are read from central YAML config and applied by shared state infrastructure.
- Eviction strategy is configurable (default policy may use `updated_at` ordering).

Minimum policy dimensions (YAML):

- `max_contexts` (per optimization namespace),
- `soft_size_limit_bytes`,
- `hard_size_limit_bytes`,
- `eviction_strategy` (`updated_at`, `created_at`, etc.),
- optional `ttl_days` (disabled by default unless explicitly configured).

Rationale:

- consistent behavior across `state.json`, `projects.json`, and future state artifacts,
- no policy drift between managers,
- easier operational tuning without code changes.

---

## 8. Effort vs Performance Value Assessment

### 8.1 Is this worth it?

Short answer: **yes, if implemented in phases with hard fallback to correctness**.

### 8.2 Expected Benefit

- **run_quality_gates:** high expected gain when project scope and gate execution are heavy.
- **run_tests:** medium-to-high expected gain in large, slow test files (especially with optional L2 node acceleration).
- **Developer loop:** faster fix-validate cycles and less redundant reruns.

### 8.3 Cost / Complexity

Main complexity drivers:

- deterministic context/fingerprint maintenance,
- per-target state consistency,
- safe fallback logic,
- migration/compatibility handling.

### 8.4 Risk Control (required)

- Optimization must be best-effort only.
- Any ambiguity or mismatch => full run.
- Identical correctness outcomes with optimization on/off.

### 8.5 Full-Run Policy Decision

Decision:

- Use **event-driven full runs only**.
- No periodic safety full-run cadence in v1.

Mandatory explicit override:

- Provide `force_full` as a **public tool parameter** to bypass optimization on demand.
- `force_full=true` must execute full resolved scope set regardless of matching fingerprint.
- `force_full=true` must refresh context baseline/snapshot after successful run.

Public-parameter rationale:

- Enables explicit co-creation control with agents.
- Makes full-run intent auditable in tool-call history.
- Avoids hidden/internal behavior that cannot be enforced by users.

Minimum trigger set for automatic full run (without `force_full`):

- fingerprint mismatch,
- missing/corrupt optimization state,
- context baseline not yet completed.

### 8.6 Recommended Phased ROI Strategy

1. **Phase A:** fingerprint + file-level L1 optimization for `run_quality_gates`.
2. **Phase B:** validate stability and performance delta in live workflow.
3. **Phase C:** extend same architecture to `run_tests` within this umbrella issue.
4. **Phase D:** optional L2 node acceleration where safety checks prove stable.

This keeps effort proportional and prevents over-engineering.

---

## 9. Non-Goals (Current Phase)

This phase does **not** yet decide:

- cache retention/TTL parameters,
- concrete implementation mapping to existing files.

---

## Open Questions

1. Should target-level history include optional failure taxonomy fields in v1 or defer to v2?
2. Which exact YAML config path should own shared state retention/size policies?

---

## Related Documentation

- [issue251/live-validation-plan.md](../issue251/live-validation-plan.md)
- [issue251/live-validation-plan-v2.md](../issue251/live-validation-plan-v2.md)
- [issue251/planning.md](../issue251/planning.md)

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-27 | Agent | Initial scaffold draft |
| 1.1 | 2026-02-27 | Agent | Added theoretical target model (uniform rerun, context fingerprint concept, invariants) |
| 1.2 | 2026-02-27 | Agent | Locked fingerprint v1 specification (fields, normalization, composition, validation contract) |
| 1.3 | 2026-02-27 | Agent | Added proposed state snapshot contract and effort-vs-performance assessment with phased ROI strategy |
| 1.4 | 2026-02-27 | Agent | Decided event-driven-only full runs and added mandatory `force_full` override requirements |
| 1.5 | 2026-02-27 | Agent | Locked `force_full` as public tool parameter and closed related open question |
| 1.6 | 2026-02-27 | Agent | Locked Git-first tracking policy, constrained optimization scope to tracked files, and added `identity_source` metadata |
| 1.7 | 2026-02-27 | Agent | Locked shared YAML-driven retention/size policy and centralized state lifecycle responsibility |
| 2.0 | 2026-02-28 | Agent | Rehomed to issue #255, updated boundaries to include both `run_quality_gates` and `run_tests`, and fixed related-doc links |
