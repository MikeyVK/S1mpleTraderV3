<!-- docs\development\issue263\planning.md -->
<!-- template=planning version=130ac5ea created=2026-03-24T17:12Z updated=2026-03-24 -->
# YAML-First Handover Block Refactor — Planning

**Status:** ACTIVE  
**Version:** 1.2  
**Last Updated:** 2026-03-24

---

## Purpose

Geef developers volledige controle over het handover-blok via YAML, zonder Python-logica te wijzigen.

## Scope

**In Scope:**
`SubRoleSpec` TypedDict (`interfaces.py`), `_SubRoleSchema` + `SubRoleRequirementsLoader` (`requirements_loader.py`), `build_crosschat_block_instruction` (`detect_sub_role.py`), `_default_requirements.yaml`, `.copilot/sub-role-requirements.yaml`, 5 test-bestanden.

**Out of Scope:**
MCP-server tools, `notify_compaction.py` en `stop_handover_guard.py` (interface ongewijzigd — geen code-change nodig).

## Prerequisites

1. Research v3.1 afgerond en gecommit (`a0536be`) — alle design-beslissingen vastgelegd
2. `build_crosschat_block_instruction` gelokaliseerd in `detect_sub_role.py` lijnen 101–114
3. Alle 4 dode velden verified als dead/feedthrough (`block_prefix`, `guide_line`, `block_prefix_hint`, `marker_verb`)

---

## Summary

Flag-day refactor van `build_crosschat_block_instruction`: verwijder 4 legacy-velden en introduceer
`block_template` als verbatim `str.format`-template met twee placeholders (`{sub_role}`, `{markers_list}`).
Alle content binnen de fence; hard-fail bij onbekende placeholder. Pydantic `@model_validator` valideert
bij laden. Geen backward compatibility — package nog nooit gereleased.

---

## Break-state Overzicht

> **Leidraad:** De refactor verloopt in volgorde C_CROSSCHAT.1 → 2 → 3 → 4 → 5.
> Tijdelijk rode testbestanden zijn **verwacht en geen blokkering** voor de desbetreffende cycle,
> tenzij hieronder anders vermeld. Een rood testbestand buiten de verwachte set is **altijd een blokkering**.

| Na cycle | ✅ Verwacht GROEN | 🔴 Verwacht tijdelijk ROOD |
|----------|-------------------|---------------------------|
| **C_CROSSCHAT.1** | `test_interfaces.py` | `test_notify_compaction.py` (r35–36), `test_detect_sub_role.py` (r261–262, r306–320), `test_optional_field_chain.py` (r33–70) |
| **C_CROSSCHAT.2** | `test_interfaces.py`, `test_requirements_loader.py` | `test_notify_compaction.py` (r35–36), `test_detect_sub_role.py` (r261–262, r306–320), `test_optional_field_chain.py` (r33–70) |
| **C_CROSSCHAT.3** | `test_interfaces.py`, `test_requirements_loader.py`, `test_detect_sub_role.py` | `test_notify_compaction.py` (r35–36), `test_optional_field_chain.py` (r33–70) |
| **C_CROSSCHAT.4** | `test_interfaces.py`, `test_requirements_loader.py`, `test_detect_sub_role.py` | `test_notify_compaction.py` (r35–36), `test_optional_field_chain.py` (r33–70) |
| **C_CROSSCHAT.5** | **Alle testbestanden** | — |

---

## Dependencies

- **C_CROSSCHAT.2** afhankelijk van **C_CROSSCHAT.1** — `SubRoleSpec` moet correct zijn vóór loader-aanpassing
- **C_CROSSCHAT.3** afhankelijk van **C_CROSSCHAT.1** — `build_crosschat_block_instruction` gebruikt `spec['block_template']`
- **C_CROSSCHAT.4** afhankelijk van **C_CROSSCHAT.2** — YAML-validatie via `_SubRoleSchema`
- **C_CROSSCHAT.5** afhankelijk van **C_CROSSCHAT.1–4** — alle wijzigingen moeten klaar zijn vóór sweep

---

## TDD Cycles

> **Context:** Dit zijn cycles 13–17 van issue #263 (voortbouwend op cycles 1–12 van de VS Code orchestration refactor).

---

### C_CROSSCHAT.1 — Contracts: `SubRoleSpec` TypedDict update (Cycle 13)

**Goal:** Verwijder 4 legacy-velden uit `SubRoleSpec` TypedDict en voeg `block_template: str` toe. Dit is de contractwijziging die alle andere cycles mogelijk maakt.

**Tests:**
- `test_interfaces.py`: `block_template` aanwezig in `SubRoleSpec`
- `test_interfaces.py`: `block_prefix`, `guide_line`, `block_prefix_hint`, `marker_verb` afwezig

