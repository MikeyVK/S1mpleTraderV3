# Quality Gate Findings — Issue #251

**Branch:** `refactor/251-refactor-run-quality-gates`
**Scope:** TDD cycles C0–C32 for `run_quality_gates` refactor
**Purpose:** Track recurring QG failures and fixes for post-issue cleanup / rule review.

---

## Bevindingen

### [C8 REFACTOR] ANN401 — `-> Any` return type in static helper

**Gate:** Gate 1: Ruff Strict Lint (`ANN` ruleset)
**File:** `mcp_server/managers/qa_manager.py`
**Methode:** `_resolve_field_path`
**Fout:**
```
ANN401 — Dynamically typed expressions (typing.Any) are disallowed in `_resolve_field_path`
```
**Fix:** `# noqa: ANN401` toegevoegd aan de methodedefinitie.
**Vraag voor later:**
- Is `-> Any` hier werkelijk de enige optie? Alternatief: `-> str | int | float | dict | list | None` (union), of een TypeVar.
- Overweeg of `ANN401` in pyproject.toml versoepeld moet worden voor gevallen waar `Any` semantisch correct is (traversal van ongetypeerde JSON).
- Huidig beleid: gerichte `noqa` als laatste redmiddel (zie TYPE_CHECKING_PLAYBOOK).

---

### [C8 REFACTOR] Ruff Format — methode-signatuur niet ingekort genoeg

**Gate:** Gate 0: Ruff Format
**File:** `tests/mcp_server/unit/mcp_server/managers/test_parse_json_violations_nested.py`
**Fout:**
```diff
-    def test_nested_path_three_segments(
-        self, manager: QAManager
-    ) -> None:
+    def test_nested_path_three_segments(self, manager: QAManager) -> None:
```
**Context:** Methode met alleen `self` + één fixture-argument past op één regel binnen 100 tekens. Ruff wil dit samenvoegen; de handmatig opgesplitste variant wordt geweigerd.
**Fix:** Signatuur samengevoegd op één regel.
**Patroon:** Let bij het schrijven van tests op: een gesplitste handtekening wordt door ruff-format automatisch teruggezet als de gecombineerde regel ≤ 100 tekens is. Schrijf korte signaturen dus meteen op één regel.

---

### [C12 REFACTOR] B023 — inner function bindt loop-variabelen niet

**Gate:** Gate 1: Ruff Strict Lint (`B` ruleset — flake8-bugbear)
**File:** `mcp_server/managers/qa_manager.py`
**Methode:** `_parse_text_violations`
**Fout:**
```
B023 — Function definition does not bind loop variable `groups` (line 785)
B023 — Function definition does not bind loop variable `safe_groups` (line 792)
```
**Context:** `_resolve` was een inner-functie gedefinieerd *binnen* de `for raw_line in output.splitlines()` loop die `groups` en `safe_groups` (loop-variabelen) sloot. Ruff B023 blokkeert dit omdat in Python inner functions in loops de variabele binden op het moment van *aanroep*, niet aanmaken — wat tot subtiele bugs kan leiden als de functie als callback wordt doorgegeven.
**Fix:** `_resolve` geëxtraheerd als `@staticmethod _resolve_text_field(field, groups, safe_groups, defaults) -> str | None`. Aanroepen: `self._resolve_text_field("field", groups, safe_groups, parsing.defaults)`.
**Vraag voor later:**
- B023 is terecht: inner functions in loops zijn tricky. Extracting naar static method is de cleanste oplossing.

---

### [C12 REFACTOR] Ruff Format — constructor calls én methode-calls ingekort

**Gate:** Gate 0: Ruff Format
**Files:** `test_parse_text_violations_defaults.py`, `qa_manager.py`
**Fout (test file):** 3 `TextViolationsParsing(pattern=..., defaults=...)` calls over 3 regels → samenvoegen op één regel (beide args passen in ≤ 100 tekens).
**Fout (qa_manager.py):** 2 `self._resolve_text_field("message", ...)` en `self._resolve_text_field("severity", ...)` aanroepen net > 100 tekens → ruff wil ze opsplitsen naar argument op eigen regel.
**Fix:** Constructor calls collapsed; lange method calls gesplitst met argument op inliggende regel.
**Patroon:** Bij 4 args in één method-call van `self.method("key", groups, safe_groups, parsing.defaults)` snel > 100 tekens. Ruff wil dan splitting; vooraf al opsplitsen is het veiligst.

---

### [C13 REFACTOR] Ruff Format — ternary en nested literal-args uitbreiden

