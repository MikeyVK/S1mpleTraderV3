<!-- docs\development\issue443\planning.md -->
<!-- template=planning version=130ac5ea created=2026-08-18T20:33Z updated= -->
# Issue #443 Planning: Remove the Redundant search_documentation Tool

**Status:** APPROVED  
**Version:** 1.0  
**Last Updated:** 2026-08-18

---

## Purpose

Translate the approved clean-break research into two implementation-sized TDD cycles and explicit post-implementation validation and documentation obligations.

## Scope

**In Scope:**
Active agent sources and tracked consumers, role allowlists, public tool registration and contracts, dedicated services, presentation configuration, dedicated and mixed tests, active documentation, diagrams, tool inventories, and release notes.

**Out of Scope:**
Replacement search, compatibility aliases, deprecation periods, external search integration, changes to archived development artifacts, and unrelated discovery/resource-cache refactors.

## Prerequisites

Read these first:
1. Approved docs/development/issue443/research.md
2. Approved clean-break strategy and historical-archive boundary
3. docs/coding_standards/ARCHITECTURE_PRINCIPLES.md
4. docs/coding_standards/TYPE_CHECKING_PLAYBOOK.md
5. docs/coding_standards/DOCUMENTATION_STANDARD.md
---

## Summary

Execute the clean break in dependency order: first stop active agents and restricted roles from depending on the tool, then remove the callable/runtime surface and obsolete tests atomically. Preserve get_work_context, presenter/resource-cache behavior, unrelated mixed-test coverage, and all role authority boundaries. After implementation, validation must run focused and full suites plus branch gates; documentation must correct every active/published claim and add the breaking removal to the next release notes while leaving archives unchanged.

---

## Dependencies

- Cycle 1 must complete before Cycle 2 so active agent contracts no longer instruct use of a tool that the next cycle removes.
- Cycle 2 must keep the shared discovery module importable and get_work_context registered throughout the cutover.
- Documentation updates depend on final runtime names and tool inventory established by Cycle 2.
- No cycle may introduce an alias, fallback, replacement index, or other compatibility bridge.

---

## TDD Cycles


### Cycle 1: C_AGENT_CONTRACT_CUTOVER

**Goal:** Stop every active host instruction and explicit role allowlist from mandating or exposing the soon-to-be-removed MCP tool, while preserving each host's native-search guidance and existing role authority boundaries.

**Tests:**
- RED: add a focused static contract test covering authoritative agent sources and tracked workspace consumers; it must fail while the removed tool is still mandated or allowlisted.
- GREEN: run the focused agent-asset contract test after synchronizing authoritative host sources and derived consumers.
- REFACTOR: scan the complete active agent-source/consumer set for stale mandates, run documentation-alignment tests, and run quality gates on changed test files.

**Success Criteria:**
- [C1-D1] A stable agent-asset contract test covers the authoritative Codex, VS Code, and Antigravity sources plus tracked workspace consumers.
- [C1-D2] All active AGENTS.md and Codex research-rule variants direct agents to host-native repository search and do not mandate search_documentation.
- [C1-D3] VS Code @co and @qa source allowlists and tracked consumers no longer expose search_documentation; all other role permissions remain unchanged.
- Focused tests pass, source-to-consumer scans are clean, and changed Python tests pass formatting, lint, and typing gates.

**Dependencies:** Approved issue #443 research and archive policy


### Cycle 2: C_RUNTIME_AND_TEST_REMOVAL

**Goal:** Remove the public MCP tool and its exclusively dedicated runtime chain in one clean-break cutover, then remove obsolete dedicated tests without affecting get_work_context or shared server infrastructure.

**Tests:**
- RED: add negative public-inventory coverage proving search_documentation is absent while get_work_context remains registered.
- GREEN: run registration, bootstrap, presenter-alignment, output-contract, and discovery-tool tests after removing the public tool surface and dedicated runtime chain.
- REFACTOR: delete fully dedicated search test modules, remove search-only sections from mixed tests, preserve unrelated acceptance/discovery coverage, run active production/test cleanup scans, and execute focused quality gates.

**Success Criteria:**
- [C2-D1] Public server inventory no longer registers search_documentation and explicitly preserves get_work_context.
- [C2-D2] SearchDocumentationInput, SearchDocumentationTool, SearchDocumentationOutput, SearchResultDTO, bootstrap registration, and the presentation entry are absent.
- [C2-D3] SearchService and DocumentIndexer are removed with no remaining production imports or consumers.
- [C2-D4] Dedicated search tests are removed; mixed discovery, extra-forbid, and issue #56 acceptance coverage retains every unrelated assertion.
- Focused bootstrap, presenter, discovery, acceptance, and tool-inventory tests pass; Pyright and mypy report no dangling imports or symbols; active production/test scans contain only intentional regression references.

**Dependencies:** C_AGENT_CONTRACT_CUTOVER

---

## Risks & Mitigation

- **Risk:** Editing discovery_tools.py removes or destabilizes get_work_context because it shares the module with the deleted tool.
  - **Mitigation:** Use public registration tests that assert both the removed tool's absence and get_work_context's continued presence; retain all existing get_work_context tests.
- **Risk:** Authoritative host instructions and tracked consumers drift during manual synchronization.
  - **Mitigation:** Define the exact source/consumer path set in a static contract test and perform an exact-token scan after synchronization.
- **Risk:** Mixed test files lose unrelated discovery or scaffolding coverage during cleanup.
  - **Mitigation:** Treat fully dedicated modules and mixed-file sections separately; rerun the complete mixed files after edits.
- **Risk:** Deletion leaves dangling imports, exports, presentation keys, or misleading tool counts.
  - **Mitigation:** Run Pyright, mypy, presenter alignment, server inventory tests, and exact-symbol scans before completing Cycle 2.
- **Risk:** Active documentation or release assets continue to claim semantic/fuzzy search while archives are intentionally preserved.
  - **Mitigation:** In the documentation phase, scan active and shipped surfaces with explicit exclusions for issue-local research/planning and docs/development/archive.

---

## Milestones

- Implementation checkpoint after C1: active agent contracts use host-native search and restricted allowlists remain valid.
- Implementation checkpoint after C2: no callable or orphaned search runtime remains and focused tests/gates pass.
- Validation phase: run the complete workspace suite and branch quality gates, then record negative inventory and preservation evidence.
- Documentation phase: update active tool references, manuals, architecture diagrams, static tool counts, and CHANGELOG.md; preserve archives unchanged.
- Ready phase: carry the clean-break note and any genuine deferred work into the PR body.

## Related Documentation
- **[docs/development/issue443/research.md][related-1]**
- **[docs/reference/tools/discovery.md][related-2]**
- **[docs/reference/copilot-agent-instructions-model.md][related-3]**
- **[docs/coding_standards/TYPE_CHECKING_PLAYBOOK.md][related-4]**

<!-- Link definitions -->

[related-1]: research.md
[related-2]: ../../reference/tools/discovery.md
[related-3]: ../../reference/copilot-agent-instructions-model.md
[related-4]: ../../coding_standards/TYPE_CHECKING_PLAYBOOK.md

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-08-18 | Agent | Initial draft |