**Files:**
- `src/copilot_orchestration/contracts/interfaces.py`
- `tests/copilot_orchestration/unit/contracts/test_interfaces.py`

**Test State After This Cycle:**
- ✅ `test_interfaces.py` — GROEN
- 🔴 `test_notify_compaction.py` (r35–36) — VERWACHT ROOD; `block_prefix`/`guide_line` in fixture nog aanwezig
- 🔴 `test_detect_sub_role.py` (r261–262, r306–320) — VERWACHT ROOD; legacy fixture-velden nog aanwezig
- 🔴 `test_optional_field_chain.py` (r33–70) — VERWACHT ROOD; chain-test vereist nog legacy-velden

**Success Criteria:**
`block_template: str` aanwezig; alle 4 legacy-velden afwezig; `test_interfaces.py` groen; geen andere productie-bestanden aangeraakt.

**Stop-Go Gate:**
Doorgang naar **C_CROSSCHAT.2** is geblokkeerd totdat:
1. `interfaces.py` bevat `block_template: str` (grep-verifieerbaar)
2. `block_prefix`, `guide_line`, `block_prefix_hint`, `marker_verb` afwezig in `interfaces.py` (grep-verifieerbaar)
3. `test_interfaces.py` volledig GROEN
4. Rode bestanden (`test_notify_compaction.py`, `test_detect_sub_role.py`, `test_optional_field_chain.py`) zijn uitsluitend rood op de hierboven vermelde regels — geen onverwachte failures elders

---

### C_CROSSCHAT.2 — Schema & Loader: `@model_validator` + WARNING-log (Cycle 14)

**Goal:** Uitbreiden van `_SubRoleSchema` met `@model_validator(mode="after")` die `ValueError → ValidationError` gooit wanneer `requires_crosschat_block=True` en `block_template` leeg is. Verwijder verwijzingen naar legacy-velden uit de schema-klasse. Voeg tevens een best-effort WARNING-log toe in `SubRoleRequirementsLoader`: wanneer een sub-rol met `requires_crosschat_block=True` een `block_template` heeft waarvan het eerste woord na de openende fence geen herkenbare sub-rol-naam is, logt de loader een `WARNING` (geen harde blokkering — zie research v3.1 G2 constraint 5).

**Tests:**
- `test_requirements_loader.py`: `@model_validator` aanwezig in `_SubRoleSchema`
- `test_requirements_loader.py`: `ValidationError` bij `requires_crosschat_block=True` + leeg `block_template`
- `test_requirements_loader.py`: `block_prefix_hint` afwezig in `_SubRoleSchema`
- `test_requirements_loader.py`: WARNING-log gegenereerd wanneer eerste woord na openende fence geen geldige sub-rol-naam is (gebruik `caplog` fixture; asserteer op loglevel `WARNING`)
- `test_requirements_loader.py`: geen WARNING wanneer eerste woord wél een geldige sub-rol-naam is

**Files:**
- `src/copilot_orchestration/config/requirements_loader.py`
- `tests/copilot_orchestration/unit/config/test_requirements_loader.py`

**Test State After This Cycle:**
- ✅ `test_interfaces.py` — GROEN
- ✅ `test_requirements_loader.py` — GROEN (incl. WARNING-log tests)
- 🔴 `test_notify_compaction.py` (r35–36) — VERWACHT ROOD; nog niet aangepast
- 🔴 `test_detect_sub_role.py` (r261–262, r306–320) — VERWACHT ROOD; nog niet aangepast
- 🔴 `test_optional_field_chain.py` (r33–70) — VERWACHT ROOD; nog niet aangepast

**Success Criteria:**
`@model_validator` en `_validate_template_required` aanwezig; `ValidationError` correct gegooid; WARNING-log tests GROEN; `block_prefix_hint` afwezig; `test_requirements_loader.py` volledig GROEN.

**Stop-Go Gate:**
Doorgang naar **C_CROSSCHAT.3** is geblokkeerd totdat:
1. `_validate_template_required` aanwezig in `requirements_loader.py` (grep-verifieerbaar)
2. `block_prefix_hint` afwezig in `requirements_loader.py` (grep-verifieerbaar)
3. `test_requirements_loader.py` volledig GROEN — inclusief WARNING-log tests
4. Rode bestanden beperkt tot de hierboven vermelde bestanden/regels

---

### C_CROSSCHAT.3 — Core function: `build_crosschat_block_instruction` rewrite (Cycle 15)

**Goal:** Herschrijf `build_crosschat_block_instruction` zodat de functie `spec['block_template']` ophaalt en `str.format` aanroept met `{sub_role}` en `{markers_list}`. `markers_list` = `"\n\n".join(f"## {m}" for m in spec["markers"])`. Bij `KeyError` → `ConfigError` (hard falen). Verwijder gelijktijdig alle vijf legacy-testmethoden en bijbehorende fixture-velden.

