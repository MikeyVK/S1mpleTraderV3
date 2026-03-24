<!-- docs\development\issue263\planning.md -->
<!-- template=planning version=130ac5ea created=2026-03-24T17:12Z updated=2026-03-24 -->
# YAML-First Handover Block Refactor — Planning

**Status:** ACTIVE  
**Version:** 1.1  
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

**Success Criteria:**
`block_template: str` aanwezig; alle 4 legacy-velden afwezig; `test_interfaces.py` groen; geen andere bestanden aangeraakt.

---

### C_CROSSCHAT.2 — Schema & Loader: `@model_validator` in `_SubRoleSchema` (Cycle 14)

**Goal:** Uitbreiden van `_SubRoleSchema` met `@model_validator(mode="after")` die `ValueError → ValidationError` gooit wanneer `requires_crosschat_block=True` en `block_template` leeg is. Verwijder ook verwijzingen naar legacy-velden uit de schema-klasse.

**Tests:**
- `test_requirements_loader.py`: `@model_validator` aanwezig
- `test_requirements_loader.py`: `ValidationError` bij `requires_crosschat_block=True` + leeg `block_template`
- `test_requirements_loader.py`: `block_prefix_hint` afwezig in `_SubRoleSchema`

**Files:**
- `src/copilot_orchestration/config/requirements_loader.py`
- `tests/copilot_orchestration/unit/config/test_requirements_loader.py`

**Success Criteria:**
`@model_validator` en `_validate_template_required` aanwezig; `ValidationError` correct gegooid bij opstart met ongeldige config; `block_prefix_hint` afwezig; `test_requirements_loader.py` groen.

---

### C_CROSSCHAT.3 — Core function: `build_crosschat_block_instruction` rewrite (Cycle 15)

**Goal:** Herschrijf `build_crosschat_block_instruction` zodat de functie `spec['block_template']` ophaalt en `str.format` aanroept met `{sub_role}` en `{markers_list}`. `markers_list` = `"\n\n".join(f"## {m}" for m in spec["markers"])`. Bij `KeyError` → `ConfigError` (hard falen).

**Tests:**
- `test_detect_sub_role.py`: correcte output met ingevulde `{sub_role}` en `{markers_list}` als `## Header` regels
- `test_detect_sub_role.py`: onbekende placeholder `{xyz}` → `ConfigError`
- `test_detect_sub_role.py`: Windows `\r\n` in template → gestript vóór `.format()`
- `test_detect_sub_role.py`: `block_prefix` niet meer in output

**Files:**
- `src/copilot_orchestration/hooks/detect_sub_role.py`
- `tests/copilot_orchestration/unit/hooks/test_detect_sub_role.py`

**Success Criteria:**
`markers_list` als `## Header` regels aanwezig; `ConfigError` bij `KeyError`; `block_prefix` afwezig; CRLF-mitigatie aanwezig; `test_detect_sub_role.py` groen.

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

**Success Criteria:**
`block_template` aanwezig en `block_prefix` afwezig in beide YAML-bestanden; loader laadt correct; rendered output is copy-paste klaar als één blok.

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

**Success Criteria:**
Geen legacy-assertions; volledige testsuite groen; `validate_architecture(scope="all")` clean; klaar voor PR.

---

## Risks & Mitigation

- **Risk:** `test_notify_compaction.py` asserteert op `block_prefix` of `guide_line` in output
  - **Mitigation:** Expliciet opgenomen in C_CROSSCHAT.5; assertions vervangen door `block_template`-gebaseerde checks
- **Risk:** YAML `|` (trailing newline) i.p.v. `|-` veroorzaakt regex-failures in tests
  - **Mitigation:** Conventie: altijd `|-` in `block_template`; in C_CROSSCHAT.4 expliciet toegepast
- **Risk:** Windows `\r\n` in verbatim block-template
  - **Mitigation:** `.replace("\r\n", "\n")` vóór `.format()` in C_CROSSCHAT.3 geïmplementeerd

---

## Milestones

- **C_CROSSCHAT.1 groen:** `SubRoleSpec` clean zonder legacy-velden
- **C_CROSSCHAT.3 groen:** `build_crosschat_block_instruction` produceert fence-correcte output
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
