# Sessie Overdracht — Issue #251 — 2026-02-23

**Branch:** `refactor/251-refactor-run-quality-gates`
**Fase:** TDD — cycle 23 (nog niet gestart, volgende stap = C23 RED)
**Datum:** 2026-02-23
**Status werkboom:** schoon (alle wijzigingen gecommit)

---

## Wat er gedaan is deze sessie

### 1. C22 afgerond (voor sessionstart)
- Commits `471eae6` (GREEN) en `b694dcd` + `4f5dfae` (REFACTOR) waren al compleet.

### 2. Remediation: C13–C22 in lijn gebracht met design.md + planning.md

Na een read-only review van planning.md:87–444 en design.md:141–285 zijn 6 non-conformances gevonden en gefixed. Alles gecommit als `835b152`.

| Non-conformance | Fix |
|----------------|-----|
| **C17/C18:** `_is_pytest_gate` bestond nog; `_get_skip_reason` had een onnodige `gate`-parameter en `is_file_specific_mode`-logica | `_is_pytest_gate` volledig verwijderd; `_get_skip_reason(gate_files)` vereenvoudigd tot 3 regels; alle call-sites bijgewerkt in prod + 4 testbestanden |
| **C17/C18:** `_files_for_gate` had een pytest-special-case die lege lijst teruggaf | Special-case verwijderd; methode is nu puur capability-driven via `file_types` |
| **C21:** `project_scope.include_globs` ontbrak in `.st3/quality.yaml` | Toegevoegd: `mcp_server/**/*.py` en `tests/mcp_server/**/*.py` |
| **C22:** `_resolve_branch_scope` gebruikte `HEAD~1..HEAD` (hardcoded) | Leest nu `workflow.parent_branch` uit `.st3/state.json`, fallback `"main"` → `git diff --name-only <parent>..HEAD` |
| **C14:** `json_field` en `text_regex` dispatch-branches stonden nog in `_execute_gate` | Beide branches verwijderd; `TestJsonFieldSuccessCriteria` class (5 tests) verwijderd |
| **Tests:** `test_skip_reason_unified.py`, `test_files_for_gate.py`, `test_qa_manager.py` testten nog oud gedrag | Alle tests herschreven/verwijderd conform nieuw contract |

**QG na remediation:** 5/5 ✅ (Gate 0–4b)
**Testsuite:** 1982/1982 ✅

### 3. Findings doc bijgewerkt
`docs/development/issue251/quality_gate_findings.md` uitgebreid met 4 nieuwe entries en 4 tabelrijen voor de QG-violations gevonden tijdens de remediation-REFACTOR:
- ARG002: `gate`-parameter ongebruikt in `_get_skip_reason`
- F841: `combined_output` dode variabele na verwijderen json_field/text_regex branches
- PLC0415: `import json as _json` binnenin testfunctie
- Gate 0 Ruff Format: 2 methode-signaturen over 3 regels in `test_qa_manager.py`

---

## Huidige toestand codebase

### `mcp_server/managers/qa_manager.py` — relevante methoden

```python
def _files_for_gate(self, gate: QualityGate, python_files: list[str]) -> list[str]:
    """Puur capability-driven — geen pytest-special-case."""
    eligible = [f for f in python_files if any(str(f).endswith(ext) for ext in gate.capabilities.file_types)]
    if gate.scope is not None:
        eligible = gate.scope.filter_files(eligible)
    return eligible

def _get_skip_reason(self, gate_files: list[str]) -> str | None:
    """Vereenvoudigd: alleen controleren of er bestanden zijn."""
    if not gate_files:
        return "Skipped (no matching files)"
    return None

def _resolve_branch_scope(self) -> list[str]:
    """Leest parent_branch uit state.json; fallback 'main'."""
    parent = "main"
    if self.workspace_root is not None:
        state = self._load_state_json(self.workspace_root / ".st3" / "state.json")
        parent = state.get("workflow", {}).get("parent_branch") or "main"
    result = subprocess.run(
        ["git", "diff", "--name-only", f"{parent}..HEAD"], ...
    )
    ...
```

