# Sessie Overdracht - Issue #257 - 2026-03-16

## Metadata

- Issue: #257
- Branch: `feature/257-reorder-workflow-phases`
- Werkitem: `C_LOADER.3` (Cycle 2c in planning)
- Status bij overdracht: structureel ver gevorderd, maar nog **NOGO** als cycle-afsluiting
- Reden NOGO: runtime-bewijs is nog niet hard genoeg; eerdere groene signalen waren onvoldoende voor eerlijke stop/go

## Samenvatting

Deze sessie stond in het teken van het echt sluiten van `C_LOADER.3` volgens de gerepareerde planning, niet van cosmetisch groen krijgen. De kern van het werk was:

1. productiecode opschonen zodat config/self-loading en fallback-construction buiten `config/` verdwijnen
2. test-oppervlak mee refactoren binnen dezelfde blast radius zodat de QA-evidence nog betekenis heeft
3. alleen richting GO bewegen als de structurele stop/go uit de planning werkelijk klopt

De planning voor `C_LOADER.3` is in deze sessie ook aangescherpt naar de reele scope: 26 productie- en composition-root files, inclusief `validation/` en `server.py`, met expliciete stop/go-criteria voor verboden self-loading, verboden manager-imports uit `mcp_server.config`, en volledige testpassage.

## Wat Deze Sessie Is Gedaan

### 1. Productie-opruiming naar expliciete DI

De relevante productie-oppervlakken zijn breed opgeschoond zodat constructorinjectie de norm wordt en verborgen config-loading uit execute-paden verdwijnt.

Belangrijkste lijnen:

- `GitManager` vraagt nu expliciet een `GitConfig`
- `ProjectManager` vraagt nu expliciet een `WorkflowConfig` en gebruikt optioneel een geinjecteerde `GitManager`
- `PhaseStateEngine` vraagt nu expliciet `GitConfig`, `WorkflowConfig` en `WorkphasesConfig`
- `QAManager` draait nu op geinjecteerde `QualityConfig`
- `ArtifactManager` en `TemplateScaffolder` zijn strakker naar expliciete registry/config-injectie gezet
- `PolicyEngine` en `DirectoryPolicyResolver` zijn ontdaan van verborgen fallback-loading
- `server.py` is omgezet naar een duidelijke composition root die config eenmalig laadt en vervolgens managers/tools injecteert
- diverse tools zijn omgezet van zelf managers/config bouwen naar gebruik van geinjecteerde dependencies

Hiermee is de structurele richting van `C_LOADER.3` in lijn gebracht met het plandoel:

> geen `from_file()` / `load()` / fallback construction buiten `config/`, en geen directe manager-importclosure uit `mcp_server.config` in productie-managers.

### 2. Testblast-radius bewust mee gemigreerd

Omdat deze productie-refactor constructoroppervlakken en composition-root wiring veranderde, is een groot deel van het testoppervlak mee aangepast binnen dezelfde cycle. Dat was nodig om te voorkomen dat tests groen blijven via oude verborgen coupling.

Belangrijkste zet:

- nieuw gedeeld builder/support-bestand: `tests/mcp_server/test_support.py`

Deze helpers centraliseren DI-first setup voor onder meer:

- `make_project_manager`
- `make_phase_state_engine`
- `make_qa_manager`
- `make_git_manager`
- `make_phase_config_context`
- `make_artifact_manager`
- `make_policy_engine`
- create-issue / create-branch / create-pr input configuratie

Daarnaast is `tests/mcp_server/conftest.py` aangepast zodat tests tool-input configuratie resetten in plaats van terug te vallen op singleton-resetgedrag.

### 3. Grote constructor-migratie in tests

Een brede set testfiles is aangepast om oude patronen zoals directe `ProjectManager(...)`, `PhaseStateEngine(...)`, `QAManager(...)` of impliciete config-loading te vervangen door expliciete builders of expliciet geladen config-objecten.

De laatste migratiegolf in deze sessie zat vooral in:

- cycle tools tests
- discovery/work-context tests
- phase-state-engine testfamilie
- state repository tests
- cross-machine en workflow e2e tests
- server/tool wiring tests

Na die migratie is de resterende constructor-oppervlakte sterk teruggebracht. De relevante resterende hits waren op het moment van overdracht nog hoofdzakelijk:

- `tests/mcp_server/test_support.py` zelf, bewust als builderlaag
- `tests/mcp_server/unit/managers/test_project_manager.py`
- `tests/mcp_server/unit/test_server.py`

Dat is dus geen brede verspreide legacy-schade meer, maar een kleine restset die gericht beoordeeld kan worden.

## Belangrijkste Gewijzigde Productie-Oppervlakken

