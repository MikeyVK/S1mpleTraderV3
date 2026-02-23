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
| Remediation C17/C18 REFACTOR | Gate 1 Ruff Strict Lint | ARG002 unused method arg `gate` | `qa_manager.py` + 4 testbestanden | `gate: QualityGate` param verwijderd uit `_get_skip_reason`; alle call-sites bijgewerkt |
| Remediation C14 REFACTOR | Gate 1 Ruff Strict Lint | F841 dead variable `combined_output` | `qa_manager.py` | `combined_output = ...` regel verwijderd (wees na deleten json_field/text_regex branches) |
| Remediation C22 addendum | Gate 2 Imports | PLC0415 inline import in testfunctie | `test_scope_resolution.py` | `import json as _json` → module-niveau `import json` |
| Remediation batch REFACTOR | Gate 0 Ruff Format | 2 signaturen 3→1 regel | `test_qa_manager.py` | `test_get_skip_reason_no_files_returns_skip` + `_with_files_returns_none` collapsed |
| C23 REFACTOR | Gate 0 Ruff Format | multi-line assert met `()` → 1 regel | `test_auto_scope_resolution.py` | `assert x, (\n    f"..."\n)` → `assert x, f"..."` |
| C23 REFACTOR | Gate 3 Line Length | E501 (101>100) | `test_auto_scope_resolution.py` | string literal in assert opgesplitst via impliciete concatenatie |
| C24 REFACTOR | Gate 0 Ruff Format | methode-signatuur 3→1 regel | `test_auto_scope_resolution.py` | `test_auto_scope_no_baseline_sha_falls_back_to_project_scope(self, tmp_path)` collapsed |
| C24 REFACTOR | Gate 0 Ruff Format + Gate 1 W292 | trailing newline verwijderd | `test_auto_scope_resolution.py` | `safe_edit_file` verwijderde te veel newlines; één `\n` teruggeplaatst |
| C25 REFACTOR | Gate 0 Ruff Format | kwargs op 1 regel met trailing comma → multi-line | `test_summary_line_formatter.py` | `_make_results(passed=0, failed=1, skipped=0, total_violations=2,` → 4 aparte regels |
| C26 REFACTOR | Gate 0 Ruff Format + Gate 3 E501 | frozenset set-literal op 1 regel (101>100) | `test_compact_payload_builder.py` | `frozenset({"a", "b", ... 8 items})` → multi-line met trailing comma |
| C27 REFACTOR | Gate 0 Ruff Format | blank line ontbreekt na module-docstring; 3-regel kwargs collapsed | `test_tool_result_contract.py` | Lege regel voor `from __future__` toegevoegd; kwargs naar 1 regel |
| C27 REFACTOR | Gate 3 E501 | docstring 102>100 in testmethode | `test_quality_tools.py` | Docstring ingekort naar ≤100 tekens |

---

---

### [Remediation C17/C18 REFACTOR] ARG002 — ongebruikte methodeparameter `gate`

**Gate:** Gate 1: Ruff Strict Lint (`ARG` ruleset)
**File:** `mcp_server/managers/qa_manager.py`
**Methode:** `_get_skip_reason`
**Fout:**
```
ARG002 — Unused method argument: `gate`
```
**Context:** Tijdens de C17/C18-conformantiefix (verwijderen van `_is_pytest_gate`) was de `gate: QualityGate` parameter uit de body overbodig geworden omdat de methode alleen nog `gate_files` inspecteerde. ARG002 vuurde in de REFACTOR QG-check.
**Fix:** `gate: QualityGate` volledig verwijderd uit methodesignatuur; alle call-sites bijgewerkt (prod code + 4 testbestanden: `test_qa_manager.py`, `test_skip_reason_unified.py`, `test_files_for_gate.py`, `test_scope_resolution.py`).
**Patroon:** Na het verwijderen van gedrag uit een methode controleer altijd of de resterende parameters nog daadwerkelijk gebruikt worden. ARG002 vangt dit automatisch op in de QG.

---

### [Remediation C14 REFACTOR] F841 — dode variabele `combined_output`

**Gate:** Gate 1: Ruff Strict Lint (`F` ruleset)
**File:** `mcp_server/managers/qa_manager.py`
**Methode:** `_execute_gate`
**Fout:**
```
F841 — Local variable `combined_output` is assigned to but never used
```
**Context:** `combined_output = (proc.stdout or "") + (proc.stderr or "")` was opgebouwd voor de `json_field`- en `text_regex`-dispatch-branches. Na het verwijderen van die branches (C14-conformantiefix) bleef de toewijzing achter als dode code.
**Fix:** De `combined_output`-regel volledig verwijderd.
**Patroon:** Na het verwijderen van dispatch-branches controleer altijd of variabelen die uitsluitend door die branches werden gelezen nu als F841 verschijnen.

---

### [Remediation C22 REFACTOR addendum] PLC0415 — `import` binnen testfunctie

