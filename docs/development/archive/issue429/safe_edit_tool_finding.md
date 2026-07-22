<!-- docs\development\issue429\safe_edit_tool_finding.md -->
<!-- template=generic_doc version=43c84181 created=2026-07-18T17:07Z updated= -->
# Safe Edit Tool UX Finding (Deferred Work)

**Status:** DRAFT  
**Version:** 1.0  
**Last Updated:** 2026-07-18

---

## Summary

The safe_edit_file tool requires exact file line counts to append, leading to fragile agent edits. We propose adding an explicit append mode or relative index support.

---

## The Problem

The `safe_edit_file` tool provides an `insert_lines` operation which requires an absolute `at_line` integer. To append, the documentation states to use `file_lines + 1`. This forces the agent to accurately measure the file length before making the edit. If the file length changes (e.g., due to previous bulk edits or trailing newline interpretations), the calculated `at_line` becomes out-of-bounds, causing the tool to reject the change in `strict` mode.

When faced with this rejection during Issue #429, the agent erroneously fell back to using `line_edits` with a `start_line` and `end_line`, which explicitly *replaced* the end of the file rather than appending to it. This led to unintentional data loss (document corruption).

Furthermore, even if an `append: true` mode existed, simply appending to the absolute end of a document is often structurally incorrect. For example, appending content *after* a `## Related Documentation` or `## Version History` table instead of inserting it before these footers. This highlights a secondary risk: agents lack structural awareness when blindly appending.

## Proposed Solution (Deferred Work)

To make the tool more robust against AI line-counting errors, the `safe_edit_file` tool should natively support appending text without requiring explicit line numbers.
Possible implementations:
1. Add an explicit `append: true` or `append_content: "..."` mode.
2. Support relative indices in `at_line` (e.g., `at_line: -1` or `at_line: eof`).

This work is deferred to a future issue and should be handed over to the `@co` agent during PR creation.

---

## Related Documentation
None

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-07-18 | Agent | Initial draft |