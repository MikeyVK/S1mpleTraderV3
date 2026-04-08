# Sessie Overdracht — Issue #273
<!-- template=manual version=issue273 -->

## Branch
`refactor/273-remove-commit-prefix-map`

## Status
**Implementatie volledig. Quality gates groen. Laatste commit: 3dc5266 (REFACTOR). Klaar voor validation + documentation fase.**

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

### Implementatie overdracht (imp agent — einde sessie)

**Geïmplementeerd (C1 volledig, alle gates groen):**
- `commit_prefix_map` + `tdd_phases` volledig verwijderd uit `git.yaml` en `GitConfig`
- `validate_cross_references` vervangen door `validate_branch_name_pattern` (branch-regex validatie behouden)
- `has_phase()` en `get_prefix()` verwijderd — geen productie-callers
- `get_all_prefixes()` herschreven: `[f"{t}:" for t in self.commit_types]` → 11 types
- PolicyEngine accepteert nu alle 11 conventional commit-types (was: 4)
- 2657/2657 tests groen, quality gates groen

**Verificatiepunten voor volgende sessie:**
1. `validate_architecture(scope="all")` uitvoeren
2. Grep bevestigen: alleen docs-bestanden bevatten nog `tdd_phases`/`commit_prefix_map`
3. Documentatie bijwerken in documentation-fase (zie hieronder)

---

## ✅ Quality Gates (opgelost)

QA signaleerde na C1-REFACTOR drie gate-blockers; imp agent heeft deze in dezelfde sessie
opgelost voordat de handover werd vastgelegd. Uiteindelijke staat: **alle gates groen**.

> Eerder geïdentificeerde blockers (ruff format, E501 op regel 399, Pyright
> `reportPrivateUsage` op `_compiled_pattern` in testbestand) zijn afgehandeld.

---

## Volgende stap voor imp agent (documentation-fase)

1. `validate_architecture(scope="all")` uitvoeren
2. Grep bevestigen: alleen docs-bestanden bevatten nog `tdd_phases`/`commit_prefix_map`
3. Documentatie bijwerken:
   - `docs/reference/mcp/git_config_customization.md` — verwijder tdd_phases/commit_prefix_map vermeldingen
   - `docs/reference/mcp/git_config_api.md` — verwijder has_phase()/get_prefix() API-docs, update get_all_prefixes()
   - `docs/reference/mcp/tools/git.md` — update commit-type sectie (11 types, niet meer 4)
   - `docs/reference/mcp/mcp_vision_reference.md` — update indien relevant
4. Validation report aanmaken
5. PR naar `main` (epic #257 is gesloten en gemerged)

## Follow-up issues (buiten scope #273)
- **#274**: Terminal-fase exit gates worden nooit gevalideerd (child #257)
- **#272**: ScopeDecoder wrong phase op child branches (priority:low)
- **Proxy log duplication**: `raw_stderr` embed in `message` — laag-prioriteit cosmetic fix