**Gate:** Gate 2: Imports (`PLC0415`)
**File:** `tests/mcp_server/unit/mcp_server/managers/test_scope_resolution.py`
**Fout:**
```
PLC0415 — `import` should be at the top of the file
```
**Context:** De twee nieuwe C22-tests (`test_branch_scope_uses_parent_from_state_json` en `test_branch_scope_falls_back_to_main_without_state`) gebruikten `import json as _json` binnenin de testfunctie om een `state.json`-fixture te serialiseren. Gate 2 (select=`PLC0415`) vuurde hierop.
**Fix:** `import json as _json` verplaatst naar module-niveau als `import json`.
**Patroon:** Inline imports in testfuncties zijn verleidelijk voor tijdelijke fixtures, maar worden geweigerd door Gate 2. Altijd op module-niveau importeren, ook in tests.

---

### [Remediation batch REFACTOR] Ruff Format — 2 methode-signaturen in `test_qa_manager.py` gesplitst

**Gate:** Gate 0: Ruff Format
**File:** `tests/mcp_server/unit/mcp_server/managers/test_qa_manager.py`
**Fout:**
```diff
-    def test_get_skip_reason_no_files_returns_skip(
-        self, manager: QAManager
-    ) -> None:
+    def test_get_skip_reason_no_files_returns_skip(self, manager: QAManager) -> None:
-    def test_get_skip_reason_with_files_returns_none(
-        self, manager: QAManager
-    ) -> None:
+    def test_get_skip_reason_with_files_returns_none(self, manager: QAManager) -> None:
```
**Context:** Beide methoden in `TestSkipReasonLogic` waren tijdens de C17/C18-fix op 3 regels geschreven. De gecombineerde signatuur past comfortabel binnen 100 tekens (73 resp. 76 chars). Ruff Format weigert de gesplitste variant.
**Fix:** Beide signaturen samengevoegd op één regel.
**Patroon:** Zie ook C8/C9/C19 — bij `self` + één fixture-argument past de signatuur bijna altijd op één regel. Schrijf dit direct zo.

---

### [C23 REFACTOR] Ruff Format — multi-line assert met onnodige haakjes

**Gate:** Gate 0: Ruff Format
**File:** `tests/mcp_server/unit/mcp_server/managers/test_auto_scope_resolution.py`
**Fout:**
```diff
-        assert result.count("shared.py") == 1, (
-            f"Duplicate entry in result: {result!r}"
-        )
+        assert result.count("shared.py") == 1, f"Duplicate entry in result: {result!r}"
```
**Context:** Assert-boodschappen met impliciete haakjes over 3 regels worden door ruff-format gereduceerd naar 1 regel als de gecombineerde regel ≤ 100 tekens is.
**Fix:** Haakjes verwijderd; assert-boodschap op dezelfde regel als de assert.
**Patroon:** Dezelfde als bij methode-signaturen: schrijf korte assert-berichten direct op één regel. Haakjes zijn alleen gerechtvaardigd als de gecombineerde regel > 100 tekens is.

---

### [C23 REFACTOR] Gate 3 E501 — assert-boodschap te lang via impliciete string-concatenatie

**Gate:** Gate 3: Line Length (E501)
**File:** `tests/mcp_server/unit/mcp_server/managers/test_auto_scope_resolution.py`
**Fout:** Regel 140: 101 tekens (> 100)
```python
# Te lang (101 chars):
        assert "main..HEAD" not in captured[0], (
            "scope=auto must NOT use workflow.parent_branch — it must use quality_gates.baseline_sha"
        )
```
**Fix:** String literal opgesplitst via impliciete Python-concatenatie:
```python
        assert "main..HEAD" not in captured[0], (
            "scope=auto must NOT use workflow.parent_branch"
            " — it must use quality_gates.baseline_sha"
        )
```
**Patroon:** Lange string-literals in assert-berichten splitsen met impliciete concatenatie (twee string-literals naast elkaar in `()`). Geen backslash-continuation nodig.

---

### [C24 REFACTOR] Ruff Format — methode-signatuur 3→1 regel en W292 trailing newline

**Gate:** Gate 0: Ruff Format + Gate 1: W292
**File:** `tests/mcp_server/unit/mcp_server/managers/test_auto_scope_resolution.py`
**Fout 1 — signatuur:**
```diff
-    def test_auto_scope_no_baseline_sha_falls_back_to_project_scope(
-        self, tmp_path: Path
-    ) -> None:
+    def test_auto_scope_no_baseline_sha_falls_back_to_project_scope(self, tmp_path: Path) -> None:
```
**Fout 2 — W292:** Na het handmatig verwijderen van een dubbele trailing newline verdween ook de verplichte afsluitende newline (`\\ No newline at end of file`). Ruff W292 vuurde hierop.
**Fix 1:** Signatuur samengevoegd (95 tekens — past comfortabel op één regel).
**Fix 2:** Één `\n` teruggeplaatst aan het einde van het bestand.
**Patroon:** Bij `safe_edit_file` met search/replace op de laatste regel van een bestand: controleer altijd of de verplichte trailing newline behouden blijft. De tool schrijft exact wat er in `replace` staat.

