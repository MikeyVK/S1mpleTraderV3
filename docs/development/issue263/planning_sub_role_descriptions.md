<!-- docs\development\issue263\planning_sub_role_descriptions.md -->
<!-- template=planning version=130ac5ea created=2026-03-25T07:51Z updated= -->
# Sub-Role Description Injection — Planning

**Status:** DRAFT  
**Version:** 1.1  
**Last Updated:** 2026-03-25

---

## Scope

**In Scope:**
SubRoleSpec TypedDict (interfaces.py), _SubRoleSchema + SubRoleRequirementsLoader (requirements_loader.py), build_ups_output() (detect_sub_role.py), build_compaction_output() (notify_compaction.py), _default_requirements.yaml, .copilot/sub-role-requirements.yaml, prepare-qa-brief.prompt.md, 4 test fixture files

**Out of Scope:**
session_start hooks, stop_handover_guard.py (zero changes), MCP server, new sub-roles beyond existing 11, toolRules

## Prerequisites

Read these first:
1. design_sub_role_descriptions.md v1.1 (QA PASS)
2. C_CROSSCHAT.1-5 complete
3. 10 SubRoleSpec fixture-locaties geidentificeerd (4 test files)
4. requires_crosschat_block() extern geconsumeerd door stop_handover_guard.py:60
---

## Summary

Voeg description: str (required) toe aan SubRoleSpec en _SubRoleSchema. Refactor build_ups_output() voor 4-case return contract. Refactor build_compaction_output() to hoist get_requirement(). Populate beide YAML-bestanden met descriptions voor alle 11 sub-rollen. Fix prepare-qa-brief.prompt.md broken guide_line reference. Geen backward compatibility — package nog nooit gereleased.

---

## Dependencies

- C_DESC.2 na C_DESC.1: spec["description"].strip() vereist SubRoleSpec update en beschikbare YAML
- C_DESC.3 na C_DESC.1: zelfde reden
- C_DESC.4 na C_DESC.2+C_DESC.3: integration tests verifieren gecombineerd gedrag van beide functies

---

## TDD Cycles

| Cycle | Naam | Afhankelijkheden |
|-------|------|-----------------|
| C_DESC.1 | SubRoleSpec + _SubRoleSchema + get_requirement() + beide YAMLs + 10 fixture updates | — |
| C_DESC.2 | build_ups_output() 4-case return contract | C_DESC.1 |
| C_DESC.3 | build_compaction_output() structurele refactor | C_DESC.1 |
| C_DESC.4 | Integration tests + prepare-qa-brief.prompt.md fix | C_DESC.2, C_DESC.3 |

---

### Cycle 1: C_DESC.1 — SubRoleSpec + _SubRoleSchema + get_requirement() + YAML + fixture updates

**Goal:** `description: str` veld toevoegen aan de volledige datalagen: TypedDict, Pydantic-schema, loader-output, beide YAML-bestanden. Alle 10 fixture-constructies in test-code bijwerken zodat ze de nieuwe required key leveren.

**RED:**
- Test in `tests/.../unit/contracts/test_interfaces.py`: SubRoleSpec met `description` key is valid TypedDict; SubRoleSpec zonder `description` faalt Pyright-check (statische test).
- Test in `tests/.../unit/config/test_requirements_loader.py`: `get_requirement(sub_role)` retourneert dict met key `"description"`.
- Test in `tests/.../unit/config/test_requirements_loader.py`: `_SubRoleSchema.model_validate({...})` zonder `description` veld → `ValidationError` (bewijst dat geen Pydantic default aanwezig is).

**GREEN:**
1. `interfaces.py`: `description: str` toevoegen aan `SubRoleSpec` TypedDict.
2. `requirements_loader.py`: `description: str` toevoegen aan `_SubRoleSchema` (geen default → YAML verplicht).
3. `requirements_loader.py`: `get_requirement()` emitteert altijd `description=spec.description`.
4. `_default_requirements.yaml` + `.copilot/sub-role-requirements.yaml`: beide atomisch bijwerken met `description:` voor alle 11 sub-rollen (teksten uit design §4.2).
5. 10 `SubRoleSpec(...)` constructies in 4 test-bestanden voorzien van `description="..."`:
   - `tests/.../unit/contracts/test_interfaces.py` (L43, L63)
   - `tests/.../unit/hooks/test_notify_compaction.py` (L32: `_SPEC_STUB`)
   - `tests/.../unit/hooks/test_detect_sub_role.py` (L64, L196, L266, L277, L329, L342)
   - `tests/.../unit/hooks/test_stop_handover_guard.py` (L39: `_SPEC_STUB`)

**REFACTOR:**
- Enkelvoudig fixture helper per test-bestand overwegen indien >4 constructions.
- Quality gates (scope="files") over gewijzigde bestanden.

**Success Criteria:**
- Alle bestaande unit tests groen.
- `get_requirement()` retourneert `description` key voor alle 11 sub-rollen.
- Pydantic valideert YAML bij import zonder errors.

---

### Cycle 2: C_DESC.2 — build_ups_output() 4-case return contract

**Goal:** `build_ups_output()` in `detect_sub_role.py` implementeert het exacte 4-case return contract: lege description + geen crosschat → `{}`; lege description + crosschat → crosschat-block only; description + geen crosschat → description only; description + crosschat → description + crosschat-block (newline-separated).