**Legacy testmethoden — expliciete bestemming:**

De volgende vijf methoden en bijbehorende fixtures in `test_detect_sub_role.py` testen gedrag dat na deze cycle niet meer bestaat. Ze worden **verwijderd** (niet herschreven):

| Methode / fixture | Reden verwijdering |
|-------------------|--------------------|
| `test_contains_block_prefix` | Test dat `block_prefix` in output zit — veld bestaat niet meer |
| `test_contains_guide_line` | Test dat `guide_line` in output zit — veld bestaat niet meer |
| `test_block_prefix_stripped` | Test `.strip()` op `block_prefix` — veld bestaat niet meer |
| `test_guide_line_stripped` | Test `.strip()` op `guide_line` — veld bestaat niet meer |
| Fixtures met `block_prefix`/`guide_line` sleutels | Legacy fixture-velden verwijderen; `block_template` toevoegen |

Nieuwe tests dekken de vervanger: correcte `str.format`-output, `## Header`-generatie, `ConfigError` bij onbekende placeholder, CRLF-strip.

**Tests:**
- `test_detect_sub_role.py`: correcte output met ingevulde `{sub_role}` en `{markers_list}` als `## Header` regels
- `test_detect_sub_role.py`: onbekende placeholder `{xyz}` → `ConfigError`
- `test_detect_sub_role.py`: Windows `\r\n` in template → gestript vóór `.format()`
- `test_detect_sub_role.py`: `block_prefix` niet meer in output
- De vijf legacy-methoden en bijbehorende fixtures: **verwijderd**

**Files:**
- `src/copilot_orchestration/hooks/detect_sub_role.py`
- `tests/copilot_orchestration/unit/hooks/test_detect_sub_role.py`

**Test State After This Cycle:**
- ✅ `test_interfaces.py` — GROEN
- ✅ `test_requirements_loader.py` — GROEN
- ✅ `test_detect_sub_role.py` — GROEN (legacy methoden verwijderd; nieuwe tests dekken nieuwe functie)
- 🔴 `test_notify_compaction.py` (r35–36) — VERWACHT ROOD; nog niet aangepast
- 🔴 `test_optional_field_chain.py` (r33–70) — VERWACHT ROOD; nog niet aangepast

**Success Criteria:**
`markers_list` als `## Header` regels aanwezig; `ConfigError` bij `KeyError`; `block_prefix` afwezig in `detect_sub_role.py`; CRLF-mitigatie aanwezig; vijf legacy-methoden en bijbehorende fixtures verwijderd; `test_detect_sub_role.py` volledig GROEN.

**Stop-Go Gate:**
Doorgang naar **C_CROSSCHAT.4** is geblokkeerd totdat:
1. `markers_list` en `block_template` aanwezig in `detect_sub_role.py` (grep-verifieerbaar)
2. `block_prefix` afwezig in `detect_sub_role.py` (grep-verifieerbaar)
3. `test_contains_block_prefix`, `test_contains_guide_line`, `test_block_prefix_stripped`, `test_guide_line_stripped` afwezig in `test_detect_sub_role.py` (grep-verifieerbaar)
4. `test_detect_sub_role.py` volledig GROEN
5. Rode bestanden beperkt tot `test_notify_compaction.py` (r35–36) en `test_optional_field_chain.py` (r33–70)

---

### C_CROSSCHAT.4 — YAML files: default + project override bijwerken (Cycle 16)

**Goal:** Verwijder `block_prefix`, `guide_line`, `block_prefix_hint`, `marker_verb` uit alle sub-rollen in `_default_requirements.yaml` en `.copilot/sub-role-requirements.yaml`. Voeg ingevulde `block_template` toe aan sub-rollen met `requires_crosschat_block: true` (gebruik `|-` literal block scalar; alles binnen de fence).

**Tests:**
- `test_requirements_loader.py` (integration): loader laadt correct met `block_template`
- `test_requirements_loader.py`: `ValidationError` bij `requires_crosschat_block=True` + leeg `block_template` in YAML
- Smoke: rendered instructie bevat `## Scope` etc. als H2-headers binnen fence

**Files:**
- `src/copilot_orchestration/config/_default_requirements.yaml`
- `.copilot/sub-role-requirements.yaml`
- `tests/copilot_orchestration/unit/config/test_requirements_loader.py`

**Test State After This Cycle:**
- ✅ `test_interfaces.py` — GROEN
- ✅ `test_requirements_loader.py` — GROEN
- ✅ `test_detect_sub_role.py` — GROEN
- 🔴 `test_notify_compaction.py` (r35–36) — VERWACHT ROOD; legacy-assertions worden pas in C_CROSSCHAT.5 verwijderd
- 🔴 `test_optional_field_chain.py` (r33–70) — VERWACHT ROOD; legacy-assertions worden pas in C_CROSSCHAT.5 verwijderd

