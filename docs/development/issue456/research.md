<!-- docs/development/issue456/research.md -->
<!-- template=research version=8b7bb3ab created=2026-08-20T19:16Z updated=2026-08-20 -->
# Compact Actionable Tool Summaries — Research

**Status:** APPROVED  
**Version:** 1.1  
**Last Updated:** 2026-08-20

---

## Purpose

Establish the evidence, scope, and Approved Strategy for compact, actionable MCP tool text presentations without weakening the resource cache as the complete structured source of truth.

## Scope

**In Scope:**

- Text produced by `TextPresenter` and configured through `.pgmcp/config/presentation.yaml`.
- All 50 currently registered public tools and their output DTO shapes.
- Configuration validation, presentation alignment, unit and integration tests, active tool documentation, and agent-facing cache guidance.
- Cross-harness output constraints relevant to selecting a conservative text-response ceiling.
- Removal of `tests/documentation/test_c4_doc_alignment.py` and `tests/documentation/test_agent_instruction_search_contract.py`, including all 62 collected cases, because they lock incidental wording, historical migrations, or invalid exact-consumer parity rather than durable behavior.
- Correction of active agent-instruction documentation that currently overstates source/consumer synchronization as mandatory exact parity; authoritative ownership remains, while host consumers may intentionally or temporarily diverge.

**Out of Scope:**

- Tool execution semantics, DTO contents, resource-cache publication, or cache retention.
- Tool-specific Python rendering branches, tool-specific sorting, or changing authoritative DTO order.
- Inline publication of complete verbose logs, tracebacks, JSON Schemas, diffs, or other deep structured payloads.
- A transport-wide byte guarantee for separately embedded MCP resources.
- Unrelated documentation modernization.

## Prerequisites

1. Issue #399 established the current phase-instruction and ownership baseline.
2. The bounded residual documentation reconciliation requested by issue #456 has been completed on this branch.
3. [Documentation Standard](../../coding_standards/DOCUMENTATION_STANDARD.md) governs this Research artifact.

---

## Problem Statement

Current text presentations often expose only an aggregate status line. Routine discovery therefore requires a second resource read even when a small, stable subset of the DTO would answer the immediate question. Richer inline output, however, must not recreate the context pressure and client-side truncation that resource caching was designed to prevent.

## Research Goals

- Audit all 50 public tools and identify the useful inline presentation boundary for each.
- Determine whether one configuration-driven presentation strategy can cover different DTO shapes without tool-specific Python branches.
- Establish the boundary between compact text and the complete cached DTO.
- Select a conservative, reproducible text ceiling across agent harnesses.
- Identify the production, configuration, test, documentation, agent-instruction, template, and consumer blast radius.

---

## Current Architecture and Evidence

| Boundary | Current behavior | Evidence |
|---|---|---|
| Tool result | Tools return frozen Pydantic DTOs. | [tool outputs](../../../mcp_server/schemas/tool_outputs.py), [GitHub models](../../../mcp_server/schemas/github_models.py) |
| Cache | The DTO is published before presentation and remains complete. | [server](../../../mcp_server/server.py), [cache publication schema](../../../mcp_server/schemas/cache_publication.py) |
| Text presentation | `TextPresenter` formats top-level scalar placeholders, notes, next instructions, and the cache URI. Lists and mappings are converted through normal Python string formatting rather than purpose-built Markdown rendering. | [TextPresenter](../../../mcp_server/presenters/text_presenter.py) |
| Configuration | Tool templates are declarative, but the schema has no collection presentation or text-budget concepts. | [presentation config schema](../../../mcp_server/config/schemas/presentation_config.py), [presentation configuration](../../../.pgmcp/config/presentation.yaml) |
| Composite presentation | `ResponsePresenter` combines text with separately embedded validation resources. | [ResponsePresenter](../../../mcp_server/presenters/response_presenter.py), [validation resource presenter](../../../mcp_server/presenters/validation_resource_presenter.py) |
| Documentation | Active references describe a short text summary plus a cache link, but several summaries are currently less informative than those descriptions imply. | [presentation architecture](../../reference/presentation_architecture.md), [tools overview](../../reference/tools/README.md) |

The complete DTO cache is already the correct deep-inspection mechanism. The missing capability is a bounded text projection, not an alternative data authority.

## Harness Evidence

Published harness behavior is not uniform:

