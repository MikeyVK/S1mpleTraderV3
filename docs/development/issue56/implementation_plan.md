# Issue #56 Fix-Forward Implementation Plan: Integratie & Migratie naar Unified Artifact System

| Metadata | Value |
|----------|-------|
| **Date** | 2026-01-18 |
| **Author** | GitHub Copilot (GPT-5.2) |
| **Status** | APPROVED |
| **Issue** | #56 |
| **Phase** | Integration Planning |
| **Goal** | Werkende, uniforme integratie in live MCP server |

---

## 0. Executive Summary

De fundering voor Issue #56 is grotendeels aanwezig (artifacts.yaml, ArtifactRegistryConfig, TemplateScaffolder, ArtifactManager, SearchService/DocumentIndexer en tests), maar de **integratie in de live MCP-server ontbreekt** of is inconsistent.

Dit plan kiest bewust voor een **clean break (optie B)**:

- **Geen mix** van nieuwe en legacy paden.
- **Geen alias-entrypoints** die oude tool-namen “doorrouteren” naar nieuw gedrag.
- **Eén source-of-truth** voor artifact types en templates: `.st3/artifacts.yaml`.

Het doel is een codebase die eenduidig is voor mensen én agents: één manier van scaffolding, één manier van search, één error-contract.

---

## 1. Current State (Observed)

### 1.1 Functional gaps

- `search_documentation` gebruikt nog `DocManager` met hardcoded `TEMPLATES` en `SCOPE_DIRS`.
- `TemplatesResource` expose’t nog `DocManager.TEMPLATES`.
- Nieuwe `SearchService` + `DocumentIndexer` zijn niet aangesloten op `SearchDocumentationTool`.
- Nieuwe `scaffold_artifact` tool bestaat, maar is **niet geregistreerd** in `mcp_server/server.py`.
- Bestaande `scaffold_component` flow gebruikt nog `.st3/components.yaml` en `mcp_server/scaffolding/*`.
- `.st3/components.yaml` bestaat nog naast `.st3/artifacts.yaml` → parallelle registries.

### 1.2 Architectural gaps

- Er zijn nu meerdere error-hierarchieën:
  - `mcp_server/core/exceptions.py` (bestaand, MCPError-gebaseerd)
  - `mcp_server/core/errors.py` (nieuw)
  - `ConfigError` in `mcp_server/config/artifact_registry_config.py` (nieuw)

Dit veroorzaakt inconsistent gedrag in tool error-handling (runtime errors vallen buiten catches).

### 1.3 Quality gaps (baseline: docs/coding_standards)

- Quality gates halen niet 10/10 (o.a. trailing whitespace, broad exception catch, import-outside-toplevel).
- mypy errors over ontbrekende stubs voor `yaml`.

---

## 2. Target Outcome (Definition of Done)

### 2.1 Functioneel (uniform)

- `scaffold_artifact` is geregistreerd en bruikbaar via MCP.
- `search_documentation` gebruikt `DocumentIndexer + SearchService` (geen DocManager hardcoded dicts meer).
- Er is precies één “source of truth” voor artifact types en templates: `.st3/artifacts.yaml`.
- Legacy configuratie en entrypoints zijn verwijderd:
  - `.st3/components.yaml` bestaat niet meer
  - legacy scaffold tools (`scaffold_component`, `scaffold_design_doc`) zijn niet meer geregistreerd
  - `DocManager` is niet meer het search/template vertrekpunt
  - `TemplatesResource` (legacy listing) is verwijderd

### 2.2 Codebase consistency

- Eén exception pattern voor tools/managers/adapters (bij voorkeur `core.exceptions` MCPError-hierarchy).
- Eén config pattern (Pydantic + singleton + `from_file` + `reset_instance`).
- Template loading via bestaande `JinjaRenderer` en/of `FilesystemAdapter` (geen directe `open()` met onveilige paden).

### 2.3 Kwaliteit

