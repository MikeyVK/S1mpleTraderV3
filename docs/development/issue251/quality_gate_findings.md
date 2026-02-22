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

## Overzicht per cycle

| Cycle | Gate | Regel | Bestand | Actie |
|-------|------|-------|---------|-------|
| C8 REFACTOR | Gate 1 Ruff Strict Lint | ANN401 | `qa_manager.py` | `# noqa: ANN401` |
| C8 REFACTOR | Gate 0 Ruff Format | signatuur samenvoegen | `test_parse_json_violations_nested.py` | signatuur op één regel |
| C9 REFACTOR | Gate 0 Ruff Format | constructor call samenvoegen | `test_extract_violations_array.py` | `JsonViolationsParsing(...)` op één regel; signatuur collapsed |

---

## Open vragen / aanbevelingen

1. **ANN401 policy:** Wanneer is `-> Any` acceptabel en wanneer moeten we een nauwkeuriger type kiezen? Documenteer richtlijn in TYPE_CHECKING_PLAYBOOK.
2. **Ruff format gewenning:** Bij schrijven van nieuwe testmethoden bewust kiezen voor korte signaturen op één regel als ze ≤ 100 tekens zijn.
3. **Mogelijk: ruff config aanpassen** om `ANN401` globaal te ignoren voor `managers/` of alleen toe te staan met `noqa` — afhankelijk van hoe often dit nog optreedt.
