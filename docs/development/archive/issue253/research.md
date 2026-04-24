<!-- docs\development\issue253\research.md -->
<!-- template=research version=8b7bb3ab created=2026-03-02T15:01Z updated= -->
# Issue #253: RunTestsTool refactor — pytest-agnostic design + SOLID alignment

**Status:** DRAFT  
**Version:** 1.0  
**Last Updated:** 2026-03-02

---

## Purpose

Fungeert als architectureel fundament voor planning en TDD van issue #253. Verhindert dat gap-fixes ad-hoc in de bestaande monolithische structuur worden geplakt.

## Scope

**In Scope:**
RunTestsTool + module-level functies _run_pytest_sync en _parse_pytest_output (mcp_server/tools/test_tools.py); QAManager als referentiemodel (mcp_server/managers/qa_manager.py); SOLID-analyse van beide tools; Gap 1 (summary_line JSON vs text inconsistentie), Gap 2 (pytest exit code 4 niet gedetecteerd als hard error), Gap 3 (coverage/Gate 6 niet bereikbaar); pytest-agnostic principe op tool-laag niveau; inventaris van herbruikbare QAManager-componenten richting issue #255.

**Out of Scope:**
Scope-aware rerun optimization en context fingerprinting (issue #255); gedeelde ScopeResolver/BaselineManager extractie (issue #255); coverage threshold configuratie buiten pyproject.toml; integratie met CI/CD pipeline.

## Prerequisites

Read these first:
1. Issue #251 gesloten: QAManager volledig afgewerkt, Gate 4c geïmplementeerd (PR #256, SHA 56be0fb)
2. Issue #253 aangemaakt met drie geïdentificeerde gaps (Gap 1/2/3)
3. Issue #255 aangemaakt als umbrella voor gedeelde scope-optimalisatie
---

## Problem Statement

RunTestsTool (test_tools.py) bundelt drie verantwoordelijkheden in één bestand — subprocess management, output parsing en tool-orchestratie — en koppelt de tool-laag hard aan pytest-specifieke CLI-details. Dit veroorzaakt drie concrete correctheidsbugs (Gap 1–3 uit issue #253) en blokkeert hergebruik van de SOLID-gelaagde architectuur die in QAManager/issue #251 is gebouwd. Het eerste teken van drift is dat de tool zelf pytest-aannames bevat in plaats van achter een runner-abstractie te zitten.

## Research Goals

- Identificeer alle SOLID-schendingen in de huidige RunTestsTool implementatie
- Formuleer het pytest-agnostic principe als architectureel anker voor de tool-laag
- Breng in kaart welke componenten uit QAManager direct herbruikbaar zijn
- Definieer de doelarchitectuur (PytestManager) die de drie gaps uit #253 structureel oplost
- Bepaal de afbakening tussen issue #253 (bug fixes + refactor) en issue #255 (gedeelde orchestrator)

---

## Background

Na de afronding van issue #251 is QAManager uitgegroeid tot een volledig SOLID-gelaagde manager (1235 regels) met duidelijke scheiding tussen scope-resolutie, subprocess-uitvoering, output-parsing en lifecycle-mutatie. RunQualityGatesTool delegeert volledig aan QAManager en is zelf slechts ~40 regels coördinatiecode. RunTestsTool is nooit meegegroeid: het bundelt subprocess-aanroep (_run_pytest_sync als module-level functie), pytest-output-parsing (_parse_pytest_output als module-level functie) en tool-orchestratie in één bestand zonder injectable manager. De drie gaps in issue #253 zijn directe symptomen van deze architecturele schuld, niet op zichzelf staande bugs.

---

## Findings

**SRP-schending (Single Responsibility Principle):**
test_tools.py heeft drie verantwoordelijkheden: (1) subprocess management via _run_pytest_sync, (2) pytest output parsing via _parse_pytest_output, (3) tool-orchestratie in RunTestsTool.execute(). Elke verantwoordelijkheid moet een afzonderlijke klasse/module zijn.

**OCP-schending (Open/Closed Principle):**
Om Gap 3 (coverage) toe te voegen moeten _build_cmd, _parse_pytest_output én execute() simultaan gewijzigd worden. Een gesloten tool-laag zou alleen de manager-interface aanroepen.

**DIP-schending (Dependency Inversion Principle):**
execute() roept asyncio.to_thread(_run_pytest_sync, ...) direct aan. Er is geen PytestManager-abstractie waartegen gemockt kan worden. Gap 2-tests vereisen nu subprocess-niveau mocking.

**pytest-agnostic principe (eerste driftindicator):**
De tool-laag (quality_tools.py, test_tools.py) MAG geen framework-specifieke CLI-aannames bevatten. RunQualityGatesTool weet niets over ruff/mypy/pylint — dat zit in QAManager en quality.yaml. RunTestsTool daarentegen bevat pytest-regex-patterns, xdist-aannames en pytest exit-code-semantiek direct in de tool. Dit is het eerste teken van drift: zodra een tweede test-runner (bijv. unittest, ward) of een andere pytest-configuratie wordt overwogen, moet de tool-klasse gewijzigd worden.

**Gap 1 (summary_line bug) — structurele oorzaak:**
De fallback-logica voor summary_line zit in execute() i.p.v. in een DTO-returnend parser-object. Een ParsedTestRun Pydantic DTO (geïnspireerd op ViolationDTO/QualityGateResult uit QAManager) zou garanderen dat summary_line altijd consistent is — door validatie op DTO-niveau, niet door ad-hoc post-parsing correctie.

**Gap 2 (exit code 4) — structurele oorzaak:**
Er is geen exit-code-interpretatie-laag. QAManager valideert subprocess return codes per gate. RunTestsTool ignoreert de return code volledig (de _ in stdout, stderr, _ = await ...). Een PytestManager zou exit codes 0/1/2/4/5 semantisch interpreteren.

**Gap 3 (coverage/Gate 6) — structurele oorzaak:**
Coverage is een optionele run-mode, niet een extra flag. In de doelarchitectuur is dit een parameter op PytestRunConfig (Pydantic model) die de manager interpreteert. De tool-laag kent alleen scope + coverage=bool.

**Herbruikbare QAManager-componenten:**
- Subprocess runner pattern (venv-path, CREATE_NO_WINDOW, Popen met timeout) → direct overnemen in PytestManager._run_subprocess()
- _format_summary_line / _build_compact_result scheiding (rich internal result vs compact tool payload) → tegenhanger voor ParsedTestRun DTO
- ViolationDTO als DTO-patroon → inspiratie voor FailureDTO en TestRunResultDTO
- Pydantic DTO contract voor tool input/output → RunTestsInput is al goed, alleen de manager-laag ontbreekt

**Doelarchitectuur:**
RunTestsTool (coördinator, ~40 regels) → PytestManager (subprocess, parsing, exit-code-interpretatie, coverage) → ParsedTestRun DTO (Pydantic). PytestManager weet alles over pytest; de tool weet niets.

## Open Questions

- ❓ Moet PytestManager als aparte module in mcp_server/managers/ landen (spiegelend aan qa_manager.py)?
- ❓ Wat is de minimale interface van PytestManager zodat issue #255 later een gedeelde BaseTestRunner-abstractie kan introduceren?
- ❓ Moet ParsedTestRun DTO in mcp_server/config/ (naast quality_config.py) of in een nieuw mcp_server/config/test_config.py?
- ❓ Gap 2: welke exit codes moeten als hard error geclassificeerd worden? (pytest: 0=ok, 1=failures, 2=interrupted, 3=internalerror, 4=usageerror, 5=nocollected)
- ❓ Coverage threshold: hardcoded 90 (zoals in pyproject.toml) of via .st3/quality.yaml Gate 6 definitie?


## Related Documentation
- **[pytest exit codes: https://docs.pytest.org/en/stable/reference/exit-codes.html][related-1]**
- **[pytest-cov usage: https://pytest-cov.readthedocs.io/en/latest/][related-2]**

<!-- Link definitions -->

[related-1]: pytest exit codes: https://docs.pytest.org/en/stable/reference/exit-codes.html
[related-2]: pytest-cov usage: https://pytest-cov.readthedocs.io/en/latest/

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 |  | Agent | Initial draft |