| Harness | Evidence | Relevance |
|---|---|---|
| GitHub Copilot CLI | Tool output above 20 KiB is saved to a temporary file by default; this explicitly includes MCP tools. | A server response below 8,000 UTF-8 bytes remains well below this published threshold. |
| Claude Code | Claude warns above 10,000 MCP-output tokens and documents a configurable 25,000-token default maximum. | Token limits are substantially above the proposed byte ceiling, but token-to-byte ratios are content-dependent. |
| Codex | The project has moved from historical 10 KiB/256-line truncation toward configurable token budgets; current behavior remains client/model/version-sensitive. | The historical 10 KiB boundary makes 8,000 bytes a conservative server-side choice. |
| Antigravity | A local harness investigation supplied during this Research observed a 46,080-byte view/file-spill boundary. No authoritative public contract was found. | Treat as observed supporting evidence, not a stable external guarantee. |
| Gemini CLI | No universal documented MCP text-output ceiling was found. | Reinforces choosing a conservative server-owned budget rather than relying on a client default. |

The selected 8,000-byte ceiling is one safety boundary, not a soft target plus a second hard target. Normal summaries should usually remain far smaller.

## Complete Tool Audit

### Compact scalar confirmation remains sufficient

The following 32 tools already expose enough information for their normal immediate decision. They require only the global text ceiling; their complete DTOs remain available in cache:

`health_check`, `restart_server`, `transition_cycle`, `force_cycle_transition`,
`initialize_project`, `save_planning_deliverables`,
`update_planning_deliverables`, `git_diff_stat`, `get_parent_branch`,
`check_merge`, `create_branch`, `git_add_or_commit`, `git_restore`,
`git_checkout`, `git_push`, `git_merge`, `git_delete_branch`,
`git_fetch`, `git_pull`, `create_issue`, `update_issue`, `close_issue`,
`submit_pr`, `merge_pr`, `create_label`, `delete_label`, `add_labels`,
`remove_labels`, `create_milestone`, `close_milestone`,
`transition_phase`, and `force_phase_transition`.

These are primarily confirmations or bounded status responses. Repeating caller-supplied input or complete changed-file sets inline would add noise without improving the next decision.

### Declarative collection presentation is useful

| Tool | Inline decision data | Cache-only detail |
|---|---|---|
| `auto_fix` | Gate names and a bounded modified-file list. | Complete file list and DTO. |
| `get_project_plan` | Phases and their tasks, preserving DTO order. | Complete plan DTO. |
| `git_list_branches` | Bounded branch list with current/upstream identity. | Complete branch list. |
| `git_status` | Bounded modified and untracked path lists. | Complete status DTO. |
| `git_stash` | Bounded stash list when the action returns stashes. | Complete stash list. |
| `list_issues` | Number, title, state, labels, and URL for a bounded issue list. | Complete result set. |
| `list_prs` | Number, title, state, refs, and URL for a bounded PR list. | Complete result set. |
| `list_labels` | Bounded label list. | Complete label set. |
| `list_milestones` | Number, title, and state for a bounded milestone list. | Complete milestone set. |
| `scaffold_artifact` | Bounded created-file list. | Validation schema and complete scaffolding DTO. |
| `run_quality_gates` | Scope, overall result, and bounded gate status/score list. | Verbose stdout/stderr and full gate details. |
| `run_tests` | Counts plus bounded failure identifiers, locations, and short reasons. | Tracebacks, stderr, and complete verbose evidence. |
| `validate_template` | Result/count plus bounded severity/message findings. | Complete finding set. |

`get_project_plan` is the only currently audited response that requires nested collection data to remain actionable. Research requires a generic declarative capability for that shape; Design owns the exact configuration contract.

### Scalar template expansion is useful

| Tool | Required expansion | Reason |
|---|---|---|
| `get_work_context` | Phase instructions and hand-over template. | These are core outputs of the context call. The largest current phase-instruction plus hand-over combination is 2,911 UTF-8 bytes and fits comfortably within the selected ceiling. |
| `get_issue` | URL, labels, and body. | Routine issue inspection should not require a second call when the body fits. |
| `get_pr` | State and body. | Routine PR inspection should expose its actionable content directly when it fits. |
| `safe_edit_file` | Validation findings when present. | Interactive writes can succeed while retaining warnings that must remain visible. |

These are ordinary scalar template expansions. They do not justify special rendering code. The final text limiter handles exceptional length.

### Deliberate resource-oriented exception

`scaffold_schema` returns a nested JSON Schema whose semantics cannot be represented reliably by a bounded item list. Its compact text should identify the artifact type and direct the consumer to the complete cached schema. Adding a generic JSON pretty-printer solely to inline this payload would increase complexity while duplicating the resource authority.

## Documentation Test Debt Added to Scope

The targeted `tests/documentation` run collected 62 cases but did not validate the five changed documents generically. It consists of 13 test functions, with four parameterized functions expanding to 53 cases.

