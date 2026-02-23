"""Tests for quality gates configuration (QualityConfig and related models).

Scope:
- YAML loading (valid YAML, missing file, invalid YAML)
- Schema validation (required fields, forbidden extra fields)
- Strategy validation (only exit_code strategy accepted)
- Success validation (`success.mode` must be 'exit_code')
- Active gates (config-driven gate selection)

Quality Requirements:
- Pylint: 10/10
- Mypy: strict mode passing
- Coverage: 100% for mcp_server/config/quality_config.py
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml  # type: ignore[import-untyped]
from pydantic import ValidationError

from mcp_server.config.quality_config import (
    CapabilitiesMetadata,
    GateScope,
    QualityConfig,
    QualityGate,
)


@pytest.fixture(name="quality_yaml_path")
def fixture_quality_yaml_path(tmp_path: Path) -> Path:
    """Create a valid quality.yaml fixture with exit_code gates only."""
    config_data = {
        "version": "1.0",
        "gates": {
            "linter": {
                "name": "Linter",
                "description": "Static analysis",
                "execution": {
                    "command": ["tool", "check"],
                    "timeout_seconds": 60,
                    "working_dir": None,
                },
                "success": {"exit_codes_ok": [0]},
                "capabilities": {
                    "file_types": [".py"],
                    "supports_autofix": False,
                },
            },
            "formatter": {
                "name": "Formatter",
                "description": "Code formatter",
                "execution": {
                    "command": ["fmt", "--check"],
                    "timeout_seconds": 30,
                    "working_dir": None,
                },
                "success": {"exit_codes_ok": [0]},
                "capabilities": {
                    "file_types": [".py"],
                    "supports_autofix": True,
                },
            },
        },
    }

    yaml_path = tmp_path / "quality.yaml"
    with open(yaml_path, "w", encoding="utf-8") as file_handle:
        yaml.dump(config_data, file_handle)

    return yaml_path


@pytest.fixture(name="invalid_yaml_path")
def fixture_invalid_yaml_path(tmp_path: Path) -> Path:
    """Create malformed YAML file."""
    yaml_path = tmp_path / "invalid.yaml"
    yaml_path.write_text("invalid: yaml: content: [unclosed", encoding="utf-8")
    return yaml_path


class TestQualityConfigLoading:
    """Test QualityConfig.load() behavior."""

    def test_load_valid_yaml(self, quality_yaml_path: Path) -> None:
        """Loads YAML and returns a QualityConfig."""
        config = QualityConfig.load(quality_yaml_path)
        assert isinstance(config, QualityConfig)
        assert config.version == "1.0"
        assert set(config.gates) == {"linter", "formatter"}

    def test_load_missing_file(self, tmp_path: Path) -> None:
        """Raises FileNotFoundError for missing file."""
        missing_path = tmp_path / "does_not_exist.yaml"
        with pytest.raises(FileNotFoundError) as exc_info:
            QualityConfig.load(missing_path)
        assert str(missing_path) in str(exc_info.value)

    def test_load_invalid_yaml(self, invalid_yaml_path: Path) -> None:
        """Raises when YAML parsing fails."""
        with pytest.raises((yaml.YAMLError, ValidationError, ValueError)):
            QualityConfig.load(invalid_yaml_path)


class TestQualityConfigValidation:
    """Test schema validation rules."""

    def test_gates_must_be_non_empty(self) -> None:
        """Reject empty gates map."""
        with pytest.raises(ValidationError):
            QualityConfig(version="1.0", gates={})

    def test_forbid_extra_fields_on_gate(self) -> None:
        """Reject enforcement-like fields (extra keys) on QualityGate."""
        with pytest.raises(ValidationError) as exc_info:
            QualityGate.model_validate(
                {
                    "name": "X",
                    "description": "",
                    "execution": {
                        "command": ["x"],
                        "timeout_seconds": 1,
                        "working_dir": None,
                    },
                    "success": {"exit_codes_ok": [0]},
                    "capabilities": {
                        "file_types": [".py"],
                        "supports_autofix": False,
                    },
                    "enabled": True,
                }
            )

        error_text = str(exc_info.value).lower()
        assert "extra" in error_text or "forbidden" in error_text

    def test_success_mode_must_match_parsing_strategy(self) -> None:
        """Reject success.mode values other than 'exit_code' (only valid mode)."""
        with pytest.raises(ValidationError):
            QualityConfig.model_validate(
                {
                    "version": "1.0",
                    "gates": {
                        "ruff": {
                            "name": "Ruff",
                            "description": "",
                            "execution": {
                                "command": ["ruff", "check"],
                                "timeout_seconds": 1,
                                "working_dir": None,
                            },
                            "success": {"mode": "text_regex", "exit_codes_ok": [0]},
                            "capabilities": {
                                "file_types": [".py"],
                                "supports_autofix": True,
                            },
                        }
                    },
                }
            )



class TestActiveGatesField:
    """Test active_gates field for config-driven execution (Issue #131)."""

    def test_active_gates_defaults_to_empty_list(self) -> None:
        """active_gates defaults to empty list when not provided."""
        config = QualityConfig.model_validate(
            {
                "version": "1.0",
                "gates": {
                    "ruff": {
                        "name": "Ruff",
                        "description": "",
                        "execution": {
                            "command": ["ruff", "check"],
                            "timeout_seconds": 1,
                            "working_dir": None,
                        },
                        "success": {"exit_codes_ok": [0]},
                        "capabilities": {
                            "file_types": [".py"],
                            "supports_autofix": True,
                        },
                    }
                },
            }
        )
        assert config.active_gates == []

    def test_active_gates_accepts_list_of_gate_names(self) -> None:
        """active_gates accepts a list of gate names."""
        config = QualityConfig.model_validate(
            {
                "version": "1.0",
                "active_gates": ["gate1", "gate2"],
                "gates": {
                    "gate1": {
                        "name": "Gate1",
                        "description": "",
                        "execution": {
                            "command": ["tool1"],
                            "timeout_seconds": 1,
                            "working_dir": None,
                        },
                        "success": {"exit_codes_ok": [0]},
                        "capabilities": {
                            "file_types": [".py"],
                            "supports_autofix": False,
                        },
                    },
                    "gate2": {
                        "name": "Gate2",
                        "description": "",
                        "execution": {
                            "command": ["tool2"],
                            "timeout_seconds": 1,
                            "working_dir": None,
                        },
                        "success": {"exit_codes_ok": [0]},
                        "capabilities": {
                            "file_types": [".py"],
                            "supports_autofix": False,
                        },
                    },
                },
            }
        )
        assert config.active_gates == ["gate1", "gate2"]

    def test_active_gates_allows_empty_list(self) -> None:
        """active_gates can be explicitly set to empty list."""
        config = QualityConfig.model_validate(
            {
                "version": "1.0",
                "active_gates": [],
                "gates": {
                    "ruff": {
                        "name": "Ruff",
                        "description": "",
                        "execution": {
                            "command": ["ruff", "check"],
                            "timeout_seconds": 1,
                            "working_dir": None,
                        },
                        "success": {"exit_codes_ok": [0]},
                        "capabilities": {
                            "file_types": [".py"],
                            "supports_autofix": True,
                        },
                    }
                },
            }
        )
        assert config.active_gates == []

    def test_active_gates_subset_of_catalog(self) -> None:
        """active_gates can reference subset of gates catalog."""
        config = QualityConfig.model_validate(
            {
                "version": "1.0",
                "active_gates": ["gate1"],
                "gates": {
                    "gate1": {
                        "name": "Gate1",
                        "description": "",
                        "execution": {
                            "command": ["tool1"],
                            "timeout_seconds": 1,
                            "working_dir": None,
                        },
                        "success": {"exit_codes_ok": [0]},
                        "capabilities": {
                            "file_types": [".py"],
                            "supports_autofix": False,
                        },
                    },
                    "gate2": {
                        "name": "Gate2",
                        "description": "",
                        "execution": {
                            "command": ["tool2"],
                            "timeout_seconds": 1,
                            "working_dir": None,
                        },
                        "success": {"exit_codes_ok": [0]},
                        "capabilities": {
                            "file_types": [".py"],
                            "supports_autofix": False,
                        },
                    },
                },
            }
        )
        assert config.active_gates == ["gate1"]
        assert "gate2" in config.gates  # gate2 exists but not active

    def test_active_gates_loads_from_yaml(self, tmp_path: Path) -> None:
        """active_gates field loads correctly from YAML file."""
        yaml_data = {
            "version": "1.0",
            "active_gates": ["ruff"],
            "gates": {
                "ruff": {
                    "name": "Ruff",
                    "description": "Fast linter",
                    "execution": {
                        "command": ["ruff", "check"],
                        "timeout_seconds": 60,
                        "working_dir": None,
                    },
                    "success": {"exit_codes_ok": [0]},
                    "capabilities": {
                        "file_types": [".py"],
                        "supports_autofix": True,
                    },
                }
            },
        }

        yaml_path = tmp_path / "test_quality.yaml"
        with open(yaml_path, "w", encoding="utf-8") as f:
            yaml.dump(yaml_data, f)

        config = QualityConfig.load(yaml_path)
        assert config.active_gates == ["ruff"]


class TestRuffGateDefinitions:
    """Test new Ruff-based gate definitions (Issue #131 Cycle 3)."""


class TestArtifactLoggingConfig:
    """Test artifact_logging root config behavior."""

    def test_artifact_logging_defaults(self) -> None:
        config = QualityConfig.model_validate(
            {
                "version": "1.0",
                "gates": {
                    "ruff": {
                        "name": "Ruff",
                        "description": "",
                        "execution": {
                            "command": ["ruff", "check"],
                            "timeout_seconds": 1,
                            "working_dir": None,
                        },
                        "success": {"exit_codes_ok": [0]},
                        "capabilities": {
                            "file_types": [".py"],
                            "supports_autofix": True,
                        },
                    }
                },
            }
        )

        assert config.artifact_logging.enabled is True
        assert config.artifact_logging.output_dir == "temp/qa_logs"
        assert config.artifact_logging.max_files == 200

    def test_artifact_logging_custom_values(self) -> None:
        config = QualityConfig.model_validate(
            {
                "version": "1.0",
                "artifact_logging": {
                    "enabled": False,
                    "output_dir": "temp/custom_artifacts",
                    "max_files": 50,
                },
                "gates": {
                    "ruff": {
                        "name": "Ruff",
                        "description": "",
                        "execution": {
                            "command": ["ruff", "check"],
                            "timeout_seconds": 1,
                            "working_dir": None,
                        },
                        "success": {"exit_codes_ok": [0]},
                        "capabilities": {
                            "file_types": [".py"],
                            "supports_autofix": True,
                        },
                    }
                },
            }
        )

        assert config.artifact_logging.enabled is False
        assert config.artifact_logging.output_dir == "temp/custom_artifacts"
        assert config.artifact_logging.max_files == 50

    def test_gate1_formatting_loads_from_yaml(self) -> None:
        """gate1_formatting definition loads correctly from quality.yaml."""
        # Load from actual quality.yaml
        quality_yaml = Path(".st3/quality.yaml")
        config = QualityConfig.load(quality_yaml)

        assert "gate1_formatting" in config.gates
        gate = config.gates["gate1_formatting"]
        assert gate.name == "Gate 1: Ruff Strict Lint"
        assert gate.execution.command[:4] == ["python", "-m", "ruff", "check"]
        assert "--isolated" in gate.execution.command
        assert "--output-format=json" in gate.execution.command
        assert "--ignore=E501,PLC0415" in gate.execution.command

    def test_gate2_imports_loads_from_yaml(self) -> None:
        """gate2_imports definition loads correctly from quality.yaml."""
        quality_yaml = Path(".st3/quality.yaml")
        config = QualityConfig.load(quality_yaml)

        assert "gate2_imports" in config.gates
        gate = config.gates["gate2_imports"]
        assert gate.name == "Gate 2: Imports"
        assert gate.execution.command[:4] == ["python", "-m", "ruff", "check"]
        assert "--isolated" in gate.execution.command
        assert "--output-format=json" in gate.execution.command
        assert "--select=PLC0415" in gate.execution.command
        assert "--target-version=py311" in gate.execution.command

    def test_gate3_line_length_loads_from_yaml(self) -> None:
        """gate3_line_length definition loads correctly from quality.yaml."""
        quality_yaml = Path(".st3/quality.yaml")
        config = QualityConfig.load(quality_yaml)

        assert "gate3_line_length" in config.gates
        gate = config.gates["gate3_line_length"]
        assert gate.name == "Gate 3: Line Length"
        assert gate.execution.command[:4] == ["python", "-m", "ruff", "check"]
        assert "--isolated" in gate.execution.command
        assert "--output-format=json" in gate.execution.command
        assert "--select=E501" in gate.execution.command
        assert "--line-length=100" in gate.execution.command
        assert "--target-version=py311" in gate.execution.command

    def test_active_gates_includes_ruff_gates(self) -> None:
        """active_gates list includes new Ruff-based gates."""
        quality_yaml = Path(".st3/quality.yaml")
        config = QualityConfig.load(quality_yaml)

        assert "gate1_formatting" in config.active_gates
        assert "gate2_imports" in config.active_gates
        assert "gate3_line_length" in config.active_gates

    def test_ruff_gates_use_exit_code_strategy(self) -> None:
        """All Ruff gates pass/fail on exit code (no parsing_strategy declared)."""
        quality_yaml = Path(".st3/quality.yaml")
        config = QualityConfig.load(quality_yaml)

        for gate_name in ["gate1_formatting", "gate2_imports", "gate3_line_length"]:
            gate = config.gates[gate_name]
            assert gate.success.exit_codes_ok == [0]


class TestActiveGatesContract:
    """Config-contract tests for active_gates list (Issue #251 C0).

    These tests enforce that the active gates list in .st3/quality.yaml
    does not contain pytest/coverage gates that would invoke the test-runner
    as a quality gate — a broken pattern identified in F1/F10.
    """

    def test_gate5_tests_not_in_active_gates(self) -> None:
        """gate5_tests must not appear in active_gates (F1/F10 guard)."""
        config = QualityConfig.load(Path(".st3/quality.yaml"))
        assert "gate5_tests" not in config.active_gates

    def test_gate6_coverage_not_in_active_gates(self) -> None:
        """gate6_coverage must not appear in active_gates (F1/F10 guard)."""
        config = QualityConfig.load(Path(".st3/quality.yaml"))
        assert "gate6_coverage" not in config.active_gates

    def test_static_analysis_gates_remain_active(self) -> None:
        """Static analysis gates 0–4b must still be active after gate5/6 removal."""
        config = QualityConfig.load(Path(".st3/quality.yaml"))
        expected = {
            "gate0_ruff_format",
            "gate1_formatting",
            "gate2_imports",
            "gate3_line_length",
            "gate4_types",
            "gate4_pyright",
        }
        assert expected.issubset(set(config.active_gates))

    def test_gate5_tests_not_in_gates_catalog(self) -> None:
        """gate5_tests must be removed from gates catalog entirely (C30 cleanup)."""
        config = QualityConfig.load(Path(".st3/quality.yaml"))
        assert "gate5_tests" not in config.gates, (
            "gate5_tests gate must be fully removed from quality.yaml gates section"
        )

    def test_gate6_coverage_not_in_gates_catalog(self) -> None:
        """gate6_coverage must be removed from gates catalog entirely (C30 cleanup)."""
        config = QualityConfig.load(Path(".st3/quality.yaml"))
        assert "gate6_coverage" not in config.gates, (
            "gate6_coverage gate must be fully removed from quality.yaml gates section"
        )


class TestProjectScopeField:
    """Tests for project_scope field on QualityConfig (Issue #251 C3).

    These tests enforce that QualityConfig accepts an optional GateScope
    under the ``project_scope`` key for project-level scanning.
    """

    _MINIMAL_GATE: dict = {
        "name": "Ruff",
        "description": "Fast linter",
        "execution": {
            "command": ["ruff", "check"],
            "timeout_seconds": 60,
            "working_dir": None,
        },
        "success": {"exit_codes_ok": [0]},
        "capabilities": {
            "file_types": [".py"],
            "supports_autofix": True,
        },
    }

    def test_accepts_project_scope_with_include_globs(self) -> None:
        """QualityConfig accepts project_scope.include_globs without validation error."""
        config = QualityConfig.model_validate(
            {
                "version": "1.0",
                "gates": {"ruff": self._MINIMAL_GATE},
                "project_scope": {
                    "include_globs": ["mcp_server/**/*.py", "tests/mcp_server/**/*.py"],
                },
            }
        )
        assert config.project_scope is not None
        assert "mcp_server/**/*.py" in config.project_scope.include_globs

    def test_project_scope_defaults_to_none(self) -> None:
        """QualityConfig.project_scope is None when not specified."""
        config = QualityConfig.model_validate(
            {"version": "1.0", "gates": {"ruff": self._MINIMAL_GATE}}
        )
        assert config.project_scope is None

    def test_project_scope_is_gate_scope_instance(self) -> None:
        """project_scope is a GateScope instance when provided."""
        config = QualityConfig.model_validate(
            {
                "version": "1.0",
                "gates": {"ruff": self._MINIMAL_GATE},
                "project_scope": {"include_globs": ["backend/**/*.py"]},
            }
        )
        assert isinstance(config.project_scope, GateScope)


class TestProducesJsonRemoved:
    """Guard tests: produces_json must no longer be a field on CapabilitiesMetadata (Issue #251 C4).

    After removal, passing produces_json is an extra field and must raise
    ValidationError (CapabilitiesMetadata uses extra="forbid").
    """

    def test_produces_json_raises_validation_error(self) -> None:
        """CapabilitiesMetadata rejects produces_json as an unknown field."""
        with pytest.raises(ValidationError):
            CapabilitiesMetadata(
                file_types=[".py"],
                supports_autofix=False,
                produces_json=False,  # type: ignore[call-arg]
            )

    def test_capabilities_valid_without_produces_json(self) -> None:
        """CapabilitiesMetadata accepts the minimal valid set without produces_json."""
        caps = CapabilitiesMetadata(file_types=[".py"], supports_autofix=False)
        assert caps.file_types == [".py"]
        assert caps.supports_autofix is False


class TestParsingStrategyMigration:
    """C31/F2: quality.yaml parsing-strategy migration — all active gates covered.

    After full migration, every active gate declares a parsing_strategy:
    - gate0_ruff_format: text_violations (diff output)
    - gate1_formatting: json_violations (ruff JSON)
    - gate2_imports: json_violations (ruff JSON)
    - gate3_line_length: json_violations (ruff JSON)
    - gate4_types: text_violations (mypy text output)
    - gate4_pyright: json_violations (pyright JSON)
    """

    def test_gate4_pyright_uses_json_violations_capability(self) -> None:
        """gate4_pyright must declare json_violations in capabilities (no legacy parsing shim)."""
        config = QualityConfig.load(Path(".st3/quality.yaml"))
        gate = config.gates["gate4_pyright"]
        assert gate.capabilities.parsing_strategy == "json_violations", (
            f"gate4_pyright should use capabilities.parsing_strategy='json_violations', "
            f"got '{gate.capabilities.parsing_strategy}'"
        )
        assert gate.capabilities.json_violations is not None

    def test_gate1_formatting_has_json_violations_capability(self) -> None:
        """gate1_formatting must declare json_violations strategy in capabilities."""
        config = QualityConfig.load(Path(".st3/quality.yaml"))
        gate = config.gates["gate1_formatting"]
        assert gate.capabilities.parsing_strategy == "json_violations", (
            "gate1_formatting must declare parsing_strategy='json_violations' in capabilities"
        )
        assert gate.capabilities.json_violations is not None
        assert "file" in gate.capabilities.json_violations.field_map

    def test_gate0_ruff_format_has_text_violations_capability(self) -> None:
        """gate0_ruff_format must declare text_violations strategy in capabilities (diff output)."""
        config = QualityConfig.load(Path(".st3/quality.yaml"))
        gate = config.gates["gate0_ruff_format"]
        assert gate.capabilities.parsing_strategy == "text_violations", (
            "gate0_ruff_format must declare parsing_strategy='text_violations' in capabilities"
        )
        assert gate.capabilities.text_violations is not None
        assert gate.capabilities.text_violations.pattern != ""

    def test_gate2_imports_has_json_violations_capability(self) -> None:
        """gate2_imports must declare json_violations in capabilities (F2: uniform coverage)."""
        config = QualityConfig.load(Path(".st3/quality.yaml"))
        gate = config.gates["gate2_imports"]
        assert gate.capabilities.parsing_strategy == "json_violations", (
            f"gate2_imports should use json_violations, got '{gate.capabilities.parsing_strategy}'"
        )
        assert gate.capabilities.json_violations is not None
        assert "file" in gate.capabilities.json_violations.field_map

    def test_gate3_line_length_has_json_violations_capability(self) -> None:
        """gate3_line_length must declare json_violations in capabilities (F2: uniform coverage)."""
        config = QualityConfig.load(Path(".st3/quality.yaml"))
        gate = config.gates["gate3_line_length"]
        assert gate.capabilities.parsing_strategy == "json_violations", (
            f"gate3_line_length should use json_violations, "
            f"got '{gate.capabilities.parsing_strategy}'"
        )
        assert gate.capabilities.json_violations is not None

    def test_gate4_types_has_text_violations_capability(self) -> None:
        """gate4_types must declare text_violations in capabilities (mypy text output)."""
        config = QualityConfig.load(Path(".st3/quality.yaml"))
        gate = config.gates["gate4_types"]
        assert gate.capabilities.parsing_strategy == "text_violations", (
            f"gate4_types should use text_violations, got '{gate.capabilities.parsing_strategy}'"
        )
        assert gate.capabilities.text_violations is not None
        assert gate.capabilities.text_violations.pattern != ""

    def test_all_active_gates_have_parsing_strategy(self) -> None:
        """Every active gate must have a non-None parsing_strategy (F2: full coverage)."""
        config = QualityConfig.load(Path(".st3/quality.yaml"))
        for gate_id in config.active_gates:
            gate = config.gates[gate_id]
            assert gate.capabilities.parsing_strategy is not None, (
                f"{gate_id} has no parsing_strategy declared; all active gates must have one"
            )