- Quality gates zijn groen op repo-niveau.
- Tests zijn groen, met E2E coverage voor elke slice (zie Test Strategy).

---

## 3. Strategy: Increments (PR Slices)

We knippen de fix-forward in kleine, reviewbare stappen. Elke slice moet:

- unit + integration + end-to-end testen hebben (minimaal één van elk per slice),
- quality gates halen voor aangeraakte files,
- parallelle subsystemen elimineren (geen dubbele paden),
- expliciet een **breaking change** mogen zijn indien nodig om uniformiteit te bereiken.

### Slice 0 — Test Infrastructure Setup (mandatory)

**Waarom:** zonder hermetic test setup ga je “wiring” en migratie alleen met losse unit tests bewijzen; dat is te zwak.

**Doel:** één herbruikbare test-harness die realistisch is (real config, real templates, real filesystem in temp dir).

**Deliverables:**
- Test fixtures/factories voor:
  - temp workspace root
  - real `.st3/artifacts.yaml` in temp workspace
  - minimal templates onder `mcp_server/templates/...` (of fixtures die templates kopiëren)
  - filesystem adapter writes naar temp dir
- E2E helper die het pad simuleert: tool → manager → scaffolder → adapter → disk.
- Smoke test (E2E): één minimale “happy path” die met real `.st3/artifacts.yaml` een doc-artifact schrijft naar temp disk en de output file assert.

---

### Slice 1 — Harmoniseer Exceptions (Critical)

**Waarom eerst:** elke volgende integratie (tools → managers → adapters) moet hetzelfde error contract volgen.

**Doel:** verwijder duplicatie en convergeer op één error-hierarchie.

**Aanpak:**

- **Single source:** `mcp_server/core/exceptions.py` blijft leidend.
- Verwijder of refactor `mcp_server/core/errors.py` zodat er geen parallel error-model meer is.
- `mcp_server/config/artifact_registry_config.py` gebruikt geen lokale `ConfigError(Exception)` maar `core.exceptions.MCPError`-afgeleiden.

**Tests (verplicht):**
- Unit: exception types en messages (contract).
- Integration: tool/manager codepad dat errors produceert, zonder mocks die types maskeren.
- E2E: één scenario dat een config/template error triggert en als MCPError terugkomt.

---

### Slice 2 — Fix Template Loading & Paths (TemplateScaffolder)

**Probleem:** `TemplateScaffolder` doet `open(template_path)` direct, en doc template paths zijn relatief.

**Doel:** templates laden op dezelfde manier als bestaande scaffolding (`JinjaRenderer` + templates root).

**Aanpak:**
- Laat `TemplateScaffolder` de bestaande `JinjaRenderer` gebruiken:
  - template root = `mcp_server/templates`
  - template_path in registry is altijd “relative to templates root” (zoals nu voor docs: `documents/design.md.jinja2`).
- Vul ontbrekende template paths in `.st3/artifacts.yaml` aan (geen fallback/legacy mapping).

**Tests (verplicht):**
- Unit: render contract (required fields, context merging).
- Integration: render een echte template (jinja2) in temp env.
- E2E: scaffold doc + scaffold code artifact naar disk met real artifacts.yaml.

---

### Slice 3 — Validation alignment (ArtifactManager complete)

**Probleem:** `ValidationService` moet valideren op wat er *echt* geschreven wordt.

**Dependency:** Bouwt voort op Slice 2. De `TemplateScaffolder` (met JinjaRenderer) moet gebruikt worden om content te genereren voor validatie.

**Beslissing (nu vastgelegd):**
- code artifacts: **BLOCK** bij validation errors.
- doc artifacts: **WARN** bij validation issues (niet blokkeren).

**Aanpak:**
- In `ArtifactManager.scaffold_artifact()`:
  - Gebruik `TemplateScaffolder.render()` (uit Slice 2) om **realistische content** te genereren (geen mocks).
  - Valideer de gerenderde content via `ValidationService.validate(path, content)`.
  - write via adapter

