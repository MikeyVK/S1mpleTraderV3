# Sessie Overdracht — Issue #273
<!-- template=manual version=issue273 -->

## Branch
`refactor/273-remove-commit-prefix-map`

## Status
**C1 RED/GREEN/REFACTOR gecommit. Quality gates branch-scope NIET schoon — 3 blockers open.**

## Wat er gedaan is deze sessie

### QA Design Review (goedgekeurd)
Research en planning door imp agent gereviewd en goedgekeurd met één toevoeging:
- GREEN stap 4: docstring in `test_policy_engine_config.py:22` bijwerken
  (`commit_prefix_map` → `commit_types`).
- Overige planning: correct en volledig bevonden.

### Implementatie C1 (door imp agent)
Drie commits op branch:
```
test(P_IMPLEMENTATION_SP_C1_RED):     update test fixtures + tests (8 bestanden)
feat(P_IMPLEMENTATION_SP_C1_GREEN):   remove commit_prefix_map/tdd_phases, fix get_all_prefixes
refactor(P_IMPLEMENTATION_SP_C1_REFACTOR): ruff format git_config.py
```

### Log-analyse mcp_audit.log (door QA)
Gebruiker vroeg om dubbele regels in het logbestand te onderzoeken.

**Bevinding: twee afzonderlijke problemen, geen verband met #272.**

1. **Dubbele regels** — proxy-logging design: elk `validation_error_detected` record
   embedt de server-fout in zowel `"message"` als `"raw_stderr"`. Niet een applicatiebug;
   elke fout is zo altijd tweemaal leesbaar per logregel. Zie proxy-implementatie.

2. **BranchState schema-fouten (25–26 mrt)** — `cycle_history` schema-migratie na epic #257:
   bestaande `state.json` bestanden hadden `cycle_history: [1, 2, 3]` (oud formaat),
   Pydantic verwachtte `list[dict]`. PSE ving dit op met "reconstructing". Opgelost door
   state.json te verversen. Geen actie nodig.

3. **#272 (ScopeDecoder wrong phase)** — staat los van bovenstaande. Dat issue beschrijft
   dat op child-branches de commit-scope van de parent-commit hogere prioriteit heeft dan
   state.json. Niet zichtbaar in recente log-entries.

---

## ❌ Open Blockers — Quality Gates

`run_quality_gates(scope="branch")` faalt op 3 punten. **Moet gefixed zijn vóór merge.**

### Gate 0: Ruff Format (2 bestanden)
```
tests/mcp_server/config/test_git_config.py       → ruff format nodig
tests/unit/config/test_c_loader_structural.py    → ruff format nodig
```
Fix: `ruff format <bestand>` op beide bestanden.

### Gate 3: Line Length
```
tests/unit/config/test_c_loader_structural.py:399  → 101 tekens (max 100)
```
Fix: regel handmatig inbreken (ruff formatteert dit niet automatisch bij E501).

### Gate 4b: Pyright — `reportPrivateUsage`
```
tests/mcp_server/config/test_git_config.py:116  → GitConfig._compiled_pattern = None
tests/mcp_server/config/test_git_config.py:119  → GitConfig._compiled_pattern is not None
```
`_compiled_pattern` is een `ClassVar` met underscore-prefix. Pyright markeert directe
externe toegang als `reportPrivateUsage`. Dit was een pre-existing issue — is zichtbaar
geworden door branch-scope gate run. Twee opties:
- Rename `_compiled_pattern` → `_pattern_cache` is niet voldoende (zelfde probleem).
- Voeg `# type: ignore[reportPrivateUsage]` toe op regels 116 en 119 in de test,
  conform TYPE_CHECKING_PLAYBOOK §targeted-ignore-last-resort.
- Of: maak `_compiled_pattern` publiek (`compiled_pattern`) — maar dat wijzigt productie-API.

**Aanbevolen fix:** targeted `# type: ignore[reportPrivateUsage]` op de twee testregels,
met comment dat dit een ClassVar-reset is die buiten de klasse plaatsvindt in testcontext.

---

## Volgende stap voor imp agent
1. Fix gate-violations (zie boven)
2. Run `run_quality_gates(scope="branch")` → alle gates groen
3. Run `run_tests(path="tests/")` → volledige suite groen
4. Valdation report aanmaken
5. PR naar `epic/257-reorder-workflow-phases` (of main als epic gesloten)

## Follow-up issues (buiten scope #273)
- **#274**: Terminal-fase exit gates worden nooit gevalideerd (child #257)
- **#272**: ScopeDecoder wrong phase op child branches (priority:low)
- **Proxy log duplication**: `raw_stderr` embed in `message` — laag-prioriteit cosmetic fix
