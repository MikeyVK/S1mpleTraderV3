# Sessie Overdracht — 17 maart 2026 (deel b)

## Branch
feature/257-reorder-workflow-phases

## Issue
#257

## Scope
Afhandeling van de QA-afwijzing op de file-level Ruff-suppressies in 14 expliciet gescopeerde bestanden onder tests/mcp_server/.

Doel van deze sessie:
- alle file-level # ruff: noqa headers verwijderen uit de 14 afgesproken bestanden
- de suppressies vervangen door echte annotaties en kleine test-only typefixes
- geen production code aanraken
- tests/mcp_server/test_support.py niet aanraken
- niet verbreden naar C_LOADER.5

## Resultaat
Alle 14 gevraagde file-level # ruff: noqa headers zijn verwijderd.

De ontbrekende annotaties zijn echt toegevoegd in plaats van suppressies te laten staan:
- expliciete -> None return types
- expliciete fixture- en helper-parameterannotaties
- gerichte vervanging van Any waar nodig
- een kleine TypedDict-guard in de YAML-test om Pyright branch-groen te houden
- een enkele unused-parameterfix via hernoeming naar _is_ephemeral

Geen production files aangepast voor deze vraag.
Geen wijzigingen gedaan in tests/mcp_server/test_support.py.
Geen nieuwe # noqa of type: ignore annotaties toegevoegd.

## Per-file Bevestiging
1. tests/mcp_server/test_artifacts_yaml_type_field.py
   - file-level header verwijderd
   - fixtures/tests geannoteerd
   - TypedDict-typing toegevoegd voor veilige YAML-shape
2. tests/mcp_server/managers/test_git_manager_config.py
   - file-level header verwijderd
3. tests/mcp_server/managers/test_phase_state_engine_async.py
   - file-level header verwijderd
   - Any vervangen door object en Callable[..., object]
4. tests/mcp_server/core/test_policy_engine.py
   - file-level header verwijderd
   - ontbrekende -> None annotaties toegevoegd
5. tests/mcp_server/integration/test_validation_policy_e2e.py
   - file-level header verwijderd
   - helper/fixtures expliciet geannoteerd
6. tests/mcp_server/integration/test_v2_smoke_all_types.py
   - file-level header verwijderd
   - unused parameter hernoemd naar _is_ephemeral
7. tests/mcp_server/integration/test_concrete_templates.py
   - file-level header verwijderd
   - helper return type toegevoegd
8. tests/mcp_server/integration/test_config_error_e2e.py
   - file-level header verwijderd
   - helper return type toegevoegd
9. tests/mcp_server/unit/tools/test_scaffold_artifact.py
   - file-level header verwijderd
   - fixture return types en testparameters geannoteerd
10. tests/mcp_server/unit/tools/test_github_extras.py
   - file-level header verwijderd
   - fixture return types en testparameters geannoteerd
11. tests/mcp_server/unit/tools/test_pr_tools.py
   - file-level header verwijderd
   - fixture return types en testparameters geannoteerd
12. tests/mcp_server/unit/tools/test_git_tools.py
   - file-level header verwijderd
   - testparameters en return types geannoteerd
13. tests/mcp_server/unit/config/test_template_config.py
   - file-level header verwijderd
   - ontbrekende -> None annotaties toegevoegd
14. tests/mcp_server/unit/config/test_scaffold_metadata_config.py
   - file-level header verwijderd
   - Path/helper types toegevoegd

## Out Of Scope Bewaakt
Niet gedaan in deze sessie:
- geen production code wijzigingen voor deze implementatievraag
- geen wijzigingen in tests/mcp_server/test_support.py
- geen scope-uitbreiding buiten de 14 afgesproken bestanden
- geen C_LOADER.5 werk

