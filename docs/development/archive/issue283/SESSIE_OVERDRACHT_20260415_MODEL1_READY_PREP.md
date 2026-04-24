# Sessie Overdracht — 15 april 2026 (Model 1)

## Branch
`refactor/283-ready-phase-enforcement`

## Issue
#283

## Huidige fase
`ready`

## Aanleiding

In deze sessie is het functionele doel van issue #283 opnieuw scherp getrokken.
Het geaccepteerde model is nu:

- De child branch mag de echte werkgeschiedenis van `.st3/state.json` en
  `.st3/deliverables.json` behouden tijdens het werk.
- De parent branch (`main` of een epic parent) mag door de merge niet geraakt worden
  op deze excluded files.
- Daarom moet de branch-tip vlak voor PR merge-neutraal worden gemaakt ten opzichte van
  de target base branch.
- De history mag dus de echte werkstate tonen tot en met de commit vlak voor de ready /
  prepare-for-PR commit.

Dit document legt vast wat inhoudelijk is geaccepteerd, wat de huidige status is, en
welke chirurgische wijzigingen nodig zijn om dit model te implementeren.

---

## Geaccepteerd doelbeeld

### Model 1 — Geaccepteerd

1. De excluded files blijven zichtbaar in de commit history van de child branch tijdens het werk.
2. De laatste ready / prepare-for-PR commit neutraliseert deze files terug naar de base branch.
3. Daardoor is `merge-base..HEAD` op deze paden leeg op het moment van PR-aanmaak.
4. De merge verandert de parent-state op deze paden niet.

### Belangrijke implicatie

Dit model betekent expliciet:

- De excluded files blijven **niet** zichtbaar op de uiteindelijke branch-tip als die tip
  merge-neutraal moet zijn.
- Ze blijven wel zichtbaar in de **geschiedenis** van de child branch, tot en met de commit
  vlak voor de ready / prepare-for-PR commit.

Dat is geaccepteerd als correct gedrag.

---

## Wat in deze sessie is vastgesteld

### 1. De huidige create_pr-check gebruikt inhoudelijk het juiste controlepunt

De huidige create_pr-gate kijkt naar netto branch-diff tegen de base via
`git diff --name-only merge_base..HEAD -- path` in:

- `mcp_server/managers/enforcement_runner.py`

Dat is nog steeds het juiste controlepunt voor model 1. De PR-tool moet **niet** kijken
naar de lokale staging area van de laatste commit. Een GitHub PR-merge merge-t de
gecommitte branch-tip tegen de base branch; daarom is branch-tip versus base de relevante
invariant.

### 2. De huidige ready-flow lost alleen het commit-probleem op, niet het branch-tip-probleem

De huidige flow gebruikt `ExclusionNote` → `skip_paths` → `git restore --staged` om
excluded files uit de **nieuwe commit** te houden:

- `mcp_server/tools/git_tools.py`
- `mcp_server/managers/git_manager.py`
- `mcp_server/adapters/git_adapter.py`

Dat voorkomt delta in die commit, maar neutraliseert de branch-tip niet automatisch tegen
de base branch. Voor model 1 is dit dus onvoldoende als hoofdmechanisme.

### 3. De huidige branch op deze machine is nog niet model-1-ready

Tijdens deze sessie is vastgesteld dat de actieve branch nog netto diff heeft tegen `main`
op de excluded files. Daarom is een create_pr-blokkade onder de huidige code op dit moment
inhoudelijk verklaarbaar.

Daarnaast is op deze machine de worktree niet clean:

- `.st3/state.json` is lokaal gewijzigd

Deze lokale wijziging hoort **niet** in deze overdrachtscommit thuis.

---

## Vereiste productiewijzigingen

### A. GitCommitTool — ready-flow moet base-neutralisatie uitvoeren

Bestand:

- `mcp_server/tools/git_tools.py`

Huidig gedrag in ready-flow:

- `ExclusionNote` entries worden gelezen
- daaruit worden `skip_paths` gebouwd
- `GitManager.commit_with_scope(..., skip_paths=excluded_paths)` commit een delta-vrije commit

Gewenst gedrag voor model 1:

- `ExclusionNote` blijft de trigger
- in de ready / terminal flow worden de excluded files eerst teruggezet naar de effectieve
  base branch
- daarna wordt een echte ready / prepare-for-PR cleanup commit gemaakt die deze
  neutralisatie vastlegt op de branch-tip

Concreet:

1. Lees `excluded_paths` uit `NoteContext`.
2. Resolve de effectieve base branch.
3. Zet elk excluded path terug naar de base-versie in worktree + index.
4. Commit vervolgens deze neutralisatie.
5. Gebruik in deze route niet langer `skip_paths` als hoofdmechanisme.

### B. GitAdapter — hergebruik / uitbreiding van restore voor align-to-base

Bestand:

- `mcp_server/adapters/git_adapter.py`

De bestaande `restore(files, source=...)` helper is de juiste bouwsteen.
Voor model 1 is waarschijnlijk een kleine uitbreiding nodig:

- Als het pad op de base bestaat: restore die versie.
- Als het pad op de base **niet** bestaat: verwijder het pad zodat de branch-tip gelijk wordt
  aan de base branch.

Belangrijk: dit is **niet** hetzelfde als `git rm --cached` als exclude-mechanisme.
Hier gaat het om een expliciete branch-tip cleanup commit, niet om het verbergen van een pad
uit één commit.

### C. Basisbranch-resolutie moet overal gelijk zijn

Bestanden:

- `mcp_server/tools/git_tools.py`
- `mcp_server/tools/pr_tools.py`
- mogelijk klein deel van `mcp_server/server.py` als extra injectie nodig blijkt

Voor model 1 moeten ready-cleanup en create_pr exact dezelfde base gebruiken.
De gewenste resolutievolgorde is:

1. expliciet meegegeven `base`
2. `parent_branch` uit branch state
3. `git_config.default_base_branch`

Op dit moment gebruikt `CreatePRInput` vooral `git_config.default_base_branch` als fallback.
Dat is te smal voor epic-parent scenario's.

### D. create_pr guard inhoudelijk behouden, remediation aanpassen

Bestand:

- `mcp_server/managers/enforcement_runner.py`

Behoud:

- `_has_net_diff_for_path(...)`
- check tegen `merge-base..HEAD`

Aanpassen:

- fouttekst
- remediation / suggestion notes

Nieuwe bedoeling van de melding:

- niet: “artifact is nog git-tracked”
- wel: “excluded files zijn nog niet geneutraliseerd tegen de base; voer eerst de ready /
  prepare-for-PR cleanup uit”

---

## Wat expliciet niet moet gebeuren

1. `git restore --staged` generiek vervangen door `git rm --cached` als oplossing.
   Dat lost model 1 niet op en breekt het bestaande zero-delta ontwerp.

2. create_pr versoepelen naar controle op alleen de laatste commit of alleen de staging area.
   Dat is te zwak voor gewone PR-merge semantiek.

3. `.gitattributes merge=ours` opnieuw als hoofdrichting openen.
   Dit pad is in research en design al verworpen als onbetrouwbaar voor GitHub PR-merges.

---

## Verwachte testimpact

### Bestaande tests die niet langer het hoofdcontract vertegenwoordigen

- `tests/mcp_server/unit/adapters/test_git_adapter_skip_paths.py`
- `tests/mcp_server/integration/test_git_add_commit_regression_c6.py`

Deze tests kunnen mogelijk deels blijven als regressie op de generieke `skip_paths` primitive,
maar ze mogen niet meer het hoofdcontract van ready / prepare-for-PR zijn.

### Nieuwe hoofdcontracttests voor model 1

1. Branch wijzigt `state.json` / `deliverables.json` tijdens het werk.
2. Ready / prepare-for-PR commit neutraliseert deze paden terug naar de base.
3. `git diff --name-only merge_base..HEAD -- excluded_paths` is leeg na deze commit.
4. `create_pr` wordt daarna niet meer geblokkeerd.
5. De geschiedenis vóór die ready commit toont nog steeds de echte werkstate.
6. Zelfde bewijs voor:
   - base zonder deze files
   - epic parent met eigen versies van deze files

### Cruciale extra integration-test

De belangrijkste nog ontbrekende proof is een echte merge-neutralisatie-test:

- setup van een parent branch met of zonder eigen excluded files
- child branch voert echte werkcommits uit op deze files
- ready / prepare-for-PR commit neutraliseert ze naar base
- merge-base..HEAD op die paden is leeg
- een merge-simulatie laat zien dat parent-state inhoudelijk onveranderd blijft

---

## Aanbevolen implementatievolgorde

1. Voeg base-resolutie helper toe of centraliseer die.
2. Pas `GitCommitTool.execute()` aan voor ready / terminal cleanup naar base.
3. Breid `GitAdapter.restore()` of een kleine helper eromheen uit voor “align to source”.
4. Pas create_pr messaging aan, maar behoud net-diff check.
5. Herschrijf / vervang de integration tests naar model 1 contracten.
6. Verifieer op zowel `main`-base als epic-parent scenario.

---

## Huidige sessiestatus

Deze sessie heeft alleen analyse en besluitvorming gedaan.

Gedaan:

- model 1 inhoudelijk vastgelegd
- vastgesteld dat create_pr naar het juiste controlepunt moet blijven kijken
- vastgesteld dat ready-flow moet verschuiven van commit-level exclusion naar
  branch-tip neutralisatie tegen base
- vastgesteld dat dit chirurgisch mogelijk is met een beperkte set productie-aanpassingen

Niet gedaan:

- geen productiecode aangepast
- geen tests aangepast
- geen cleanup van `.st3/state.json` op deze machine

---

## Praktische noot voor vervolg op andere machine

Als je dit op een andere machine uitvoert:

- begin vanaf een schone worktree
- neem deze overdracht als leidraad
- commit de implementatie pas nadat de nieuwe model-1 contracttests groen zijn
- laat lokale branch-state artifacts van de huidige machine buiten beschouwing
