<!-- c:\temp\st3\docs\development\issue251\design_v2.md -->
<!-- template=design version=5827e841 created=2026-02-26T10:49Z updated= -->
# Design Addendum — Post-Validation Hardening (C32–C39)

**Status:** DRAFT  
**Version:** 1.0  
**Last Updated:** 2026-02-26

---

## Purpose

Define a compact design gate before TDD for post-validation fixes C32–C39.

## Scope

**In Scope:**
Contract and scope-behavior design decisions for C32–C39: mixed file/dir input resolution (C34), compact payload semantics (C35), summary-line context and message sanitation (C39), plus dependent consistency choices for path normalization and severity mapping.

**Out of Scope:**
Replanning C0–C31, introducing new quality gates, transport-layer redesign for large payloads, and broad architectural rewrites.

## Prerequisites

Read these first:
1. Read `docs/development/issue251/research_v2.md`.
2. Read `docs/development/issue251/planning.md` Addendum A (C32–C39).
3. Inspect `mcp_server/managers/qa_manager.py` scope and result-building paths.
4. Inspect `.st3/projects.json` planning_deliverables for issue 251.
---

## 1. Context & Requirements

### 1.1. Problem Statement

Research_v2 identified open findings requiring explicit design choices before implementation to avoid contract drift across TDD cycles. Without a short design gate, cycles C34/C35/C39 risk inconsistent semantics for scope resolution, gate status signaling, and one-line summary behavior.

### 1.2. Requirements

**Functional:**
- [ ] `scope="files"` must accept a mixed list of explicit files and directory paths and resolve to a deterministic concrete file set before gate filtering.
- [ ] Compact JSON payload must expose top-level `overall_pass` and `duration_ms` and provide unambiguous per-gate evaluation status.
- [ ] Summary line must communicate both outcome and effective scope-resolution context for all scope inputs (`auto`, `branch`, `project`, `files`).
- [ ] Violation file paths must be normalized to one canonical workspace-relative POSIX format in compact payload.
- [ ] Pyright-derived messages must be sanitized to stable single-line output for downstream consumers.

**Non-Functional:**
- [ ] Preserve backward readability of existing outputs while improving contract clarity.
- [ ] Keep implementation changes localized to existing manager/tool boundaries.
- [ ] Maintain deterministic behavior and testability across Windows path conventions.
- [ ] Avoid duplicated normalization logic; centralize in shared flow.
- [ ] Minimize risk by sequencing fixes into small, independently verifiable TDD cycles.

### 1.3. Constraints

- Must remain compatible with quality gate configuration model and current tool invocation patterns.
- Must support Windows and POSIX path behavior consistently.
- Must not require new MCP tool APIs.
- Design phase should remain compact and directly traceable to findings F-1..F-19.
- Any `projects.json` planning updates should be managed via planning-deliverables tools only.
---

## 2. Design Options
---

## 3. Chosen Design

**Decision:** Use a lightweight design addendum with centralized normalization and explicit output contract: introduce a dedicated path-resolution utility for `scope="files"`, formalize per-gate status semantics, enrich summary-line context for scope-driven runs, and keep gate-level file filtering unchanged.

**Rationale:** This approach resolves the post-validation gaps with minimal surface-area change and clear SRP boundaries: input expansion happens once before gate dispatch, normalization happens once in shared violation processing, and presentation/context responsibilities stay in summary/result builders. It maximizes correctness and traceability while avoiding unnecessary architectural churn.

### 3.1. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Resolve mixed `scope="files"` input via dedicated utility before gate dispatch | Keeps SRP boundaries clean and prevents silent directory skips while reusing existing gate filtering. |
| Keep gate-level `filter_files()` unchanged | Gate ownership of applicability stays intact; avoids duplicated validator logic and regression risk. |
| Add explicit per-gate `status` and top-level `overall_pass`/`duration_ms` | Makes compact payload deterministic for agents without multi-step inference. |
| Normalize violation `file` path at shared normalization point | Ensures one canonical path format across all gates and prevents parser-specific drift. |
| Extend summary line with effective scope context for all scope inputs (`auto`,`branch`,`project`,`files`) | Improves quick rerun usability for humans and agents without opening full payload/state. |

## Related Documentation
- **[docs/development/issue251/research_v2.md][related-1]**
- **[docs/development/issue251/planning.md][related-2]**
- **[.st3/projects.json][related-3]**
- **[docs/development/issue251/live-validation-plan.md][related-4]**

<!-- Link definitions -->

[related-1]: docs/development/issue251/research_v2.md
[related-2]: docs/development/issue251/planning.md
[related-3]: .st3/projects.json
[related-4]: docs/development/issue251/live-validation-plan.md

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-26 | Agent | Initial draft |