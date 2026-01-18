# Issue 56 — Slice 1 Gaps & Checklist (Harmoniseer Exceptions)

**Datum:** 2026-01-18  
**Status (git):** HEAD, working tree clean  
**Doel van dit document:** hard oordeel + concrete afvink/TODO-lijst om Slice 1 aantoonbaar “DONE” te krijgen volgens het fix-forward plan en de coding standards.

## 1) Slice 1 Definition of Done (bron: implementation plan)

Slice 1 ("Harmoniseer Exceptions") eist:
- **Single source of truth:** `mcp_server/core/exceptions.py` is leidend.
- **Geen parallel error-model:** `mcp_server/core/errors.py` verwijderen of refactoren zodat er geen alternatief exception-contract bestaat.
- `mcp_server/config/artifact_registry_config.py` gebruikt **geen lokale exceptions**, maar `core.exceptions.MCPError`-afgeleiden.

**Tests (verplicht):**
- Unit: exception types/messages (contract).
- Integration: tool/manager codepad dat errors produceert, zonder mocks die types maskeren.
- E2E: één scenario dat een config/template error triggert en als MCPError terugkomt.

## 2) Wat is al “OK” (bewijs/observaties)

- ✅ **Legacy module referenties weg:** repo-brede search naar `mcp_server.core.errors` levert **NO_MATCHES**.
- ✅ **Fixture mismatch opgelost:** repo-brede search naar `_temp_workspace` levert **NO_MATCHES**; [tests/integration/test_exception_propagation.py](../../../tests/integration/test_exception_propagation.py) gebruikt nu `temp_workspace`.
- ✅ **Registry gebruikt core exceptions:** [mcp_server/config/artifact_registry_config.py](../../../mcp_server/config/artifact_registry_config.py) importeert `ConfigError` uit `mcp_server.core.exceptions`.
- ✅ **Unit contract test aanwezig:** [tests/unit/core/test_exceptions.py](../../../tests/unit/core/test_exceptions.py) verifieert code/message/hints en inheritance.
- ✅ **Integration propagatie test aanwezig (manager-level):** [tests/integration/test_exception_propagation.py](../../../tests/integration/test_exception_propagation.py) verifieert `ConfigError`/`ValidationError` door `ArtifactManager` heen.

## 3) Kritische gaps (wat verhindert “Slice 1 DONE”)

### Gap A — E2E eis “komt als MCPError terug” is niet hard bewezen

Het plan vraagt een E2E scenario “dat een config/template error triggert en als MCPError terugkomt”.

Huidige situatie:
- Tool boundary gebruikt `ToolResult` (tekst + `is_error`) en niet een gestructureerde error met `code/hints`.
- `BaseTool` wrapt elke tool met `tool_error_handler` ([mcp_server/tools/base.py](../../../mcp_server/tools/base.py)), die exceptions **omzet naar `ToolResult.error(message)`** ([mcp_server/core/error_handling.py](../../../mcp_server/core/error_handling.py)).
- `ToolResult` heeft **geen velden** voor `code` of `hints` ([mcp_server/tools/tool_result.py](../../../mcp_server/tools/tool_result.py)).

Gevolg:
- Zelfs als intern `MCPError` gebruikt wordt, is het aan de client-kant niet aantoonbaar “MCPError contract preserved”; je hebt alleen een string.

**Waarom dit kritisch is:** Slice 1 gaat juist over één contract door alle lagen. Als de tool-laag het contract altijd “plat slaat” naar tekst, is Slice 1 inhoudelijk half.

### Gap B — Redundante error handling maakt contract inconsistent

- `ScaffoldArtifactTool.execute()` vangt zelf `ValidationError`/`ConfigError` en formatteert hints/file_path in tekst ([mcp_server/tools/scaffold_artifact.py](../../../mcp_server/tools/scaffold_artifact.py)).
- Tegelijkertijd is er een generieke `tool_error_handler` die ook exceptions afvangt en formatteert.