**Success Criteria:**
`block_template` aanwezig en `block_prefix` afwezig in beide YAML-bestanden; loader laadt correct; rendered output is copy-paste klaar als één blok.

**Stop-Go Gate:**
Doorgang naar **C_CROSSCHAT.5** is geblokkeerd totdat:
1. `block_template` aanwezig in `_default_requirements.yaml` (grep-verifieerbaar)
2. `block_prefix` afwezig in `_default_requirements.yaml` (grep-verifieerbaar)
3. `block_template` aanwezig in `.copilot/sub-role-requirements.yaml` (grep-verifieerbaar)
4. `block_prefix` afwezig in `.copilot/sub-role-requirements.yaml` (grep-verifieerbaar)
5. `test_requirements_loader.py` volledig GROEN
6. Rode bestanden beperkt tot `test_notify_compaction.py` (r35–36) en `test_optional_field_chain.py` (r33–70)

---

### C_CROSSCHAT.5 — Integration & sweep (Cycle 17)

**Goal:** Verwijder alle resterende legacy-assertions (`block_prefix`, `guide_line`) in `test_notify_compaction.py` en `test_optional_field_chain.py`. Draai volledige testsuite. Voer `validate_architecture(scope="all")` uit.

**Tests:**
- `test_notify_compaction.py`: geen `block_prefix` of `guide_line` assertions meer
- `test_optional_field_chain.py`: geen `guide_line` assertions meer
- Volledige suite: alle tests groen

**Files:**
- `tests/copilot_orchestration/unit/hooks/test_notify_compaction.py`
- `tests/copilot_orchestration/integration/test_optional_field_chain.py`

**Test State After This Cycle:**
- ✅ Alle testbestanden — GROEN; er zijn geen verwacht-rode bestanden meer

**Success Criteria:**
Geen legacy-assertions; volledige testsuite groen; `validate_architecture(scope="all")` clean; klaar voor PR.

**Stop-Go Gate (PR-klaar):**
Doorgang naar **PR aanmaken** is geblokkeerd totdat:
1. `block_prefix` afwezig in `test_notify_compaction.py` (grep-verifieerbaar)
2. `guide_line` afwezig in `test_optional_field_chain.py` (grep-verifieerbaar)
3. Volledige testsuite GROEN — nul failures, nul errors
4. `validate_architecture(scope="all")` geeft nul fouten

---

## Risks & Mitigation

- **Risk:** `test_notify_compaction.py` asserteert op `block_prefix` of `guide_line` in output
  - **Mitigation:** Expliciet opgenomen in C_CROSSCHAT.5; assertions vervangen door `block_template`-gebaseerde checks
- **Risk:** YAML `|` (trailing newline) i.p.v. `|-` veroorzaakt regex-failures in tests
  - **Mitigation:** Conventie: altijd `|-` in `block_template`; in C_CROSSCHAT.4 expliciet toegepast
- **Risk:** Windows `\r\n` in verbatim block-template
  - **Mitigation:** `.replace("\r\n", "\n")` vóór `.format()` in C_CROSSCHAT.3 geïmplementeerd
- **Risk:** WARNING-log in C_CROSSCHAT.2 detecteert sub-rol-namen niet juist (valid_sub_roles set niet beschikbaar op schema-niveau)
  - **Mitigation:** Best-effort check — loader gebruikt de reeds geladen set van sub-rol-namen; als die set leeg is, wordt de WARNING overgeslagen (geen harde blokkering)

---

## Milestones

- **C_CROSSCHAT.1 groen:** `SubRoleSpec` clean zonder legacy-velden
- **C_CROSSCHAT.2 groen:** Loader valideert bij opstart + WARNING-log geïmplementeerd
- **C_CROSSCHAT.3 groen:** `build_crosschat_block_instruction` produceert fence-correcte output; legacy testmethoden verwijderd
- **C_CROSSCHAT.4 groen:** YAML-bestanden volledig bijgewerkt, loader valideert correct
- **C_CROSSCHAT.5 groen:** Volledige testsuite groen, architecture validate clean — klaar voor PR

## Related Documentation

- [docs/development/issue263/research_yaml_first_handover_block.md](../../docs/development/issue263/research_yaml_first_handover_block.md)

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-03-24 | Agent | Initial scaffold (leeg template) |
| 1.1 | 2026-03-24 | Agent | Concrete cycle-invulling C_CROSSCHAT.1–5 (cycles 13–17 van issue #263) |
| 1.2 | 2026-03-24 | Agent | QA F1: break-state tabel + per-cycle test state; F2: Stop-Go Gate per cycle; F3: WARNING-log aan C_CROSSCHAT.2 toegewezen; F4: vijf legacy testmethoden expliciet benoemd in C_CROSSCHAT.3 |
