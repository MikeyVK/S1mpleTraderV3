# tests\mcp_server\integration\test_qa.py
# template=integration_test version=85ea75d4 created=2026-02-22T13:43Z updated=
"""
Integration tests for QA tool execution with real workspace files.

These tests run ruff/mypy on real files in the workspace (not tmp_path),
making them true integration tests — they depend on the real filesystem state.

Marked @pytest.mark.integration: skipped by default, run via:
    pytest tests/mcp_server/ -m integration

@layer: Tests (Integration)
@dependencies: [pytest, pytest-asyncio, QAManager, RunQualityGatesTool]
@responsibilities:
    - Test end-to-end QA tool execution with real workspace files
    - Verify RunQualityGatesTool JSON output structure
    - Validate dynamic gate switching via quality.yaml
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from mcp_server.config.quality_config import QualityConfig
from mcp_server.managers.qa_manager import QAManager
from mcp_server.tools.quality_tools import RunQualityGatesInput, RunQualityGatesTool

pytestmark = pytest.mark.integration


def test_qa_manager_run_gates_with_real_file() -> None:
    """QAManager runs quality gates on a real clean file."""
    manager = QAManager()
    result = manager.run_quality_gates(["backend/core/enums.py"])

    assert len(result["gates"]) >= 6, f"Expected at least 6 gates, got {len(result['gates'])}"
    assert "Ruff Format" in result["gates"][0]["name"]
    assert isinstance(result["overall_pass"], bool)


@pytest.mark.asyncio
async def test_quality_tool_output_format() -> None:
    """RunQualityGatesTool returns schema-first JSON with text_output."""
    manager = QAManager()
    tool = RunQualityGatesTool(manager=manager)

    result = await tool.execute(RunQualityGatesInput(files=["backend/core/enums.py"]))

    # Output must be native JSON object (schema-first)
    assert result.content[0]["type"] == "json"
    data = result.content[0]["json"]
    assert isinstance(data, dict)

    # Text fallback for legacy clients
    assert result.content[1]["type"] == "text"
    assert isinstance(result.content[1]["text"], str)

    assert "version" in data
    assert "mode" in data
    assert data["mode"] == "file-specific"
    assert "summary" in data
    assert "gates" in data
    assert "text_output" in data
    assert "overall_pass" in data
    assert "total_violations" in data["summary"]
    assert "auto_fixable" in data["summary"]
    assert "Quality Gates Results" in data["text_output"]
    for gate in data["gates"]:
        assert "status" in gate, f"Gate '{gate.get('name')}' missing 'status'"


def test_switching_active_gates_changes_execution(tmp_path: Path) -> None:
    """Switching active_gates in quality.yaml changes which gates run.

    Verifies acceptance criteria for Issue #131: QAManager dynamically loads
    gates from active_gates list in quality.yaml.
    """
    custom_config = {
        "version": "1.0",
        "active_gates": ["gate1_formatting", "gate3_line_length"],
        "artifact_logging": {
            "enabled": False,
            "output_dir": "temp/qa_logs",
            "max_files": 200,
        },
        "gates": {
            "gate1_formatting": {
                "name": "Gate 1: Formatting",
                "description": "Formatting check",
                "execution": {
                    "command": ["python", "-m", "ruff", "check", "--select=W291"],
                    "timeout_seconds": 60,
                    "working_dir": None,
                },
                "parsing": {"strategy": "exit_code"},
                "success": {"mode": "exit_code", "exit_codes_ok": [0]},
                "capabilities": {
                    "file_types": [".py"],
                    "supports_autofix": True,
                    "produces_json": True,
                },
                "scope": None,
            },
            "gate3_line_length": {
                "name": "Gate 3: Line Length",
                "description": "Line length check",
                "execution": {
                    "command": ["python", "-m", "ruff", "check", "--select=E501"],
                    "timeout_seconds": 60,
                    "working_dir": None,
                },
                "parsing": {"strategy": "exit_code"},
                "success": {"mode": "exit_code", "exit_codes_ok": [0]},
                "capabilities": {
                    "file_types": [".py"],
                    "supports_autofix": False,
                    "produces_json": True,
                },
                "scope": None,
            },
        },
    }

    config_file = tmp_path / "quality.yaml"
    config_file.write_text(json.dumps(custom_config), encoding="utf-8")

    def mock_load() -> QualityConfig:
        return QualityConfig.model_validate(custom_config)

    with patch.object(QualityConfig, "load", side_effect=mock_load):
        manager = QAManager()
        result = manager.run_quality_gates(["backend/core/enums.py"])

        gate_names = [gate["name"] for gate in result["gates"]]
        assert len(gate_names) == 2, f"Expected 2 gates, got {len(gate_names)}: {gate_names}"
        assert "Gate 1: Formatting" in gate_names
        assert "Gate 3: Line Length" in gate_names
        assert not any("Gate 0:" in name for name in gate_names)
        assert not any("Gate 2:" in name for name in gate_names)
        assert not any("Gate 4:" in name for name in gate_names)
