<!-- docs\development\issue272\research.md -->
<!-- template=research version=8b7bb3ab created=2026-04-08T19:25Z updated= -->
# ScopeDecoder wrong phase on child branches with inherited commits

**Status:** DRAFT  
**Version:** 1.0  
**Last Updated:** 2026-04-08

---

## Purpose

Volledige root-cause analyse en structurele fix-aanbeveling voor issue #272, inclusief state.json contaminatie via merges en merge-strategie enforcement

## Scope

**In Scope:**
ScopeDecoder.detect_phase() precedentie, .gitattributes merge=ours, MergePRInput.merge_method beperking

**Out of Scope:**
get_state() state-reconstructie (#231), SSOT phase_contracts.yaml (#271), lokale git rebase operaties (niet geraakt door merge_method wijziging), uitbreiding workflow-fasedefinitie

## Prerequisites

Read these first:
1. Issue #272 gelezen
2. phase_detection.py volledig gelezen
3. GitAdapter.get_recent_commits() geanalyseerd
4. Git-history van bug/272 en refactor/270 gereconstrueerd
5. state.json tracking-history onderzocht (git log, git check-ignore)
6. merge-commits op main geanalyseerd (true merge vs squash)
7. pr_tools.py MergePRInput geanalyseerd
---

## Problem Statement

Op een verse child-branch (geen eigen commits) rapporteert ScopeDecoder.detect_phase() de fase van de parent-branch in plaats van de fase in state.json. Daarnaast belandt state.json van feature-branches via merges op parent-branches en op main, wat leidt tot contaminatie. Beide problemen hebben dezelfde grondoorzaak: de precedentie-volgorde commit-scope > state.json is verouderd en staat haaks op de huidige architectuur.

## Research Goals

- Bevestig de exacte code-paden die de onjuiste fase veroorzaken
- Reconstrueer waarom het bug op deze branch niet optrad maar op refactor/270 wel
- Evalueer en verwerp de patch-oplossing (branch_point_sha)
- Stel de structurele fix voor: precedentie omdraaien
- Analyseer state.json contaminatie via merges en definieer de oplossing
- Bepaal implicaties voor merge_method in merge_pr tool

---

## Background

ScopeDecoder is geïntroduceerd in issue #138 toen state.json nog in .gitignore stond. In die situatie was commit-scope de enige betrouwbare bron na een git checkout. State.json kon lokaal ontbreken na een branch-wissel. De volgorde commit-scope > state.json was destijds correct.

Sinds die tijd is state.json uit .gitignore gehaald en wordt het actief getrackt en gecommit. State.json is nu de autoritatieve bron voor de huidige workflow-fase van een branch — gezet door initialize_project en transition_phase. De oorspronkelijke rechtvaardiging voor commit-scope > state.json bestaat niet meer.

---

## Findings

## Root Cause

`GitAdapter.get_recent_commits(limit=N)` gebruikt `self.repo.iter_commits(max_count=limit)` wat de volledige git-history van HEAD itereert, inclusief geërfde parent-commits. Op een verse child-branch is de meest recente commit de laatste commit van de parent-branch. Als die commit een fase-scope heeft (bijv. `docs(P_DOCUMENTATION): ...`), retourneert `_parse_commit_scope()` die fase met `confidence=high`. De state.json-fallback wordt nooit bereikt.

## Reconstructie: waarom werkt bug/272 wél correct

Branch `bug/272` is aangemaakt van `main`. De top van main op dat moment:
```
1934d87  refactor: remove commit_prefix_map and tdd_phases from GitConfig (#273) (#277)
```
Dit is een GitHub squash-merge commit. GitHub schrijft squash-merges altijd als `type: titel (#issue) (#pr)` — zonder haakjes met een fase-scope. `_parse_commit_scope()` vindt geen `(P_???)` patroon → retourneert `None` → fallback naar state.json → `research` ✅

Direct na `initialize_project`, vóór de eigen research-commit, zou `get_work_context` dus al correct `research` rapporteren — toevallig, omdat de bovenste main-commit geen fase-scope heeft.

## Reconstructie: het bug-scenario (refactor/270 van epic/257)

Branch `refactor/270` aangemaakt van `epic/257`. Top van epic/257 op dat moment:
```
9096b0e  docs(P_DOCUMENTATION): add SESSIE_OVERDRACHT_270.md — document issue #270...
```
Dit heeft scope `P_DOCUMENTATION`. `_parse_commit_scope()` → `documentation`, confidence `high`. State.json zegt `research`. State.json wordt nooit bereikt. `get_work_context` rapporteert `documentation` ❌

## Waarom de patch (branch_point_sha) verworpen wordt

Een eerder overwogen fix was `branch_point_sha` opslaan in state.json en `get_recent_commits(base_sha=...)` aanroepen met `SHA..HEAD`. Dit filtert branch-eigen commits correct. Maar:
- Het voegt een nieuw veld toe aan state.json en BranchState
- Het vereist aanpassingen in initialize_project, git_adapter, project_manager én discovery_tools  
- Het lost het symptoom op zonder de verouderde architectuurbeslissing te corrigeren
- De werkelijke oorzaak — een verouderde precedentie — blijft intact

## Fix 1: precedentie omdraaien in detect_phase()

State.json is nu de SSOT voor branch-fase. Commit-scope is metadata voor traceerbaarheid, niet voor fase-detectie. De precedentie moet zijn: state.json > commit-scope > unknown.

```python
# Huidig (verouderd):
# commit-scope > state.json > unknown

# Nieuw (correct):
def detect_phase(self, commit_message, fallback_to_state=True):
    # PRIMARY: state.json (autoritatief voor huidige branch)
    if fallback_to_state:
        state_result = self._read_state_json()
        if state_result:
            return state_result
    # SECONDARY: commit-scope (voor gebruik zonder state.json, bijv. state_reconstructor)
    if commit_message:
        scope_result = self._parse_commit_scope(commit_message)
        if scope_result:
            return scope_result
    return self._unknown_fallback()
```

Backward compatibility: `state_reconstructor.py` roept `detect_phase(fallback_to_state=False)` aan — dat pad slaat state.json expliciet over. Dat gebruik blijft intact.

## State.json contaminatie via merges

Via git log is vastgesteld:
- `684b7ea` (merge refactor/270 → epic/257): state.json van refactor/270 overschreef epic/257's state.json
- `1934d87` (squash merge #273 → main): state.json van refactor/273 belandde op main
- `git show main:.st3/state.json` → `branch: refactor/273-remove-commit-prefix-map, phase: documentation`

Main heeft nu een state.json die nergens op slaat.

## Merge-typen en hun effect op state.json

| Type | Commits | Parents | .gitattributes merge=ours werkt? |
|---|---|---|---|
| True merge (`merge`) | Merge-commit aangemaakt | 2 | ✅ Ja |
| Squash merge | Diff samengepakt als 1 commit | 1 | ❌ Nee |
| Rebase merge | Commits opnieuw afgespeeld | 1 per commit | ❌ Nee |

Historisch patroon in dit project: uitsluitend true merges, met uitzondering van #273 (squash per abuis).

## Fix 2: .gitattributes merge=ours

```
.st3/state.json merge=ours
```

Bij elke true merge wint de state.json van de **target branch** altijd. Feature-branches contamineeren de epic- of main-branch niet meer.

## Fix 3: merge_method beperken tot 'merge'

`MergePRInput.merge_method` heeft nu `pattern='^(merge|squash|rebase)$'`. Squash en rebase produceren geen two-parent merge-commit, waardoor .gitattributes merge=ours niet activeert. Beide moeten geblokkeerd worden.

MergePRInput is **niet** config-driven (geen configure()-mechanisme zoals CreatePRInput). Het pattern is hardcoded in Pydantic Field. Oplossing: pattern aanpassen naar `'^merge$'` en description bijwerken. Het veld blijft aanwezig (backward compat voor tooling die expliciet merge_method doorgeeft).

Tests te updaten: `test_pr_tools.py`, `test_github_extras.py`, `test_github_adapter.py` bevatten nog `merge_method='squash'`.

## Open Questions

- ❓ Is er een scenario in dit project waarbij rebase-merge legitiem gewenst is? (Conclusie: nee — nooit gebruikt, epic-structuur werkt natural met true merges)
- ❓ Moet de fallback_to_state parameter hernoemd worden nu de semantiek omgedraaid is? (Conclusie: nee — de parameter-naam klopt nog steeds, alleen de volgorde in de implementatie wijzigt)


## Related Documentation
- **[mcp_server/core/phase_detection.py — ScopeDecoder.detect_phase()][related-1]**
- **[mcp_server/adapters/git_adapter.py — get_recent_commits()][related-2]**
- **[mcp_server/managers/project_manager.py:440-475 — _get_project_plan()][related-3]**
- **[mcp_server/tools/discovery_tools.py:240-270 — _detect_workflow_phase()][related-4]**
- **[mcp_server/managers/state_reconstructor.py:98 — detect_phase(fallback_to_state=False)][related-5]**
- **[mcp_server/tools/pr_tools.py:115-155 — MergePRInput / MergePRTool][related-6]**
- **[git log --merges --oneline -10 --first-parent main — historisch merge-patroon][related-7]**
- **[git show main:.st3/state.json — bevestigt state.json contaminatie op main][related-8]**

<!-- Link definitions -->

[related-1]: mcp_server/core/phase_detection.py — ScopeDecoder.detect_phase()
[related-2]: mcp_server/adapters/git_adapter.py — get_recent_commits()
[related-3]: mcp_server/managers/project_manager.py:440-475 — _get_project_plan()
[related-4]: mcp_server/tools/discovery_tools.py:240-270 — _detect_workflow_phase()
[related-5]: mcp_server/managers/state_reconstructor.py:98 — detect_phase(fallback_to_state=False)
[related-6]: mcp_server/tools/pr_tools.py:115-155 — MergePRInput / MergePRTool
[related-7]: git log --merges --oneline -10 --first-parent main — historisch merge-patroon
[related-8]: git show main:.st3/state.json — bevestigt state.json contaminatie op main

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 |  | Agent | Initial draft |