Gevolg:
- De manier waarop errors gepresenteerd worden verschilt per tool (sommige tools gebruiken alleen decorator; deze tool heeft eigen format).
- Dit maakt “één contract” aan de buitenkant lastiger te garanderen.

### Gap C — Coding standards (mandatory) niet consistent toegepast in Slice 1 kern

Volgens [docs/coding_standards/CODE_STYLE.md](../../../docs/coding_standards/CODE_STYLE.md) zijn o.a. **file headers** en **import-secties** mandatory.

Observaties:
- [mcp_server/core/exceptions.py](../../../mcp_server/core/exceptions.py) mist de verplichte file header template (met `@layer/@dependencies/@responsibilities`) en ook de “first line path” comment uit het voorbeeld.
- [mcp_server/adapters/filesystem.py](../../../mcp_server/adapters/filesystem.py) mist eveneens het verplichte header-format.

**Waarom dit telt voor Slice 1:** jouw kwaliteitsbaseline gebruikt deze docs als review-basis; als Slice 1 “critical” is, moeten kernfiles juist voorbeeldig zijn.

### Gap D — Type-hint discipline: validator signature niet volledig getypeerd

In [mcp_server/config/artifact_registry_config.py](../../../mcp_server/config/artifact_registry_config.py) is:
- `validate_initial_state(cls, v: str, info) -> str` waarbij `info` niet getypeerd is.

Volgens coding standards is “Full Type Hinting” mandatory; bovendien is dit een typisch mypy/pyright pijnpunt.

## 4) Slice 1 Checklist (af te vinken)

### 4.1 Must-have (blokkerend voor DONE)

- [ ] **E2E error contract proof:** voeg één E2E test toe die via de tool-laag (`ScaffoldArtifactTool`) een config/template error triggert en hard verifieert dat het “unified error contract” behouden blijft.
  - Acceptatie: test faalt als error code/hints niet observeerbaar zijn (dus niet alleen `"❌" in text`).
- [ ] **Beslis en documenteer tool-level contract:** kies één van:
  - (a) `ToolResult` uitbreiden met `error_code` + `hints` (+ evt. `file_path`), of
  - (b) eenduidige string-encoding afspreken (maar dan expliciet in standards/plan opnemen), of
  - (c) exceptions doorlaten tot MCP transportlaag (en daar structureren).
  - Acceptatie: alle tools volgen dezelfde contractvorm.
- [ ] **Verwijder dubbele error-formatting paden:** kies of tools zelf formatten, of via `tool_error_handler` (niet allebei).
  - Acceptatie: 1 bron van waarheid voor tool error formatting.

### 4.2 Should-have (sterk aanbevolen, review-gate)

- [ ] **Coding standards compliance (Slice 1 kern):** breng file headers + import-secties in lijn met [docs/coding_standards/CODE_STYLE.md](../../../docs/coding_standards/CODE_STYLE.md).
  - Target files minimaal: [mcp_server/core/exceptions.py](../../../mcp_server/core/exceptions.py), [mcp_server/adapters/filesystem.py](../../../mcp_server/adapters/filesystem.py).
- [ ] **Volledige type hints in validators:** type de `info` parameter (Pydantic v2 `ValidationInfo`) of documenteer een expliciete uitzondering.

### 4.3 Nice-to-have (mag in Slice 2/3, maar noteer expliciet)

- [ ] **“hints” semantiek normaliseren:** `hints` is nu zowel blockers/recovery/general tips. Overweeg een eenduidig model (of expliciete naming) zodat downstream tooling beter kan formatteren.

## 5) Eind-oordeel (kort)

- **Architectuur-richting:** goed (unified exceptions, legacy errors refs weg).
- **Bewijslast vs. plan:** nog niet compleet voor Slice 1 “DONE” zolang het E2E/tool-boundary contract niet aantoonbaar hetzelfde exception-contract preserveert.
- **Kwaliteit vs. coding standards:** kernfiles missen mandatory style-headers; dat is een review blocker als je baseline strikt is.
