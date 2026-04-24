# Sessie Overdracht — 18 februari 2026

**Branch:** `feature/149-redesign-create-issue-tool`
**Issue:** #149 Redesign `create_issue` tool: structured input, config-driven validation, Jinja2 body scaffolding
**Date:** 2026-02-18
**Focus:** Cycles 5 & 6 + integration phase volledig afgerond; tool live in productie
**Status:** Branch clean; integration fase voltooid; documentatie fase open

---

## Wat er gedaan is deze sessie

### Cycle 5 — Label assembly (volledig)

- **RED** (`9843b1e`): 25 tests in `tests/unit/tools/test_create_issue_label_assembly.py`
  - Dekt: `type:*` labels per `issue_type`, `is_epic` override naar `type:epic`, `hotfix` → `type:bug`, `scope:*`, `priority:*`, `phase:*` (eerste workflow-fase), `parent:N`, volledige label-set tellingen
- **GREEN** (`7b3c93f`): Nieuw `WorkflowConfig` singleton + `_assemble_labels()` in `CreateIssueTool`
  - Nieuw bestand: `mcp_server/config/workflow_config.py`
  - `WorkflowEntry(**v)` (niet `WorkflowEntry(name=k, **v)`) — YAML heeft al `name:` field
  - `execute()` wired: `labels = self._assemble_labels(params)`
  - Quality gates 5/5 pass

### Cycle 6 — Error handling (volledig + gap fix)

- **RED** (`7f46810`): 11 tests in `tests/unit/tools/test_create_issue_errors.py`
  - Dekt: `ExecutionError` → `ToolResult.error`, `jinja2.TemplateError` → `ToolResult.error` met actionable bericht, `ValueError` (uit `_assemble_labels`) → `ToolResult.error`, geen lekkende exceptions
- **GREEN** (`4a08a7d`): Expliciete `except jinja2.TemplateError` in `execute()` met bericht: `"Body rendering failed: {e}. Check that issue.md.jinja2 exists..."`
- **Gap fix** (`ba8a67f`): `ValueError` uit `_assemble_labels()` werd niet gecatcht — toegevoegd als `except ValueError as e: return ToolResult.error(f"Label assembly failed: {e}.")`

Volgorde exception handlers in `execute()`:
```python
except jinja2.TemplateError as e: ...
except ValueError as e: ...
except ExecutionError as e: ...
```

### Integration phase (volledig)

- Fase transitie: `tdd → integration` uitgevoerd
- **Commit** (`1046d5b`): `tests/integration/test_create_issue_e2e.py` — 7 tests, allemaal groen

**Test resultaten:**

