<!-- docs\development\issue459\pr.md -->
<!-- template=pr version=93bb9b4e created=2026-08-22T19:05Z updated= -->
# feat: Expose structured quality-gate findings for bounded presentation

Expose actionable quality-gate diagnostics as additive structured records, render a
bounded nested projection, and retain complete raw evidence in the MCP Resource cache.

## Changes

## Delivered Scope

- Add frozen, extra-forbidden `GateFindingDTO` records beneath
  `GateResultDTO.findings`.
- Preserve `ViolationParser` and `QAManager` as normalization authorities while
  `RunQualityGatesTool` performs structural field adaptation only.
- Render ordered findings through the existing declarative nested collection mechanism,
  with ten gates and ten findings per gate plus the universal 8,000 UTF-8-byte ceiling.
- Keep gate and finding `details` cache-only and preserve every record in the
  authoritative cached DTO.
- Reconcile active quality-tool and presentation-architecture references with validated
  behavior.

## Compatibility

The change is additive. Existing tool inputs, output fields, resource URIs, failure
envelopes, verbose raw gate details, and gates without findings remain compatible.
Generic presenter, presentation-schema, manager, and parser behavior required no
migration.

## Primary Artifacts

- [Research and Approved Strategy](https://github.com/MikeyVK/phase-gate-mcp/blob/feature/459-structured-quality-gate-findings/docs/development/issue459/research.md)
- [Design](https://github.com/MikeyVK/phase-gate-mcp/blob/feature/459-structured-quality-gate-findings/docs/development/issue459/design.md)
- [Implementation Plan](https://github.com/MikeyVK/phase-gate-mcp/blob/feature/459-structured-quality-gate-findings/docs/development/issue459/planning.md)
- [Validation Report](https://github.com/MikeyVK/phase-gate-mcp/blob/feature/459-structured-quality-gate-findings/docs/development/issue459/validation.md)
- [Quality Tool Reference](https://github.com/MikeyVK/phase-gate-mcp/blob/feature/459-structured-quality-gate-findings/docs/reference/tools/quality.md)
- [Presentation Architecture](https://github.com/MikeyVK/phase-gate-mcp/blob/feature/459-structured-quality-gate-findings/docs/reference/presentation_architecture.md)

## Additional Traveling Artifact

- [Issue #460 Research](https://github.com/MikeyVK/phase-gate-mcp/blob/feature/459-structured-quality-gate-findings/docs/development/issue460/research.md) is intentionally included
  at the repository owner's explicit direction.
- It is not part of issue #459's implementation or Validation claims and does not close
  issue #460.

## Tracking State

Issue #459 is reconciled with its Approved Strategy, delivered behavior, additive
compatibility, independent evidence, and completed acceptance criteria. Issue #460
remains open in Research under its own tracking state.

## Residual Risk

The validated branch was clean, so live runtime output contained empty finding
collections. Public tool/presenter tests cover populated, message-only, over-limit, and
cache-complete finding behavior without intentionally breaking production files.

## Testing

- Focused structured-output and presentation tests: 49 passed, 0 failed.
- Complete workspace suite: 2,863 passed, 0 failed, 2 skipped, 0 errors.
- Branch-wide quality gates: overall pass across all four implementation files.
- Ruff formatting, strict lint, imports, line length, Pyright, and mcp_server typing
  passed.
- Server restart, runtime presentation alignment, and live cached findings fields were
  verified.
- Documentation-only follow-up changes were checked through focused stale-claim,
  contract, structure, and local-link inspection; they did not invalidate the
  implementation evidence.

## Checklist

- [x] Code follows project standards
- [x] Tests added/updated
- [x] Documentation updated
- [x] Quality gates passing

## ⚠️ Breaking Changes

None. The public DTO extension and presentation behavior are additive.

## Deferred Work

None identified for issue #459. Issue #460 remains a separately tracked open chore and
is not closed by this PR.

---

Closes: #459