| Current test group | Cases | Research conclusion |
|---|---:|---|
| Issue-specific documentation wording and migration assertions | 9 | Remove. They preserve literal words, section ordering, and temporary migration history rather than supported behavior. |
| Absence of the removed `search_documentation` name | 11 | Remove. This is historical negative locking with no durable product obligation. |
| Exact `host-native repository search` wording | 7 | Remove. The semantic guidance may evolve without a behavioral regression. |
| Byte-exact authoritative-source/consumer equality | 28 | Remove. Authoritative sources establish ownership, but host consumers may intentionally or temporarily diverge; exact parity is not a valid universal invariant. |
| QA headings and required literal marker fragments | 7 | Remove. Substring presence does not demonstrate independent QA behavior. |

Both test files must be deleted during Implementation, not weakened or replaced with equivalent wording assertions. The related active references must also stop describing every tracked consumer as an exact synchronized copy; source authority and consumer equality are separate concerns:

- [C4 documentation alignment tests](../../../tests/documentation/test_c4_doc_alignment.py)
- [Agent instruction search contract tests](../../../tests/documentation/test_agent_instruction_search_contract.py)
- [Agent Instructions Model](../../reference/copilot-agent-instructions-model.md)
- [Workflow Extension Guide](../../reference/workflow-extension-guide.md)

Any durable obligation exposed while deleting them must be evaluated independently. Only an actual uncovered runtime, loaded-configuration, schema, or public-boundary behavior warrants replacement coverage. In particular, first-push behavior belongs in parsed workflow/configuration behavior tests if it is not already protected; it does not justify retaining the current Markdown/YAML substring tests.

## Semantic Defects Found

Synthetic DTO presentation through the current `TextPresenter` reproduced two contradictory messages:

- `run_quality_gates` can say “Quality gates passed successfully” while `overall_pass=False`, because execution success and gate success are different concepts.
- `validate_template` can say “Template validation passed: False”.

Both templates must use outcome-neutral completion wording and expose the actual result as data. This is distinct from the four scalar template expansions above.

## Options Considered

| Option | Benefit | Cost / risk | Decision |
|---|---|---|---|
| Keep count-only text and require resource reads | No production change. | Preserves unnecessary two-step discovery and fails the issue objective. | Rejected |
| Inline complete DTOs | Maximum immediate detail. | Recreates context growth, harness truncation, and duplicated authority. | Rejected |
| Add bespoke renderer logic per tool | Fine-grained output. | Violates configuration ownership, increases drift, and scales poorly. | Rejected |
| Add one bounded declarative projection pipeline | Compact common behavior with per-tool presentation choices in configuration. | Requires a small generic collection capability and robust final text limiting. | Approved |
| Add sorting/filtering semantics | Could prioritize selected records. | Changes authoritative order and expands configuration complexity. | Rejected |
| Add a generic JSON renderer | Could inline `scaffold_schema`. | Adds complexity for one deep-inspection case and duplicates cache data. | Rejected |

---

## Approved Strategy

Human approval was recorded in this Research conversation on 2026-08-20.

1. Preserve every tool DTO and the untruncated resource cache as the complete structured source of truth.
2. Apply one configurable `8,000` UTF-8-byte ceiling to the chat text produced by `TextPresenter`.
3. Use one generic, configuration-driven presentation pipeline. Tools may declare bounded collections and a per-tool item limit in `presentation.yaml`; production code must not branch on tool names.
4. Preserve DTO order. Do not introduce presentation sorting or filtering.
5. Support actionable nested plan data generically; Design will define the minimal configuration interface.
6. Use ordinary templates for `get_work_context`, `get_issue`, `get_pr`, and `safe_edit_file` scalar expansions.
7. Correct the outcome wording for `run_quality_gates` and `validate_template`.
8. Keep tracebacks, stderr, verbose gate logs, full JSON Schemas, diffs, and other deep payloads cache-only.
9. When text exceeds the budget, retain a clear truncation notice and the cache URI within the same budget.
10. The ceiling applies to `TextPresenter` chat text. Separately embedded validation resources remain governed by the existing presentation-resource contract; no transport-wide response-size guarantee is claimed.
11. Preserve supported consumer contracts: no DTO field, tool input, cache URI, or resource payload migration is required. Text becomes additively more informative.
12. Delete both current `tests/documentation` test modules and all 62 collected cases during Implementation.
13. Do not replace removed wording, migration, removed-name, exact-parity, or QA-marker assertions with equivalent textual lock-in.
14. Add replacement coverage only when direct inspection proves an uncovered durable runtime, parsed-configuration, schema, or public-boundary behavior; test that behavior at its owning layer.
15. Preserve `docs/agents/<host>/` as the authoritative ownership layer without requiring all active or derived consumers to remain byte-identical; document intentional or temporary divergence instead of failing a universal equality test.

