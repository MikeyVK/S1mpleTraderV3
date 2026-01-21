# Unified Research: Template-Driven Validation & Content-Aware Editing

**Issues:** #120 + #121 (Integrated System)  
**Status:** 🔬 Research  
**Version:** 1.0  
**Date:** 2026-01-21

---

## Executive Summary

Issue #120 and #121 zijn geen losstaande features maar twee aspecten van hetzelfde systeem: **template-driven artifact lifecycle management**. Templates zijn de Single Source of Truth voor wat een artifact IS. Validatie, error messages, en content-aware editing moeten allemaal uit deze SSOT afleiden.

**Kernprincipe:** Als een template definieert wat nodig is om een artifact te CREËREN, moet diezelfde informatie beschikbaar zijn om een artifact te VALIDEREN en te EDITEN.

---

## Problem Space Analysis

### Huidige Situatie: Gefragmenteerde Flows

**Bij Scaffolding (Creatie):**
1. Agent roept `scaffold_artifact(type, **context)` aan
2. TemplateScaffolder.validate() controleert `required_fields` uit artifacts.yaml
3. Template wordt gerenderd met Jinja2
4. Als variabele ontbreekt → cryptische `UndefinedError: 'name' is undefined`
5. Agent moet raden wat er nodig is

**Bij Editing (Bestaand Bestand):**
1. Agent wil gescaffold bestand aanpassen
2. Geen tool beschikbaar die template-structuur begrijpt
3. safe_edit_file werkt op tekst-niveau, niet op artifact-semantiek
4. Validatie gebeurt niet (Issue #121 scope)

**Problemen:**
- **Dubbele waarheid**: artifacts.yaml `required_fields` ≠ template variabelen
- **Late feedback**: Errors pas bij rendering, niet bij validatie
- **Geen symmetrie**: Creatie kent template, editing kent template niet
- **Lost context**: Gescaffold bestand weet niet van welke template het komt (tot Issue #120 Phase 0 - metadata)

### Wat Ontbreekt

**Voor Agents:**
1. **Pre-flight checks**: "Wat heb ik nodig voordat ik scaffold?"
2. **Gerichte errors**: "Je mist field X, hier is het schema + voorbeeld"
3. **Discovery**: "Welke artifacts kan ik maken? Wat verwachten ze?"
4. **Structured editing**: "Pas dit DTO field aan zonder syntax te breken"

**Voor Systeem:**
1. **Template introspection**: Automatisch detecteren welke variabelen een template gebruikt
2. **Schema generation**: Van template → schema (niet handmatig in artifacts.yaml)
3. **Metadata tracking**: Elk gescaffold bestand weet van welke template + versie het komt
4. **Content-aware validation**: Editten moet template-regels respecteren

---

## Core Components Analysis

### 1. Templates als Single Source of Truth

**Wat Templates Definiëren:**
- **Structuur**: Welke secties, welke volgorde
- **Variabelen**: Welke data nodig is (required vs optional via {% if %})
- **Validatie regels**: TEMPLATE_METADATA met strict rules
- **Type informatie**: Impliciet via usage ({{ name }} suggereert string)

**Bestaande Template Infrastructure:**
- `TemplateAnalyzer`: Kan al AST parsen, variabelen extraheren
- `extract_jinja_variables(path)`: Geeft alle undeclared variabelen
- TEMPLATE_METADATA systeem: YAML frontmatter met validation rules
- Inheritance support: `{% extends %}` met metadata merging

**Wat Template Analyzer NOG NIET Doet:**
- Required vs Optional detectie ({% if var %} = optional)
- Default values identificeren ({{ var | default(...) }})
- Type inference (primitief mogelijk via usage patterns)
- Schema representatie (machine-readable format)

### 2. Artifact Registry (artifacts.yaml)

**Huidige Rol:**
- Maps type_id → template_path
- Definieert `required_fields` (HANDMATIG - kan driften!)
- Definieert `optional_fields` (HANDMATIG - kan driften!)
- Output type, file extension, test generation flags

**Probleem - DRY Violation:**
```yaml
# artifacts.yaml
required_fields:
  - name
  - description

# components/dto.py.jinja2
{{ name }}  # Gebruikt name
{{ description }}  # Gebruikt description
{{ fields }}  # GEBRUIKT fields - maar niet in required_fields!
```

**Wat Registry WEL Moet Blijven Doen:**
- Type mapping (dto → components/dto.py.jinja2)
- Output configuratie (file extension, paths)
- Metadata (versie, beschrijving artifact types)

**Wat Registry NIET Meer Moet Doen:**
- `required_fields` / `optional_fields` → AFLEIDEN uit template!
- `example_context` → Kan driften, schema is genoeg (user feedback)

### 3. Validation Flow (Huidig vs Gewenst)

**User Correctie: Wat wordt gevalideerd?**
- **Agent input**: Tool call parameters tegen template schema → FAIL FAST
- **Templates zelf**: NIET valideren - templates zijn getest voor productie
- **Gerenderde output**: 
  - Bij scaffolding: NEE (template getest = output OK)
  - Bij editing: JA (check dat mutatie structuur behoud)

**Huidig (Issue #120 Probleemstelling):**
```
scaffold_artifact(dto, name="X")
  ↓
TemplateScaffolder.validate()
  ├─ Check: required_fields uit artifacts.yaml (kan driften!)
  │  └─ Mist 'description' → ValidationError (minimale hint)
  ↓
render_template()
  └─ Jinja2 rendering
     └─ {{ fields }} undefined → UndefinedError (cryptisch)
```

**Gewenst (Issue #120 Oplossing):**
```
scaffold_artifact(dto, name="X")
  ↓
[FAIL FAST VALIDATION]
TemplateScaffolder.validate()
  ├─ Extract schema uit template AST (via meta.find_undeclared_variables)
  │  └─ Required: [name, description]
  │  └─ Optional: [fields, frozen]
  ├─ Vergelijk provided vs required
  │  └─ Mist 'description' → ValidationError met:
  │     - Schema (wat verwacht template)
  │     - Status (✓ name, ✗ description)
  ↓
render_template()
  └─ Template rendering (geen validation - template is getest)
  └─ Success → File + metadata
```

**Resultaat:**
- **Fail fast**: Errors vóór rendering (agent input validatie)
- **Rich hints**: Agent ziet exact wat ontbreekt (flat schema, geen nested)
- **No duplication**: Schema komt uit template (SSOT)
- **No template validation**: Templates zijn pre-productie getest

### 4. Scaffold Metadata (Phase 0 - Completed)

**Wat Phase 0 Opleverde:**
- `# SCAFFOLD:` comment systeem in gegenereerde files
- Metadata: template, version, created, updated, path
- ScaffoldMetadataParser: Kan metadata lezen/schrijven
- scaffold_metadata.yaml: Patterns per bestandstype

**Gebruik Voor Issues #120 + #121:**
- **Discovery**: Find all scaffolded files (`grep SCAFFOLD:`)
- **Template mapping**: File → template relatie bekend
- **Staleness detection**: Template versie vs file versie
- **Content-aware editing**: Weet welke template-regels gelden

**Voorbeeld Metadata:**
```python
# SCAFFOLD: template=dto version=1.0 created=2026-01-21T10:30:00Z path=backend/dtos/trade_signal.py
```

Nu weten we: Dit bestand kwam van `dto` template v1.0, dus validatie-regels van die template gelden.

---

## Issue Scope Definition

### Issue #120: Template-Driven Validation & Self-Documenting Errors

**Wat Het Oplost:**
1. **Voor Agents**: Duidelijke feedback wat nodig is om artifact te scaffolden
2. **Voor Systeem**: Validatie gebaseerd op template-waarheid, niet handmatige config

**Deliverables:**
1. **Template Introspection** (gebruikt Jinja2 `meta.find_undeclared_variables`):
   - Parse template AST → detect all variables
   - Conditional detection ({% if var %} = optional)
   - Default detection ({{ var | default(...) }} = optional)
   - Rest = required (conservatief)

2. **Schema Generation**:
   - Automatisch schema uit template genereren
   - Format: `{"required": [...], "optional": [...]}` (FLAT - geen nesting)
   - Cache schema results (templates veranderen zelden)

3. **Enhanced Error Messages**:
   - ValidationError met flat schema hints bij missing fields
   - No example_context (kan driften)
   - Status indicators (✓/✗ per field)

4. **Query Tool** (Mogelijk - later fase):
   - `get_artifact_schema(type)` → schema only
   - Agent kan vragen: "Wat heb ik nodig voor dto?"
   - Returns template-derived schema (niet handmatig)

**Niet In Scope #120:**
- Content-aware editing (dat is #121)
- Type validation (alleen aanwezigheid van velden)
- Nested schema validation (dat komt later)

### Issue #121: Content-Aware Editing van Gescaffold Files

**Wat Het Oplost:**
1. **Voor Agents**: Edit gescaffold files zonder structure te breken
2. **Voor Systeem**: Edits volgen template-regels automatisch

**Deliverables:**
1. **Discovery Capability**:
   - Find scaffolded files by template type
   - Query: "Geef alle dto files" → parsed SCAFFOLD metadata
   - Staleness check: template versie vs file versie

2. **Template-Aware Editing**:
   - Weet van welke template file komt (via metadata)
   - Valideer edit tegen template-structuur
   - Voorbeeld: DTO field toevoegen → check tegen template

3. **VS Code Integration** (Als nodig):
   - Position/Range API voor exacte edits
   - ScaffoldEdit extensions voor structured mutations

4. **Validation on Edit**:
   - Hergebruik template introspection uit #120
   - Check: blijft file valid volgens template?
   - Error hints consistent met scaffolding errors

**Overlap Met #120:**
- **Shared**: Template introspection, schema generation
- **Shared**: Validation logic (template = SSOT)
- **Verschil #120**: Bij creatie - valideer context
- **Verschil #121**: Bij edit - valideer mutatie

**Niet In Scope #121:**
- Scaffolding nieuwe files (dat is bestaand)
- Non-scaffolded files (alleen files met metadata)
- Refactoring tools (rename, extract)

---

## Integrated Architecture Vision

### Unified Template Service

**Conceptueel (Descriptief, Geen Code):**

Een centrale service die template-kennis beschikbaar maakt:

**Input**: Template path of artifact type_id  
**Output**: Schema, validation rules, examples, metadata

**Capabilities:**
1. **Schema Extraction**: Parse template → required/optional vars
2. **Example Provision**: Return example_context from artifacts.yaml
3. **Validation**: Check context/edit against template requirements
4. **Discovery**: List all templates, find files by template

**Consumers:**
- TemplateScaffolder (bij creatie validatie)
- safe_edit_file (bij edit validatie - Issue #121)
- get_artifact_schema tool (query interface)
- Content-aware edit tool (structured mutations)

### Validation Points

**1. Pre-Scaffold Validation (Issue #120):**
- Agent geeft context → validate tegen template schema
- Error: Toon schema + example + status
- Success: Proceed to rendering

**2. Template Rendering (Huidige Catch):**
- Jinja2 rendering
- Error: Wrap UndefinedError met schema hints
- Success: File created met metadata

**3. Post-Scaffold Metadata (Phase 0):**
- Write `# SCAFFOLD:` comment
- Track: template, version, timestamp, path
- Enable discovery later

**4. Pre-Edit Validation (Issue #121):**
- Agent wil file editen → load metadata
- Validate: Blijft structure consistent?
- Error: Toon template requirements
- Success: Apply edit

**5. Post-Edit Validation (Issue #121):**
- Check: File nog steeds valid?
- Update metadata: updated timestamp
- Success: Edit complete

### Data Flow

**Creatie (Issue #120 Scope):**
```
Agent: scaffold_artifact(dto, name="Signal")
  ↓
[PRE-VALIDATION]
  Extract schema: dto template → {required: [name, desc], optional: [fields]}
  Compare: provided={name} vs required={name, desc}
  Error: Missing 'desc' + hints (schema + example)
  ↓
Agent: scaffold_artifact(dto, name="Signal", description="Trading signal")
  ↓
[RENDER]
  Template render met context
  Success → File + metadata
```

**Editing (Issue #121 Scope):**
```
Agent: Wil DTO field toevoegen
  ↓
[DISCOVERY]
  Find: trade_signal.py heeft metadata: template=dto v1.0
  Load: dto template schema
  ↓
[PRE-EDIT VALIDATION]
  Proposed edit: Add field to fields list
  Check: Blijft binnen template structure?
  Success → Apply edit
  ↓
[POST-EDIT VALIDATION]
  Parse: File nog steeds valid Python?
  Check: Metadata nog accurate?
  Update: updated=2026-01-21T14:30:00Z
```

---

## Requirements Analysis

### Functional Requirements

**FR-1: Template Introspection**
- Systeem MOET template AST kunnen parsen
- Systeem MOET undeclared variabelen kunnen detecteren
- Systeem MOET required vs optional kunnen onderscheiden
- Systeem MOET default values kunnen herkennen

**FR-2: Schema Generation**
- Systeem MOET schema uit template kunnen genereren
- Schema formaat MOET machine-readable zijn
- Schema MOET cachebaar zijn (templates veranderen zelden)
- Schema invalidatie MOET automatisch bij template wijziging

**FR-3: Enhanced Errors**
- Errors MOETEN template-derived schema tonen
- Errors MOETEN example context tonen (uit artifacts.yaml)
- Errors MOETEN status indicators tonen (✓/✗ per field)
- Errors MOETEN dynamisch zijn (geen hardcoded values)

**FR-4: Metadata Tracking** (Phase 0 - Done)
- Files MOETEN template metadata bevatten
- Metadata MOET parseable zijn
- Metadata MOET non-intrusive zijn (comments)

**FR-5: Discovery**
- Systeem MOET scaffolded files kunnen vinden
- Systeem MOET files kunnen groeperen by template
- Systeem MOET staleness kunnen detecteren

**FR-6: Content-Aware Editing**
- Systeem MOET template van file kunnen afleiden (via metadata)
- Edits MOETEN gevalideerd worden tegen template
- Edit errors MOETEN consistent met scaffold errors zijn

### Non-Functional Requirements

**NFR-1: Performance**
- Template parsing mag niet bij elke validatie (cache!)
- Schema generation < 100ms per template
- Cache invalidation alleen bij template change

**NFR-2: Consistency**
- ALLE validation errors gebruiken zelfde hint format
- Schema source = template (SSOT)
- Geen duplication tussen artifacts.yaml en templates

**NFR-3: Maintainability**
- Template changes → auto schema update
- Geen handmatige sync tussen components
- DRY principe gerespecteerd

**NFR-4: Backward Compatibility**
- Bestaande templates blijven werken
- Bestaande gescaffolde files blijven geldig
- Phase 0 metadata optioneel voor legacy files

---

## Open Questions

### Q1: Required vs Optional Detection Algorithm

**Vraag**: Hoe detecteren we betrouwbaar of een template variabele required of optional is?

**Standaard Jinja2 Tooling Beschikbaar:**
- Jinja2 heeft `jinja2.meta.find_undeclared_variables(ast)` - officiële API
- Huidig systeem gebruikt dit al in TemplateAnalyzer.extract_jinja_variables()
- Geeft ALLE undeclared variabelen - geen required/optional onderscheid

**Patronen Te Detecteren:**
- `{{ name }}` → Required (unconditional use)
- `{% if fields %}{{ fields }}{% endif %}` → Optional (conditional)
- `{{ fields | default([]) }}` → Optional (default filter)
- `{% for f in fields %}` → Required? Optional? (loop over undefined = error)

**Mogelijke Aanpak:**
1. Basis: Use `meta.find_undeclared_variables()` voor lijst
2. Parse AST voor If nodes → vars in condition test = optional
3. Parse AST voor Filter nodes → vars met default filter = optional  
4. Conservatieve fallback: Onbekend = required (veiliger voor agent)

**BESLISSING (User):** Start simpel (If nodes + default filters only), extend iteratief

### Q2: Schema Representation Format

**Vraag**: Hoe representeren we schema voor MCP tools?

**MCP Context:**
- MCP tool responses moeten begrijpelijk zijn voor agents (Claude)
- Issue #99 toonde: nested schemas kunnen problematisch zijn voor Claude
- Simpele, platte structures werken beter

**Opties:**
1. **Simple dict**: `{"required": [...], "optional": [...]}`  
2. **JSON Schema**: Volledige spec met types, patterns
3. **Hybrid**: Required/optional + descriptions (geen types)

**Trade-offs:**
- Simple: Snel, werkt goed met Claude, geen types
- JSON Schema: Krachtig maar complex te genereren + nested problemen
- Hybrid: Balans, maar custom format

**BESLISSING (User):** Start simpel (flat dict), MCP tool schema moet zonder gedoe begrepen worden

### Q3: Scope van Content-Aware Editing

**Vraag**: Hoe "template-aware" moet editing zijn?

**Scenarios:**
1. **Minimal**: Valideer alleen dat file nog valid is na edit
2. **Structural**: Check dat edit binnen template structure blijft
3. **Semantic**: Understand artifact semantics (DTO field = bepaalde syntax)

**Voorbeeld - DTO Field Toevoegen:**
- Minimal: File parse-t nog als Python ✓
- Structural: Field staat in fields lijst ✓  
- Semantic: Field heeft name/type/description attributen ✓

**BESLISSING (User):** Semantic validation - templates definiëren field STRUCTUUR, niet inhoud
- Template zegt: "DTO field MOET name/type/description hebben"
- Template zegt NIET: "DTO MOET exact deze 5 fields hebben"
- Inhoud (welke fields) = creatief proces, structure (hoe fields eruitzien) = template regel
- Voorbeeld: `example` field in DTO is eigen toevoeging (self-documenting code) - moet wel aan structure voldoen

### Q4: Integration met Bestaande safe_edit_file

**Vraag**: Nieuwe tool of extend safe_edit_file?

**Optie A - Extend safe_edit_file:**
- Detecteer scaffolded files via metadata
- Auto-enable template validation als metadata present
- Transparant voor agent

**Optie B - Nieuwe Tool:**
- `scaffold_edit(path, mutations)` specifiek voor scaffolded files
- Expliciete template-aware editing
- Duidelijker intent

**Trade-offs:**
- Extend: Minder tools, maar meer complexity in één tool
- New: Cleaner separation, maar meer tools

**BESLISSING (User):** Nieuwe tool - voorkomt breuk van safe_edit

### Q5: Artifact Type Inference

**Vraag**: Kan systeem artifact type afleiden uit file zonder metadata?

**Use Cases:**
- Legacy files (geen SCAFFOLD metadata)
- Handmatig gecreëerde files die template pattern volgen
- Migration scenario

**Heuristics:**
- File path matching (backend/dtos/*.py → dto?)
- Content analysis (class X(BaseModel) → dto?)
- Import patterns (from backend.core.interfaces → worker?)

**BESLISSING (User):** GEEN inference - legacy files zijn niet gescaffold
- Als retrospectieve validatie nodig → aparte slag (niet standaard tooling)
- Scaffold metadata = vereiste voor template-aware features

---

## Success Criteria

### Issue #120 Success Metrics

**Agent Experience:**
- ✅ Agent krijgt schema + example bij missing field error
- ✅ Agent kan pre-flight check doen (query schema before scaffold)
- ✅ Error messages zijn actionable (niet cryptisch)
- ✅ Geen duplication in feedback (schema komt uit template)

**System Quality:**
- ✅ No hardcoded values in error messages
- ✅ Template changes → error messages update auto
- ✅ DRY principle: schema source = template only
- ✅ Performance: Schema generation cached, fast

**Measurable:**
- Reduction in "invalid scaffold" attempts (agent gets it right first time)
- Error message completeness (contains schema + example)
- Template-to-schema sync (zero drift)

### Issue #121 Success Metrics

**Agent Experience:**
- ✅ Agent kan scaffolded files vinden by template type
- ✅ Edit errors consistent met scaffold errors (zelfde hints)
- ✅ Structured edits mogelijk (niet alleen text manipulation)
- ✅ Template violations detected before file corruption

**System Quality:**
- ✅ Metadata tracking accurate (updated timestamps)
- ✅ Template staleness detectable (version mismatch)
- ✅ Validation reuses #120 infrastructure (no duplication)

**Measurable:**
- Edit success rate for scaffolded files
- Template violation detection rate
- Metadata accuracy (% files with correct metadata)

---

## Dependencies & Risks

### Dependencies

**Internal:**
- Phase 0 (Scaffold Metadata) - ✅ COMPLETE
- TemplateAnalyzer - ✅ EXISTS (needs extension)
- TemplateScaffolder - ✅ EXISTS (needs enhancement)
- safe_edit_file - ✅ EXISTS (needs integration)

**External:**
- Jinja2 AST API (stable)
- VS Code API (if Position/Range needed for #121)

### Risks

**R1: Algorithm Complexity**
- **Risk**: Required/optional detection complex, edge cases
- **Mitigation**: Start conservative (simple If detection), extend iteratively
- **Impact**: Medium - affects error quality

**R2: Performance**
- **Risk**: Template parsing on every validation = slow
- **Mitigation**: Aggressive caching, invalidation only on template change
- **Impact**: Low - templates change rarely

**R3: Backward Compatibility**
- **Risk**: Changes break existing templates/files
- **Mitigation**: Phase 0 metadata optional, graceful degradation
- **Impact**: Low - additive features

**R4: Scope Creep**
- **Risk**: Issues #120 + #121 too large as single unit
- **Mitigation**: Clear phase boundaries, incremental delivery
- **Impact**: High - affects timeline

---

## Implementation Strategy

### Phase Boundaries (Workflow Fases)

**Research Phase** (CURRENT):
- Analyse probleem space
- Identify components
- Define scope boundaries
- Document what exists vs what's needed
- ✅ Dit document

**Design Phase**:
- Ontwerp template introspection algoritme
- Definieer schema format
- Specify validation integration points
- Define tool interfaces (if new tools needed)

**TDD Phase**:
- Implement template introspection
- Implement schema generation
- Implement enhanced error formatting
- Implement discovery (if #121 in scope)
- Implement edit validation (if #121 in scope)

**Integration Phase**:
- Connect to TemplateScaffolder
- Connect to safe_edit_file (if applicable)
- End-to-end testing
- Performance validation

**Documentation Phase**:
- Update agent.md
- Document new capabilities
- Create examples
- Update architecture docs

### Incremental Delivery Options

**Option A - Sequential (#120 → #121):**
1. Complete #120 (validation + errors)
2. Then #121 (editing)
3. Clean separation, easier to manage

**Option B - Integrated Foundation:**
1. Build shared infrastructure (introspection + schema)
2. Apply to both use cases simultaneously
3. More efficient, but higher initial complexity

**Recommendation**: Depends on scope decision - als #121 uitgesteld kan, doe Option A.

---

## Conclusion

Issues #120 en #121 vormen een **coherent system** voor template-driven artifact lifecycle:

**#120 = Creatie**: Valideer dat agent de juiste dingen geeft  
**#121 = Mutatie**: Valideer dat agent de juiste dingen aanpast

**Kern Insight**: Template is SSOT voor beide. Als we template introspection goed bouwen, gebruikt ALLES dezelfde waarheid.

**Next Steps:**
1. **Scope Decision**: #120 + #121 samen of sequentieel?
2. **Design Phase**: Algorithms, formats, interfaces
3. **TDD Implementation**: Build incrementally, test-first

**Success = Agent workflow efficiency**:
- Minder trial-and-error bij scaffolding
- Betere errors (actionable, niet cryptisch)
- Content-aware editing (templates blijven gerespecteerd)