De belangrijkste productie-aanpassingen van deze sessie zitten rond:

- `mcp_server/server.py`
- `mcp_server/managers/git_manager.py`
- `mcp_server/managers/project_manager.py`
- `mcp_server/managers/phase_state_engine.py`
- `mcp_server/managers/qa_manager.py`
- `mcp_server/managers/artifact_manager.py`
- `mcp_server/managers/enforcement_runner.py`
- `mcp_server/managers/phase_contract_resolver.py`
- `mcp_server/core/policy_engine.py`
- `mcp_server/core/directory_policy_resolver.py`
- `mcp_server/scaffolding/metadata.py`
- `mcp_server/scaffolders/template_scaffolder.py`
- diverse toolmodules onder `mcp_server/tools/`
- `mcp_server/validation/python_validator.py`
- nieuw compat-bestand: `mcp_server/config/compat_roots.py`
- verbrede schema-export in `mcp_server/schemas/__init__.py`

## Huidige Beoordeling Tegen C_LOADER.3

### Wat er sterk uitziet

- de plandoelstelling voor productie-DI is inhoudelijk serieus aangepakt
- de composition root in `server.py` is explicieter geworden
- het grootste deel van de oude zelfladende constructor-coupling is uit de bedoelde productie-oppervlakken gehaald
- editor-diagnostics op recent aangepakte files waren herhaaldelijk schoon
- brede grep- en constructor-checks hebben de resterende schuld sterk versmald
- de testblast-radius is niet genegeerd, maar bewust meegetrokken in dezelfde cycle

### Wat nog niet hard genoeg bewezen is

De cycle mag nog niet als GO worden gemarkeerd. De ontbrekende schakel is niet vooral statisch, maar operationeel:

- een gerichte runtime-testuitvoering leverde geen bruikbare bewijsvoering op, maar effectief een lege uitkomst (`0 passed, 0 failed`)
- daardoor is er nog geen overtuigend bewijs dat de nieuw omgebouwde testoppervlakken ook echt als set correct draaien
- branch-wide quality gates zijn na de laatste migratiegolf nog niet opnieuw als eindbewijs vastgelegd
- de volledige `pytest tests/mcp_server/ --override-ini="addopts=" --tb=short -q` stop/go uit planning is nog niet hard afgevinkt

Kort gezegd: structureel staat het werk er veel beter voor, maar de bewijslaag is nog onvoldoende om `C_LOADER.3` eerlijk af te sluiten.

## Waar De Volgende Sessie Moet Oppakken

### Directe eerstvolgende stap

Voer geen nieuwe brede refactor meer uit voordat het bestaande werk eerst als bewijsbaar pakket is gevalideerd.

De eerstvolgende werkgang hoort te zijn:

1. herbevestig de resterende constructor/self-loading hits op de kleine restset
2. draai gerichte runtime-tests op de recent gemigreerde clusters tot er echte uitvoer is
3. draai daarna pas de bredere relevante testset / branchbrede gates
4. bepaal pas daarna GO/NOGO voor `C_LOADER.3`

### Concreet aandachtspunt

Het belangrijkste risico is nu een valse positieve afsluiting. Alles in deze overdracht moet gelezen worden vanuit dat uitgangspunt:

- niet aannemen dat structurele grep-cleanliness gelijk staat aan cycle-closure
- niet aannemen dat eerdere groene tests nog representatief zijn na de DI-refactor
- niet terugvallen op oude optimistische overdrachten als bron van waarheid
- runtime-evidence is de beslissende ontbrekende stap

## Aanbevolen Vervolgvolgorde

1. Controleer de kleine restset in `test_project_manager.py` en `test_server.py` nog eenmaal op legacy constructorvormen versus intentionele expliciete config-injectie.
2. Draai daarna gerichte testselecties op de laatst gemigreerde files, zodat je echte pass/fail-uitvoer krijgt in plaats van een lege run.
3. Als die stabiel zijn, voer de bredere `tests/mcp_server/` validatie uit die in de planning als stop/go voor `C_LOADER.3` staat.
4. Werk pas daarna de cycle-status en eventuele QA-overdracht bij.

## Eerlijke Eindconclusie

Deze sessie heeft de cycle inhoudelijk veel dichter bij echte closure gebracht. Vooral productie-DI, composition-root wiring en de meeverhuisde testblast-radius zijn stevig opgeruimd. Maar zonder overtuigende runtime-uitvoering is dit nog geen verifieerbare GO.

De juiste overdrachtsboodschap is daarom:

**`C_LOADER.3` is structureel sterk verbeterd, maar op dit moment nog NOGO tot de runtime-bewijslaag opnieuw hard is gemaakt.**
