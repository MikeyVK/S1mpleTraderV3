<!-- docs\development\issue239\planning.md -->
<!-- template=planning version=130ac5ea created=2026-02-21T15:17Z updated= -->
# Issue #239 — Tier0 Conditional SCAFFOLD Header

**Status:** DRAFT  
**Version:** 1.0  
**Last Updated:** 2026-02-21

---

## Purpose

Fix de lege `<!-- -->` SCAFFOLD-header die _render_body() genereert voor GitHub issue bodies. Tegelijk: stille fallback in template_scaffolder.py (rule 168) voorkomen door ValidationError te gooien als output_type='file' maar output_path leeg/None is.

## Scope

**In Scope:**
tier0_base_artifact.jinja2 conditional logic; template_scaffolder.validate() file artifact gate; issue_tools._render_body() output_path=None + version_hash berekening; tests voor alle drie lagen.

**Out of Scope:**
Andere tier0-variabelen of template-inheritance. issues.yaml / IssueBody structuur (dat is #238). Backfill van bestaande issues (dat is #236).

## Prerequisites

Read these first:
1. #237 gemerged (pytest marker fix — zorgt dat integration tests niet draaien bij normale testrun)
2. Research findings F6 (template structuur) en F8 (SCAFFOLD metadata) beschikbaar op main via docs/development/issue236/research.md
---

## Summary

Drie TDD-cycli om de tier0 SCAFFOLD-header conditioneel te maken op `output_path`. Niet-file artifacts (GitHub issue bodies) krijgen een compacte `<!-- template=X version=Y -->` header zonder filepath/created/updated. File artifacts behouden het huidige twee-regel formaat ongewijzigd. Design-beslissingen zijn inline opgenomen — design-fase samengevoegd met planning.

---

## Dependencies

- C2 (scaffolder validation) vereist dat C1 (tier0 template) groen is — anders ruis in tier0-output bij scaffolder tests
- C3 (_render_body) vereist dat C1 en C2 beide groen zijn

---

## TDD Cycles


### Cycle 1: Tier0 conditional header (`tier0_base_artifact.jinja2`)

**Goal:** `tier0_base_artifact.jinja2` rendert een compacte HTML-comment header als
`output_path` `None` of leeg is, en het huidige twee-regel formaat als `output_path` een
niet-leeg pad is.

**Design beslissing:** `output_path: str | None` als expliciete contract-parameter.
`None` = deliberate non-file artifact (bijv. GitHub issue body). `""` (lege string) = ook
compacte mode (behandeld als None). Dit voorkomt stille fallbacks.

**Gewenst resultaat voor issue bodies:**
```html
<!-- template=issue version=8b7bb3ab -->
```

**Gewenst resultaat voor file artifacts (ongewijzigd):**
```
# src/path/to/file.py
# template=worker version=8b7bb3ab created=2026-02-21T15:00Z updated=
```

**Tests:**
- render met `output_path=None` → uitvoer is exact `<!-- template=X version=Y -->` (geen filepath-regel, geen created/updated)
- render met `output_path=""` → zelfde compacte output (lege string = None semantiek)
- render met `output_path="src/foo.py"` → uitvoer is ongewijzigd (twee regels, filepath + metadata)
- bestaande tier0-snapshot tests blijven groen (geen regressie)

**Success Criteria:**
- Alle bestaande tier0-tests blijven groen
- Twee nieuwe tests slagen (None → compacte header; str → twee-regel ongewijzigd)
- Geen regressie in design/research/planning templates

---

### Cycle 2: Scaffolder validation — file artifact vereist `output_path` (`template_scaffolder.py`)

**Goal:** `template_scaffolder.validate()` gooit een `ValidationError` met hints als een
artifact met `output_type="file"` wordt aangeroepen zonder niet-lege `output_path`.
De stille fallback op regel 168 wordt dode code.

**Design beslissing:** Validatie vindt plaats in `validate()`, vóór de fallback op
regel 168. `output_type="ephemeral"` artifacts mogen `output_path=None` hebben. Foutmelding
bevat hints: `["output_path is required for file artifacts"]`.

**Huidige bug (regel 168):**
```python
output_path = kwargs.get("output_path") or f"{name}{suffix}{extension}"  # silent fallback
```

**Tests:**
- `validate()` met file-artifact + `output_path=""` → `ValidationError` met hint `"output_path is required for file artifacts"`
- `validate()` met file-artifact + `output_path=None` → zelfde `ValidationError`
- `validate()` met file-artifact + geldige `output_path` → geen fout
- `validate()` met ephemeral-artifact + `output_path=None` → geen fout (ephemeral mag zonder pad)

**Success Criteria:**
- Stille fallback (regel 168) is niet meer bereikbaar voor file artifacts
- `ValidationError` met hints gegooid bij file-artifact zonder `output_path`
- Ephemeral artifacts (bijv. `commit`, `pr`) zijn ongewijzigd

---

### Cycle 3: `_render_body` — `output_path=None` + `version_hash` (`issue_tools.py`)

**Goal:** `_render_body()` geeft `output_path=None` door aan de scaffolder en berekent
`version_hash` via `compute_version_hash()` op de `issue.md.jinja2` template, zodat de
rendered body de vorm `<!-- template=issue version=8b7bb3ab -->` heeft.

**Design beslissing:** `output_path=None` is de correcte waarde voor GitHub issue bodies
(niet-file artifact). `version_hash` wordt berekend via `compute_version_hash(template_path)`
— deterministic, gebaseerd op template-inhoud, 8-karakter hex.

**Huidige bug (rendering van lege header):**
```html
<!--  -->
<!-- template= version= created= updated= -->
```

**Gewenste output:**
```html
<!-- template=issue version=8b7bb3ab -->
```

**Tests:**
- rendered body bevat `"template=issue"` en `"version="` gevolgd door 8-karakter hex hash
- rendered body bevat NIET `"created="`, `"updated="`, of een lege filepath-regel `<!--  -->`
- rendered body is HTML-comment formaat (`<!-- ... -->`) niet Python-comment (`#`)
- hash is reproduceerbaar (zelfde template → zelfde hash bij herhaalde aanroepen)

**Success Criteria:**
- GitHub issue body heeft fingerprint-header `<!-- template=issue version=XXXXXXXX -->`
- Hash is deterministisch en reproduceerbaar
- Geen regressie op andere `CreateIssueTool` calls


## Related Documentation
- **[docs/development/issue236/research.md (F6: template structuur, F8: SCAFFOLD metadata)][related-1]**
- **[mcp_server/scaffolding/templates/tier0_base_artifact.jinja2 (target C1)][related-2]**
- **[mcp_server/scaffolders/template_scaffolder.py (target C2)][related-3]**
- **[mcp_server/tools/issue_tools.py (target C3)][related-4]**

<!-- Link definitions -->

[related-1]: docs/development/issue236/research.md (F6: template structuur, F8: SCAFFOLD metadata)
[related-2]: mcp_server/scaffolding/templates/tier0_base_artifact.jinja2 (target C1)
[related-3]: mcp_server/scaffolders/template_scaffolder.py (target C2)
[related-4]: mcp_server/tools/issue_tools.py (target C3)

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 |  | Agent | Initial draft |