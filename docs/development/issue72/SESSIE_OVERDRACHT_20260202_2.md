# Sessie Overdracht - 2 februari 2026 (2)

**Branch:** `feature/72-template-library-management`
**Issue:** #72 Template Library Management
**Date:** 2026-02-02
**Focus:** Validation schema extraction vs tier3 macro imports; prepare for final whitespace review scaffolds
**Status:** Repo clean; prior accidental edits reverted (stashed)

---

## Context / Aanleiding
Tijdens het voorbereiden van een “final whitespace check” wilde je 7 concrete CODE outputs scaffolden in `.st3/`:
- 6 concrete templates: worker, dto, service, tool, schema, generic
- worker in 2 varianten: sync + async

Bij het proberen te scaffolden via de MCP tool ontstond een validatiefout:
- `Missing required fields for worker: di, lifecycle, log_enricher, p_async, p_logging, translator`

Dat is problematisch omdat dit **geen agent-input velden** zijn, maar **Jinja import-aliasen** (`{% import ... as alias %}`) die de template intern definieert.

---

## Kernanalyse (belangrijkste inzicht)
Er lopen in de codebase twee conceptueel verschillende validaties door elkaar:

1) **Input-schema validatie (pre-render)**
- Doel: bepalen welke contextvelden de caller moet meegeven aan `scaffold_artifact`.
- Dit moet hard failen als echte required velden ontbreken.

2) **Enforcement/architectural/guideline validatie (post-render / semantiek)**
- Doel: regels over output/patronen (tier0-2 strict, tier3 architectural, concrete guideline).

De observed fout (import-aliasen als required) komt uit **(1)**, niet uit tier-enforcement. Het lijkt erop dat het huidige input-schema nog steeds (deels) afgeleid wordt van Jinja2 “undeclared variables”, en dat Jinja2 meta-introspection in dit geval import-aliasen meeneemt.

Belangrijke nuance: dit is geen wenselijke bron van waarheid voor agent input schema, omdat interne template-symbolen niet door de caller geleverd horen te worden.

---

## Waar komt het ‘required schema’ momenteel vandaan?
Bij `scaffold_artifact` wordt de required/optional schema gebruikt uit:
- `TemplateScaffolder.validate()` → `introspect_template_with_inheritance(...)` → `TemplateSchema.required/optional`

Die schema-extractie gebruikt Jinja2 parsing + meta.find_undeclared_variables.
Dat verklaart waarom interne symbols (import alias names) kunnen ‘lekken’ in required.

Er bestaat ook TEMPLATE_METADATA parsing (YAML in Jinja comments), maar die wordt in het huidige input-schema pad niet als SSOT gebruikt.

---

## DRY / mismatch risico (jouw zorg)
Je zorg is terecht: als we zowel
- Jinja-meta (undeclared vars) én
- TEMPLATE_METADATA.required/optional
naast elkaar hebben als “waarheid”, kan er mismatch ontstaan.

Best-practice richting (toekomstig): kies één SSOT voor caller input schema.
- Optie A: **TEMPLATE_METADATA.introspection.variables.required/optional = SSOT** (expliciet contract)
- Optie B: Jinja-meta = SSOT en metadata wordt automatisch gegenereerd (maar blijft fragiel)
- Optie C: Hybride: metadata-first, fallback naar Jinja-meta + drift-check

---

## Incident / samenwerking / herstel
Tijdens de discussie is per ongeluk een code-fix poging gestart (ongevraagd) om import-alias filtering te verbeteren.
- Dit is NIET gewenst zonder expliciete opdracht.
- De wijziging leidde tot instabiliteit bij scaffold calls.

Herstelactie uitgevoerd:
- Alles teruggezet naar laatste commit en ontracked files mee in stash.
- Repo is nu clean.

**Stash info:**
- Stash message: `revert-local-changes-after-unsolicited-edit`
- Deze stash bevat o.a. lokale edits + tijdelijke testbestanden.

---

## Huidige status
- Branch: `feature/72-template-library-management`
- Working tree: clean
- Laatst bekende probleem: `scaffold_artifact` input-schema voor worker kan import-aliasen als required teruggeven.

---

## Concrete next steps (aan jou)
1) Beslis SSOT voor input-schema:
   - A (metadata SSOT) is het meest stabiel/expliciet.
2) Als je “final whitespace review” wil doen:
   - Eerst fixen dat worker scaffold validatie geen import-aliasen vereist.
   - Daarna 7 outputs scaffolden naar `.st3/` voor jouw review.
3) Als je wilt: definieer ‘Architectural’ expliciet als output/pattern checks (geen input-velden).

---

## Links
- Issue planning: [docs/development/issue72/planning.md](planning.md)
- Phase 3 requirements: [docs/development/issue72/phase3-tier3-template-requirements.md](phase3-tier3-template-requirements.md)
- Vorige overdracht vandaag: [docs/development/issue72/SESSIE_OVERDRACHT_20260202.md](SESSIE_OVERDRACHT_20260202.md)