## Proof
### 1. Exacte strikte Ruff-opdracht op alle 14 bestanden
Command:
```text
.\.venv\Scripts\python -m ruff check --isolated tests/mcp_server/test_artifacts_yaml_type_field.py tests/mcp_server/managers/test_git_manager_config.py tests/mcp_server/managers/test_phase_state_engine_async.py tests/mcp_server/core/test_policy_engine.py tests/mcp_server/integration/test_validation_policy_e2e.py tests/mcp_server/integration/test_v2_smoke_all_types.py tests/mcp_server/integration/test_concrete_templates.py tests/mcp_server/integration/test_config_error_e2e.py tests/mcp_server/unit/tools/test_scaffold_artifact.py tests/mcp_server/unit/tools/test_github_extras.py tests/mcp_server/unit/tools/test_pr_tools.py tests/mcp_server/unit/tools/test_git_tools.py tests/mcp_server/unit/config/test_template_config.py tests/mcp_server/unit/config/test_scaffold_metadata_config.py --select ANN001,ANN201,ANN202,ANN401,ARG001
```

Output:
```text
All checks passed!
```

### 2. Branch quality gates
Command:
```text
run_quality_gates(scope="branch")
```

Output:
```text
⚠️ Quality gates: 6/6 active (1 skipped) [branch · 218 files] — 10183ms{
  "overall_pass": true,
  "gates": [
    {
      "id": "Gate 0: Ruff Format",
      "passed": true,
      "skipped": false,
      "status": "passed",
      "violations": []
    },
    {
      "id": "Gate 1: Ruff Strict Lint",
      "passed": true,
      "skipped": false,
      "status": "passed",
      "violations": []
    },
    {
      "id": "Gate 2: Imports",
      "passed": true,
      "skipped": false,
      "status": "passed",
      "violations": []
    },
    {
      "id": "Gate 3: Line Length",
      "passed": true,
      "skipped": false,
      "status": "passed",
      "violations": []
    },
    {
      "id": "Gate 4: Types",
      "passed": true,
      "skipped": true,
      "status": "skipped",
      "violations": []
    },
    {
      "id": "Gate 4b: Pyright",
      "passed": true,
      "skipped": false,
      "status": "passed",
      "violations": []
    },
    {
      "id": "Gate 4c: Types (mcp_server)",
      "passed": true,
      "skipped": false,
      "status": "passed",
      "violations": []
    }
  ]
}
```

### 3. Volledige testsuite tests/mcp_server/
Command:
```text
run_tests(path="tests/mcp_server/")
```

Output:
```text
2132 passed, 12 skipped, 2 xfailed, 24 warnings in 36.28s{
  "summary": {
    "passed": 2132,
    "failed": 0
  },
  "summary_line": "2132 passed, 12 skipped, 2 xfailed, 24 warnings in 36.28s"
}
```

### 4. Controle op resterende file-level # ruff: noqa headers
Command:
```text
Select-String -Path "tests/mcp_server/test_artifacts_yaml_type_field.py","tests/mcp_server/managers/test_git_manager_config.py","tests/mcp_server/managers/test_phase_state_engine_async.py","tests/mcp_server/core/test_policy_engine.py","tests/mcp_server/integration/test_validation_policy_e2e.py","tests/mcp_server/integration/test_v2_smoke_all_types.py","tests/mcp_server/integration/test_concrete_templates.py","tests/mcp_server/integration/test_config_error_e2e.py","tests/mcp_server/unit/tools/test_scaffold_artifact.py","tests/mcp_server/unit/tools/test_github_extras.py","tests/mcp_server/unit/tools/test_pr_tools.py","tests/mcp_server/unit/tools/test_git_tools.py","tests/mcp_server/unit/config/test_template_config.py","tests/mcp_server/unit/config/test_scaffold_metadata_config.py" -Pattern "^# ruff: noqa"
```

