<!-- task37-issue-example.md -->
<!-- template=issue version=8dd42510 created=2026-02-06T11:04Z updated= --># Implement tracking templates for VCS workflow artifacts

Add tier1_base_tracking + tier2 text/markdown + concrete templates for commit messages, PR descriptions, and issue descriptions as part of template library management.
## Problem
No template library exists for tracking artifacts (commit messages, PR descriptions, issue descriptions). These VCS workflow artifacts need consistent structure and should support cross-branch pattern imports.

## Expected Behavior

- tier1_base_tracking.jinja2 with minimal workflow metadata structure (NO status lifecycle, NO versioning)
- tier2_tracking_text.jinja2 for plain text formatting
- tier2_tracking_markdown.jinja2 for markdown formatting
- concrete/commit.txt.jinja2 (Conventional Commits format)
- concrete/pr.md.jinja2 (standard PR sections)
- concrete/issue.md.jinja2 (problem/solution structure)
- Cross-branch pattern imports working (tier3 patterns from DOCUMENT branch used in TRACKING branch)
- Comprehensive test coverage
## Actual Behavior

No tracking templates exist. Current system only has CODE and DOCUMENT templates.
## Context

Part of Issue #72 Task 3.7 - Template Library Management (11h estimated).

Tracking artifacts are DISTINCT from documents:
- NO status lifecycle (ephemeral workflow metadata)
- NO versioning (single-version artifacts)
- NO Purpose/Scope sections (not knowledge documentation)
- Workflow context only (timestamp, branch, phase, type)
## Related Documentation
- **[docs/development/issue72/planning.md][related-1]**
- **[docs/development/issue72/tracking-type-architecture.md][related-2]**
- **[docs/development/issue72/whitespace_strategy.md][related-3]**
- **[docs/architecture/DTO_ARCHITECTURE.md][related-4]**

---

**Metadata:**
- Labels: type:feature, area:templates, priority:high
- Milestone: Issue #72 Template Library
- Assignees: agent
