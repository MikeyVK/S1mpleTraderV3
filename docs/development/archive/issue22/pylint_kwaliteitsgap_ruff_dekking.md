<!-- docs\development\issue257\pylint_kwaliteitsgap_ruff_dekking.md -->
<!-- template=research version=8b7bb3ab created=2026-03-26T14:20Z updated= -->
# Pylint Quality Gap — Coverage via Ruff Config

**Status:** DRAFT  
**Version:** 1.0  
**Last Updated:** 2026-03-26

---

## Purpose

Decide what to add to pyproject.toml [tool.ruff.lint] to close the real quality gaps surfaced by the pylint IDE scan.

## Scope

**In Scope:**
mcp_server/ production code and tests/mcp_server/ as scanned by Pylint IDE extension on 2026-03-26; pyproject.toml ruff config; ruff rule catalogue (G, BLE, D1xx groups)

**Out of Scope:**
backend/ package; full pylint re-integration; .st3/quality.yaml CI gate changes; violations in files not open in the IDE at scan time

## Prerequisites

Read these first:
1. Quality gates 0–6 defined in docs/coding_standards/QUALITY_GATES.md
2. Ruff rule catalogue (https://docs.astral.sh/ruff/rules/)
3. pylint scan output as provided in session (2026-03-26)
---

## Problem Statement

A pylint scan of files open in the IDE revealed ~150 diagnostics across production and test code. The project's formal quality gates (0–6) use ruff/mypy/pytest — pylint is not part of the gate chain. This creates a gap: violations that pylint detects are not caught by any automated gate. The question is whether this gap can be closed by extending the existing ruff config, without re-introducing pylint.

## Research Goals

- Categorise all diagnostics from the IDE scan into: real violations, false positives, and structural/design issues
- Map each real violation to the ruff rule that would catch its equivalent
- Determine blast radius of activating each new ruff rule on the existing codebase
- Identify violations that are structurally unfixable via ruff config alone
- Propose minimal config change to pyproject.toml that closes the production violations without noise

---

## Background

Pylint was removed from the formal quality gates at some point in favour of ruff + mypy. The IDE still runs pylint as a passive linter. A handover of ~150 diagnostics was provided covering: E1101 (no-member), W1203 (logging-fstring), C0115/C0116 (missing docstring), W0212 (protected-access), W0621 (redefined-outer-name), W0718 (broad-exception-caught).

---

## Findings

## Categorised Diagnostics

### Categorie 1 — FALSE POSITIVES (E1101 Pydantic v2)

Pylint `E1101:no-member` fires on Pydantic v2 field access because pylint does not understand Pydantic's metaclass-based field resolution. Affected:
- `mcp_server/config/schemas/quality_config.py` L51: `self.defaults.values()` (field is `dict[str, str]`)
- `tests/mcp_server/unit/tools/test_create_issue_input.py` L92, 97, 147, 161, 162, 163: `inp.body.problem`, `.expected`, `.related_docs`, `.steps_to_reproduce`

**Root cause:** Known Pylint+Pydantic v2 incompatibility. Documented in QUALITY_GATES.md §'Known Acceptable Warnings §2'.
**ruff dekking:** n.v.t. — false positive.
**Fix:** `pylint-pydantic` plugin (als pylint ooit terugkeert).

---

### Categorie 2 — ECHTE PRODUCTIEOVERTREDING: W1203 → G004 (12×)

**Bestand:** `mcp_server/managers/phase_state_engine.py`
**Regels:** 588, 608, 647, 667, 691, 714, 722, 745, 753, 776, 784, 800
**Patroon:** `logger.info(f"...")` — fstring-interpolation in logging call.
**Impact:** Verhindert lazy evaluation; string wordt altijd gebouwd, ook als het logniveau uitgeschakeld is.
**ruff equivalent:** `G004` (flake8-logging-format rule set `G`).
**Blast radius:** Minimaal — patroon bestaat uitsluitend in phase_state_engine.py.

---

### Categorie 3 — ECHTE PRODUCTIEOVERTREDING: C0116/C0115 → D1xx (11×)

**Bestanden:**
- `mcp_server/config/schemas/git_config.py` — 10 methoden zonder docstring (regels 63, 87, 90, 95, 98, 101, 104, 107, 111, 114)
- `mcp_server/config/schemas/quality_config.py` — 1 methode zonder docstring (`filter_files`, regel 95)

**ruff equivalent:** `D` rule set (pydocstyle), met name `D102` (missing docstring in public method) en `D101` (missing docstring in public class).
**Blast radius:** ONBEKEND — `D`-rules zijn niet eerder actief geweest op de codebase. Audit run vereist vóór activering.
**Alternatief:** Direct de 11 ontbrekende docstrings schrijven (lagere blast radius dan gate activeren).

---

### Categorie 4 — ECHTE PRODUCTIEOVERTREDING: W0718 → BLE001 (3×)

**Bestanden:**
- `mcp_server/server.py` L500: `except Exception as exc:  # noqa: BLE001`
- `tests/mcp_server/unit/tools/test_create_issue_errors.py` L162, L171: `except Exception as exc:  # noqa: BLE001`

**Opmerking:** Alle drie locaties hebben al `# noqa: BLE001`. De codebase bevat 12 `# noqa: BLE001` suppressions totaal — inclusief `label_config.py`, `core/error_handling.py`, scaffolding templates. Dit bewijst dat de authors `BLE` al verwacht hadden actief te zijn.
**ruff equivalent:** `BLE001` (flake8-blind-except, rule set `BLE`).
**Blast radius:** Nul — alle intentionele `except Exception` hebben al de suppressie.

---

### Categorie 5 — STRUCTUREEL (W0621 fixture-scoping) — geen ruff equivalent

**Bestanden:**
- `tests/mcp_server/unit/integration/test_github.py` L19, L39: `mock_adapter` shadowing
- `tests/mcp_server/unit/tools/test_issue_tools.py` L28, 55, 84, 103, 123, 138, 162: `mock_github_manager` shadowing

**ruff dekking:** Geen. W0621 heeft geen directe ruff-equivalent.
**Fix:** `@pytest.fixture(name='mock_adapter')` met private functienaam `_mock_adapter(...)` — standaard pytest-patroon per QUALITY_GATES.md §4.

---

### Categorie 6 — STRUCTUREEL (W0212 protected-access) — geen ruff equivalent

**Subgroep A — `_assemble_labels` (20× in test_create_issue_label_assembly.py):**
Whitebox-test van private methode. Beslissing: `_assemble_labels` → `assemble_labels` (API publiek maken) OF testen via publieke tool-interface.

**Subgroep B — `_git_config` singleton reset in conftest.py L28–29:**
Noodzakelijke test-isolatie. Fix: `classmethod reset_for_testing()` toevoegen.

**Subgroep C — `_resolve_scope`, `_build_compact_result` (test_all_tools.py), `_milestone_config` (test_issue_tools.py):**
Idem; testen via publieke interface of methode publiek verklaren.

**ruff dekking:** Geen. W0212 heeft geen directe ruff-equivalent.

---

### Categorie 7 — CONVENTIE (C0115/C0116 in test-bestanden) — ~150×

Vrijwel alle testmethoden en test-klassen missen docstrings. Technisch overtreding van CODE_STYLE.md, maar zelfverklarend via methodenamen (`test_body_must_not_be_plain_string` etc.).
**ruff equivalent:** `D`-rules zijn activeerbaar via `per-file-ignores` uitzondering voor tests.
**Beslissing:** Optie A (config-uitzondering voor tests, consistent met bestaand `ANN`-beleid) of Optie B (~150 one-liner docstrings).

---

## Aanbevolen config-wijziging (minimaal, nul blast radius)

```toml
# pyproject.toml [tool.ruff.lint]
select = [
    "E", "W", "F", "I", "N", "UP", "ANN", "B", "C4", "DTZ", "T10",
    "ISC", "RET", "SIM", "ARG", "PLC",
    "G",    # NIEUW — W1203 fstring logging (G004), blast radius: ~12 regels
    "BLE",  # NIEUW — W0718 broad-exception (BLE001), blast radius: 0 (alle # noqa al aanwezig)
]
```

Daarnaast: 11 ontbrekende docstrings in `git_config.py` en `quality_config.py` direct schrijven.

## Open Questions

- ❓ Moet `D`-rule set geactiveerd worden voor productiegode, of volstaat handmatig de 11 ontbrekende docstrings schrijven?
- ❓ Worden W0621 fixture-scoping fixes (cat. 5) opgepakt als onderdeel van C_CLEANUP of als los ticket?
- ❓ Moet `_assemble_labels` gepromoveerd worden naar publieke API (cat. 6A), of is testen via publieke tool-interface de juiste aanpak?
- ❓ Moet `reset_for_testing()` op `CreateBranchInput`/`CreatePRInput` als deliverable in C_LOADER.3 worden toegevoegd?


## Related Documentation
- **[docs/coding_standards/QUALITY_GATES.md][related-1]**
- **[docs/coding_standards/CODE_STYLE.md][related-2]**
- **[docs/development/issue257/gap_analyse_architectuur_dekking.md][related-3]**
- **[docs/development/issue257/planning.md][related-4]**

<!-- Link definitions -->

[related-1]: docs/coding_standards/QUALITY_GATES.md
[related-2]: docs/coding_standards/CODE_STYLE.md
[related-3]: docs/development/issue257/gap_analyse_architectuur_dekking.md
[related-4]: docs/development/issue257/planning.md

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 |  | Agent | Initial draft |