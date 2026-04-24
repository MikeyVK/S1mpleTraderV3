<!-- docs\development\issue273\research.md -->
<!-- template=research version=8b7bb3ab created=2026-04-07T13:08Z updated= -->
# Issue #273: Remove commit_prefix_map from git.yaml

**Status:** DRAFT  
**Version:** 1.0  
**Last Updated:** 2026-04-07

---

## Purpose

Verwijder het redundante commit_prefix_map veld uit git.yaml en GitConfig, en herstel PolicyEngine zodat alle 11 commit-types worden geaccepteerd via de SSOT commit_types lijst.

## Scope

**In Scope:**
git.yaml (commit_prefix_map, tdd_phases velden), GitConfig (has_phase, get_prefix, get_all_prefixes methoden, cross-ref validator), PolicyEngine.decide() valid_prefixes logica, policies.yaml commentaar, bijbehorende tests en fixtures

**Out of Scope:**
PhaseContractResolver, phase_contracts.yaml, commit_types veld zelf, GitManager, ScopeEncoder, git_add_or_commit tool logic

## Prerequisites

Read these first:
1. Research afgerond
2. main up-to-date (SHA 75ad38c)
3. Epic #257 gesloten
---

## Problem Statement

git.yaml bevat twee velden (commit_prefix_map en tdd_phases) die redundant zijn geworden na introductie van phase_contracts.yaml. De PolicyEngine.decide() bouwt zijn allowlist op basis van commit_prefix_map, waardoor slechts 4 van de 11 commit-types worden geaccepteerd. Dit is een DRY-schending, een SSOT-overtreding en een bug.

## Research Goals

- Identificeer alle gevallen waar commit_prefix_map en tdd_phases worden gebruikt
- Bepaal of er productie-aanroepen zijn op has_phase(), get_prefix(), get_all_prefixes()
- Stel de juiste SSOT vast voor commit-type-validatie
- Inventariseer alle te wijzigen bestanden inclusief test-fixtures

---

## Background

Na introductie van phase_contracts.yaml en PhaseContractResolver (epic #257) is de commit-type-per-subfase mapping verplaatst naar commit_type_map in phase_contracts.yaml. De velden in git.yaml zijn nooit opgeschoond. git_add_or_commit gebruikt al uitsluitend PhaseContractResolver — commit_prefix_map wordt door geen enkel productiepad meer aangeraakt.

---

## Findings

DODE CODE (nul productie-aanroepen):
- GitConfig.has_phase() — alleen in tests
- GitConfig.get_prefix() — alleen in tests
- GitConfig.get_all_prefixes() — alleen door PolicyEngine (dit is de bug)
- validate_cross_references model_validator — valideert alleen commit_prefix_map vs tdd_phases

BUG: PolicyEngine.decide(operation='commit') bouwt allowlist via get_all_prefixes() die leest uit commit_prefix_map. Resultaat: alleen ['test:', 'feat:', 'refactor:', 'docs:']. Hierdoor worden chore:, fix:, ci:, build:, perf:, style:, revert: geblokkeerd.

IMPACT ANALYSE:
Productiebestanden:
- .st3/config/git.yaml: verwijder tdd_phases en commit_prefix_map blokken
- mcp_server/config/schemas/git_config.py: verwijder velden tdd_phases + commit_prefix_map, verwijder methoden has_phase() + get_prefix(), herschrijf get_all_prefixes() naar commit_types, verwijder validate_cross_references validator
- mcp_server/core/policy_engine.py: update commentaar regel 155
- .st3/config/policies.yaml: update commentaar regel 44

Testbestanden:
- tests/mcp_server/config/test_git_config.py: verwijder fixture-sleutels, verwijder test_has_phase/test_get_prefix/oud test_get_all_prefixes/test_invalid_commit_prefix_phase_raises, voeg nieuw test_get_all_prefixes toe (11 types)
- tests/mcp_server/core/test_policy_engine_config.py: voeg tests toe voor chore:/fix:/ci: als geldig
- tests/mcp_server/integration/test_workflow_cycle_e2e.py regels 115-116
- tests/mcp_server/tools/test_pr_tools_config.py regels 33-34
- tests/mcp_server/tools/test_git_tools_config.py regels 35-36
- tests/mcp_server/unit/managers/test_github_manager.py regels 207-208
- tests/unit/config/test_c_loader_structural.py regels 59-60
- tests/mcp_server/unit/config/test_loader_behaviors.py regel 74

SUB-PHASE TRACKING (navraag gebruiker): state.json slaat current_phase + current_cycle op. sub_phase (red/green/refactor) is altijd expliciete agentkennis — niet in state. build_phase_guard() valideert dat workflow_phase en cycle_number overeenkomen met state.json.

## Related Documentation
None
---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 |  | Agent | Initial draft |