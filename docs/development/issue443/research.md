<!-- docs\development\issue443\research.md -->
<!-- template=research version=8b7bb3ab created=2026-08-18T20:24Z updated= -->
# Issue #443 Research: Remove the Redundant search_documentation Tool

**Status:** APPROVED  
**Version:** 1.0  
**Last Updated:** 2026-08-18

---

## Purpose

Establish the complete removal boundary, preservation goals, dependency inventory, risks, and approved clean-break policy before planning.

## Scope

**In Scope:**
Search-specific tool/input/output symbols, bootstrap and presentation registration, orphaned services, active agent sources and tracked consumers, role allowlists, active documentation and diagrams, release notes, dedicated and mixed tests, and negative published-inventory verification.

**Out of Scope:**
Replacement search, embeddings, external search servers, new indexing infrastructure, an authoritative-context tool, deprecation aliases, compatibility bridges, and unrelated discovery or resource-cache refactors.

## Prerequisites

Read these first:
1. GitHub issue #443 and its approved clean-break strategy
2. docs/coding_standards/ARCHITECTURE_PRINCIPLES.md
3. docs/coding_standards/DOCUMENTATION_STANDARD.md
4. docs/reference/copilot-agent-instructions-model.md
---

## Problem Statement

The generic search_documentation MCP tool duplicates stronger host-native repository search while exposing a narrower implementation than its public documentation claims. Removing it safely requires eliminating its isolated runtime chain and every active consumer without damaging shared discovery behavior.

## Research Goals

- Identify every runtime, contract, presentation, instruction, documentation, release, and test dependency.
- Separate dedicated search infrastructure from shared discovery and workflow behavior that must remain.
- Confirm the clean-break compatibility policy per affected boundary.
- Provide evidence-backed seams, risks, and expected results for planning.

---

## Background

The tool was introduced as documentation discovery infrastructure but currently scans only Markdown under a fixed docs root and exposes literal substring ranking behind claims of semantic/fuzzy search. Host environments already provide repository-wide search over code and documentation.

---

## Findings

### Current runtime boundary

`SearchDocumentationTool` is registered directly by `mcp_server/bootstrap.py` and is presented through `.pgmcp/config/presentation.yaml`. Its implementation in `mcp_server/tools/discovery_tools.py` rebuilds an in-memory index of `<workspace_root>/docs/**/*.md` for every call, delegates literal ranking to `SearchService`, maps results to two dedicated DTOs, and returns them through the normal cached tool-response pipeline.

The advertised semantic/fuzzy behavior is not implemented. `SearchService` performs case-insensitive contiguous substring counts with fixed title/path/content weights. `DocumentIndexer` reads every Markdown file on each call, silently skips unreadable files, derives scope from the first directory component, and does not calculate line ranges. The tool fixes `max_results` at ten and maps absent line data to line 1.

### Dependency inventory

| Boundary | Concrete surfaces | Coupling assessment |
|---|---|---|
| MCP input/tool | `SearchDocumentationInput`, `SearchDocumentationTool` in `mcp_server/tools/discovery_tools.py` | Search-only; `GetWorkContextTool` shares the module and must remain |
| Services | `mcp_server/services/document_indexer.py`, `mcp_server/services/search_service.py` | No production consumers outside `SearchDocumentationTool` |
| Output contracts | `SearchResultDTO`, `SearchDocumentationOutput` in `mcp_server/schemas/tool_outputs.py` | No remaining production consumers |
| Composition | import and registration in `mcp_server/bootstrap.py` | One direct import and one tool-list entry |
| Presentation | `search_documentation` entry in `.pgmcp/config/presentation.yaml` | Must disappear with the tool to preserve presentation/tool alignment |
| Agent instructions | root and host-specific `AGENTS.md` files, Codex research rule, VS Code `@co` and `@qa` allowlists | Current instructions mandate or explicitly allow the removed tool |
| Active documentation | tool references, discovery guide, manuals, architecture diagrams, workflow guidance | Contains incorrect semantic/fuzzy/TF-IDF, caching, scope, and line-number claims |
| Release boundary | `CHANGELOG.md` and release assets selected by `.pgmcp/config/release_manifest.yaml` | Breaking removal must be visible in the next release notes and synchronized release assets |
| Tests | search service unit tests, service/indexer integration tests, tool E2E tests, discovery-tool unit tests, one acceptance segment, and extra-forbid coverage | Dedicated search tests become obsolete; mixed files must preserve unrelated coverage |

### Host and source synchronization