**RED:**
- Tests in `tests/.../unit/hooks/test_detect_sub_role.py`: één test per case van het 4-case contract.
- Accessor `spec["description"].strip()` (NIET `.get()`).

**GREEN:**
- `detect_sub_role.py`: `build_ups_output()` herschreven met 4-case logica.
- Bestaande tests groen houden (geen regressie).

**REFACTOR:**
- Early-return structuur voor leesbaarheid.
- Quality gates (scope="files") op `detect_sub_role.py`.

**Success Criteria:**
- 4 nieuwe tests groen.
- Accessor gebruikt `spec["description"]` (KeyError op ontbrekende key — geen silent default).
- Alle eerder-groene tests blijven groen.

---

### Cycle 3: C_DESC.3 — build_compaction_output() structurele refactor

**Goal:** `build_compaction_output()` in `notify_compaction.py` host `get_requirement()` **voor** de crosschat-conditional, zodat description beschikbaar is voor alle 11 sub-rollen — niet alleen de 4 met `crosschat=True`.

**RED:**

Alle 4 gedragsgevallen uit design §5 C_DESC.3 Focus moeten falen vóór de implementatie:

1. `crosschat=False` + `description` non-empty → description aanwezig in compaction-output
2. `crosschat=True` + `description` non-empty → description én crosschat-block aanwezig (in die volgorde)
3. `crosschat=False` + `description=""` → geen extra tekst; uitsluitend base message
4. `crosschat=True` + `description=""` → base message + crosschat-block (huidig gedrag onveranderd)

Tests locatie: `tests/.../unit/hooks/test_notify_compaction.py` — één test per geval.
Huidige implementatie: `get_requirement()` enkel op crosschat-pad → tests 1 en 3 falen.

**GREEN:**
- `notify_compaction.py`: hoist `spec = get_requirement(sub_role)` naar vóór conditional.
- Gebruik `spec["description"].strip()` in output-constructie.

**REFACTOR:**
- Verwijder dode conditionals indien van toepassing.
- Quality gates (scope="files") op `notify_compaction.py`.

**Success Criteria:**
- Alle 4 gedragstests groen (cases 1–4 zoals beschreven in RED).
- `get_requirement()` wordt altijd aangeroepen (geen dead code meer).
- Alle overige tests groen.

---

### Cycle 4: C_DESC.4 — Integration tests + prepare-qa-brief.prompt.md fix

**Goal:** End-to-end integratie valideren: detectie → description injection via UPS en compaction. Broken `guide_line` reference in `prepare-qa-brief.prompt.md` verwijderen (Phase 1 fix).

**RED (integration):**
- Tests in `tests/.../integration/hooks/`: end-to-end doorloop voor sub-rollen met/zonder description, met/zonder crosschat.
- Test verifiëert gecombineerd gedrag van C_DESC.2 + C_DESC.3.

**GREEN:**
- `prepare-qa-brief.prompt.md`: verwijder/vervang `guide_line` reference (veld bestaat niet) door directe tekst of verwijzing naar bestaand veld.
- Integratie-tests groen maken.

**REFACTOR:**
- `run_quality_gates(scope="branch")` voor totaaloverzicht.
- Planning en design doc eventueel bijwerken als bevindingen afwijken.

**Success Criteria:**
- Volledige test-suite groen (inclusief alle vorige cycles).
- `guide_line` reference volledig verwijderd uit `.github/prompts/prepare-qa-brief.prompt.md`.
- Quality gates pass.


---

## Risks & Mitigation

- **Risk:** 10 fixture-constructies vergeten bij te werken in C_DESC.1 GREEN → Pyright-compile-error of runtime KeyError op description-access in latere cycles.
  - **Mitigation:** Zoek op `SubRoleSpec(` in de 4 test-bestanden vóór commit; bevestig dat alle 10 locaties zijn bijgewerkt.
- **Risk:** YAML niet atomisch bijwerken in C_DESC.1 → Pydantic ValidationError op import van `_SubRoleSchema` (description verplicht, geen default).
  - **Mitigation:** Beide YAML-bestanden (`_default_requirements.yaml` en `.copilot/sub-role-requirements.yaml`) in dezelfde safe_edit_file-sessie bijwerken; valideren met `run_tests` vóór commit.

---

## Milestones

- C_DESC.1 GROEN: alle bestaande tests groen + description beschikbaar via loader
- C_DESC.2 GROEN: 4-case return contract van build_ups_output() volledig getest
- C_DESC.3 GROEN: alle sub-rollen krijgen description na compactie (4 cases gedekt)
- C_DESC.4 GROEN: alle tests groen, quality gates pass, broken reference verwijderd

## Related Documentation
- **[design_sub_role_descriptions.md][related-1]**
- **[research_sub_role_descriptions.md][related-2]**
- **[planning.md][related-3]**

<!-- Link definitions -->

[related-1]: design_sub_role_descriptions.md
[related-2]: research_sub_role_descriptions.md
[related-3]: planning.md

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-03-25 | Agent | Initial draft |
| 1.1 | 2026-03-25 | Agent | F1-F2 QA corrections: C_DESC.3 RED 4 tests, C_DESC.1 ValidationError test |