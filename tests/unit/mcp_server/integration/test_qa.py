"""Tests for QA integration.

Integration tests for real QA tool execution with actual files.
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from mcp_server.config.quality_config import QualityConfig
from mcp_server.managers.qa_manager import QAManager
from mcp_server.tools.quality_tools import RunQualityGatesInput, RunQualityGatesTool


def test_qa_manager_run_gates_with_real_file() -> None:
    """Test QAManager runs quality gates on a real clean file."""
    manager = QAManager()
    # Use a real file that is known to be clean
    result = manager.run_quality_gates(["backend/core/enums.py"])

    # Should have all active gates from quality.yaml (8 gates configured)
    # Some gates may be skipped (e.g., Gate 5/6 in file-specific mode)
    assert len(result["gates"]) >= 6, f"Expected at least 6 gates, got {len(result['gates'])}"

    # Verify first gate is Ruff Format (Gate 0)
    assert "Ruff Format" in result["gates"][0]["name"]

    # overall_pass depends on actual file quality
    assert isinstance(result["overall_pass"], bool)


@pytest.mark.asyncio
async def test_quality_tool_output_format() -> None:
    """Test RunQualityGatesTool returns schema-first JSON with text_output."""
    manager = QAManager()
    tool = RunQualityGatesTool(manager=manager)

    result = await tool.execute(RunQualityGatesInput(files=["backend/core/enums.py"]))

    # Output must be valid JSON (schema-first)
    data = json.loads(result.content[0]["text"])

    # Verify JSON structure
    assert "version" in data
    assert "mode" in data
    assert data["mode"] == "file-specific"
    assert "summary" in data
    assert "gates" in data
    assert "text_output" in data
    assert "overall_pass" in data

    # Summary has totals
    assert "total_violations" in data["summary"]
    assert "auto_fixable" in data["summary"]

    # text_output contains human-readable content
    assert "Quality Gates Results" in data["text_output"]
    assert "Ruff Format" in data["text_output"] or "Gate 0" in data["text_output"]

    # Gates have enriched schema
    for gate in data["gates"]:
        assert "status" in gate, f"Gate '{gate.get('name')}' missing 'status'"


def test_switching_active_gates_changes_execution(tmp_path: Path) -> None:
    """Integration test: switching active_gates in quality.yaml changes which gates run.

    Verifies acceptance criteria for Issue #131: QAManager dynamically loads gates
    from active_gates list in quality.yaml.
    """
    # Create a custom quality.yaml with only 2 gates active
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

    # Mock QualityConfig.load to return our custom config
    def mock_load() -> QualityConfig:
        return QualityConfig.model_validate(custom_config)

    with patch.object(QualityConfig, "load", side_effect=mock_load):
        manager = QAManager()
        result = manager.run_quality_gates(["backend/core/enums.py"])

        # Should only have 2 gates (the ones in active_gates)
        gate_names = [gate["name"] for gate in result["gates"]]
        assert len(gate_names) == 2, f"Expected 2 gates, got {len(gate_names)}: {gate_names}"
        assert "Gate 1: Formatting" in gate_names
        assert "Gate 3: Line Length" in gate_names

        # Verify gates NOT in active_gates are NOT executed
        assert not any("Gate 0:" in name for name in gate_names), "Gate 0 should not run"
        assert not any("Gate 2:" in name for name in gate_names), "Gate 2 should not run"
        assert not any("Gate 4:" in name for name in gate_names), "Gate 4 should not run"
