<!-- docs\development\issue257\research_config_layer_srp.md -->
<!-- template=research version=8b7bb3ab created=2026-03-14T06:31Z updated= -->
# Config Layer SRP Violations: Missing Loader, Validator and Schema Separation

**Status:** DRAFT  
**Version:** 1.0  
**Last Updated:** 2026-03-14

---

## Purpose

Informeert de planning van de volgende implementatiecycli voor issue #257. De bevindingen vormen de basis voor cycli gericht op het introduceren van ConfigLoader, ConfigValidator, het aanmaken van mcp_config.yaml en het opruimen van schema/loader-conflaties.

## Scope

**In Scope:**
mcp_server/config/*.py analyse; .st3/*.yaml volledigheidscheck; vergelijking met backend/config/ referentiepatroon; identificatie van config vs constanten mix-ups; prioritering van cycli

**Out of Scope:**
Implementatie van de fixes; template engine config (issue #72); sections.yaml architectuur (issue #258); state.json pad-centralisatie (aparte C9 cyclus)

## Prerequisites

Read these first:
1. GAP_ANALYSE_ISSUE257.md volledig gelezen (10/20 KPI rood, RC-1 t/m RC-8)
2. backend/config/__init__.py referentiearchitectuur bestudeerd (ConfigLoader/ConfigValidator/ConfigTranslator)
3. docs/coding_standards/ARCHITECTURE_PRINCIPLES.md secties 1-4 gelezen (SRP, Config-First, Fail-Fast, SSOT)
4. docs/system/addendums/Addendum_ 3.8 Configuratie en Vertaal Filosofie.md gelezen (drie lagen: Platform/Operation/Strategy)
---

## Problem Statement

mcp_server/config/ heeft 15 config-klassen die elk hun eigen YAML lader, foutafhandeling en hardcoded pad implementeren. Er is geen centrale ConfigLoader, geen ConfigValidator en mcp_config.yaml bestaat niet. Elke klasse is tegelijk Pydantic-schema en loader — een directe SRP-schending. Python-defaults spiegelen YAML-waarden (DRY-schending), er is een stille waarde-conflict in quality_config.py, en twee niet-schema bestanden staan verkeerd geplaatst in de config/ map. De huidige situatie is het spiegelbeeld van de ARCHITECTURE_PRINCIPLES (Config-First, Fail-Fast, SSOT) die het project zelf hanteert.

## Research Goals

- Identificeer alle plekken waar Python-defaults YAML-waarden dupliceren (DRY-schending)
- Stel vast welke YAML-bestanden ontbreken versus config-klassen die wel bestaan
- Documenteer de afwijking van het backend ConfigLoader/ConfigValidator referentiepatroon
- Breng config vs constanten mix-ups in kaart (GitConfig, Settings, ServerSettings)
- Bepaal welke bestanden in mcp_server/config/ geen Pydantic-schema zijn
- Stel een geprioriteerde cyclus-volgorde op voor de volgende implementatierun

---

## Background

De mcp_server is gegroeid vanuit de S1mpleTrader V3 workspace die een strak config-systeem had (backend/config/ met ConfigLoader/ConfigValidator/ConfigTranslator). Tijdens de MCP-serverontwikkeling zijn config-klassen incrementeel toegevoegd (Issue #55, #138, etc.) zonder de centrale loader-laag over te nemen. Elke klasse implementeerde zijn eigen from_file() of load() methode. Settings.py introduceert mcp_config.yaml als configuratiebron, maar dat YAML-bestand is nooit aangemaakt — de server draait dus altijd op hardcoded Python-defaults.

---

## Findings

**F1 — Geen centrale ConfigLoader (SRP-schending)**
Elke van de 15 config-klassen implementeert zijn eigen YAML-laadlogica via from_file() of load(). Elke klasse hardcodeert zijn eigen .st3/xxx.yaml pad. Foutafhandeling is inconsistent (FileNotFoundError vs ConfigError vs ValueError). Dit is het tegenovergestelde van het backend-patroon: één ConfigLoader-klasse met één methode per YAML-bestand, config_root als constructor-parameter.

**F2 — Geen ConfigValidator (cross-config validatie ontbreekt)**
De ARCHITECTURE_PRINCIPLES schrijven voor: 'Config loaders raise ConfigError for logically inconsistent combinations — detected at startup, not at runtime.' Er is geen centrale validator. Cross-config checks zijn verspreid: operation_policies.py valideert allowed_phases tegen workflows.yaml intern, project_structure.py valideert artifact_types tegen artifacts.yaml intern. Ze zijn niet zichtbaar als startup-validatie en produceren geen gestructureerde foutrapportage.

**F3 — mcp_config.yaml bestaat niet (fail-silent boot)**
Settings.load() doet if path.exists(): ... — als het bestand ontbreekt wordt de data stilzwijgend overgeslagen, geen fout, geen waarschuwing. De test test_default_settings() bevestigt dit: Settings() zonder YAML construeren en hardcoded waarden asserteren. Dit is een directe schending van Fail-Fast: 'Missing config files → explicit FileNotFoundError with path, never None return.'

**F4 — Python-defaults spiegelen YAML exact (DRY-schending)**
GitConfig heeft Field(default=["feature", "bug", "fix", ...]) terwijl .st3/git.yaml exact dezelfde waarden bevat. Alle 5 consumers gebruiken GitConfig.from_file(), nooit GitConfig() direct — de Python-defaults zijn dode code die de illusie wekt van graceful degradation terwijl het systeem zonder YAML niet functioneert.

**F5 — Waarde-conflict in quality_config.py vs quality.yaml**
ArtifactLoggingConfig hardcodeert output_dir default als 'temp/qa_logs'. quality.yaml definieert 'mcp_server/logs/qa_logs'. De YAML wint nu, maar als artifact_logging uit de YAML verwijderd wordt schakelt de server stil over naar het verkeerde pad.

**F6 — Niet-schema bestanden in config/**
template_config.py is geen Pydantic-schema: het is een path-resolution functie (get_template_root()) met env var en filesystem checks. label_startup.py is geen config-schema: het is een startup-validatiefunctie die warnings logt. Beide horen in utils/ respectievelijk services/core/ thuis.

**F7 — Config vs constanten mix-ups**
GitConfig.branch_types, GitConfig.commit_types, GitConfig.protected_branches bevatten domeinkennis die nooit door een gebruiker geconfigureerd wordt (ze zijn bouw-tijd conventies). Settings.ServerSettings.name ('st3-workflow'), .version ('1.0.0'), GitHubSettings.owner ('MikeyVK'), .repo ('S1mpleTraderV3') zijn projectspecifieke constanten. Ze dragen het uiterlijk van configureerbare instellingen maar functioned als compile-time constanten.

**F8 — Schema's buiten config/ geplaatst**
EnforcementConfig (enforcement_runner.py) en het Pydantic-rootobject voor phase_contracts.yaml (phase_contract_resolver.py) leven in managers/ in plaats van config/schemas/. Inconsistent met alle overige config-klassen.

## Open Questions

- ❓ Moet mcp_config.yaml aangemaakt worden als SSOT voor server-naam, versie, GitHub-owner/repo — of zijn dit echte constanten die uit Settings moeten?
- ❓ Moet ConfigLoader config_root als constructor-parameter krijgen (C9 pad-centralisatie meteen inbegrepen) of als class-level constant?
- ❓ Moeten de Python Field(default=...) waarden in GitConfig verwijderd worden (schema strikt), of vervangen door Field(...) zodat ze required worden zonder YAML?
- ❓ Hoe verhoudt label_startup.py zich tot een toekomstige ConfigValidator.validate_startup() — is label_startup.py dan volledig overbodig?


## Related Documentation
- **[docs/coding_standards/ARCHITECTURE_PRINCIPLES.md — secties 3 (Config-First), 4 (Fail-Fast), 2 (DRY+SSOT)][related-1]**
- **[docs/system/addendums/Addendum_ 3.8 Configuratie en Vertaal Filosofie.md — ConfigLoader/ConfigValidator/ConfigTranslator patroon][related-2]**
- **[backend/config/__init__.py — referentie-implementatie van het drielaagse patroon][related-3]**

<!-- Link definitions -->

[related-1]: docs/coding_standards/ARCHITECTURE_PRINCIPLES.md — secties 3 (Config-First), 4 (Fail-Fast), 2 (DRY+SSOT)
[related-2]: docs/system/addendums/Addendum_ 3.8 Configuratie en Vertaal Filosofie.md — ConfigLoader/ConfigValidator/ConfigTranslator patroon
[related-3]: backend/config/__init__.py — referentie-implementatie van het drielaagse patroon

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 |  | Agent | Initial draft |