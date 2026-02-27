"""Quality gates tooling configuration (.st3/quality.yaml).

This module defines Pydantic models and a loader for the quality gates tool catalog.
It validates tool definitions only (commands/parsing/success/capabilities) and
explicitly does not model enforcement policy (Epic #18).

Quality Requirements:
- Pyright: strict mode passing
- Ruff: all configured rules passing
- Coverage: 100% for this module
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


@dataclass
class ViolationDTO:
    """Uniform violation contract returned by every gate parser.

    ``file`` and ``message`` are always present.  All other fields
    are optional and default to ``None`` / ``False`` / ``"error"``
    so callers can construct minimal stubs for file-level violations.
    """

    file: str
    message: str
    line: int | None = None
    col: int | None = None
    rule: str | None = None
    fixable: bool = False
    severity: str = "error"


class JsonViolationsParsing(BaseModel):
    """JSON parsing strategy: extracts violations from structured tool output.

    Used for gates that emit a JSON array of violation objects (ruff check,
    pyright). ``field_map`` maps ViolationDTO field names to source JSON keys
    (optionally as ``/``-separated paths for nested access).
    """

    field_map: dict[str, str] = Field(
        ...,
        min_length=1,
        description="ViolationDTO field → source JSON key mapping.",
    )
    violations_path: str | None = Field(
        default=None,
        description="Dot-separated path to the violations array (None = root).",
    )
    line_offset: int = Field(
        default=0,
        description="Added to the mapped line value to normalize 0-based indices.",
    )
    fixable_when: str | None = Field(
        default=None,
        description="Source JSON key; sets fixable=True when the extracted value is truthy.",
    )

    model_config = ConfigDict(extra="forbid", frozen=True)


class TextViolationsParsing(BaseModel):
    """Text parsing strategy: extracts violations from line-based tool output.

    Used for gates that emit violations as plain text (mypy, pylint, bandit).
    ``pattern`` is a regex with named groups that map to ViolationDTO fields
    (e.g. ``file``, ``line``, ``col``, ``message``, ``rule``, ``severity``).
    ``defaults`` supplies static values for fields absent from the pattern.
    """

    pattern: str = Field(
        ...,
        description="Regex with named groups mapping to ViolationDTO fields.",
    )
    severity_default: str = Field(
        default="error",
        description="Severity used when the pattern has no 'severity' group.",
    )
    defaults: dict[str, str] = Field(
        default_factory=dict,
        description="Static default values for ViolationDTO fields not captured by the pattern.",
    )
    fixable_when: str | None = Field(
        default=None,
        description=(
            "When set to 'gate', violations are marked fixable=True iff the gate's "
            "supports_autofix=True. Mirrors the json_violations fixable_when field."
        ),
    )

    @model_validator(mode="after")
    def _validate_defaults_placeholders(self) -> TextViolationsParsing:
        """Ensure every {placeholder} in defaults refers to a named group in pattern."""
        named_groups = set(re.findall(r"\(\?P<(\w+)>", self.pattern))
        unknown: list[str] = []
        for value in self.defaults.values():
            for token in re.findall(r"\{(\w+)\}", value):
                if token not in named_groups:
                    unknown.append(token)
        if unknown:
            raise ValueError(
                f"defaults references placeholder(s) not in pattern named groups: "
                f"{', '.join(sorted(set(unknown)))}. "
                f"Known groups: {sorted(named_groups) or '(none)'}."
            )
        return self

    model_config = ConfigDict(extra="forbid", frozen=True)


class ExecutionConfig(BaseModel):
    """How to execute a gate tool."""

    command: list[str] = Field(
        ...,
        min_length=1,
        description="Subprocess argv list (non-empty).",
    )
    timeout_seconds: int = Field(
        ...,
        gt=0,
        description="Timeout in seconds (must be > 0).",
    )
    working_dir: str | None = Field(
        default=None,
        description="Optional working directory for execution.",
    )

    model_config = ConfigDict(extra="forbid", frozen=True)


class SuccessCriteria(BaseModel):
    """Defines pass/fail criteria for a tool.

    Gates pass/fail purely on exit code (exit_codes_ok) or violation count
    (json_violations / text_violations strategy via capabilities.parsing_strategy).
    """

    exit_codes_ok: list[int] = Field(default_factory=lambda: [0])
    max_errors: int | None = Field(default=None)
    min_score: float | None = Field(default=None)
    require_no_issues: bool = Field(default=True)

    model_config = ConfigDict(extra="forbid", frozen=True)


class GateScope(BaseModel):
    """File scope filtering for quality gates.

    Defines which files a gate should apply to using glob patterns.
    Empty scope means "apply to all files".
    """

    include_globs: list[str] = Field(default_factory=list)
    exclude_globs: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid", frozen=True)

    def filter_files(self, files: list[str]) -> list[str]:
        """Filter files based on include/exclude globs.

        Args:
            files: List of file paths (absolute or relative)

        Returns:
            Filtered list of files matching scope rules
        """
        if not self.include_globs and not self.exclude_globs:
            return files  # No filtering

        # Make iteration explicit for pylint
        include_patterns: list[str] = list(self.include_globs)
        exclude_patterns: list[str] = list(self.exclude_globs)

        filtered = []
        for file_path in files:
            # Normalize to POSIX for glob matching
            posix_path = Path(file_path).as_posix()

            # Include matching
            if include_patterns and not any(
                PurePosixPath(posix_path).full_match(pattern) for pattern in include_patterns
            ):
                continue  # Skip if not in include list

            # Exclude matching
            if exclude_patterns and any(
                PurePosixPath(posix_path).full_match(pattern) for pattern in exclude_patterns
            ):
                continue  # Skip if in exclude list
            filtered.append(file_path)

        return filtered


class CapabilitiesMetadata(BaseModel):
    """Metadata about what a gate applies to / can do."""

    file_types: list[str] = Field(..., min_length=1)
    supports_autofix: bool
    parsing_strategy: Literal["json_violations", "text_violations"] | None = Field(
        default=None,
        description="New-style violation-parsing strategy (json_violations or text_violations).",
    )
    json_violations: JsonViolationsParsing | None = Field(
        default=None,
        description="Config for json_violations parsing strategy.",
    )
    text_violations: TextViolationsParsing | None = Field(
        default=None,
        description="Config for text_violations parsing strategy.",
    )

    model_config = ConfigDict(extra="forbid", frozen=True)


class QualityGate(BaseModel):
    """Single quality gate tool definition."""

    name: str = Field(..., min_length=1)
    description: str = Field(default="")
    execution: ExecutionConfig
    success: SuccessCriteria
    capabilities: CapabilitiesMetadata
    scope: GateScope | None = Field(default=None)

    model_config = ConfigDict(extra="forbid", frozen=True)


class ArtifactLoggingConfig(BaseModel):
    """Artifact logging behavior for failed gate diagnostics."""

    enabled: bool = Field(default=True)
    output_dir: str = Field(default="temp/qa_logs", min_length=1)
    max_files: int = Field(default=200, ge=1)

    model_config = ConfigDict(extra="forbid", frozen=True)


class QualityConfig(BaseModel):
    """Root quality gates configuration."""

    version: str = Field(..., min_length=1)
    active_gates: list[str] = Field(
        default_factory=list, description="List of active gate names to execute from gates catalog"
    )
    artifact_logging: ArtifactLoggingConfig = Field(default_factory=ArtifactLoggingConfig)
    project_scope: GateScope | None = Field(
        default=None,
        description="Glob patterns for project-level scope (scope=project scanning).",
    )
    gates: dict[str, QualityGate] = Field(..., min_length=1)

    model_config = ConfigDict(extra="forbid", frozen=True)

    @classmethod
    def load(cls, path: Path | None = None) -> QualityConfig:
        """Load configuration from YAML.

        Args:
            path: Path to .st3/quality.yaml (default: .st3/quality.yaml)

        Returns:
            Validated QualityConfig instance.

        Raises:
            FileNotFoundError: Config file not found.
            ValidationError: Schema validation failed.
        """
        if path is None:
            path = Path(".st3/quality.yaml")

        if not path.exists():
            raise FileNotFoundError(
                f"Quality config not found: {path}\n"
                "Expected location: .st3/quality.yaml\n"
                "Hint: Add .st3/quality.yaml to define available gate tools"
            )

        with open(path, encoding="utf-8") as file_handle:
            data = yaml.safe_load(file_handle)

        return cls(**data)
