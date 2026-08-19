<!-- docs\development\issue443\validation.md -->
<!-- template=validation_report version=1.0.0 created=2026-08-18 updated=2026-08-18 -->
# Issue #443 Validation: Remove the Redundant search_documentation Tool

**Status:** APPROVED  
**Version:** 1.0  
**Last Updated:** 2026-08-18  
**Issue:** #443  
**Validation Status:** PASS

---

## Scope and Prerequisites

This validation covers the completed `C_AGENT_CONTRACT_CUTOVER` and
`C_RUNTIME_AND_TEST_REMOVAL` cycles. The approved research, planning artifact,
clean-break strategy, architecture principles, and documentation standard are
the authoritative baseline.

Validated boundaries:

- Active agent sources, tracked consumers, and restricted role allowlists.
- Public MCP registration, presentation configuration, input/output contracts,
  dedicated services, and bootstrap composition.
- Preservation of `get_work_context` and unrelated discovery behavior.
- Dedicated and mixed test cleanup.
- Full workspace tests and branch-scoped quality gates.

Historical artifacts under `docs/development/archive/**` are intentionally
excluded from active-surface cleanup.

## Summary Verdict

PASS. The removed tool is absent from active agent contracts and from the
freshly bootstrapped public tool inventory. Its dedicated runtime chain and
tests are gone, while `get_work_context`, shared bootstrap behavior, mixed
acceptance coverage, and role authority boundaries remain green.

Two non-blocking repository-level caveats are disclosed below: the known Ruff
strict-lint command construction defect in the quality-gate runner and the
existing workspace coverage level below the optional 90% threshold.

## Test Evidence

### Required full workspace suite

`run_tests(scope='full')`:

- Result: PASS
- Tests: 2737 passed, 2 skipped, 1 xpassed
- Warnings: 24
- Duration: 39.73 seconds
- Exit code: 0
- Cached run: `pgmcp://cache/runs/16c30c857b2b4360b2c8a99bc29b42c6`

### Focused implementation evidence

- Agent contract suite: 23 passed.
- Registration, bootstrap, presenter, discovery, extra-forbid, and acceptance
  scope: 132 passed.
- Active production/test symbol scan contains only the two intentional negative
  regression-test references to `search_documentation`.

### Additional coverage diagnostic

An additional full run with `coverage=true` had no test failures
(2737 passed, 2 skipped, 1 xpassed) but exited with code 1 because total
workspace coverage is 86%, below the configured 90% threshold. Coverage mode is
not part of the required refactor validation command and the shortfall is not
attributed to this removal.

## Branch Quality Gates

`run_quality_gates(scope='branch')` reported overall PASS for eight changed
Python files:

- Ruff format: PASS.
- Imports: PASS.
- Line length: PASS.
- Pyright: PASS, zero diagnostics across eight files.
- MCP server typing: PASS.
- General type gate: skipped because no matching files were selected.

The Ruff strict-lint entry is not reliable evidence: its subprocess returned
exit code 2 because the generated `--per-file-ignores` value `ARG` is
invalid, while the wrapper still classified the gate as passed. This known
quality-gate/fix-command infrastructure defect is deferred for triage in its
own issue and is not changed under #443.

Cached run: `pgmcp://cache/runs/4819e7b7daca4767ad762cae7fccd4a0`.

## Deliverable and Exit-Criteria Mapping

| Deliverable | Observed evidence | Result |
|---|---|---|
| C1-D1 | `tests/documentation/test_agent_instruction_search_contract.py` covers all authoritative host sources and tracked consumers; 23 tests pass | PASS |
| C1-D2 | Active AGENTS.md and Codex research-rule variants contain host-native repository-search guidance and omit the removed tool | PASS |
| C1-D3 | VS Code `@co` and `@qa` sources and consumers omit the obsolete allowlist item; exact source-consumer equality tests pass | PASS |
| C2-D1 | Fresh server registration test proves `search_documentation` absent and `get_work_context` present | PASS |
| C2-D2 | Search input/tool/output DTOs, bootstrap registration, and presentation entry are absent | PASS |
| C2-D3 | `SearchService` and `DocumentIndexer` files are deleted and active production scans find no consumers | PASS |
| C2-D4 | Dedicated search tests are deleted; mixed discovery, extra-forbid, issue #56 acceptance, and full-suite coverage remain green | PASS |

Both cycle exit criteria are satisfied. The only surviving exact tool-name
references in production/test scope are assertions that prevent its
reintroduction.

## Research and Approved Strategy Alignment

The implementation honors the approved clean break at every affected boundary:

- No alias, fallback, compatibility bridge, or replacement search was added.
- Existing clients must refresh or reconnect after upgrade; stale calls receive
  normal unknown-tool behavior.
- Active agent behavior now relies on host-native repository search.
- `get_work_context`, resource caching, presenter alignment, and unrelated
  discovery behavior were preserved.
- Historical archives remain unchanged as approved.

No architecture-contract mismatch or hidden redesign was found.

## Live Demonstration Proposal

The smallest operator-visible demonstration requires a fresh server process and
client tool-list refresh:

1. Check out this branch and restart phase-gate-mcp.
2. Reconnect or refresh the MCP client so it requests a new tool inventory.
3. Observe that `search_documentation` is no longer listed.
4. Invoke `get_work_context` and observe a normal structured response.

The current chat client may cache its tool inventory, so it is not a reliable
live list-tools demonstrator without reconnection. The closest deterministic
fallback is
`test_search_documentation_removed_and_get_work_context_preserved`, which
constructs a fresh server from the branch and verifies both observations in one
test. The complete bootstrap/discovery suite supplies additional preservation
evidence.

## Residual Risks, Caveats, and Deferred Work

- Deferred for triage and its own issue: repair quality-gate and fix-command
  construction so invalid Ruff arguments fail the wrapper and strict lint
  executes normally.
- Existing workspace coverage is 86% versus the optional 90% threshold.
  This validation found no failing tests and makes no unrelated coverage change.
- MCP clients must restart or refresh after upgrade to discard cached tool
  inventories.
- Archived development artifacts intentionally retain historical references and
  must not be interpreted as current tool guidance.

No issue-specific implementation work remains.

## Version History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-08-18 | Agent | Branch-wide clean-break validation and deferred-work disclosure |
