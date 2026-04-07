# Sessie Overdracht — 13 maart 2026

## Branch
`feature/257-reorder-workflow-phases`

## Context
QA-sessie voor issue #257 (Config-First PSE architecture). Implementatie-agent had Cycle 7 als "done" gerapporteerd. QA-agent heeft de volledige implementatie (Cycles 1–7) grondig gecontroleerd tegen design.md, planning.md en research KPIs 1–20. Resultaat: **10 van 20 KPIs groen, 10 rood — branch is nog niet PR-gereed.**

De gaps zijn grotendeels structureel en wijzen op pre-implementatie-fases die onvoldoende of incorrect zijn uitgevoerd. Op de andere machine analyseren hoe de gaps hebben kunnen ontstaan en bepalen welke pre-implementatie-fases (deels) opnieuw doorlopen moeten worden.

## Test baseline (huidig)
```
2132 passed, 11 skipped, 2 xfailed
```

## Cycle 7 commits (op e10c60c)
```
fec31d0  ...
c0cf3d5  ...
2600601  ...
2aa9309  HEAD
```
**Gewijzigde files in C7:** `.gitignore`, `.st3/state.json`, `phase_state_engine.py`, `project_manager.py`, `test_phase_state_engine_parent_branch.py`, `test_project_manager.py`

---

## KPI-overzicht (QA-resultaat)

| KPI | Omschrijving | Status |
|-----|-------------|--------|
| 1 | workflows.yaml gebruikt "implementation" | ✅ |
| 2 | .st3/ split: config/ + registries/ aanwezig | ❌ |
| 3 | phase_contracts.yaml bestaat (file) | ✅ |
| 3 | PSE exit-hooks via PhaseContractResolver (code) | ❌ |
| 4 | deliverables.json in .st3/registries/ | ❌ |
| 5 | projects.json verwijderd (fysiek bestand) | ❌ |
| 6 | PhaseContractResolver klasse aanwezig | ✅ |
| 7 | StateRepository klasse aanwezig | ✅ |
| 8 | PSE OCP: exit-hook registry i.p.v. if-chain | ❌ |
| 9 | DeliverableChecker max 1× geïnstantieerd | ❌ |
| 10 | DRY on_exit methoden (één generieke methode) | ❌ |
| 11 | Geen f-string logging in PSE | ❌ |
| 12 | Geen "tdd" literals in source + tests | ❌ |
| 13 | Geen sub_phase if-chain in git_manager | ✅ |
| 14 | branch_name_pattern enforceert issue-nummer prefix | ❌ |
| 15 | _extract_issue_from_branch verwijderd uit PSE | ✅ |
| 16 | workflow_config.py verwijderd | ✅ |
| 17 | Volledige testsuite groen | ✅ |
| 18 | enforcement.yaml bevat post-merge cleanup rules | ❌ |
| 19 | state.json git-tracked + startup guard | ✅ |
| 20 | AtomicJsonWriter aanwezig en gebruikt | ✅ |

**Groen: 10 / 20 | Rood: 10 / 20**

---

## Gap-lijst (geordend op prioriteit)

### PRIORITEIT 1 — Cycle 7 directe deliverables (blokkeren Stop/Go C7)

#### Gap 1 — B2: Completed-cycle guard ontbreekt in `update_planning_deliverables`

- **Locatie:** `mcp_server/managers/project_manager.py` — methode `update_planning_deliverables()`
- **Probleem:** Nergens in de merge-loop wordt gecontroleerd of een inkomende cycle al in `state.json::cycle_history` staat als `completed`. Een afgesloten cycle is per design.md immutable.
- **Vereiste implementatie:**
  1. Lees `state.json` via `FileStateRepository` aan het begin van `update_planning_deliverables`
  2. Bouw een `frozenset` van completed cycle-nummers uit `state_data["cycle_history"]`
  3. Voor elk `incoming_cycle` in de merge-loop: `if incoming_cycle["cycle_number"] in completed_cycles:` → `raise ValidationError(f"Cycle {number} is completed and read-only (see branch {branch})")`
