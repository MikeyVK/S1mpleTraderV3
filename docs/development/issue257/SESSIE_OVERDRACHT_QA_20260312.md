<!-- docs\development\issue257\SESSIE_OVERDRACHT_QA_20260312.md -->
<!-- template=planning version=130ac5ea created=2026-03-12T00:00Z updated= -->
# Issue257 Sessieoverdracht QA (2026-03-12)

**Status:** ACTIVE  
**Version:** 1.2  
**Last Updated:** 2026-03-13

---

## Purpose

Read-only QA-log voor issue #257 na hercontrole van Cycle 1, Cycle 2 en Cycle 3.
Doel van dit document:
- vastleggen welke punten nu `GO` zijn;
- vastleggen welke restschuld bewust niet blockend is;
- een concrete input geven voor een eventuele extra schuld-cycle.

---

## QA-oordeel op dit moment

### Cycle 1
**Oordeel:** GO

Bevestigd:
- `tdd` is vervangen door `implementation` in `.st3/workflows.yaml`
- `GitConfig.extract_issue_number()` bestaat en wordt gebruikt
- `_extract_issue_from_branch` is verwijderd uit PSE
- `workflow_config.py` is verwijderd
- broncode-PSE bevat geen blocking `projects.json`-afhankelijkheid meer voor Cycle 1-doelen

### Cycle 2
**Oordeel:** GO

Bevestigd:
- `StateRepository`-laag bestaat met `FileStateRepository` en `InMemoryStateRepository`
- `BranchState` is frozen en gebruikt de design-richting met `current_cycle`, `last_cycle`, `cycle_history`
- `PhaseStateEngine.get_state()` retourneert `BranchState`
- `PhaseStateEngine._save_state()` werkt op `BranchState`
- PSE unit tests gebruiken repository-injectie met `InMemoryStateRepository`
- onderzochte Cycle 2-files passeren quality gates en typechecks

### Cycle 3
**Oordeel:** GO

Bevestigd:
- `phase_contracts.yaml` bestaat als aparte contractlaag naast `workphases.yaml`
- `PhaseContractsConfig`, `PhaseConfigContext`, `CheckSpec` en `PhaseContractResolver` bestaan
- Fail-Fast validatie op `cycle_based=true` zonder `commit_type_map` is aanwezig
- resolver heeft geen dependency op `StateRepository` en gebruikt geen `glob`
- A6 merge-semantiek is aanwezig: required config-gates blijven immutabel, issue-specifieke checks kunnen recommended gedrag uitbreiden of overschrijven
- `commit_type_map` voor `implementation` gebruikt `red: test`, `green: feat`, `refactor: refactor`
- gerichte resolver-tests en quality gates zijn groen

---

## Niet-blockerende restschuld

Deze punten blokkeren Cycle 1/2/3 niet meer, maar zijn waardevol als aparte opschoon- of alignmentslag.

### 1. Oude cycle-terminologie leeft nog in delen van de testlaag
Voorbeelden:
- `current_tdd_cycle`
- `last_tdd_cycle`
- `tdd_cycle_history`

Belangrijkste hotspot:
- `tests/mcp_server/unit/tools/test_transition_tools.py`

Risico:
- verwarring tussen compatibility-laag en beoogde eindterminologie;
- toekomstige refactors moeten oude alias-namen blijven meeslepen zolang tests daarop leunen.

Aanbevolen actie:
- migreer tool-tests stapsgewijs naar `current_cycle`, `last_cycle`, `cycle_history`;
- behoud aliases alleen zolang productiecode of migratiepad ze nog echt nodig heeft.

### 2. Open documentatie- en issue-map drift
Belangrijkste hotspots:
- oudere issue257 handovers zoals `SESSIE_OVERDRACHT_20260311.md`
- research/planning artefacten die nog bewust historische `tdd`/`projects.json` context beschrijven

Risico:
- actuele implementatiestatus en historische ontwerpcontext lopen door elkaar;
- nieuwe sessies kunnen verkeerde vervolgstappen kiezen op basis van verouderde handover-notes.

Aanbevolen actie:
- houd handover-docs expliciet bij als historisch versus actueel;
- werk issue-map/backlog alleen bij in het actuele overdrachtsdocument.

### 4. Compatibility helpers in `BranchState` zijn nog aanwezig
Huidige compatibility-laag:
- aliases voor oude veldnamen via `AliasChoices`
- properties `current_tdd_cycle`, `last_tdd_cycle`, `tdd_cycle_history`
- helper-methoden `get`, `__getitem__`, `__contains__`