`docs/agents` is shipped as a release asset. Search requirements occur in authoritative host variants and in tracked workspace consumers: root `AGENTS.md`, `.agents/AGENTS.md`, the three host instruction variants, Codex research rules, and VS Code `@co`/`@qa` allowlists. `@imp` uses a wildcard and needs no allowlist edit. Source variants must be updated first and their tracked consumers synchronized so no host continues to mandate an unavailable MCP tool.

### Preservation goals

- `GetWorkContextTool` and all of its imports, DTOs, registration, presentation, and tests remain intact.
- Generic resource caching and presentation alignment remain intact; only the removed tool-specific entry and contracts disappear.
- Scaffold acceptance behavior unrelated to search remains covered after the search-specific portion of issue #56 acceptance coverage is removed.
- `@co`, `@imp`, and `@qa` retain their existing authority boundaries; only an obsolete allowlist item disappears.
- Host agents use their native repository-search capability for both code and documentation without a pgmcp compatibility alias.
- Published active documentation and release assets describe the current tool inventory accurately.

### Risks and candidate seams

| Risk | Evidence | Candidate seam for planning |
|---|---|---|
| Accidentally removing `get_work_context` while editing the shared discovery module | Both tools live in `discovery_tools.py` | Treat search-specific symbols and shared discovery behavior as separate verification boundaries |
| Bootstrap or presenter drift | Tool registration and presentation are separately declared | Verify negative tool inventory and presentation alignment together |
| Agent-source drift | The same mandate exists across host sources and tracked consumers | Group updates by authoritative host source and synchronized consumer set |
| Over-deleting mixed tests | `test_discovery_tools.py` and issue #56 acceptance contain unrelated coverage | Remove only search-specific sections and retain the rest |
| Leaving misleading architectural claims | Multiple active manuals describe services and semantic behavior | Scan active docs after deletion for tool and dedicated service names plus semantic-search claims |
| Treating archived plans as current guidance | Twenty-two archived files mention the historical capability | Preserve archives as historical records; exclude them from the active/published-current-doc scan |
| Unclear client behavior after upgrade | MCP clients may cache a previously listed tool | Release notes should state that upgraded clients must refresh/restart and old calls receive tool-not-found |

No external research is necessary: the removal policy and all affected contracts are repository-specific, and direct repository evidence is sufficient.

## Open Questions

None. The user approved preserving archived development artifacts as historical evidence while correcting every active and shipped surface.


---

## Approved Strategy

Use the issue-approved clean break with no deprecation, alias, compatibility bridge, or replacement search implementation. The user explicitly approved the historical-archive boundary on 2026-08-18.

| Boundary | Approved policy |
|---|---|
| Public MCP tool | Remove the name, input schema, callable registration, presentation entry, and output contracts in one release |
| Internal services | Remove `SearchService` and `DocumentIndexer`; repository evidence shows no remaining production consumer |
| Existing clients | No runtime fallback; after upgrade/restart, stale invocations receive the normal unknown-tool behavior |
| Agent behavior | Remove mandates and explicit allowlist entries; document host-native repository search as the default |
| Active documentation and release assets | Remove obsolete references and false semantic/fuzzy/TF-IDF claims; add a breaking removal entry to the next release notes |
| Historical archives | Preserve unchanged as historical evidence; they are not current tool guidance or shipped active instructions |
| Tests | Remove dedicated capability tests, preserve unrelated mixed-file coverage, and add negative inventory/alignment proof |
| Future discovery capability | Out of scope; any pgmcp-specific discovery tool requires a new issue and unique workflow semantics |

---

## Expected Results

- `list_tools` and published inventories no longer expose `search_documentation`.
- Importing and bootstrapping the server no longer requires any search-specific input, tool, DTO, service, or presentation symbol.
- `GetWorkContextTool` remains registered and fully covered.
- No active agent instruction or role allowlist refers to the removed tool; host-native repository search is the documented path.
- Active manuals, references, examples, diagrams, and release notes no longer make misleading search claims.
- Dedicated search tests and orphaned services are absent while all unrelated discovery, scaffolding, presenter, and acceptance coverage remains green.
- Repository-wide active-surface scans, the full test suite, and functioning quality gates pass.

## Related Documentation
- **[docs/reference/tools/discovery.md][related-1]**
- **[docs/reference/copilot-agent-instructions-model.md][related-2]**
- **[docs/manuals/architecture.md][related-3]**
- **[CHANGELOG.md][related-4]**

<!-- Link definitions -->

[related-1]: ../../reference/tools/discovery.md
[related-2]: ../../reference/copilot-agent-instructions-model.md
[related-3]: ../../manuals/architecture.md
[related-4]: ../../../CHANGELOG.md

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-08-18 | Agent | Approved clean-break research baseline and historical-archive boundary |