| Scenario | Test | Resultaat |
|----------|------|-----------|
| Minimal input | `type:feature`, `scope:tooling`, `priority:low`, `phase:research` op GitHub | ✅ |
| Full options | `type:epic`, `parent:149`, `scope:mcp-server`, `priority:medium`, `phase:research` | ✅ |
| Validatie | Ongeldig `issue_type` geweigerd vóór API call | ✅ |
| Validatie | Ongeldige `scope` geweigerd vóór API call | ✅ |
| Validatie | Ongeldige `priority` geweigerd vóór API call | ✅ |
| Validatie | Titel te lang geweigerd vóór API call | ✅ |
| Milestone | Lege `milestones.yaml` → permissief (Risk #2 planning.md) | ✅ |

**Live test:** Issue #157 aangemaakt via MCP tool call — volledig geautomatiseerd met nieuw schema (`issue_type`, `priority`, `scope`, `body`).

---

## Huidige staat van de code

### Gewijzigde bestanden (t.o.v. main)

| Bestand | Wijziging |
|---------|----------|
| `mcp_server/tools/issue_tools.py` | `CreateIssueInput` + `CreateIssueTool` volledig herontwikkeld |
| `mcp_server/config/workflow_config.py` | Nieuw — `WorkflowConfig.from_file()` singleton |
| `mcp_server/config/issue_config.py` | `IssueConfig` singleton (cycle 1) |
| `mcp_server/config/scope_config.py` | `ScopeConfig` singleton (cycle 1) |
| `mcp_server/config/milestone_config.py` | `MilestoneConfig` singleton — permissief bij lege lijst |
| `mcp_server/config/contributor_config.py` | `ContributorConfig` singleton (cycle 1) |
| `.st3/issues.yaml` | Nieuw — issue type definities + workflow mapping |
| `.st3/scopes.yaml` | Nieuw — geldige scopes |
| `.st3/labels.yaml` | Cleanup: `status:*` verwijderd, `parent:N` patroon, `type:chore` toegevoegd |
| `.st3/git.yaml` | `issue_title_max_length: 72` toegevoegd |
| `tests/unit/tools/test_create_issue_label_assembly.py` | Nieuw — 25 tests |
| `tests/unit/tools/test_create_issue_errors.py` | Nieuw — 11 tests |
| `tests/integration/test_create_issue_e2e.py` | Nieuw — 7 e2e tests |

### Nieuw `CreateIssueInput` schema

```python
CreateIssueInput(
    issue_type="feature",   # valideert tegen issues.yaml
    title="...",            # max 72 chars (git.yaml)
    priority="medium",      # valideert tegen labels.yaml priority categorie
    scope="mcp-server",     # valideert tegen scopes.yaml
    body=IssueBody(problem="..."),  # gerenderd via issue.md.jinja2
    is_epic=False,          # optioneel — override type label naar type:epic
    parent_issue=None,      # optioneel — voegt parent:N label toe
    milestone=None,         # optioneel — permissief als milestones.yaml leeg
    assignees=None,         # optioneel — valideert tegen contributors.yaml
)
```

Labels worden **intern geassembleerd** — caller geeft geen labels mee.

### Eerste fasen per workflow (workflows.yaml)

| issue_type | workflow | eerste fase | phase label |
|-----------|----------|-------------|-------------|
| feature | feature | research | `phase:research` |
| bug | bug | research | `phase:research` |
| hotfix | hotfix | tdd | `phase:tdd` |
| refactor | refactor | research | `phase:research` |
| docs | docs | planning | `phase:planning` |
| chore | feature | research | `phase:research` |
| epic | epic | research | `phase:research` |

---

## Commit history deze branch

```
1046d5b  feat: integration smoke tests for CreateIssueTool — real GitHub API validation (7/7 pass)
ba8a67f  fix: catch ValueError from _assemble_labels() in execute() (cycle 6 gap)
4a08a7d  feat: explicit jinja2.TemplateError handling in execute() with actionable message (cycle 6)
7f46810  test: error handling contract for execute() — TemplateError, ExecutionError, ValueError (cycle 6)
7b3c93f  feat: add WorkflowConfig + _assemble_labels() in CreateIssueTool; wire into execute() (cycle 5)
9843b1e  test: label assembly rules for _assemble_labels() and execute() forwarding (cycle 5)
6c76c81  fix(cycle4): priority validation config-driven via LabelConfig; pass params.milestone in execute()
004431b  feat: refactor CreateIssueInput: structured schema (cycle 4)
7bffc41  test: CreateIssueInput schema tests (cycle 4)
8c82fd2  feat: IssueBody model and _render_body() in CreateIssueTool (cycle 3)
81e87d9  test: IssueBody + _render_body tests (cycle 3)
5e96f61  feat: remove type:enhancement from labels.yaml (cycle 2)
ee8c31e  test: test type:enhancement removed from labels.yaml (cycle 2)
e21e3cb  feat: update labels.yaml — remove status labels, numeric parent pattern, type:chore (cycle 2)
625b98a  test: labels.yaml convention tests (cycle 2)
```

---

## Open: Documentation phase

Nog te doen per `planning.md`:

1. **`agent.md` §2.1** — werksequentie bijwerken: `create_issue(issue_type, title, priority, scope, body)` (vervangt `create_issue(title, body, labels)`)
2. **`agent.md` §2.1 voorbeeld** — concreet voorbeeld met alle verplichte velden toevoegen
3. **Config reference docs** — korte beschrijving per nieuw `.st3/` bestand in `docs/reference/`
4. **Inline docstrings** — `CreateIssueInput`, `IssueBody`, `_assemble_labels()`, `_render_body()` volledig gedocumenteerd
5. **`labels.yaml` CHANGELOG** — verwijdering `status:*` en wijziging `parent:*` patroon vastleggen

---

## Aandachtspunten voor volgende sessie

- **Smoke issues opruimen**: Issues #155, #156 (aangemaakt door integration tests), #157 (live test) kunnen gesloten worden
- **`milestones.yaml` leeg**: Validatie momenteel permissief — pas strict als milestones.yaml gevuld wordt (Risk #2)
- **`contributors.yaml` leeg**: Zelfde situatie — valideert niet zolang lijst leeg is
- **agent.md §2.1**: Oude `create_issue` signature staat er nog in — misleidend voor nieuwe sessies, prioriteit in docs fase
- **Breaking change**: Alle bestaande callers die `labels=[...]` meegaven werken niet meer — maar er zijn geen andere callers in codebase gevonden