`_is_pytest_gate` → **verwijderd**
`_execute_gate` dispatch: alleen `json_violations`, `text_violations`, `exit_code` (+ `else` fallback)

### `.st3/quality.yaml`
```yaml
project_scope:
  include_globs:
    - "mcp_server/**/*.py"
    - "tests/mcp_server/**/*.py"
```

---

## Volgende stap: C23 RED

**Doel (planning.md:421):** `run_quality_gates(scope="auto")` met aanwezige baseline geeft de **unie** van `git diff --name-only <baseline_sha>..HEAD` en `failed_files` (persisted in baseline state).

### Wat C23 RED moet testen

Er zijn twee dingen die de auto-scope moet combineren:
1. Bestanden gewijzigd t.o.v. de baseline SHA (`baseline_sha..HEAD` diff)
2. Bestanden die bij de vorige run gefaald hebben (`failed_files` in baseline state)

De RED-test schrijft cases waarbij de huidige implementatie **één van de twee negeert**:
- Test A: `failed_files = ["old_fail.py"]`, geen diff → auto-scope geeft `[]` (fout: moet `["old_fail.py"]` geven)
- Test B: diff = `["changed.py"]`, geen `failed_files` → auto-scope geeft `[]` (fout: moet `["changed.py"]` geven)
- Test C: beide aanwezig → unie verwacht; huidige impl geeft incompleet resultaat

### Relevante klassen/methoden

- `QAManager._resolve_auto_scope()` — **bestaat nog niet**, moet worden aangemaakt
- `QAManager.run_quality_gates(scope: str | list[str])` — de `scope="auto"` branch roept `_resolve_auto_scope()` aan
- Baseline state: `QAManager._load_baseline_state()` of gelijkwaardig (zie hoe `_resolve_branch_scope` `_load_state_json` gebruikt)
- Design contract in `design.md` sectie over scope-resolution

### Testbestand voor C23

Nieuw bestand aanmaken:
```
tests/mcp_server/unit/mcp_server/managers/test_auto_scope_resolution.py
```

Bestaande scope-testsuite als referentie:
```
tests/mcp_server/unit/mcp_server/managers/test_scope_resolution.py
```

### Aandachtspunten

- `_resolve_branch_scope` gebruikt nu `parent_branch..HEAD` — voor auto-scope wil je `baseline_sha..HEAD` (andere ref)
- Scherm de twee git-diff varianten duidelijk af: branch-scope ≠ auto-scope
- `failed_files` staat in de baseline state (niet in workflow state); check hoe `C19/C20` de baseline state persisteren

### Hoe starten

```python
# 1. Check waar baseline_sha en failed_files worden opgeslagen
# (C19/C20 implementatie)
grep_search "baseline_sha|failed_files" in qa_manager.py

# 2. Lees design.md sectie scope=auto
read_file design.md rond "scope=auto" / "auto"

# 3. Schrijf RED tests in test_auto_scope_resolution.py
# 4. Run tests → verwacht: FAIL
# 5. Commit: git_add_or_commit(workflow_phase="tdd", cycle_number=23, sub_phase="red", ...)
```

---

## Git log recente commits (deze + vorige sessie)

```
835b152  refactor(P_TDD_C23_SP_REFACTOR): bring C14/C17/C18/C21/C22 into design conformance ...
4f5dfae  refactor(P_TDD_C22_SP_REFACTOR): update findings doc with C22 QG violations
b694dcd  refactor(P_TDD_C22_SP_REFACTOR): fix ARG001 in test_scope_resolution mock callbacks
471eae6  feat(P_TDD_C22_SP_GREEN): implement _resolve_branch_scope using git diff --name-only HEAD~1..HEAD
```

---

## Omgeving

- Python: 3.13.5, venv: `.venv`
- Activeren: `. .venv/Scripts/Activate.ps1` (Windows PowerShell)
- Tests draaien: `run_tests(path="tests/mcp_server/unit/mcp_server/managers/")`
- QG draaien: `run_quality_gates(files=[...])`
- MCP server starten: `start_mcp_server.ps1`
