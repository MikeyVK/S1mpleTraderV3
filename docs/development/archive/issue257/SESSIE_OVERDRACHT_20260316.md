# Sessie Overdracht - Issue #257 - 2026-03-16

## Metadata

- Issue: #257
- Branch: `feature/257-reorder-workflow-phases`
- Werkitem: `C_LOADER.3`
- Status bij overdracht: **NOGO**
- Reden NOGO: config-root en DI-contract zijn breed gelijkgetrokken, maar de MCP unit-suite heeft nog 10 open failures in tooltests

## Samenvatting

Deze sessie heeft de resterende `C_LOADER.3`-refactor vooral geconcentreerd op twee lijnen:

1. runtime en tests laten resolven op een expliciete `config_root` in plaats van impliciete cwd/fallback-paden
2. legacy unit-tests ombouwen naar expliciete injectie van config- en managerdependencies

De branch staat daardoor structureel verder dan aan het begin van de sessie, maar de cycle is nog niet afsluitbaar. De manager-, schema- en een groot deel van de server/test-support laag zijn inmiddels groen; de resterende failures zitten nu geconcentreerd in een kleinere tooltest-restset.

## Wat Deze Sessie Heeft Opgeleverd

### 1. Runtime `config_root` expliciet gemaakt

De composition root en compat-resolving zijn aangepast zodat runtime en tests dezelfde definitie van config-root gebruiken.

Belangrijkste wijzigingen:

- `mcp_server/config/compat_roots.py`
  - nieuwe publieke helpers `get_candidate_config_roots(...)` en `resolve_config_root(...)`
- `mcp_server/config/settings.py`
  - `ServerSettings.config_root: str | None = None`
- `mcp_server/server.py`
  - server composeert nu via `resolve_config_root(preferred_root=workspace_root, explicit_root=settings.server.config_root, required_files=(...))`
- `mcp_server/tools/git_tools.py`
  - verboden fallback-construction voor `GetParentBranchTool` verwijderd; state-engine moet nu expliciet geïnjecteerd zijn

### 2. Gedeelde test-support naar dezelfde resolver omgebouwd

`tests/mcp_server/test_support.py` is uitgebreid tot de centrale builderlaag voor de huidige DI-first contracten.

Belangrijkste helpers/aanpassingen:

- `_load_config(...)` voor file-specifieke config loading
- `load_workflow_config(...)`
- `make_project_manager(...)`
- `make_phase_state_engine(...)`
- `make_qa_manager(...)`
- `make_artifact_manager(...)`
- `configure_create_issue_input(...)`
- `configure_create_pr_input(...)`
- resolver in test-support hergebruikt nu de runtime helper in plaats van parallelle padlogica

### 3. Testblast-radius meegetrokken naar expliciete injectie

De grootste ombouw zat in unit-tests die nog uitgingen van hidden loading, singleton state of constructor-fallbacks.

Belangrijkste clusters die zijn aangepast:

- `tests/mcp_server/unit/test_server.py`
  - gebruikt gedeelde builders
  - mocked settings zetten nu expliciet `server.config_root`
- `tests/mcp_server/unit/managers/test_project_manager.py`
  - lokale workflow-loader verwijderd
  - gebruikt `load_workflow_config(...)` en `make_project_manager(...)`
- `tests/mcp_server/unit/managers/test_baseline_advance.py`
  - `QualityConfig.load`-patching verwijderd ten gunste van directe injectie
- `tests/mcp_server/unit/managers/test_scope_resolution.py`
- `tests/mcp_server/unit/managers/test_auto_scope_resolution.py`
- `tests/mcp_server/unit/managers/test_autofix_propagation.py`
- `tests/mcp_server/unit/managers/test_feature_flag_v2.py`
- `tests/mcp_server/unit/managers/test_artifact_manager*.py`
- `tests/mcp_server/unit/schemas/test_*_v2_parity.py`
- `tests/mcp_server/unit/test_dto_parity.py`
- `tests/mcp_server/unit/tools/test_create_issue_input.py`
  - validatorconfig wordt nu per test via autouse fixture gezet
