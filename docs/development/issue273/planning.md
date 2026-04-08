<!-- docs\development\issue273\planning.md -->
<!-- template=planning version=130ac5ea created=2026-04-07T13:16Z updated= -->
# Issue #273: Planning — Remove commit_prefix_map from git.yaml

**Status:** DRAFT  
**Version:** 1.0  
**Last Updated:** 2026-04-07

---

## Purpose

Eén TDD-cyclus om dode code en een bug in één atomaire commit-reeks te verwijderen.

## Scope

**In Scope:**
.st3/config/git.yaml, mcp_server/config/schemas/git_config.py, mcp_server/core/policy_engine.py, .st3/config/policies.yaml, bijbehorende tests en fixtures (8 bestanden)

**Out of Scope:**
PhaseContractResolver, phase_contracts.yaml, commit_types veld zelf, GitManager, ScopeEncoder, git_add_or_commit tool logic

## Prerequisites

Read these first:
1. Research afgerond (docs/development/issue273/research.md)
2. Branch refactor/273-remove-commit-prefix-map actief op tdd-fase
3. main up-to-date (SHA 75ad38c, epic #257 gesloten)
---

## Summary

Verwijder de redundante velden commit_prefix_map en tdd_phases uit git.yaml en GitConfig. Herstel PolicyEngine zodat alle 11 commit-types worden geaccepteerd via de SSOT commit_types. Breaking/flag-day change: geen backward compatibility, geen legacy verwijzingen na implementatie.

---

## Dependencies

- get_all_prefixes() wijziging in git_config.py is vereist vóór PolicyEngine-test slaagt
- git.yaml wijziging en git_config.py wijziging moeten samen zijn in GREEN (Pydantic-validatie laadt git.yaml bij import)

---

## TDD Cycles


### Cycle 1 RED — Schrijf falende tests

**Goal:** Alle testen en fixtures bijwerken zodat ze de nieuwe toestand (zonder `commit_prefix_map` en `tdd_phases`) verwachten. De testsuite faalt na deze stap want productiecode is nog niet aangepast.

**Stap 1 — `tests/mcp_server/config/test_git_config.py`**

In `_git_config_payload()`: verwijder de sleutels `tdd_phases` en `commit_prefix_map` volledig.

Verwijder de volgende testmethoden:
- `test_has_phase` — test van dode methode `GitConfig.has_phase()`
- `test_get_prefix` — test van dode methode `GitConfig.get_prefix()`
- `test_get_all_prefixes` (bestaand) — asserteert `== ["test:", "feat:", "refactor:", "docs:"]`, onjuist na fix
- `test_invalid_commit_prefix_phase_raises` — test van verwijderde cross-ref validator

Update `test_load_git_yaml_success`: verwijder assertions op `config.tdd_phases` en `config.commit_prefix_map`.

Voeg toe: nieuw `test_get_all_prefixes` dat alle 11 types asserteert:
```python
def test_get_all_prefixes(self) -> None:
    config = _load_git_config()
    expected = [
        "feat:", "fix:", "docs:", "style:", "refactor:",
        "test:", "chore:", "perf:", "ci:", "build:", "revert:",
    ]
    assert config.get_all_prefixes() == expected
```

**Stap 2 — `tests/mcp_server/core/test_policy_engine_config.py`**

Voeg toe aan `TestPolicyEngineConfigIntegration`:
```python
def test_commit_allows_all_commit_types(self) -> None:
    for prefix in ["chore:", "fix:", "ci:", "build:", "perf:", "style:", "revert:"]:
        decision = self.engine.decide(
            operation="commit",
            context={"message": f"{prefix} some message"},
        )
        assert decision.allowed is True, (
            f"Expected '{prefix}' to be allowed after fix, got: {decision.reason}"
        )
```

**Stap 3 — 6 fixture-helpers (verwijder `tdd_phases` + `commit_prefix_map` sleutels)**

| Bestand | Context | Te verwijderen |
|---|---|---|
| `tests/mcp_server/integration/test_workflow_cycle_e2e.py` | `git_config` dict (~regel 115) | `tdd_phases`, `commit_prefix_map` |
| `tests/mcp_server/tools/test_pr_tools_config.py` | `custom_config` dict (~regel 33) | `tdd_phases`, `commit_prefix_map` |
| `tests/mcp_server/tools/test_git_tools_config.py` | `custom_config` dict (~regel 35) | `tdd_phases`, `commit_prefix_map` |
| `tests/mcp_server/unit/managers/test_github_manager.py` | `GitConfig(...)` constructor (~regel 207) | `tdd_phases=`, `commit_prefix_map=` |
| `tests/unit/config/test_c_loader_structural.py` | `write_yaml("git.yaml", ...)` dict (~regel 59) | `tdd_phases`, `commit_prefix_map` |
| `tests/mcp_server/unit/config/test_loader_behaviors.py` | YAML-string `"branch_types: []\ntdd_phases: []\n"` (~regel 74) | `tdd_phases: []` uit de string |

**Success Criteria:**
- `pytest tests/mcp_server/config/test_git_config.py` → faalt op `test_get_all_prefixes` (productiecode nog oud)
- `pytest tests/mcp_server/core/test_policy_engine_config.py` → faalt op `test_commit_allows_all_commit_types`
- Alle 6 fixture-bestanden compileren foutloos
- Geen `tdd_phases` of `commit_prefix_map` meer in testcode

---

### Cycle 1 GREEN — Minimale productiewijzigingen

**Goal:** Productiecode aanpassen zodat alle RED-testen slagen. Geen nieuw gedrag toevoegen.

**Stap 1 — `.st3/config/git.yaml`**

Verwijder de twee blokken inclusief commentaarregels:
```yaml
# Convention #2: TDD phases (commit_tdd_phase validation)
tdd_phases:
  - red
  - green
  - refactor
  - docs

# Convention #3: Commit prefix mapping (TDD phase → Conventional Commit)
commit_prefix_map:
  red: test
  green: feat
  refactor: refactor
  docs: docs
```
Hernummer overblijvende `Convention #4–#6` commentaren naar `Convention #2–#4`.

**Stap 2 — `mcp_server/config/schemas/git_config.py`**

Verwijder velden:
```python
tdd_phases: list[str] = Field(...)
commit_prefix_map: dict[str, str] = Field(...)
```

Verwijder de gehele `validate_cross_references` model_validator (bevat zowel de prefix/phase cross-ref als de branch_name_pattern validatie). **Let op:** `test_whitespace_branch_name_pattern_raises` en `test_invalid_branch_name_regex_raises` moeten blijven slagen. Breng de regex-validatielogica over naar een nieuwe dedicated validator:
```python
@model_validator(mode="after")
def validate_branch_name_pattern(self) -> GitConfig:
    pattern = str(self.branch_name_pattern)
    if not pattern or pattern.isspace():
        raise ValueError(
            "branch_name_pattern cannot be empty. "
            "Provide a valid regex pattern (e.g. '^[a-z0-9-]+$' for kebab-case)"
        )
    try:
        GitConfig._compiled_pattern = re.compile(pattern)
    except re.error as exc:
        raise ValueError(
            f"Invalid branch_name_pattern regex: {pattern}. Error: {exc}"
        ) from exc
    return self
```

Verwijder de dode methoden:
```python
def has_phase(self, phase: str) -> bool: ...
def get_prefix(self, phase: str) -> str: ...
```

Herschrijf `get_all_prefixes()`:
```python
# Van:
def get_all_prefixes(self) -> list[str]:
    prefix_dict: dict[str, str] = dict(self.commit_prefix_map)
    return [f"{prefix}:" for prefix in prefix_dict.values()]

# Naar:
def get_all_prefixes(self) -> list[str]:
    return [f"{t}:" for t in self.commit_types]
```

**Stap 3 — `.st3/config/policies.yaml` (~regel 44)**

```yaml
# Van:
require_tdd_prefix: true  # Commit messages must start with TDD phase prefix (via GitConfig.commit_prefix_map)

# Naar:
require_tdd_prefix: true  # Commit messages must start with a conventional commit type (via GitConfig.commit_types)
```

**Stap 4 — `mcp_server/core/policy_engine.py` (~regel 157)**

Geen logicawijziging. Update commentaar bij de aanroep als aanwezig:
```python
valid_prefixes = self._git_config.get_all_prefixes()  # via GitConfig.commit_types
```

**Stap 5 — `tests/mcp_server/core/test_policy_engine_config.py` (~regel 22)**

Update docstring van `test_commit_uses_git_config_prefixes`:
```python
# Van:
"Fix: PolicyEngine should derive prefixes from GitConfig.commit_prefix_map"

# Naar:
"Fix: PolicyEngine should derive prefixes from GitConfig.commit_types"
```

**Success Criteria:**
- `pytest tests/mcp_server/config/test_git_config.py` → volledig groen
- `pytest tests/mcp_server/core/test_policy_engine_config.py` → volledig groen
- `pytest tests/` → volledige suite groen
- `grep -r "commit_prefix_map" .` (excl. `.git/`) → nul resultaten
- `grep -r "tdd_phases" .` (excl. `.git/`) → nul resultaten

---

### Cycle 1 REFACTOR — Kwaliteitscontrole

**Goal:** Verifieer code-kwaliteit en volledige afwezigheid van legacy referenties.

**Stap 1 — Quality gates**

```
run_quality_gates(scope="files", files=[
    "mcp_server/config/schemas/git_config.py",
    "mcp_server/core/policy_engine.py",
])
```

**Stap 2 — Codebase-brede grep**

Verifieer nul verwijzingen naar:
- `commit_prefix_map` → nul hits
- `tdd_phases` → nul hits
- `has_phase` → nul hits (methode verwijderd)
- `get_prefix` → nul hits (methode verwijderd)
- `validate_cross_references` → nul hits

**Stap 3 — Volledige testsuite**

```
run_tests(path="tests/")
```

**Success Criteria:**
- Geen ruff/mypy/pylint fouten op gewijzigde bestanden
- Nul legacy verwijzingen in de hele codebase
- Volledige testsuite groen


---

## Risks & Mitigation

- **Risk:** Onbekende fixtures buiten de impact-analyse gebruiken nog `tdd_phases`/`commit_prefix_map`.
  - **Mitigation:** Na GREEN een codebase-brede grep uitvoeren op beide namen (REFACTOR-stap 2). Bij treffer: fix toevoegen en tests herdraaien vóór commit.

- **Risk:** `validate_cross_references` bevat ook de `branch_name_pattern` validatielogica. Door de volledige validator te verwijderen vallen `test_whitespace_branch_name_pattern_raises` en `test_invalid_branch_name_regex_raises` weg.
  - **Mitigation:** De regex-validatielogica overplaatsen naar een nieuwe `validate_branch_name_pattern` validator (uitgewerkt in GREEN stap 2). RED-stap verandert die tests niet — ze moeten groen blijven na GREEN.

- **Risk:** Volgorde RED → GREEN is kritisch. Als productiecode eerst wordt aangepast vóór fixtures bijgewerkt zijn, mislukken bestaande tests met Pydantic-validatiefouten in plaats van de verwachte assertion-fouten.
  - **Mitigation:** Strikte RED-GREEN scheiding: fixtures én nieuwe testkeuzes first, productiewijzigingen second.

---

## Milestones

- C1 RED committed: alle falende tests aanwezig, fixtures schoon
- C1 GREEN committed: alle tests groen, geen legacy verwijzingen in productie
- C1 REFACTOR committed: quality gates clean
- PR aangemaakt naar main

## Related Documentation
- **[docs/development/issue273/research.md][related-1]**

<!-- Link definitions -->

[related-1]: docs/development/issue273/research.md

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 |  | Agent | Initial draft |