"""Tests for quality gates configuration (QualityConfig and related models).

Scope:
- YAML loading (valid YAML, missing file, invalid YAML)
- Schema validation (required fields, forbidden extra fields)
- Strategy validation (parsing strategy discriminated union)
- Success validation (`success.mode` must match `parsing.strategy`)
- JSON Pointer validation (RFC 6901-style basic constraints)
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

from mcp_server.config.quality_config import QualityConfig, QualityGate


@pytest.fixture(name="quality_yaml_path")
def fixture_quality_yaml_path(tmp_path: Path) -> Path:
    """Create a valid quality.yaml fixture."""
    config_data = {
        "version": "1.0",
        "gates": {
            "pylint": {
                "name": "Pylint",
                "description": "Python linting",
                "execution": {
                    "command": ["python", "-m", "pylint"],
                    "timeout_seconds": 60,
                    "working_dir": None,
                },
                "parsing": {
                    "strategy": "text_regex",
                    "patterns": [
                        {
                            "name": "rating",
                            "regex": "Your code has been rated at ([\\d.]+)/10",
                            "flags": ["MULTILINE"],
                            "group": 1,
                            "required": True,
                        }
                    ],
                },
                "success": {
                    "mode": "text_regex",
                    "min_score": 10.0,
                    "require_no_issues": True,
                },
                "capabilities": {
                    "file_types": [".py"],
                    "supports_autofix": False,
                    "produces_json": False,
                },
            },
            "pyright": {
                "name": "Pyright",
                "description": "Type checking",
                "execution": {
                    "command": ["pyright", "--outputjson"],
                    "timeout_seconds": 120,
                    "working_dir": None,
                },
                "parsing": {
                    "strategy": "json_field",
                    "fields": {
                        "diagnostics": "/generalDiagnostics",
                        "error_count": "/summary/errorCount",
                    },
                    "diagnostics_path": "/generalDiagnostics",
                },
                "success": {
                    "mode": "json_field",
                    "max_errors": 0,
                    "require_no_issues": True,
                },
                "capabilities": {
                    "file_types": [".py"],
                    "supports_autofix": False,
                    "produces_json": True,
                },
            },
            "ruff": {
                "name": "Ruff",
                "description": "Fast linter",
                "execution": {
                    "command": ["ruff", "check"],
                    "timeout_seconds": 60,
                    "working_dir": None,
                },
                "parsing": {"strategy": "exit_code"},
                "success": {"mode": "exit_code", "exit_codes_ok": [0]},
                "capabilities": {
                    "file_types": [".py"],
                    "supports_autofix": True,
                    "produces_json": False,
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
        assert set(config.gates) == {"pylint", "pyright", "ruff"}

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
                    "parsing": {"strategy": "exit_code"},
                    "success": {"mode": "exit_code", "exit_codes_ok": [0]},
                    "capabilities": {
                        "file_types": [".py"],
                        "supports_autofix": False,
                        "produces_json": False,
                    },
                    "enabled": True,
                }
            )

        error_text = str(exc_info.value).lower()
        assert "extra" in error_text or "forbidden" in error_text

    def test_success_mode_must_match_parsing_strategy(self) -> None:
        """Reject success.mode != parsing.strategy."""
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
                            "parsing": {"strategy": "exit_code"},
                            "success": {"mode": "text_regex", "exit_codes_ok": [0]},
                            "capabilities": {
                                "file_types": [".py"],
                                "supports_autofix": True,
                                "produces_json": False,
                            },
                        }
                    },
                }
            )

    def test_json_pointer_must_start_with_slash(self) -> None:
        """Reject JSON fields that are not JSON Pointers."""
        with pytest.raises(ValidationError):
            QualityConfig.model_validate(
                {
                    "version": "1.0",
                    "gates": {
                        "pyright": {
                            "name": "Pyright",
                            "description": "",
                            "execution": {
                                "command": ["pyright", "--outputjson"],
                                "timeout_seconds": 1,
                                "working_dir": None,
                            },
                            "parsing": {
                                "strategy": "json_field",
                                "fields": {"diagnostics": "generalDiagnostics"},
                            },
                            "success": {"mode": "json_field", "max_errors": 0},
                            "capabilities": {
                                "file_types": [".py"],
                                "supports_autofix": False,
                                "produces_json": True,
                            },
                        }
                    },
                }
            )

    def test_regex_flags_are_validated(self) -> None:
        """Reject unsupported regex flags."""
        with pytest.raises(ValidationError):
            QualityConfig.model_validate(
                {
                    "version": "1.0",
                    "gates": {
                        "pylint": {
                            "name": "Pylint",
                            "description": "",
                            "execution": {
                                "command": ["python", "-m", "pylint"],
                                "timeout_seconds": 1,
                                "working_dir": None,
                            },
                            "parsing": {
                                "strategy": "text_regex",
                                "patterns": [
                                    {
                                        "name": "rating",
                                        "regex": "x",
                                        "flags": ["NOT_A_FLAG"],
                                    }
                                ],
                            },
                            "success": {"mode": "text_regex", "min_score": 0.0},
                            "capabilities": {
                                "file_types": [".py"],
                                "supports_autofix": False,
                                "produces_json": False,
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
                        "parsing": {"strategy": "exit_code"},
                        "success": {"mode": "exit_code", "exit_codes_ok": [0]},
                        "capabilities": {
                            "file_types": [".py"],
                            "supports_autofix": True,
                            "produces_json": False,
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
                        "parsing": {"strategy": "exit_code"},
                        "success": {"mode": "exit_code", "exit_codes_ok": [0]},
                        "capabilities": {
                            "file_types": [".py"],
                            "supports_autofix": False,
                            "produces_json": False,
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
                        "parsing": {"strategy": "exit_code"},
                        "success": {"mode": "exit_code", "exit_codes_ok": [0]},
                        "capabilities": {
                            "file_types": [".py"],
                            "supports_autofix": False,
                            "produces_json": False,
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
                        "parsing": {"strategy": "exit_code"},
                        "success": {"mode": "exit_code", "exit_codes_ok": [0]},
                        "capabilities": {
                            "file_types": [".py"],
                            "supports_autofix": True,
                            "produces_json": False,
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
                        "parsing": {"strategy": "exit_code"},
                        "success": {"mode": "exit_code", "exit_codes_ok": [0]},
                        "capabilities": {
                            "file_types": [".py"],
                            "supports_autofix": False,
                            "produces_json": False,
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
                        "parsing": {"strategy": "exit_code"},
                        "success": {"mode": "exit_code", "exit_codes_ok": [0]},
                        "capabilities": {
                            "file_types": [".py"],
                            "supports_autofix": False,
                            "produces_json": False,
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
                    "parsing": {"strategy": "exit_code"},
                    "success": {"mode": "exit_code", "exit_codes_ok": [0]},
                    "capabilities": {
                        "file_types": [".py"],
                        "supports_autofix": True,
                        "produces_json": False,
                    },
                }
            },
        }

        yaml_path = tmp_path / "test_quality.yaml"
        with open(yaml_path, "w", encoding="utf-8") as f:
            yaml.dump(yaml_data, f)

        config = QualityConfig.load(yaml_path)
        assert config.active_gates == ["ruff"]