Risico:
- nuttig voor tussenstap, maar het houdt de dict- en legacy-mentaliteit langer in leven dan het design idealiter wil.

Aanbevolen actie:
- plan een gerichte cleanup-cycle waarin callers worden overgezet op typed attribute access;
- verwijder compatibility helpers pas nadat tool- en integration-tests mee zijn gemigreerd.

### 5. Cycle 3 houdt nog een tijdelijke contract-compatibilitylaag aan in `phase_contracts`
Huidige compatibility-laag:
- alias-ondersteuning voor oudere contractnamen via `AliasChoices`
- ondersteuning voor zowel `checks` als `exit_requires`
- ondersteuning voor zowel `cycle_checks` als `cycle_exit_requires`

Risico:
- een afgesproken flag-day kan semantisch verwateren als oude contracttaal te lang naast de nieuwe blijft bestaan;
- documentatie, fixtures en toekomstige tool-integratie kunnen opnieuw divergeren als niet expliciet naar één definitieve contracttaal wordt geconvergeerd.

Aanbevolen actie:
- leg in Cycle 4+ vast welke contractnamen definitief publiek zijn;
- migreer fixtures/tests/tooling naar alleen die contracttaal;
- verwijder alias-ondersteuning zodra de toollaag en tests niet meer op de oude sleutels leunen.

---

## Aanbevolen extra schuld-cycle

### Doel
Na de functionele refactor een korte stabilisatie-/opschooncycle uitvoeren die alleen technische schuld en alignment opruimt.

### Scope
**In scope:**
- testmigratie van oude cycle-velden naar nieuwe `BranchState`-velden
- beoordelen of `BranchState` compatibility helpers nog nodig zijn
- convergeren van `phase_contracts` op één definitieve contracttaal zonder alias-dubbels
- handover-documenten en issue-map actueel houden

**Out of scope:**
- nieuwe architectuurbeslissingen
- uitbreiding van `phase_contracts.yaml`
- wijziging van workflowvolgorde
- functionele wijzigingen aan Cycle 3+ ontwerpkeuzes

### Definition of Done
- geen actieve unit/integration-tests leunen nog onnodig op `current_tdd_cycle`-namen, behalve waar expliciet als backward compatibility gedocumenteerd;
- legacy `projects.json` testreferenties zijn of gemigreerd, of expliciet gelabeld als legacy-compatibiliteit;
- comments/docstrings gebruiken consequent `implementation` waar dat de bedoelde fase is;
- resterende compatibility helpers in `BranchState` zijn geminimaliseerd of expliciet verantwoord;
- `phase_contracts` gebruikt nog maar één publiek gedragen contracttaal voor gates en cycle-gates.

---

## Concrete backlog voor implementatie-agent

1. Maak een inventaris van alle resterende `current_tdd_cycle` / `last_tdd_cycle` / `tdd_cycle_history` referenties buiten compatibility-code.
2. Migreer `tests/mcp_server/unit/tools/test_transition_tools.py` naar de nieuwe cycle-velden.
3. Evalueer of `BranchState.get()`, `__getitem__`, `__contains__` en de oude cycle-properties nog noodzakelijk zijn na verdere testmigratie.
4. Bepaal de definitieve publieke contractnamen in `phase_contracts` en migreer tests/fixtures/tooling weg van `checks` / `cycle_checks` zodra dat veilig kan.
5. Verwijder de Cycle 3 alias-ondersteuning pas nadat die convergentie aantoonbaar is afgerond.
6. Houd alleen `SESSIE_OVERDRACHT_QA_20260312.md` bij als actuele issue-map; markeer oudere handovers expliciet als historisch.

---

## Related Documentation
- [planning.md](planning.md)
- [design.md](design.md)
- [research_config_first_pse.md](research_config_first_pse.md)
- [SESSIE_OVERDRACHT_QA_20260304.md](SESSIE_OVERDRACHT_QA_20260304.md)

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.2 | 2026-03-13 | QA Agent | Verwijderde testschuld verwerkt; open restschuld teruggebracht tot compatibility-helpers, contract-convergentie en actuele issue-map |
| 1.1 | 2026-03-12 | QA Agent | Cycle 3 QA-oordeel en niet-blockerende contract-aliasschuld toegevoegd |
| 1.0 | 2026-03-12 | QA Agent | Nieuwe QA-log met restschuld na hercontrole van Cycle 1 en 2 |