**Tests (verplicht):**
- Unit: policy (warn vs block) per artifact type.
- Integration: validator draait met real path/content (rendered output).
- E2E:
  - invalid code artifact → faalt (BLOCK) en schrijft **geen** output file
  - invalid doc artifact → slaagt, schrijft output file, en emit **warning** (controleerbaar via captured logs/output)

---

### Slice 4 — Server wiring: registreer `scaffold_artifact` en verwijder legacy scaffold tools

**Doel:** één scaffolding entrypoint in de running server, pas nadat templates + validation bewezen werken.

**Aanpak:**
- Registreer `ScaffoldArtifactTool()` in `mcp_server/server.py`.
- Verwijder tool-registratie voor legacy scaffold tools (`ScaffoldComponentTool`, `ScaffoldDesignDocTool`).
- Verwijder/cleanup legacy scaffolding codepaden die alleen die tools ondersteunen (zodat agents niet per ongeluk oude paden volgen).

**Tests (verplicht):**
- Unit: tool args parsing / contract.
- Integration: server registration bevat alleen het nieuwe entrypoint.
- E2E: roep tool aan (execute) met real config en assert output file(s) bestaan.

---

### Slice 5 — Migrate Search: `search_documentation` → DocumentIndexer + SearchService (en verwijder DocManager dependency)

**Doel:** één search pad.

**Aanpak:**
- Update `SearchDocumentationTool.execute()`:
  - build index via `DocumentIndexer.build_index(docs_dir)` (gebruik `settings.server.workspace_root` + `docs`).
  - zoek via `SearchService.search_index(index, query, scope=...)`.
- Verwijder het gebruik van `DocManager` in search.

**Compat contract (expliciet):**
- Scopes: `architecture|coding_standards|development|reference|implementation|all` blijven ondersteund (of: breaking change expliciet documenteren).
- Output shape blijft compatibel met bestaande tool output (of: breaking change expliciet documenteren).

**Beslissing (nu vastgelegd):**
- `TemplatesResource`: **verwijderen**. Listing van templates loopt via `.st3/artifacts.yaml` of niet exposen.

**Tests (verplicht):**
- Unit: search scoring/scope filtering.
- Integration: indexer bouwt index over een real docs tree.
- E2E: `search_documentation` tool werkt op temp docs tree, zonder DocManager.

---

### Slice 6 — Registry clean break: artifacts.yaml als enige source-of-truth

**Doel:** geen parallelle config systemen.

**Aanpak (optie B, verplicht):**
- Verwijder `.st3/components.yaml` en de bijbehorende config-loader(s).
- Verwijder `scaffold_component`-flow (tool + registry + templates/mapping) als zelfstandig pad.
- Voorwaarde vóór delete: `.st3/artifacts.yaml` bevat minimaal templates voor deze “core types”:
  - doc: design
  - code: dto
  - code: worker
  - code: tool

**Tests (verplicht):**
- Unit: config schema validatie voor artifacts.yaml.
- Integration: project_structure cross-validatie accepteert artifact types.
- E2E: scaffold alle “core types” (minimaal 1 doc + 1 code) met artifacts.yaml.

---

### Slice 7 — Final Acceptance & Cleanup

**Doel:** Integrale validatie van de complete flow & laatste quality polish.

**Aanpak:**
- Voer "Final Acceptance Test" uit (zie sectie 4.5).
- Verifieer quality gates (pylint 10/10, mypy, coverage) over de **gehele** codebase na de grote clean-up van Slice 6.
- Voeg `types-PyYAML` toe en fix eventuele resterende linting issues die door refactoring (Slice 1-6) zijn ontstaan.

**Acceptance Test Scenario:**
1. Bootstrap een **fresh workspace**.
2. Scaffold 3 types artifacts via `scaffold_artifact`:
   - Document (bv. design doc)
   - Code (bv. DTO)
   - Worker (bv. agent)
