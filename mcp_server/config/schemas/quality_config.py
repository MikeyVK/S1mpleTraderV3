"""Pure quality gates schema definitions."""

from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


@dataclass
class ViolationDTO:
    """Uniform violation contract returned by every gate parser."""

    file: str
    message: str
    line: int | None = None
    col: int | None = None
    rule: str | None = None
    fixable: bool = False
    severity: str | None = None


class JsonViolationsParsing(BaseModel):
    """JSON parsing strategy for structured gate output."""

    field_map: dict[str, str] = Field(..., min_length=1)
    violations_path: str | None = Field(default=None)
    line_offset: int = Field(default=0)
    fixable_when: str | None = Field(default=None)

    model_config = ConfigDict(extra="forbid", frozen=True)


class TextViolationsParsing(BaseModel):
    """Text parsing strategy for line-based gate output."""

    pattern: str = Field(...)
    severity_default: str = Field(default="error")
    defaults: dict[str, str] = Field(default_factory=dict)
    fixable_when: str | None = Field(default=None)

    @model_validator(mode="after")
    def _validate_defaults_placeholders(self) -> TextViolationsParsing:
        named_groups = set(re.findall(r"\(\?P<(\w+)>", self.pattern))
        unknown: list[str] = []
        for value in self.defaults.values():
            for token in re.findall(r"\{(\w+)\}", value):
                if token not in named_groups:
                    unknown.append(token)
        if unknown:
            raise ValueError(
                "defaults references placeholder(s) not in pattern named groups: "
                f"{', '.join(sorted(set(unknown)))}. Known groups: "
                f"{sorted(named_groups) or '(none)'}."
            )
        return self

    model_config = ConfigDict(extra="forbid", frozen=True)


class ExecutionConfig(BaseModel):
    """How to execute a gate tool."""

    command: list[str] = Field(..., min_length=1)
    timeout_seconds: int = Field(..., gt=0)
    working_dir: str | None = Field(default=None)

    model_config = ConfigDict(extra="forbid", frozen=True)


class SuccessCriteria(BaseModel):
    """Defines pass/fail criteria for a tool."""

    exit_codes_ok: list[int] = Field(default_factory=lambda: [0])
    max_errors: int | None = Field(default=None)
    min_score: float | None = Field(default=None)
    require_no_issues: bool = Field(default=True)

    model_config = ConfigDict(extra="forbid", frozen=True)


class GateScope(BaseModel):
    """File scope filtering for quality gates."""

    include_globs: list[str] = Field(default_factory=list)
    exclude_globs: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid", frozen=True)

    def filter_files(self, files: list[str]) -> list[str]:
        if not self.include_globs and not self.exclude_globs:
            return files

        include_patterns = list(self.include_globs)
        exclude_patterns = list(self.exclude_globs)
        filtered: list[str] = []
        for file_path in files:
            posix_path = Path(file_path).as_posix()
            if include_patterns and not any(
                fnmatch.fnmatch(posix_path, pattern) for pattern in include_patterns
            ):
                continue
            if exclude_patterns and any(
                fnmatch.fnmatch(posix_path, pattern) for pattern in exclude_patterns
            ):
                continue
            filtered.append(file_path)
        return filtered


class CapabilitiesMetadata(BaseModel):
    """Metadata about what a gate applies to and can do."""

    file_types: list[str] = Field(..., min_length=1)
    supports_autofix: bool
    parsing_strategy: Literal["json_violations", "text_violations"] | None = Field(default=None)
    json_violations: JsonViolationsParsing | None = Field(default=None)
    text_violations: TextViolationsParsing | None = Field(default=None)

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
    """Root quality gates configuration value object."""

    version: str = Field(..., min_length=1)
    active_gates: list[str] = Field(default_factory=list)
    artifact_logging: ArtifactLoggingConfig = Field(default_factory=ArtifactLoggingConfig)
    project_scope: GateScope | None = Field(default=None)
    gates: dict[str, QualityGate] = Field(..., min_length=1)

    model_config = ConfigDict(extra="forbid", frozen=True)