- **Test:** `test_update_planning_deliverables_raises_for_completed_cycle` toevoegen in `tests/mcp_server/unit/managers/test_project_manager.py`
- **Verificatie:** `update_planning_deliverables(...)` raises `ValidationError` bij cycle in `cycle_history[status=completed]`

---

#### Gap 2 — B4: Post-merge `delete_file` enforcement volledig absent

**Deel A — Geen `delete_file` handler geregistreerd:**
- **Locatie:** `mcp_server/managers/enforcement_runner.py` — `_build_default_registry()`
- **Huidig:** Alleen `check_branch_policy` + `commit_state_files` geregistreerd. `EnforcementAction` kent het `delete_file` type (validator ~line 57) maar er is geen uitvoerder.
- **Implementatie:**
  1. Voeg toe: `self._registry["delete_file"] = self._handle_delete_file`
  2. Implementeer `_handle_delete_file(action, context, workspace_root)`: resolv `workspace_root / action.path` en verwijder idempotent (geen error als absent)

**Deel B — Geen post-merge rule in enforcement.yaml:**
- **Locatie:** `.st3/config/enforcement.yaml`
- **Huidig:** 3 regels, geen met `event_source: merge`
- **Voeg toe:**
  ```yaml
  - rule_id: post_merge_cleanup
    event_source: merge
    timing: post
    actions:
      - type: delete_file
        path: .st3/registries/state.json
      - type: delete_file
        path: .st3/registries/deliverables.json
  ```
  _(paths zijn de toekomstige registries/-paden na Gap 7)_
- **Test:** `test_post_merge_enforcement_deletes_state_and_deliverables`
- **KPI 18** volledig groen na deze gap

---

### PRIORITEIT 2 — PSE structurele refactoring (blokkeren KPIs 8–11)

Deze gaps hadden in Cycle 3 gesloten moeten zijn. Ze blokkeren het PR Stop/Go.

#### Gap 3 — KPI 8: OCP-schending — `if from_phase ==` chain in `transition()`

- **Locatie:** `mcp_server/managers/phase_state_engine.py` — `transition()` methode, ~lines 179–195
- **Bewijs:** `Select-String "if from_phase ==" mcp_server/managers/phase_state_engine.py` geeft 6 matches
- **Vereiste:** Vervang if-chain door `_exit_hooks: dict[str, Callable[[str, int], None]]` gevuld in `__init__`:
  ```python
  self._exit_hooks = {
      "planning": self.on_exit_planning_phase,
      "design": self._run_exit_gate,
      ...
  }
  # in transition():
  if from_phase in self._exit_hooks:
      self._exit_hooks[from_phase](branch, issue_number)
  ```
- **Verificatie:** `Select-String "if from_phase ==" mcp_server/managers/phase_state_engine.py` → 0 matches

---

#### Gap 4 — KPI 9: DIP-schending — `DeliverableChecker` 3× geïnstantieerd

- **Locatie:** `mcp_server/managers/phase_state_engine.py` lines 639, 749, 780
- **Bewijs:** Alle drie: `checker = DeliverableChecker(workspace_root=self._workspace_root)`
- **Vereiste:** Constructor-injection of lazy property:
  ```python
  @property
  def _checker(self) -> DeliverableChecker:
      if self.__checker is None:
          self.__checker = DeliverableChecker(workspace_root=self._workspace_root)
      return self.__checker
  ```
  Vervang alle drie instantiaties door `self._checker`.
- **Verificatie:** `Select-String "DeliverableChecker(" mcp_server/managers/phase_state_engine.py` → max 1 match

---

#### Gap 5 — KPI 10: DRY-schending — drie identiek-gestructureerde `on_exit_*_phase` methoden

- **Locatie:** `mcp_server/managers/phase_state_engine.py` — `on_exit_design_phase`, `on_exit_validation_phase`, `on_exit_documentation_phase`
- **Probleem:** Drie methoden met vrijwel identieke body (lees deliverables → call PhaseContractResolver → log → raise op failure)
- **Vereiste:** Eén generieke `_run_exit_gate(phase_name: str, branch: str, issue_number: int) -> None`. Specifieke methoden worden thin wrappers of worden direct via de exit-hooks registry aangeroepen.
- **Verificatie:** `(Select-String "def on_exit_.*_phase" mcp_server/managers/phase_state_engine.py).Count` ≤ 1