3. Zoek documentatie via `search_documentation`.
4. Verifieer dat er **0 legacy references** zijn door minimaal deze checks:
   - captured logs/output bevatten geen strings: `DocManager`, `.st3/components.yaml`, `ScaffoldComponentTool`, `ScaffoldDesignDocTool`
   - codebase bevat geen runtime imports meer naar legacy scaffolding/search modules

---

## 4. Acceptance Criteria (per area)

### 4.1 Search
- `search_documentation` geeft resultaten terug zonder DocManager.
- `DocManager` is niet meer betrokken bij search/template listing flows.
- Scopes blijven ondersteund: `architecture|coding_standards|development|reference|implementation|all` (of breaking change expliciet vastgelegd).

### 4.2 Scaffolding
- `scaffold_artifact` werkt voor minimaal 1 doc artifact (design) en 1 code artifact (dto).
- Legacy scaffold tools zijn niet meer geregistreerd.
- `.st3/components.yaml` bestaat niet meer.

### 4.3 Config
- `.st3/artifacts.yaml` is required voor `scaffold_artifact`.
- `ProjectStructureConfig` cross-validatie accepteert artifact types uit artifacts.yaml.

### 4.4 Quality baseline (expliciet)

- Pylint: **10/10 op gewijzigde files** (en repo quality gate overall groen).
- mypy: **PASS** (incl. `yaml` types via `types-PyYAML`).
- pyright: **PASS**.
- Tests: **PASS**.
- Coverage: **100% op nieuw toegevoegde modules** (of minimaal op public entrypoints) + E2E coverage per slice.

### 4.5 Final Acceptance Test
- **Scenario:** Fresh workspace bootstrapping.
- **Actions:** Scaffold doc + dto + worker. Search docs.
- **Checks:** Files created correctly? Search results valid? No legacy references (captured logs/output grep).

---

## 5. Test Strategy (per slice verplicht)

Voor **elke** slice geldt: bewijs op drie niveaus.

- Unit tests: contract-level (types, policies, pure functions).
- Integration tests: echte filesystem + echte renderer/validator waar relevant.
- End-to-end tests: tool → manager → scaffolder → adapter → disk, met real `.st3/artifacts.yaml`.

### Continuous Quality
Kwaliteit is geen achteraf-stap. Voor **elke** slice geldt:
- Pylint score moet 10/10 blijven op gewijzigde bestanden.
- Mypy checks moeten slagen.
- Geen nieuwe technical debt introduceren.

---

## 6. Rollback Strategy

We kiezen voor clean break: geen legacy paden aanhouden “voor rollback”.

Rollback gebeurt via Git (revert van PRs). Dit is in de praktijk **forward-only** ontwikkeling; je rolt terug door commits te revert’en, niet door parallelle runtime toggles.

---

## 7. Migration Checklist (breaking change)

Omdat we `.st3/components.yaml` verwijderen en legacy tools niet meer registreren, is dit een breaking change.

- Documenteer in release notes:
  - welke tool(s) verdwijnen
  - welke config(s) verdwijnen
  - wat het vervangende pad is (`scaffold_artifact` + `.st3/artifacts.yaml`)
- Bestaande eerder-gegenereerde code blijft normaal bestaan (bestanden blijven op disk); dit plan migreert geen bestaande bestanden.
- Nieuwe scaffolding gebeurt alleen nog via artifacts.
- Indien teams nog scripts hebben die legacy tools/config gebruiken: die moeten aangepast worden.

---

