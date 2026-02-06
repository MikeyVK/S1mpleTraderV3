<!-- task37-pr-example.md -->
<!-- template=pr version=93bb9b4e created=2026-02-06T11:04Z updated= --># feat(templates): implement Task 3.7 tracking templates

Implements tier1_base_tracking + tier2 text/markdown + 3 concrete templates for VCS workflow artifacts (commit messages, PR descriptions, issue descriptions).
## Changes
- Created tier1_base_tracking.jinja2 (minimal workflow metadata structure)
- Created tier2_tracking_text.jinja2 (plain text formatting for commit messages)
- Created tier2_tracking_markdown.jinja2 (markdown formatting for PR/issue descriptions)
- Created concrete/commit.txt.jinja2 (Conventional Commits format)
- Created concrete/pr.md.jinja2 (PR description with standard sections)
- Created concrete/issue.md.jinja2 (issue description with problem/solution structure)
- Updated .st3/artifacts.yaml with tracking artifact definitions

## Testing
Created comprehensive test suite:
- 6 existence tests (tier1/tier2/concrete templates)
- 11 rendering tests (commit 3, pr 4, issue 4)
- 6 tier chain validation tests
- 2 cross-branch pattern tests

All 25 tests passing (100% success rate).
## Checklist

- [x] All tests passing
- [x] Templates follow tier architecture
- [x] Cross-branch patterns validated
- [x] Documentation updated
- [x] artifacts.yaml updated

## Related Documentation
- **[docs/development/issue72/planning.md][related-1]**
- **[docs/development/issue72/tracking-type-architecture.md][related-2]**
- **[docs/development/issue72/whitespace_strategy.md][related-3]**

---

Closes: #72