Output:
```text
(.venv) PS C:\temp\st3> $files = @('tests/mcp_server/test_artifacts_yaml_type_field.py','tests/mcp_server/managers/test_git_manager_config.py','tests/mcp_server/managers/test_phase_state_engine_async.py','tests/mcp_server/core/test_policy_engine.py','tests/mcp_server/integration/test_validation_policy_e2e.py','tests/mcp_server/integration/test_v2_smoke_all_types.py','tests/mcp_server/integration/test_concrete_templates.py','tests/mcp_server/integration/test_config_error_e2e.py','tests/mcp_server/unit/tools/test_scaffold_artifact.py','tests/mcp_server/unit/tools/test_github_extras.py','tests/mcp_server/unit/tools/test_pr_tools.py','tests/mcp_server/unit/tools/test_git_tools.py','tests/mcp_server/unit/config/test_template_config.py','tests/mcp_server/unit/config/test_scaffold_metadata_config.py'); Select-String -Path $files -Pattern '^# ruff: noqa'
(.venv) PS C:\temp\st3>
```

## QA Status
Deze cleanup is QA-klaar.

Samengevat:
- 14/14 file-level # ruff: noqa headers verwijderd
- exacte Ruff-proof groen
- branch quality gates groen
- volledige tests/mcp_server-suite groen
- geen resterende file-level # ruff: noqa headers in de 14 gescopeerde bestanden
- Geen nieuwe # noqa of type: ignore annotaties toegevoegd

## Addendum — 18 maart 2026

### Laatste blocker voor C_LOADER.4
- Bestand: tests/mcp_server/unit/scaffolders/test_template_root_config.py
- Aanpassing: formatter only via ruff format
- Geen logica, annotaties of imports gewijzigd
- Status: C_LOADER.4 volledig klaar voor GO-beslissing

### Formatter-only verificatie
```text
Semantische verificatie na formatter-run:
{'ast_equal': True, 'imports_equal': True, 'signatures_equal': True, 'assert_count_before': 4, 'assert_count_after': 4}
```

### Proof 1 — Gate 0 clean op het bestand
Command:
```text
c:/temp/st3/.venv/Scripts/python.exe -m ruff format --isolated --check --line-length=100 tests/mcp_server/unit/scaffolders/test_template_root_config.py
```

Output:
```text
1 file already formatted
```

### Proof 2 — Volledige branch quality gates groen
Command:
```text
run_quality_gates(scope="branch")
```

Output:
```text
⚠️ Quality gates: 6/6 active (1 skipped) [branch · 218 files] — 10083ms{
  "overall_pass": true,
  "gates": [
    {
      "id": "Gate 0: Ruff Format",
      "passed": true,
      "skipped": false,
      "status": "passed",
      "violations": []
    },
    {
      "id": "Gate 1: Ruff Strict Lint",
      "passed": true,
      "skipped": false,
      "status": "passed",
      "violations": []
    },
    {
      "id": "Gate 2: Imports",
      "passed": true,
      "skipped": false,
      "status": "passed",
      "violations": []
    },
    {
      "id": "Gate 3: Line Length",
      "passed": true,
      "skipped": false,
      "status": "passed",
      "violations": []
    },
    {
      "id": "Gate 4: Types",
      "passed": true,
      "skipped": true,
      "status": "skipped",
      "violations": []
    },
    {
      "id": "Gate 4b: Pyright",
      "passed": true,
      "skipped": false,
      "status": "passed",
      "violations": []
    },
    {
      "id": "Gate 4c: Types (mcp_server)",
      "passed": true,
      "skipped": false,
      "status": "passed",
      "violations": []
    }
  ]
}
```

### Proof 3 — Tests ongewijzigd
Command:
```text
run_tests(path="tests/mcp_server/unit/scaffolders/")
```

Output:
```text
34 passed in 4.80s{
  "summary": {
    "passed": 34,
    "failed": 0
  },
  "summary_line": "34 passed in 4.80s"
}
```

### Proof 4 — Nog steeds 0 file-level headers
Command:
```text
Select-String -Path "tests/mcp_server/**/*.py" -Pattern "^# ruff: noqa"
```

Output:
```text
PS C:\temp\st3> Select-String -Path "tests/mcp_server/**/*.py" -Pattern "^# ruff: noqa"
```