- `tests/mcp_server/unit/tools/test_git_checkout_state_sync.py`
  - test injecteert nu direct de state-engine in plaats van oude patchtargets te verwachten
- `tests/mcp_server/unit/tools/test_cycle_tools.py`
  - mocked server settings zetten nu expliciet `server.config_root`

### 4. ArtifactManager-contract aangescherpt

De huidige testlaag is uitgelijnd op het feit dat `ArtifactManager` geen impliciete registry-loading meer doet.

Dat zie je terug in:

- expliciete registry/project-structure injectie via `make_artifact_manager(...)`
- metadata/registry tests geven nu een echte string `template_path` mee waar tier extraction op kan draaien
- directory-resolution tests voldoen nu aan het huidige `ProjectStructureConfig`-contract

## Verificatie Deze Sessie

### Gerichte subsets groen

Bevestigd groen tijdens deze sessie:

- `pytest tests/mcp_server/unit/test_server.py tests/mcp_server/unit/managers/test_project_manager.py tests/mcp_server/tools/test_pr_tools_config.py`
  - `34 passed`
- `pytest tests/mcp_server/managers tests/mcp_server/tools`
  - `18 passed`
- `pytest tests/mcp_server/unit/managers/test_artifact_manager.py tests/mcp_server/unit/managers/test_artifact_manager_registry.py tests/mcp_server/unit/managers/test_directory_resolution.py tests/mcp_server/unit/managers/test_phase_state_engine_c2.py -q`
  - `19 passed`
- `pytest tests/mcp_server/unit/schemas/test_code_artifact_v2_parity.py tests/mcp_server/unit/schemas/test_doc_artifact_v2_parity.py tests/mcp_server/unit/schemas/test_tracking_artifact_v2_parity.py tests/mcp_server/unit/test_dto_parity.py -q`
  - `65 passed, 2 skipped, 2 xfailed`
- `pytest tests/mcp_server/unit/tools/test_create_issue_input.py -q`
  - `46 passed`

### Actuele brede status

De meest bruikbare brede check aan het einde van de sessie was seriële uitvoering zonder xdist-noise:

- `pytest -n0 tests/mcp_server/unit -q`
  - resultaat: `10 failed, 1537 passed, 9 skipped, 2 xfailed`

Er was daarnaast eerder een xdist-gerelateerde Windows workercrash; voor deze overdracht geldt daarom de seriële run als waarheid, niet de parallelle run.

## Open Failures Bij Overdracht

De unit-suite is nu teruggebracht tot 10 failures in 4 clusters.

### Cluster 1. `test_cycle_tools.py`

Open failures:

- `tests/mcp_server/unit/tools/test_cycle_tools.py::TestCycleTools::test_call_tool_post_enforcement_commits_state_files_after_cycle_transition`
- `tests/mcp_server/unit/tools/test_cycle_tools.py::TestCycleTools::test_call_tool_force_cycle_post_enforcement_returns_warning`

Probleem:

- tests zetten wel `server.config_root`, maar hun tijdelijke `.st3` bevat nog niet alle vereiste files (`git.yaml`, `workflows.yaml`, `workphases.yaml`)
- daardoor faalt `resolve_config_root(...)` correct met `FileNotFoundError`

Benodigde vervolgstap:

- testfixture/bootstrap uitbreiden zodat de temp workspace een complete minimale config-root heeft
  of
- serverconstructie in de test laten wijzen naar een bestaande complete `.st3`

### Cluster 2. `test_git_pull_tool_behavior.py`

Open failures:

- `tests/mcp_server/unit/tools/test_git_pull_tool_behavior.py::test_git_pull_success_syncs_phase_state`
- `tests/mcp_server/unit/tools/test_git_pull_tool_behavior.py::test_git_pull_phase_sync_failure_is_non_fatal`

Probleem:

- test patcht nog `mcp_server.tools.git_pull_tool.Path.cwd`
- die patchtarget bestaat niet meer in de huidige toolimplementatie

Benodigde vervolgstap:

- test herschrijven naar expliciete state-engine injectie, analoog aan `test_git_checkout_state_sync.py`

### Cluster 3. `test_quality_tools.py`

Open failures:

- `TestRunQualityGatesScopeGuardC41::test_scope_files_pass_run_does_not_advance_baseline`
- `TestRunQualityGatesScopeGuardC41::test_non_auto_pass_runs_do_not_reset_auto_failed_state[branch]`
- `TestRunQualityGatesScopeGuardC41::test_non_auto_pass_runs_do_not_reset_auto_failed_state[project]`
- `TestRunQualityGatesFailedSubsetC42::test_auto_mixed_result_accumulates_only_failing_subset`
- `TestRunQualityGatesFailedSubsetC42::test_auto_mixed_result_must_not_accumulate_full_resolved_set`

Probleem:

- deze tests patchen nog `QualityConfig.load`
- `QAManager` draait nu op expliciet geïnjecteerde `QualityConfig`

Benodigde vervolgstap:

- tests omzetten naar dezelfde directe config-injectie als al gedaan is in `test_baseline_advance.py` en `test_scope_resolution.py`

### Cluster 4. `test_scaffold_artifact.py`

Open failure:

- `tests/mcp_server/unit/tools/test_scaffold_artifact.py::TestScaffoldArtifactTool::test_manager_optional_di`

Probleem:

- test verwacht nog dat `ScaffoldArtifactTool()` zonder manager een impliciete `ArtifactManager()` kan bouwen
- dat mag niet meer sinds registry-injectie verplicht is

Benodigde vervolgstap:

- test aanpassen naar expliciete managerinjectie
  of
- constructorcontract van tool herzien als die implicit path toch gewenst is

## Beoordeling Tegen `C_LOADER.3`

### Wat nu overtuigend beter is

- runtime en tests gebruiken nu dezelfde config-root-resolutie
- servermocks die een fake config-root meegaven zijn gecorrigeerd naar expliciete waarden
- DI-first contract is doorgetrokken in de belangrijkste manager- en schema-testlagen
- de resterende failures zijn geen diffuse branchbrede regressie meer, maar een smalle restset in tools

### Waarom nog steeds NOGO

`C_LOADER.3` is nog niet sluitbaar omdat de bewijslaag nog openstaat:

- brede MCP unit-suite is nog niet groen
- de open failures zitten precies in de resterende legacy-testaannames rond config-root en expliciete injectie
- er is dus nog geen eerlijke stop/go voor deze cycle

## Aanbevolen Vervolgvolgorde

1. Maak `test_cycle_tools.py` temp-config-root compleet of laat de tests naar een complete `.st3` resolven.
2. Zet `test_git_pull_tool_behavior.py` om naar expliciete injected state-engine, net als checkout.
3. Verwijder de laatste `QualityConfig.load`-patches uit `test_quality_tools.py`.
4. Beslis in `test_scaffold_artifact.py` expliciet of implicit manager-constructie nog onderdeel van het contract mag zijn; zo niet, pas de test aan.
5. Draai opnieuw `pytest -n0 tests/mcp_server/unit -q`.
6. Pas daarna opnieuw de bredere `tests/mcp_server`-stop/go voor `C_LOADER.3` bepalen.

## Eerlijke Eindconclusie

Deze sessie heeft de branch inhoudelijk verder gebracht: expliciete `config_root`, gedeelde DI-first test-support en een grote opruiming van legacy unit-tests zijn geland. De branch is daardoor beter gestructureerd en de failure-surface is sterk versmald.

De cycle is echter nog niet klaar voor GO. De actuele, seriële waarheid is:

**`pytest -n0 tests/mcp_server/unit -q` => 10 failed, 1537 passed, 9 skipped, 2 xfailed**

Daarmee is de juiste overdrachtsboodschap:

**`C_LOADER.3` is duidelijk verder gestabiliseerd, maar blijft bij overdracht NOGO totdat de laatste tooltest-restset is rechtgetrokken en de brede unit-validatie volledig groen is.**