**Gate:** Gate 0: Ruff Format
**Files:** `qa_manager.py`, `test_execute_gate_dispatch.py`
**Fout 1 — ternary op 3 regels:**
```python
# Te lang als 3-regelversie
result["score"] = (
    "Pass"
    if result["passed"]
    else f"Fail ({len(text_violations)} violations)"
)
# Ruff wil: één regel binnen ()
result["score"] = (
    "Pass" if result["passed"] else f"Fail ({len(text_violations)} violations)"
)
```
**Fout 2 — dict/list met trailing comma als directe functie-argument:**
```python
# Ruff expandeert ZOWEL de buitenste aanroep ALS het literal
return _make_gate({**caps, "key": val})  # ❌
return _make_gate(          # ✅
    {
        **caps,
        "key": val,         # trailing comma → ruff breidt beide uit
    }
)
# Zelfde voor json.dumps([{"key": "val"},])  →  json.dumps(\n    [...]\n)
```
**Patroon (nieuw):** Een dict of list met trailing comma als enig argument van een functie-aanroep → ruff breidt zowel de binnenste literal als de buitenste aanroep uit naar meerdere regels. Schrijf dit direct zo bij het opstellen van tests.

---

## Overzicht per cycle

| Cycle | Gate | Regel | Bestand | Actie |
|-------|------|-------|---------|-------|
| C8 REFACTOR | Gate 1 Ruff Strict Lint | ANN401 | `qa_manager.py` | `# noqa: ANN401` |
| C8 REFACTOR | Gate 0 Ruff Format | signatuur samenvoegen | `test_parse_json_violations_nested.py` | signatuur op één regel |
| C9 REFACTOR | Gate 0 Ruff Format | constructor call samenvoegen | `test_extract_violations_array.py` | `JsonViolationsParsing(...)` op één regel; signatuur collapsed |
| C11 REFACTOR | Gate 3 Line Length | E501 | `test_parse_text_violations.py` | `# noqa: E501` op regex constante-regel |
| C12 REFACTOR | Gate 1 Ruff Strict Lint | B023 | `qa_manager.py` | `_resolve` → `@staticmethod _resolve_text_field` |
| C12 REFACTOR | Gate 0 Ruff Format | constructor/method calls > 100 chars | `test_parse_text_violations_defaults.py`, `qa_manager.py` | collapsed / gesplitst |
| C13 REFACTOR | Gate 0 Ruff Format | ternary 3-regels: 1 regel in `()` | `qa_manager.py` | ternary op 1 regel |
| C13 REFACTOR | Gate 0 Ruff Format | dict/list trailing-comma arg → expand | `test_execute_gate_dispatch.py` | `_make_gate(\n    {...}\n)`, `json.dumps(\n    [...]\n)` |
| C14 REFACTOR | Gate 3 Line Length | E501 docstring te lang (105→101→91 chars) | `test_qa_manager.py` | docstring verkort op regel 1647 |
| C18 REFACTOR | Gate 1 Ruff Strict Lint | SIM300 Yoda condition | `test_qa_manager.py` | `"literal" == var` → `var == "literal"` op regel 1253 |
| C19 REFACTOR | Gate 0 Ruff Format | 2 method signaturen 3→1 regel | `test_baseline_advance.py` | `def test_...creates_state_file_if_absent(self, tmp_path)` + `calls_advance` collapsed |
| C19 REFACTOR | Gate 1 Ruff Strict Lint | F401 unused imports | `test_baseline_advance.py` | `import subprocess` + `import pytest` verwijderd (resterend na refactor) |
| C19 REFACTOR | Gate 4b Pyright | reportUnusedImport | `test_baseline_advance.py` | zelfde unused imports als F401 |
| C22 REFACTOR | Gate 1 Ruff Strict Lint | ARG001 unused function arguments | `test_scope_resolution.py` | 5× mock-callback `cmd`/`kw` → `_cmd`/`_kw` (fake_git_diff×3, fake_git_fail, fake_git_empty) |

---

## Open vragen / aanbevelingen

1. **ANN401 policy:** Wanneer is `-> Any` acceptabel en wanneer moeten we een nauwkeuriger type kiezen? Documenteer richtlijn in TYPE_CHECKING_PLAYBOOK.
2. **Ruff format gewenning:** Bij schrijven van nieuwe testmethoden bewust kiezen voor korte signaturen op één regel als ze ≤ 100 tekens zijn.
3. **Mogelijk: ruff config aanpassen** om `ANN401` globaal te ignoren voor `managers/` of alleen toe te staan met `noqa` — afhankelijk van hoe often dit nog optreedt.