---

#### Gap 6 — KPI 11: f-string logging in PSE (CODE_STYLE-schending)

- **Locatie:** `mcp_server/managers/phase_state_engine.py` — meerdere `logger.info(f"...")` / `logger.warning(f"...")`
- **Vereiste:** Vervang alle f-string logcalls door parameterized logging:
  ```python
  # Fout:
  logger.info(f"Planning exit gate passed for branch {branch} (issue {issue_number})")
  # Correct:
  logger.info("Planning exit gate passed for branch %s (issue %s)", branch, issue_number)
  ```
- **Scope:** Alle `logger.*` calls in `phase_state_engine.py` met f-string
- **Verificatie:** `Select-String 'logger\.\w+\(f"' mcp_server/managers/phase_state_engine.py` → 0 matches

---

### PRIORITEIT 3 — Directory structuur en file cleanup (blokkeren KPIs 2, 4, 5)

#### Gap 7 — KPI 2 + 4: `.st3/` map-split onvolledig

- **Huidige staat:** `.st3/config/` bevat alleen `enforcement.yaml` + `phase_contracts.yaml`. `.st3/registries/` bestaat niet. `workflows.yaml`, `workphases.yaml`, `git.yaml`, `artifacts.yaml` e.d. staan nog in `.st3/` root. `deliverables.json` staat in `.st3/` root in plaats van `.st3/registries/`.
- **Vereiste stappen:**
  1. Maak `.st3/registries/` aan
  2. Update `ProjectManager.deliverables_file` → `.st3/registries/deliverables.json`
  3. Update `FileStateRepository` path → `.st3/registries/state.json`
  4. Zoek en update alle hardcoded `".st3/state.json"` en `".st3/deliverables.json"` refs in source
  5. Update enforcement.yaml post-merge paths (Gap 2) naar de nieuwe registries/-paden
- **Verificatie:** `Get-ChildItem .st3\ -File` → 0 bestanden in `.st3/` root; `Test-Path .st3/registries/deliverables.json` → True na eerste write

---

#### Gap 8 — KPI 5: `.st3/projects.json` bestand bestaat nog fysiek

- **Huidig:** Geen Python-source verwijst er nog naar ✅, maar het bestand zelf staat er nog
- **Vereiste:** Verwijder `.st3/projects.json` (flag-day C4, gepland maar niet uitgevoerd)
- **Verificatie:** `Test-Path .st3\projects.json` → False

---

### PRIORITEIT 4 — String literals en config (KPIs 12, 14)

#### Gap 9 — KPI 12: "tdd" literals in `git_tools.py`

- **Locatie:** `mcp_server/tools/git_tools.py`
  - ~line 202: `description` van `workflow_phase` param bevat `"research|planning|design|tdd|..."` → update naar `"implementation"`
  - ~line 248: voorbeeld `"test(P_TDD_SP_RED): message"` → update naar `"test(P_IMPLEMENTATION_SP_RED): message"`
  - ~lines 286–287: `"cycle_number is required for TDD phase commits"` → `"cycle_number is required for implementation phase commits"`
- **Verificatie:** `Select-String "\btdd\b" mcp_server/tools/git_tools.py` → 0 matches

---

#### Gap 10 — KPI 12: "tdd" in test-fixtures

- **Locatie 1:** `tests/mcp_server/fixtures/workflow_fixtures.py` — phaselijsten met `"tdd"` (~lines 26, 39, 49, 59) → vervang door `"implementation"`
- **Locatie 2:** `tests/mcp_server/unit/config/test_workflow_config.py` — fixtures/assertions met `"tdd"` (~lines 41, 47, 292, 346, 441, 466, 467) → update
- **Verificatie:** `Select-String "\btdd\b" tests/mcp_server/` → 0 matches

---

#### Gap 11 — KPI 14: `branch_name_pattern` enforceert geen issue-nummer