---

### [C25 REFACTOR] Ruff Format — kwargs op één regel met trailing comma

**Gate:** Gate 0: Ruff Format
**File:** `tests/mcp_server/unit/mcp_server/managers/test_summary_line_formatter.py`
**Fout:**
```diff
-        results = _make_results(
-            passed=0, failed=1, skipped=0, total_violations=2,
+        results = _make_results(
+            passed=0,
+            failed=1,
+            skipped=0,
+            total_violations=2,
             failed_gate_names=["Gate 1: Ruff Strict Lint"],
         )
```
**Context:** Een reeks kwargs op één regel met een trailing comma in een multi-line aanroep triggert ruff-format om elke kwarg op een eigen regel te zetten. Zelfde mechanisme als C13 voor dict/list-literals.
**Fix:** Elke kwarg op een aparte regel gezet.
**Patroon:** Bij een function call die al over meerdere regels loopt met een trailing comma: schrijf elke kwarg direct op een eigen regel. Eén regel met meerdere kwargs wordt altijd uitgevouwen door ruff.

---

### [C26 REFACTOR] Ruff Format + E501 — frozenset set-literal op één regel (101 chars)

**Gate:** Gate 0: Ruff Format + Gate 3: Line Length (E501)
**File:** `tests/mcp_server/unit/mcp_server/managers/test_compact_payload_builder.py`
**Fout:**
```diff
-    _FORBIDDEN: frozenset[str] = frozenset(
-        {"stdout", "stderr", "raw_output", "command", "duration_ms", "hints", "skip_reason", "score"}
+    _FORBIDDEN: frozenset[str] = frozenset(
+        {
+            "stdout",
+            "stderr",
+            "raw_output",
+            "command",
+            "duration_ms",
+            "hints",
+            "skip_reason",
+            "score",
+        }
     )
```
**Context:** De set-literal met 8 string-elementen op één regel was 101 tekens (> 100). Gate 3 vuurde op E501; Gate 0 vuurde omdat ruff dezelfde set-literal ook multi-line wilde schrijven (trailing-comma patroon).
**Fix:** Elk set-element op een eigen regel gezet met trailing comma.
**Patroon:** Set-literals, dict-literals en lijst-literals met meer dan ~4 korte elementen: schrijf direct multi-line als de gecombineerde regel > 100 chars is. Trailing-comma is verplicht voor consistentie.

---

### [C27 REFACTOR] Ruff Format — blank line na module-docstring + kwargs collapse + E501 docstring

**Gate:** Gate 0: Ruff Format + Gate 3: Line Length (E501)
**Files:**
- `tests/mcp_server/unit/tools/test_tool_result_contract.py` (Gate 0, twee fixes)
- `tests/mcp_server/unit/tools/test_quality_tools.py` (Gate 3)

**Fout 1 — missing blank line after module docstring:**
```diff
-"""
-from __future__ import annotations
+"""
+
+from __future__ import annotations
```
Ruff wil altijd een lege regel tussen de module-docstring en de eerste import.

**Fout 2 — 3-regel kwargs collapsed (Gate 0):**
```diff
-        mock_manager.run_quality_gates.return_value = _make_qg_result(
-            passed=1, failed=0, skipped=0
-        )
+        mock_manager.run_quality_gates.return_value = _make_qg_result(passed=1, failed=0, skipped=0)
```
Drie kwargs zonder trailing comma en < 100 tekens → ruff collapsed naar één regel.

**Fout 3 — E501 docstring 102>100 chars:**
Docstring `"""Test tool returns compact native JSON (content[1]=json), text summary (content[0]=text)."""` was 102 chars. Ingekort naar kortere omschrijving.

**Patronen:**
- Module-docstrings altijd gevolgd door een lege regel voor de eerste import.
- Kwargs zonder trailing comma op meerdere regels: ruff collapsed als ze op 1 regel passen (< 100 chars).
- Testmethode-docstrings: controleer op lengte; gebruik kortere omschrijving als de volledige tekst > 100 chars is.

---

## Open vragen / aanbevelingen

1. **ANN401 policy:** Wanneer is `-> Any` acceptabel en wanneer moeten we een nauwkeuriger type kiezen? Documenteer richtlijn in TYPE_CHECKING_PLAYBOOK.
2. **Ruff format gewenning:** Bij schrijven van nieuwe testmethoden bewust kiezen voor korte signaturen op één regel als ze ≤ 100 tekens zijn.
3. **Mogelijk: ruff config aanpassen** om `ANN401` globaal te ignoren voor `managers/` of alleen toe te staan met `noqa` — afhankelijk van hoe often dit nog optreedt.
