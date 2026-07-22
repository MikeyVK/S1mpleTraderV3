<!-- docs\development\issue432\planning.md -->
<!-- template=planning version=130ac5ea created=2026-07-18T20:23Z updated= -->
# Bug #432 Planning: Graceful Server Initialization

**Status:** DRAFT  
**Version:** 1.0  
**Last Updated:** 2026-07-18

---

## Scope

**In Scope:**
Aanpassen van TemplateScaffolder, HealthCheckTool en cli.py om server crashes bij configuratie fouten te voorkomen.
Behouden van normale operaties (valid boot) middels bestaande regressie-tests, en toevoegen van expliciete tests voor het gedegradeerde en fout-afhandelende gedrag.

**Out of Scope:**
Geen onnodige code refactoring buiten de betrokken bestanden, geen upgrade- of tracking systemen bouwen.

**Approved Strategy Constraints:**
- "Fail-Fast" voor infrastructuur-fouten (server crash).
- "Degraded Server" uitsluitend voor domein/config-fouten (`ConfigError`, `FileNotFoundError`).

**Quality Gates & Typing Obligations (General):**
- Strict typing verplicht (geen `Any` of `# type: ignore` in nieuwe code, stricte constructor injection).
- `run_quality_gates` (10.00/10 pylint + mypy pass) vereist voor elke cycle.

---

## Summary

Implementatieplan voor Bug #432: Graceful Server Initialization. Implementeert een fail-graceful patroon voor configuratie fouten in plaats van harde crashes.

---

## TDD Cycles


### Cycle 1: C1_TEMPLATE_VALIDATION

**Goal:** Weiger ongeldige template versies via de Scaffolder door een `ValidationError` te gooien.

**Deliverables:**
- `c1-scaffolder-update`: Update TemplateScaffolder.validate() to reject mismatched template versions.
- `c1-test-scaffolder`: Test for template version validation rejection.

**Tests & Impact:**
- Test gedrag: scaffold_artifact tool met ongeldige template versie gooit de juiste validatiefout.
- Impact: unit tests in `test_template_scaffolder.py`.

**Success Criteria:**
- `TemplateScaffolder` raise't expliciet een `ValidationError` bij een versie mismatch, voordat andere iteraties plaatsvinden.
- Geen exception bubble up naar server boot (de MCP tool wrapper vangt dit af).



### Cycle 2: C2_HEALTHCHECK_INJECTION

**Goal:** HealthCheckTool kan statisch een reden injecteren

**Deliverables:**
- `c2-health-tool-update`: Add override_status and override_reason to HealthCheckTool.
- `c2-test-health-tool`: Test for injected status and reason behavior.

**Tests & Impact:**
- Test gedrag: HealthCheckTool retourneert de injected constructor waarden.
- Impact: unit tests in `test_health_tools.py`.

**Success Criteria:**
- Tool geeft UNHEALTHY + injected reason terug als resultaat.

**Dependencies:** C1_TEMPLATE_VALIDATION


### Cycle 3: C3_CLI_DEGRADED_BOOT

**Goal:** Vang ConfigError in CLI en start DegradedMCPServer (Fail-graceful voor domeinfouten)

**Deliverables:**
- `c3-cli-update`: Catch ConfigError and FileNotFoundError in cli.py and boot DegradedMCPServer.
- `c3-test-cli`: Test degraded boot sequence on invalid config.

**Tests & Impact:**
- Test gedrag: CLI boot proces wanneer artifacts.yaml ontbreekt of corrupt is.
- Regressie: Normale valid-config boot moet ongewijzigd succesvol verlopen.
- Impact: integratie tests voor `cli.py` / `test_cli.py`.

**Success Criteria:**
- Bij `ConfigError` of `FileNotFoundError` blijft het proces draaien in degraded modus.
- Enige tool beschikbaar in deze modus is `health_check` met de bijbehorende error.

**Dependencies:** C2_HEALTHCHECK_INJECTION

## Related Documentation
None
---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-07-18 | Agent | Initial draft |