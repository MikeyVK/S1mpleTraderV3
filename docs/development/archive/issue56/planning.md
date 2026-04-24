# Issue #56 Planning: Unified Artifact System

| Metadata | Value |
|----------|-------|
| **Date** | 2026-01-17 |
| **Author** | GitHub Copilot |
| **Status** | DRAFT |
| **Issue** | [#56](https://github.com/user/repo/issues/56) |
| **Epic** | [#49 - Platform Configurability](https://github.com/user/repo/issues/49) |
| **Phase** | Planning |
| **Scope** | Medium - Unified artifact registry with core tooling |

---

## Overview

This planning document defines **WHEN** and **WHAT** will be built for Issue #56, without specifying **HOW**. Design details will follow in the design phase.

**From Research Decisions:**
- ✅ Single artifacts.yaml (not separate components.yaml + documents.yaml)
- ✅ Remove base_path duplication (use project_structure.yaml only)
- ✅ Single TemplateScaffolder (eliminate 9 scaffolder classes)
- ✅ ArtifactManager (unified orchestration)
- ✅ SearchService (extract from DocManager)
- ✅ Medium scope (Epic #49 only, defer enforcement to Epic #18)

---

## TDD Cycle Breakdown

### Phase 1: Configuration Foundation
**Cycles 1-3 (~3 days)**

#### Cycle 1: ArtifactRegistryConfig Pydantic Model
**WHAT:** Config model that loads artifacts.yaml
**WHEN:** First (foundation for all other work)
**Tests:**
- Config loads from .st3/artifacts.yaml
- Singleton pattern works (from_file() caches)
- reset_instance() clears singleton (testing support)
- ConfigError raised on missing file
- ConfigError raised on invalid YAML syntax
- Validates required fields per artifact type
- State machine definitions parsed correctly

#### Cycle 2: ArtifactDefinition Nested Model
**WHAT:** Nested Pydantic model for individual artifacts
**WHEN:** After ArtifactRegistryConfig structure exists
**Tests:**
- Parses artifact with all fields (type, name, template, state_machine)
- Validates state_machine.states is list
- Validates state_machine.initial_state exists in states
- Validates state_machine.valid_transitions structure
- Optional fields work (test_base_path, generate_test)
- ValidationError on unknown artifact type

#### Cycle 3: Project Structure Extensions
**WHAT:** Extend project_structure.yaml with document directories
**WHEN:** After artifact config model works
**Tests:**
- Document directories (docs/architecture, docs/development, docs/reference) configured
- allowed_artifact_types includes document types
- DirectoryPolicyResolver finds directories for document artifact types
- Directory validation works for new document paths

---

### Phase 2: Unified Scaffolding
**Cycles 4-6 (~3 days)**

#### Cycle 4: TemplateScaffolder (Extends BaseScaffolder)
**WHAT:** Single scaffolder that uses templates from config
**WHEN:** After ArtifactRegistryConfig can provide template paths
**Tests:**
- Extends BaseScaffolder correctly
- Accepts JinjaRenderer via constructor (DI pattern)
- validate() checks artifact_type exists in registry
- validate() checks required_fields present in context
- scaffold() loads correct template from registry
- scaffold() renders template with context
- scaffold() returns ScaffoldResult dataclass
- ValidationError on unknown artifact_type
- ValidationError on missing required_fields

#### Cycle 5: FilesystemAdapter Integration
**WHAT:** Safe file operations for templates and output
**WHEN:** After TemplateScaffolder core logic works
**Tests:**
- Template reading via FilesystemAdapter
- Path validation (templates within workspace)
- Output writing via FilesystemAdapter
- Path validation (output within workspace)
- IOError translated to ConfigError/ValidationError

#### Cycle 6: Template Registry Loading
**WHAT:** TemplateScaffolder gets templates from ArtifactRegistryConfig
**WHEN:** After both TemplateScaffolder and ArtifactRegistryConfig work
**Tests:**
- TemplateScaffolder loads artifact definition from registry
- Correct template_path resolved
- Fallback template used when primary missing
- Template metadata loaded (Issue #52 integration)

---

### Phase 3: Manager Layer
**Cycles 7-8 (~2 days)**

#### Cycle 7: ArtifactManager Core
**WHAT:** Manager that orchestrates artifact scaffolding
**WHEN:** After TemplateScaffolder proven
**Tests:**
- Constructor accepts workspace_root, registry, fs_adapter (all optional DI)
- scaffold_artifact() delegates to TemplateScaffolder
- get_artifact_path() uses DirectoryPolicyResolver
- validate_artifact() exists (delegates to ValidationService)
- Stores workspace_root as instance variable
- NOT singleton (instantiated per tool)
- ValidationError propagates from TemplateScaffolder

#### Cycle 8: Directory Resolution Integration
**WHAT:** ArtifactManager resolves output paths via DirectoryPolicyResolver
**WHEN:** After ArtifactManager core methods work
**Tests:**
- get_artifact_path() finds correct directory for artifact type
- Multiple allowed directories handled correctly
- PreflightError on no valid directory found
- Path construction includes artifact name
- Extension added based on artifact type (.py, .md, etc.)

---

### Phase 4: Search Extraction
**Cycles 9-10 (~2 days)**

#### Cycle 9: SearchService (Stateless)
**WHAT:** Extract search logic from DocManager into stateless service
**WHEN:** After manager layer proven (architectural precedent set)
**Tests:**
- search_index() is static method
- Accepts index, query, max_results parameters
- Returns ranked results
- calculate_relevance() scoring algorithm works
- extract_snippets() returns context around matches
- No instance state required (pure functions)

#### Cycle 10: SearchService Integration
**WHAT:** Update search_documentation tool to use SearchService
**WHEN:** After SearchService core algorithms work
**Tests:**
- search_documentation tool calls SearchService.search_index()
- Index building extracted to separate concern
- Tool still works with existing API
- DocManager deprecated (marked for removal)

---

### Phase 5: Tool Unification
**Cycles 11-12 (~2 days)**

#### Cycle 11: scaffold_artifact Tool
**WHAT:** Unified tool replacing scaffold_component and scaffold_design_doc
**WHEN:** After ArtifactManager fully functional
**Tests:**
- Inherits from BaseTool
- ScaffoldArtifactInput Pydantic model validates input
- Optional ArtifactManager injection (DI pattern)
- execute() calls manager.scaffold_artifact()
- Returns ToolResult.text() on success
- Returns ToolResult.error() on ValidationError
- input_schema property returns JSON schema
- @tool_error_handler automatic error conversion

#### Cycle 12: Tool Unification Complete
**WHAT:** scaffold_artifact works for ALL artifact types (code + docs)
**WHEN:** After scaffold_artifact basic functionality proven
**Tests:**
- Code artifact scaffolding works (dto, worker, adapter)
- Document artifact scaffolding works (research, planning, design)
- scaffold_component marked deprecated
- scaffold_design_doc marked deprecated
- Integration test: full end-to-end scaffolding workflow

---

### Phase 6: Migration & Cleanup
**Cycles 13-14 (~3 days)**

#### Cycle 13: Breaking Changes
**WHAT:** Rename components.yaml → artifacts.yaml, update all references
**WHEN:** After new architecture fully proven
**Tests:**
- components.yaml deleted
- artifacts.yaml created with merged content
- ComponentRegistryConfig renamed to ArtifactRegistryConfig
- allowed_component_types → allowed_artifact_types
- All tools updated to use ArtifactManager
- All managers updated to use ArtifactRegistryConfig
- Existing integration tests pass with new architecture

#### Cycle 14: Final Validation
**WHAT:** Full regression test suite, cleanup legacy code
**WHEN:** After all breaking changes applied
**Tests:**
- All unit tests pass
- All integration tests pass
- 9 scaffolder stub classes deleted (only BaseScaffolder remains)
- DocManager removed (SearchService replacement complete)
- No references to old config names
- No hardcoded artifact data in Python code
- Quality gates pass (linting, type checking)

---

## Deliverables

### Configuration Files
1. `.st3/artifacts.yaml` - Unified registry (replaces components.yaml)
2. `.st3/project_structure.yaml` - Extended with document directories
3. `.st3/policies.yaml` - Updated artifact_state_triggers (Epic #18 prep)

### Python Code
1. `mcp_server/config/artifact_registry_config.py` - Pydantic models
2. `mcp_server/scaffolders/template_scaffolder.py` - Unified scaffolder
3. `mcp_server/managers/artifact_manager.py` - Orchestration
4. `mcp_server/services/search_service.py` - Stateless search (NEW pattern)
5. `mcp_server/tools/scaffold_artifact.py` - Unified tool

### Deprecated/Deleted
1. `mcp_server/config/component_registry_config.py` - Renamed
2. `.st3/components.yaml` - Deleted
3. 9 scaffolder stub classes - Deleted (only stubs existed)
4. `mcp_server/managers/doc_manager.py` - Removed
5. `mcp_server/tools/scaffold_component.py` - Marked deprecated
6. `mcp_server/tools/scaffold_design_doc.py` - Marked deprecated

### Tests
1. `tests/unit/config/test_artifact_registry_config.py`
2. `tests/unit/scaffolders/test_template_scaffolder.py`
3. `tests/unit/managers/test_artifact_manager.py`
4. `tests/unit/services/test_search_service.py`
5. `tests/integration/test_scaffold_artifact_tool.py`
6. Update all existing integration tests

---

## Dependencies

### External
- None (all dependencies already in project)

### Internal (Issue #56 depends on)
- ✅ Issue #52: Template validation (ValidationService exists)
- ✅ Issue #54: Config foundation (ComponentRegistryConfig, DirectoryPolicyResolver)
- ✅ Issue #55: Git conventions (pattern established)

### Future (depends on Issue #56)
- Issue #57+: Epic #18 enforcement (PolicyEngine uses artifacts.yaml)
- Future: Git text scaffolding (issue descriptions, PR templates)
- Future: Test scaffolding automation

---

## Risks & Mitigations

### Risk 1: Breaking Change Impact
**Risk:** Renaming components.yaml → artifacts.yaml breaks existing code
**Mitigation:** 
- Comprehensive test coverage before migration
- All changes in single atomic commit
- Cycle 13-14 dedicated to migration
- Pattern established by Issue #50 (breaking change acceptable)

### Risk 2: Scope Creep
**Risk:** Attempting Epic #18 enforcement during Issue #56
**Mitigation:**
- Strict scope definition (Epic #49 only = data externalization)
- State machine definitions stored, NOT executed
- No artifact_state_triggers execution
- Clear OUT OF SCOPE section in research

### Risk 3: Pattern Introduction (Service)
**Risk:** SearchService introduces new pattern without precedent
**Mitigation:**
- Document pattern clearly in design phase
- Simple extraction (no new concepts beyond statelessness)
- Pattern useful for future services
- Low coupling (easy to iterate)

### Risk 4: FilesystemAdapter Dependency
**Risk:** FilesystemAdapter may not exist or have different interface
**Mitigation:**
- Research confirmed it exists (mcp_server/adapters/filesystem_adapter.py)
- Adapter pattern well-established
- DI allows mocking in tests
- Cycle 5 dedicated to integration

---

## Success Criteria

Issue #56 succeeds when:

1. ✅ **Single artifacts.yaml** exists with code + document types
2. ✅ **No path duplication** (base_path removed, use project_structure.yaml)
3. ✅ **Single TemplateScaffolder** (9 scaffolder classes deleted)
4. ✅ **ArtifactManager exists** (unified orchestration)
5. ✅ **SearchService exists** (extracted from DocManager)
6. ✅ **scaffold_artifact tool** works for ALL artifact types
7. ✅ **State machines defined** in artifacts.yaml (structure only)
8. ✅ **All tests pass** (~95% coverage maintained)
9. ✅ **No hardcoded artifact data** in Python code
10. ✅ **Breaking changes complete** (no components.yaml references)

---

## Timeline Estimate

| Phase | Cycles | Estimated Days | Cumulative |
|-------|--------|----------------|------------|
| Configuration Foundation | 1-3 | 3 days | 3 days |
| Unified Scaffolding | 4-6 | 3 days | 6 days |
| Manager Layer | 7-8 | 2 days | 8 days |
| Search Extraction | 9-10 | 2 days | 10 days |
| Tool Unification | 11-12 | 2 days | 12 days |
| Migration & Cleanup | 13-14 | 3 days | 15 days |

**Total Estimate:** ~15 working days (3 weeks)

**Note:** Estimates assume:
- Full-time focus on Issue #56
- No major blockers
- Design phase completes quickly (architecture already defined in research)

---

## Next Steps

1. ✅ **Planning complete** → Approve planning.md
2. ➡️ **Force design phase** → Create design.md with schemas and implementation details
3. 🔄 **Design phase** → Complete artifacts.yaml schema, class designs, sequence diagrams
4. 🔄 **TDD phase** → Execute cycles 1-14
5. 🔄 **Integration** → Verify all integration tests pass
6. 🔄 **Documentation** → Update reference docs, CHANGELOG

---

**Status:** DRAFT → Ready for Review  
**Next:** Force design phase within refactor workflow  
**Estimate:** 15 days / 14 TDD cycles