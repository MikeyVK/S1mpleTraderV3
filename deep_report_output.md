# Comprehensive Code Quality Report

**Date:** 2025-12-13
**Scope:** All `mcp_server` Python files.

## 1. File Overview
| File | Coverage | Warnings | Status |
| :--- | :--- | :--- | :--- |
| `__init__.py` | **100%** | 0 | ✅ |
| `__main__.py` | **0%** | 0 | ⚠️ Coverage |
| `adapters/filesystem.py` | **66%** | 0 | ⚠️ Coverage |
| `adapters/git_adapter.py` | **57%** | 0 | ⚠️ Coverage |
| `adapters/github_adapter.py` | **24%** | 0 | ⚠️ Coverage |
| `cli.py` | **93%** | 2 | ⚠️ Lint |
| `config/__init__.py` | **100%** | 0 | ✅ |
| `config/settings.py` | **98%** | 0 | ✅ |
| `core/__init__.py` | **100%** | 0 | ✅ |
| `core/exceptions.py` | **100%** | 0 | ✅ |
| `core/logging.py` | **96%** | 6 | ⚠️ Lint |
| `integrations/__init__.py` | **100%** | 0 | ✅ |
| `managers/doc_manager.py` | **99%** | 0 | ✅ |
| `managers/git_manager.py` | **100%** | 0 | ✅ |
| `managers/github_manager.py` | **100%** | 0 | ✅ |
| `managers/qa_manager.py` | **96%** | 0 | ✅ |
| `managers/scaffold_manager.py` | **100%** | 0 | ✅ |
| `resources/__init__.py` | **100%** | 0 | ✅ |
| `resources/base.py` | **100%** | 0 | ✅ |
| `resources/github.py` | **82%** | 0 | ⚠️ Coverage |
| `resources/standards.py` | **100%** | 0 | ✅ |
| `resources/status.py` | **83%** | 0 | ⚠️ Coverage |
| `resources/templates.py` | **88%** | 0 | ⚠️ Coverage |
| `server.py` | **65%** | 1 | ⚠️ Coverage, ⚠️ Lint |
| `state/__init__.py` | **100%** | 0 | ✅ |
| `state/context.py` | **0%** | 2 | ⚠️ Coverage, ⚠️ Lint |
| `tools/__init__.py` | **100%** | 0 | ✅ |
| `tools/base.py` | **100%** | 0 | ✅ |
| `tools/code_tools.py` | **93%** | 2 | ⚠️ Lint |
| `tools/discovery_tools.py` | **74%** | 7 | ⚠️ Coverage, ⚠️ Lint |
| `tools/docs_tools.py` | **100%** | 2 | ⚠️ Lint |
| `tools/git_analysis_tools.py` | **66%** | 4 | ⚠️ Coverage, ⚠️ Lint |
| `tools/git_tools.py` | **100%** | 16 | ⚠️ Lint |
| `tools/health_tools.py` | **100%** | 0 | ✅ |
| `tools/issue_tools.py` | **92%** | 10 | ⚠️ Lint |
| `tools/label_tools.py` | **100%** | 4 | ⚠️ Lint |
| `tools/milestone_tools.py` | **81%** | 2 | ⚠️ Coverage, ⚠️ Lint |
| `tools/pr_tools.py` | **85%** | 6 | ⚠️ Coverage, ⚠️ Lint |
| `tools/quality_tools.py` | **100%** | 0 | ✅ |
| `tools/safe_edit_tool.py` | **95%** | 0 | ✅ |
| `tools/scaffold_tools.py` | **100%** | 22 | ⚠️ Lint |
| `tools/template_validation_tool.py` | **100%** | 0 | ✅ |
| `tools/test_tools.py` | **61%** | 3 | ⚠️ Coverage, ⚠️ Lint |
| `tools/validation_tools.py` | **100%** | 0 | ✅ |
| `validation/__init__.py` | **100%** | 0 | ✅ |
| `validation/base.py` | **94%** | 0 | ✅ |
| `validation/markdown_validator.py` | **97%** | 0 | ✅ |
| `validation/python_validator.py` | **89%** | 0 | ⚠️ Coverage |
| `validation/registry.py` | **100%** | 0 | ✅ |
| `validation/template_validator.py` | **100%** | 0 | ✅ |

## 2. Low Coverage Analysis (< 90%)
The following files require attention to meet the 90% quality gate:

### __main__.py (0.0%)
- **Missing Lines**: 2, 4, 5
- **Remediation**: Create unit tests targeting these lines. If unreachable, mark with `# pragma: no cover`.

### adapters/filesystem.py (65.6%)
- **Missing Lines**: 26, 27, 28, 29, 37, 38, 42, 43, 44, 49...
- **Remediation**: Create unit tests targeting these lines. If unreachable, mark with `# pragma: no cover`.

### adapters/git_adapter.py (56.6%)
- **Missing Lines**: 25, 26, 30, 31, 38, 40, 41, 42, 46, 50...
- **Remediation**: Create unit tests targeting these lines. If unreachable, mark with `# pragma: no cover`.

### adapters/github_adapter.py (23.9%)
- **Missing Lines**: 22, 37, 38, 54, 65, 70, 71, 73, 74, 75...
- **Remediation**: Create unit tests targeting these lines. If unreachable, mark with `# pragma: no cover`.