- **Locatie:** `.st3/git.yaml`
- **Huidig:** `branch_name_pattern: "^[a-z0-9-]+$"`
- **Vereiste:** `branch_name_pattern: "^[0-9]+-[a-z][a-z0-9-]*$"` (KPI 14: issue-nummer verplicht als prefix)
- **Test:** `create_branch(name="my-feature-without-number")` moet `ValidationError` geven
- **Verificatie:** Pattern-test toevoegen of aanpassen in unit-tests voor `git_manager`

---

### PRIORITEIT 5 — Grote PSE refactor (KPI 3)

#### Gap 12 — KPI 3: PSE exit-hooks lezen `planning_deliverables` nog steeds direct

- **Planning Cycle 3 success criterion:** *"PSE exit-hooks call PhaseContractResolver and DeliverableChecker — no hardcoded deliverables in PSE"*
- **Huidige staat:** `on_exit_planning_phase()` leest direct `planning_deliverables["tdd_cycles"]["cycles"][]["deliverables"]` etc. via dict-key lookups. `PhaseContractResolver` bestaat ✅ maar wordt niet door PSE exit-hooks gebruikt.
- **Bewijs:** `Select-String "planning_deliverables" mcp_server/managers/phase_state_engine.py` geeft meerdere matches
- **Vereiste:** PSE exit-hooks delegeren gate-check volledig aan `PhaseContractResolver.resolve(workflow_name, phase, issue_number)` + `DeliverableChecker`. Geen directe `planning_deliverables[...]` key-traversal in `phase_state_engine.py`.
- **Verificatie:** `Select-String "planning_deliverables" mcp_server/managers/phase_state_engine.py` → 0 matches
- **Opmerking:** Dit is de complexste resterende gap. Bouw als aparte commit/sub-taak zodat regressie eenvoudig te isoleren is.

---

## Aanbevolen aanpak op andere machine

1. **Analyseer eerst hoe de gaps hebben kunnen ontstaan** — bekijk design.md en planning.md opnieuw voor Cycles 3, 4, 6 (PSE refactor, dir-structuur, post-merge enforcement). Bepaal of pre-implementatie-fases onvolledig waren of of de implementatie-agent incorrect heeft geïmplementeerd.

2. **Volgorde van dichten (na analyse):**
   1. Gap 1 + 2 sluiten (Cycle 7 directe deliverables) → C7 Stop/Go
   2. Gap 7 + 8 (dir-structuur + file cleanup) — veel path-updates, doe dit vóór enforcement.yaml aanpassen
   3. Gaps 3–6 samen (PSE structurele refactor, samenhangend) → 1 commit
   4. Gaps 9–11 (string/config fixes, low risk)
   5. Gap 12 als laatste (grootste scope, eigen commit)

3. **Na elke stap:** run `pytest` + ruff + pyright om regressie vroegtijdig te detecteren.

## Belangrijke bestanden / locaties

| Bestand | Relevantie |
|---------|-----------|
| `mcp_server/managers/project_manager.py` | Gap 1 (B2 guard) |
| `mcp_server/managers/enforcement_runner.py` | Gap 2A (delete_file handler) |
| `.st3/config/enforcement.yaml` | Gap 2B (post-merge rule) |
| `mcp_server/managers/phase_state_engine.py` | Gaps 3–6, 12 |
| `.st3/config/phase_contracts.yaml` | KPI 6 context |
| `.st3/git.yaml` | Gap 11 (branch pattern) |
| `mcp_server/tools/git_tools.py` | Gap 9 ("tdd" literals) |
| `tests/mcp_server/fixtures/workflow_fixtures.py` | Gap 10 |
| `tests/mcp_server/unit/config/test_workflow_config.py` | Gap 10 |
| `docs/implementation/issue_257/design.md` | Architectuur beslissingen A–J, F1–F6.6 |
| `docs/implementation/issue_257/planning.md` | Cycles 1–7, succes criteria, B1–B5 |
| `docs/implementation/issue_257/research_config_first_pse.md` | KPIs 1–20 (Stop/Go criteria) |
