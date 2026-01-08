"""Quality gates tooling configuration (.st3/quality.yaml).

This module defines Pydantic models and a loader for the quality gates tool catalog.
It validates tool definitions only (commands/parsing/success/capabilities) and
explicitly does not model enforcement policy (Epic #18).

Quality Requirements:
- Pylint: 10/10 (strict)
- Mypy: strict mode passing
- Coverage: 100% for this module
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal, TypeAlias

import yaml  # type: ignore[import-untyped]
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


RegexFlag = Literal["IGNORECASE", "MULTILINE", "DOTALL"]


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


class RegexPattern(BaseModel):
    """Regex extraction pattern used by text-based parsers."""

    name: str = Field(..., min_length=1)
    regex: str = Field(..., min_length=1)
    flags: list[RegexFlag] = Field(default_factory=list)
    group: int | str | None = Field(default=None)
    required: bool = Field(default=True)

    model_config = ConfigDict(extra="forbid", frozen=True)


class TextRegexParsing(BaseModel):
    """Parse plain text output using regex patterns."""

    strategy: Literal["text_regex"]
    patterns: list[RegexPattern] = Field(..., min_length=1)

    model_config = ConfigDict(extra="forbid", frozen=True)


def _validate_json_pointer(pointer: str) -> str:
    """Validate a JSON Pointer string (RFC 6901).

    Minimal v1 validation per design doc: allow exactly '/', or strings that start
    with '/'. (Array segments are allowed; executor semantics are out of scope.)
    """
    if pointer == "/":
        return pointer
    if not pointer.startswith("/"):
        raise ValueError("Invalid JSON Pointer. Must start with '/' (RFC 6901)")
    if not pointer.strip():
        raise ValueError("Invalid JSON Pointer. Must be non-empty")
    return pointer


class JsonFieldParsing(BaseModel):
    """Parse JSON output and extract fields via JSON Pointer paths (RFC 6901)."""

    strategy: Literal["json_field"]
    fields: dict[str, str] = Field(..., min_length=1)
    diagnostics_path: str | None = Field(default=None)

    model_config = ConfigDict(extra="forbid", frozen=True)

    @field_validator("fields")
    @classmethod
    def validate_fields_pointers(cls, value: dict[str, str]) -> dict[str, str]:
        """Validate JSON pointers for each named field extraction."""
        for key, pointer in value.items():
            if not key.strip():
                raise ValueError("JSON field key must be non-empty")
            _validate_json_pointer(pointer)
        return value

    @field_validator("diagnostics_path")
    @classmethod
    def validate_diagnostics_pointer(cls, value: str | None) -> str | None:
        """Validate the optional diagnostics path JSON pointer."""
        if value is None:
            return None
        return _validate_json_pointer(value)


class ExitCodeParsing(BaseModel):
    """No parsing; rely on exit code only."""

    strategy: Literal["exit_code"]

    model_config = ConfigDict(extra="forbid", frozen=True)


ParsingConfig: TypeAlias = Annotated[
    TextRegexParsing | JsonFieldParsing | ExitCodeParsing,
    Field(discriminator="strategy"),
]


class SuccessCriteria(BaseModel):
    """Defines pass/fail criteria for a tool.

    A2: This model keeps an explicit `mode`, but it must match the parsing strategy
    for a given gate (validated in QualityGate).
    """

    mode: Literal["text_regex", "json_field", "exit_code"]

    exit_codes_ok: list[int] = Field(default_factory=lambda: [0])
    max_errors: int | None = Field(default=None)
    min_score: float | None = Field(default=None)
    require_no_issues: bool = Field(default=True)

    model_config = ConfigDict(extra="forbid", frozen=True)


class CapabilitiesMetadata(BaseModel):
    """Metadata about what a gate applies to / can do."""

    file_types: list[str] = Field(..., min_length=1)
    supports_autofix: bool
    produces_json: bool

    model_config = ConfigDict(extra="forbid", frozen=True)


class QualityGate(BaseModel):
    """Single quality gate tool definition."""

    name: str = Field(..., min_length=1)
    description: str = Field(default="")
    execution: ExecutionConfig
    parsing: ParsingConfig
    success: SuccessCriteria
    capabilities: CapabilitiesMetadata

    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def validate_success_matches_strategy(self) -> "QualityGate":
        """Enforce A2: success.mode must match parsing.strategy."""
        if self.success.mode != self.parsing.strategy:
            raise ValueError(
                "success.mode must match parsing.strategy "
                f"({self.success.mode} != {self.parsing.strategy})"
            )
        return self


class QualityConfig(BaseModel):
    """Root quality gates configuration."""

    version: str = Field(..., min_length=1)
    gates: dict[str, QualityGate] = Field(..., min_length=1)

    model_config = ConfigDict(extra="forbid", frozen=True)

    @classmethod
    def load(cls, path: Path | None = None) -> "QualityConfig":
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

        with open(path, "r", encoding="utf-8") as file_handle:
            data = yaml.safe_load(file_handle)

        return cls(**data)
