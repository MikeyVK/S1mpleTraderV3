<!-- docs\development\issue263\planning.md -->
<!-- template=planning version=130ac5ea created=2026-03-24T17:12Z updated= -->
# YAML-First Handover Block Refactor — Planning

**Status:** DRAFT  
**Version:** 1.0  
**Last Updated:** 2026-03-24

---

## Purpose

Geef developers volledige controle over het handover-blok via YAML, zonder Python-logica te wijzigen.

## Scope

**In Scope:**
SubRoleSpec TypedDict (interfaces.py), _SubRoleSchema + SubRoleRequirementsLoader (requirements_loader.py), build_crosschat_block_instruction (detect_sub_role.py), _default_requirements.yaml, .copilot/sub-role-requirements.yaml, 5 test-bestanden.

**Out of Scope:**
MCP-server tools, notify_compaction.py en stop_handover_guard.py (interface ongewijzigd — geen code-change nodig).

## Prerequisites

Read these first:
1. Research v3.1 afgerond en gecommit (a0536be) — alle design-beslissingen vastgelegd
2. build_crosschat_block_instruction gelokaliseerd in detect_sub_role.py lijnen 101-114
3. Alle 4 dode velden verified als dead/feedthrough
---

## Summary

Flag-day refactor van build_crosschat_block_instruction: verwijder 4 legacy-velden (block_prefix, guide_line, block_prefix_hint, marker_verb) en introduceer block_template als verbatim str.format-template met twee placeholders ({sub_role}, {markers_list}). Alle content binnen de fence; hard-fail bij onbekende placeholder. Pydantic @model_validator valideert bij laden. Geen backward compatibility — package nog nooit gereleased.

---

## Dependencies

- C_CROSSCHAT.2 afhankelijk van C_CROSSCHAT.1 (SubRoleSpec moet correct zijn vóór loader-aanpassing)
- C_CROSSCHAT.3 afhankelijk van C_CROSSCHAT.1 (build_crosschat_block_instruction gebruikt spec['block_template'])
- C_CROSSCHAT.4 afhankelijk van C_CROSSCHAT.2 (YAML-validatie via _SubRoleSchema)
- C_CROSSCHAT.5 afhankelijk van C_CROSSCHAT.1 t/m C_CROSSCHAT.4 (alle wijzigingen moeten klaar zijn)

---

## TDD Cycles


### Cycle 1: 

**Goal:** 

**Tests:**

**Success Criteria:**



### Cycle 2: 

**Goal:** 

**Tests:**

**Success Criteria:**



### Cycle 3: 

**Goal:** 

**Tests:**

**Success Criteria:**



### Cycle 4: 

**Goal:** 

**Tests:**

**Success Criteria:**



### Cycle 5: 

**Goal:** 

**Tests:**

**Success Criteria:**


---

## Risks & Mitigation

- **Risk:** 
  - **Mitigation:** 
- **Risk:** 
  - **Mitigation:** 
- **Risk:** 
  - **Mitigation:** 

---

## Milestones

- C_CROSSCHAT.1 groen: SubRoleSpec clean zonder legacy-velden
- C_CROSSCHAT.3 groen: build_crosschat_block_instruction produceert fence-correcte output
- C_CROSSCHAT.4 groen: YAML-bestanden volledig bijgewerkt, loader valideert correct
- C_CROSSCHAT.5 groen: volledige testsuite groen, architecture validate clean

## Related Documentation
- **[docs/development/issue263/research_yaml_first_handover_block.md][related-1]**

<!-- Link definitions -->

[related-1]: docs/development/issue263/research_yaml_first_handover_block.md

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 |  | Agent | Initial draft |