## 8. Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| **Unknown code depends on DocManager.TEMPLATES** | High - runtime crashes | Medium | Grep entire codebase in Slice 0 for: `DocManager.TEMPLATES`, `DocManager.SCOPE_DIRS`, legacy imports. Document all findings before Slice 5. |
| **Template paths in artifacts.yaml wrong after JinjaRenderer switch** | High - scaffolding fails | Medium | Smoke test in Slice 0 catches this early. Validate all template_path values resolve correctly. |
| **Bestaande tests fail na exception harmonization** | Medium - CI red | High | Audit test mocks in Slice 1: ensure they catch unified MCPError types, not legacy parallel errors. |
| **Breaking change in search output shape** | Medium - agents confused | Low | Document compat contract explicitly (Slice 5). Run comparison test: old vs new search output for same query. |
| **Legacy code still registered in server.py** | High - parallel paths remain | Low | Slice 4 includes explicit deletion + registration audit. Add integration test that enumerates registered tools. |
| **Coverage drops during legacy removal** | Low - quality gate red | Medium | Measure coverage baseline before Slice 6. Accept temporary dip (<5%) during legacy removal, but recover in Slice 7. |
| **E2E tests too slow / flaky** | Medium - CI unreliable | Medium | Use temp dirs (tmpdir/tmp_path fixtures). Mock filesystem only where necessary. Keep E2E focused (1-2 scenarios per slice). |

---

## 9. Success Metrics

### 9.1 Quality Metrics (Baseline)
- **Pylint:** 10/10 on all modified files
- **Pyright:** PASS (zero errors)
- **mypy:** PASS (incl. types-PyYAML)
- **Tests:** 100% pass rate (unit + integration + E2E)
- **Coverage:** 
  - New modules: 100%
  - Overall repo: ≥95% (allow max -2% during legacy cleanup, recover in Slice 7)

### 9.2 Performance Metrics (No Regression)
- **Search latency:** <100ms for 50 docs (index build + query)
- **Scaffold latency:** <500ms per artifact (template render + validation + write)
- **Server startup:** <2s (tool registration overhead)

### 9.3 Migration Success Indicators
- **Legacy references:** 0 occurrences in:
  - Runtime logs (grep for `DocManager`, `components.yaml`, `ScaffoldComponentTool`)
  - Registered tools list (assert `scaffold_artifact` present, legacy tools absent)
  - Config loader calls (no `.st3/components.yaml` reads)
- **Artifact types unified:** All core types (design doc, dto, worker, tool) scaffoldable via `scaffold_artifact`
- **Developer experience:**
  - Before: 2 tools (scaffold_component + scaffold_design_doc)
  - After: 1 tool (scaffold_artifact)
  - Reduction: 50% tool surface area

### 9.4 Documentation Completeness
- Release notes include:
  - Breaking changes list (tools removed, configs removed)
  - Migration guide (how to convert legacy usage to artifacts.yaml)
  - Examples: minimal artifacts.yaml for common use cases
- Updated docs/reference with:
  - `.st3/artifacts.yaml` schema documentation
  - `scaffold_artifact` tool usage guide

---

## 10. Notes on Standards Alignment

- Houd imports in 3 blokken (stdlib / third-party / project) zoals `docs/coding_standards/CODE_STYLE.md`.
- Vermijd `except Exception` in tools; prefer MCPError families.
- Geen imports inside functions (quality gate).
- Max line length 100.

---

## 11. Concrete Worklist (Actionable)

1. Slice 0: test infrastructure/fixtures (real config/templates/fs).
2. Slice 1: exceptions harmoniseren.
3. Slice 2: TemplateScaffolder naar JinjaRenderer.
4. Slice 3: validation alignment met dependency op Slice 2 artifact generation.
5. Slice 4: server wiring + legacy scaffold tools verwijderen.
6. Slice 5: search migratie + DocManager dependency verwijderen + TemplatesResource delete.
7. Slice 6: artifacts.yaml als enige registry; components.yaml + scaffold_component flow verwijderen.
8. Slice 7: Final Acceptance Test & Clean-up.

---

**Next step:** Start met Slice 0 (test infrastructure) zodat elke volgende slice bewijsbaar end-to-end werkt.