## Blast Radius

| Area | Expected impact |
|---|---|
| Production code | Generic text projection, collection formatting, and final UTF-8-safe limiting in the presentation layer. No tool execution changes. |
| Configuration | Additive presentation schema and `presentation.yaml` declarations for affected tools. |
| DTOs | No authoritative DTO changes expected. Existing formatted convenience fields may remain even when no longer used by text templates. |
| Tests | Delete both legacy `tests/documentation` modules and their 62 cases. For the feature itself, use presenter unit tests, configuration/alignment tests, multibyte and reserved-cache-suffix boundary tests, collection-order/item-limit tests, nested-plan coverage, and a small representative set of tool presentation tests. Avoid one wording/snapshot test per tool. |
| Test quality | Tests must verify durable presentation contracts rather than snapshot every wording detail. Verbose logs remain cache assertions, not large inline snapshots. |
| Documentation | Presentation architecture and relevant tool references for discovery/project/GitHub/quality/scaffolding must reflect the compact-text/cache boundary. The Agent Instructions Model and Workflow Extension Guide must distinguish authoritative ownership from optional or temporary consumer divergence. |
| Agent instructions | Cache guidance remains valid: agents read resources for complete structured data or verbose logs. Verify wording does not continue to require resource reads for routine summaries that are now inline. |
| Templates / enforcement | Artifact templates are unaffected. Startup presentation alignment must validate any new declarative fields against DTO shapes. |
| Consumers | Routine query consumers gain direct Markdown; consumers needing completeness continue using the same cache URI and DTO. |

## Risks and Verification Expectations

| Risk | Required evidence |
|---|---|
| Byte limiting corrupts UTF-8 or Markdown | Multibyte boundary tests and block-aware truncation tests. |
| Cache link disappears during truncation | Tests proving the cache URI and truncation notice remain inside the configured budget. |
| Collection templates drift from DTO fields | Startup/config alignment validation for collection and nested item placeholders. |
| Rich summaries accidentally inline verbose logs | Representative `run_tests` and `run_quality_gates` tests for normal and verbose DTOs. |
| Nested plan rendering becomes tool-specific | Architecture review proving no tool-name branch exists. |
| Text changes break structured consumers | Tests proving cached DTO publication and content are unchanged. |
| Documentation reintroduces mandatory resource reads or exact-consumer parity | Targeted semantic review and local-link verification of the changed active documents; do not use the removed generic wording suite as evidence. |

## Expected Results

- Routine discovery for work context, project plans, issue/PR lists, and detail views is actionable from one compact text response when the selected content fits.
- Verification tools expose concise evidence without inline tracebacks or verbose logs.
- Configured collections respect their item limit and preserve DTO order.
- Every `TextPresenter` result remains within 8,000 UTF-8 bytes while preserving a truncation notice and cache URI when content is omitted.
- Cached DTOs remain complete and unchanged.
- Presentation configuration remains the source of truth for per-tool content choices.
- No tool-specific presentation branches are introduced.
- The 62 brittle documentation cases are removed without textual replacements; any retained invariant is tested only through its owning runtime or parsed-configuration boundary.
- Active documentation preserves authoritative host sources while allowing explicit intentional or temporary consumer divergence.

## Open Questions

None at the strategy boundary. Exact configuration models and presenter interface changes belong to Design.

## Related Documentation

- [Documentation Standard](../../coding_standards/DOCUMENTATION_STANDARD.md)
- [Presentation Architecture](../../reference/presentation_architecture.md)
- [Tools Overview](../../reference/tools/README.md)
- [Discovery Tools](../../reference/tools/discovery.md)
- [Project Tools](../../reference/tools/project.md)
- [GitHub Tools](../../reference/tools/github.md)
- [Quality Tools](../../reference/tools/quality.md)
- [Scaffolding Tools](../../reference/tools/scaffolding.md)

## External References

- [GitHub Copilot CLI context management](https://docs.github.com/en/copilot/concepts/agents/copilot-cli/context-management)
- [Claude Code MCP output limits](https://docs.anthropic.com/en/docs/claude-code/mcp)
- [Codex configurable tool-output limit discussion](https://github.com/openai/codex/issues/6426)
- [Codex historical/default limit follow-up](https://github.com/openai/codex/issues/7867)
- [Gemini CLI repository](https://github.com/google-gemini/gemini-cli)

---

## Version History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-08-20 | Agent | Approved research, complete tool audit, and strategy boundary |
| 1.1 | 2026-08-20 | Agent | Add mandatory removal of brittle documentation tests to the approved scope |
