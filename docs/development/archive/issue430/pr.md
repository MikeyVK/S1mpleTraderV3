<!-- docs\development\issue430\pr.md -->
<!-- template=pr version=93bb9b4e created=2026-07-19T08:06Z updated= -->
# Refactor: Rename human_approval to human_approval_message in force transition tools

This PR renames the parameter human_approval to human_approval_message across all tools (phase and cycle), schemas, managers, unit/integration tests, and active documentation. It also implements strict input validators to reject boolean values and empty/whitespace approval strings.
## Changes
- Renamed parameter to human_approval_message in PhaseStateEngine signatures.
- Renamed parameters in phase transition and cycle transition input/output models.
- Implemented @field_validator Mode before to reject boolean inputs for human_approval_message.
- Added minLength=1 constraints in tool input models for skip_reason and human_approval_message.
- Updated active AGENTS.md files, reference manuals, and discovery guides.
- Verified legacy compatibility where old JSON structures containing 'human_approval' load successfully.

## Testing
- run_tests(path='tests/') -> 2738 passed, 0 failed.
- run_quality_gates(scope='project') -> overall pass: True (Ruff strict lint/format, Pyright).
## Checklist

- [ ] All tests are green
- [ ] Quality gates are passing
- [ ] Legacy state compatibility is verified by unit tests
- [ ] All active documentation references updated

## ⚠️ Breaking Changes

None. Historical audit entries containing 'human_approval' continue to parse correctly.
## Related Documentation
- **[docs/development/issue430/planning.md][related-1]**
- **[docs/development/issue430/validation.md][related-2]**

---

Closes: #430