### resources/github.py (81.8%)
- **Missing Lines**: 19, 20
- **Remediation**: Create unit tests targeting these lines. If unreachable, mark with `# pragma: no cover`.

### resources/status.py (82.6%)
- **Missing Lines**: 28, 30, 40, 41
- **Remediation**: Create unit tests targeting these lines. If unreachable, mark with `# pragma: no cover`.

### resources/templates.py (87.5%)
- **Missing Lines**: 15
- **Remediation**: Create unit tests targeting these lines. If unreachable, mark with `# pragma: no cover`.

### server.py (65.2%)
- **Missing Lines**: 163, 175, 176, 177, 178, 182, 196, 197, 198, 199...
- **Remediation**: Create unit tests targeting these lines. If unreachable, mark with `# pragma: no cover`.

### state/context.py (0.0%)
- **Missing Lines**: 2, 4, 7, 9, 10, 11, 13, 15, 17, 19...
- **Remediation**: Create unit tests targeting these lines. If unreachable, mark with `# pragma: no cover`.

### tools/discovery_tools.py (73.8%)
- **Missing Lines**: 132, 133, 134, 145, 146, 182, 194, 195, 196, 197...
- **Remediation**: Create unit tests targeting these lines. If unreachable, mark with `# pragma: no cover`.

### tools/git_analysis_tools.py (65.5%)
- **Missing Lines**: 19, 39, 40, 41, 42, 56, 75, 76, 77, 78
- **Remediation**: Create unit tests targeting these lines. If unreachable, mark with `# pragma: no cover`.

### tools/milestone_tools.py (80.8%)
- **Missing Lines**: 20, 37, 38, 41, 65, 95, 96, 112, 129, 130
- **Remediation**: Create unit tests targeting these lines. If unreachable, mark with `# pragma: no cover`.

### tools/pr_tools.py (85.4%)
- **Missing Lines**: 73, 104, 105, 108, 131, 166, 167
- **Remediation**: Create unit tests targeting these lines. If unreachable, mark with `# pragma: no cover`.

### tools/test_tools.py (60.8%)
- **Missing Lines**: 20, 21, 22, 23, 24, 27, 37, 38, 39, 40...
- **Remediation**: Create unit tests targeting these lines. If unreachable, mark with `# pragma: no cover`.

### validation/python_validator.py (89.1%)
- **Missing Lines**: 19, 53, 54, 72, 73
- **Remediation**: Create unit tests targeting these lines. If unreachable, mark with `# pragma: no cover`.

## 3. Pylint Warnings Inventory
Listing all files with active warnings:

### `tools/discovery_tools.py` (1)
- **line 111**: unused-argument (W0613): Unused argument 'include_closed_recent'

### `tools/issue_tools.py` (6)
- **line 55**: arguments-differ (W0221): Number of parameters was 2 in 'BaseTool.execute' and is now 7 in overriding 'CreateIssueTool.execute' method
- **line 162**: arguments-differ (W0221): Number of parameters was 2 in 'BaseTool.execute' and is now 3 in overriding 'GetIssueTool.execute' method
- **line 243**: arguments-differ (W0221): Number of parameters was 2 in 'BaseTool.execute' and is now 4 in overriding 'CloseIssueTool.execute' method
- **line 302**: arguments-differ (W0221): Number of parameters was 2 in 'BaseTool.execute' and is now 9 in overriding 'UpdateIssueTool.execute' method
- **line 302**: too-many-arguments (R0913): Too many arguments (8/5)
- **line 302**: too-many-positional-arguments (R0917): Too many positional arguments (8/5)

### `tools/label_tools.py` (4)
- **line 70**: arguments-differ (W0221): Number of parameters was 2 in 'BaseTool.execute' and is now 5 in overriding 'CreateLabelTool.execute' method
- **line 108**: arguments-differ (W0221): Number of parameters was 2 in 'BaseTool.execute' and is now 3 in overriding 'DeleteLabelTool.execute' method
- **line 141**: arguments-differ (W0221): Number of parameters was 2 in 'BaseTool.execute' and is now 4 in overriding 'RemoveLabelsTool.execute' method
- **line 178**: arguments-differ (W0221): Number of parameters was 2 in 'BaseTool.execute' and is now 4 in overriding 'AddLabelsTool.execute' method

### `tools/milestone_tools.py` (2)
- **line 81**: arguments-differ (W0221): Number of parameters was 2 in 'BaseTool.execute' and is now 5 in overriding 'CreateMilestoneTool.execute' method
- **line 123**: arguments-differ (W0221): Number of parameters was 2 in 'BaseTool.execute' and is now 3 in overriding 'CloseMilestoneTool.execute' method

### `tools/pr_tools.py` (2)
- **line 41**: arguments-differ (W0221): Number of parameters was 2 in 'BaseTool.execute' and is now 7 in overriding 'CreatePRTool.execute' method
- **line 152**: arguments-differ (W0221): Number of parameters was 2 in 'BaseTool.execute' and is now 5 in overriding 'MergePRTool.execute' method

### `tools/test_tools.py` (1)
- **line 120**: use-implicit-booleaness-not-comparison-to-zero (C1805): "returncode == 0" can be simplified to "not returncode", if it is strictly an int, as 0 is falsey

