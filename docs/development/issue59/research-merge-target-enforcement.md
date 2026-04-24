<!-- docs\development\issue59\research-merge-target-enforcement.md -->
<!-- template=research version=8b7bb3ab created=2026-04-24T14:24Z updated= -->
# Merge Target Enforcement — Analyse & Oplossingsrichting

**Status:** DRAFT  
**Version:** 1.0  
**Last Updated:** 2026-04-24

---

## Purpose

Legt de bevindingen vast van de backlog-review (2026-04-24) zodat issue #59 correct kan worden gesloten of bijgesteld.

## Scope

**In Scope:**
submit_pr merge-target validatie, enforcement.yaml, EnforcementRunner handlers, parent_branch tracking in state.json

**Out of Scope:**
create_branch base-branch validatie (al geïmplementeerd), PR review proces, GitHub branch protection rules

---

## Problem Statement

submit_pr valideert het merge-doel (base branch) niet tegen de geconfigureerde parent_branch van de werkende branch. Hierdoor kan een child-branch van een epic onbedoeld naar main worden gemerged in plaats van naar de epic branch, wat resulteert in gefragmenteerde documentatie en een incomplete epic branch.

## Research Goals

- Vaststellen welk deel van issue #59 al geïmplementeerd is vs. nog ontbreekt
- Bepalen of de merge-target validatie thuishoort in SubmitPRTool of in het enforcement-systeem
- Een concrete implementatierichting voorstellen die consistent is met de bestaande architectuur

---

## Background

Issue #59 ontstond tijdens issue #50 toen een child-branch naar main werd gemerged in plaats van naar epic/49. Het issue vroeg om twee dingen: (1) documenteer de branching-strategie, (2) handhaaf de strategie via tooling.

---

## Findings

**Wat al geïmplementeerd is (✅)**

1. `create_branch` base-restriction enforcement — volledig via `.st3/config/enforcement.yaml`:
   ```yaml
   check_branch_policy: base_restriction
     epic:    [main]
     feature: [main, 'epic/*']
     docs:    [main, 'epic/*']
   ```
   Blokkeert het aanmaken van een branch op een ongeldige base. De *bron* van branches is afgedwongen.

2. `parent_branch` tracking — geïmplementeerd via issue #79:
   - `PhaseStateEngine.start_project()` bewaart `parent_branch` in `.st3/state.json`
   - `get_parent_branch` tool bestaat
   - `.st3/projects.json` toont historische vastlegging (bijv. `'parent_branch': 'epic/49-mcp-platform-configurability'`)

3. `GIT_WORKFLOW_Legacy.md` bestaat in `docs/archive/` maar er is geen actief `GIT_WORKFLOW.md`.

**Wat ontbreekt (❌)**

`submit_pr` valideert het merge-doel NIET:
```python
# pr_tools.py — SubmitPRInput
base: str | None = Field(default=None, ...)  # → defaults naar 'main', geen validatie
```
Er is geen check: als `state.parent_branch != main` dan moet `base == parent_branch`. De agent.md toont ook altijd `submit_pr(..., base='main')` zonder epic-workflow variant.

**Oplossingsrichting**

NIET hardcoden in `SubmitPRTool` maar als nieuw enforcement action type in YAML configureren. Rationale:
- Alle drie bestaande handlers (`check_branch_policy`, `check_pr_status`, `check_phase_readiness`) volgen het patroon: YAML stuurt, handler blokkeert.
- `research_runner_architecture_baseline.md` stelt expliciet: enforcement.yaml is voor tool-level guards die invocatie blokkeren voor uitvoering.
- YAML-configuratie maakt de check uitschakelbaar zonder tool-code te wijzigen (bijv. hotfix van epic naar main).

Concrete implementatie:
1. `enforcement.yaml` — voeg `check_merge_target` action toe aan de `submit_pr` pre-block
2. `enforcement_runner.py` — nieuwe `_handle_check_merge_target()` handler:
   - Leest `parent_branch` uit `.st3/state.json`
   - Als `parent_branch` ontbreekt of gelijk aan `default_base_branch`: geen restrictie
   - Anders: vergelijk `context.get_param('base')` met `parent_branch`; blokkeer bij afwijking
3. Registreer in `_build_default_registry()`
4. `EnforcementAction.validate_required_fields()`: geen extra velden nodig

Er zijn geen wijzigingen aan `SubmitPRTool` of aan `EnforcementConfig` schema nodig.

## Related Documentation
- **[mcp_server/tools/pr_tools.py][related-1]**
- **[mcp_server/managers/enforcement_runner.py][related-2]**
- **[.st3/config/enforcement.yaml][related-3]**
- **[docs/mcp_server/architectural_diagrams/04_enforcement_layer.md][related-4]**
- **[docs/development/issue257/research_runner_architecture_baseline.md][related-5]**

<!-- Link definitions -->

[related-1]: mcp_server/tools/pr_tools.py
[related-2]: mcp_server/managers/enforcement_runner.py
[related-3]: .st3/config/enforcement.yaml
[related-4]: docs/mcp_server/architectural_diagrams/04_enforcement_layer.md
[related-5]: docs/development/issue257/research_runner_architecture_baseline.md

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 |  | Agent | Initial draft |