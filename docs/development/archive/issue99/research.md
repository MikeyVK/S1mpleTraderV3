# Issue 99 — Claude tool schema regressies (research)

## Observatie
Claude crasht/valt om bij sommige tool-calls wanneer de tool `inputSchema` een *geneste/indirecte* JSON Schema structuur bevat (met name `$defs` + `$ref`).

In deze repo worden tool schemas automatisch gegenereerd via Pydantic v2 (`args_model.model_json_schema()`) en zonder verdere "normalisatie" doorgegeven via MCP (`Tool(inputSchema=t.input_schema)`).

## Snelle scan (2026-01-08)
We hebben alle geregistreerde tools en hun `input_schema` bekeken op JSON-schema constructs die vaak problemen geven bij model-clients:

- Aantal tools: **47**
- Tools met `$ref`/`$defs`: **1/47** → alleen **`safe_edit_file`**
- Meest complexe schemas (veel `anyOf`/nested objects) bovenaan: `safe_edit_file`, `scaffold_component`, `update_issue`, …

## Hypothese (root cause)
- Zodra een tool-input model *geneste* Pydantic modellen bevat (zoals `LineEdit`, `InsertLine` in `safe_edit_file`), genereert Pydantic JSON Schema met `$defs` en verwijzingen (`$ref`).
- Sommige Claude tool-call integraties kunnen deze `$ref` niet goed dereferencen (of crashen outright), waardoor:
  - de tool niet bruikbaar wordt, of
  - de client een onvolledig/incorrect beeld krijgt van de parameters.

## Waar het in de code gebeurt
- MCP publiceert tools in [mcp_server/server.py](../../../mcp_server/server.py) door `inputSchema=t.input_schema` direct te gebruiken.
- `BaseTool` default `input_schema` is `args_model.model_json_schema()`.

## Nette oplossingsrichting (geen hacks)
1. **Schema normaliseren centraal** (aanbevolen):
   - Post-process de JSON Schema vóór we hem publiceren.
   - Inline alle `$ref` (dereference) en verwijder `$defs`.
   - Optioneel: vereenvoudig `anyOf`-patronen die alleen `T | null` uitdrukken naar `type: [T, "null"]` (dit is nog steeds geldige JSON Schema en is voor sommige clients eenvoudiger).

2. **Tool-inputs overal plat maken** (minder ideaal):
   - Geen nested Pydantic models gebruiken.
   - Werkt, maar kost veel handwerk en verliest type-veiligheid/herbruikbaarheid.

## Next
- Reproduceren: minimal test/schema snapshot die aantoont dat `$ref/$defs` aanwezig is bij nested modellen.
- Implementeren: `normalize_schema_for_llm(schema) -> schema` + unit tests.
- Valideren: check welke andere tools nog stuk gaan door `anyOf`/optionals.
