# mcp_server/config/schemas/presentation_config.py
# template=schema version=74378193 created=2026-06-12T20:49Z updated=2026-06-12T21:00Z
"""PresentationConfig schema.

@layer: Config
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class FormattingConfig(BaseModel):
    """Formatting settings for text presentation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    none_value: str = "-"


class NoteGroupConfig(BaseModel):
    """Configuration for a note group."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    emoji: str
    header: str


class GlobalNotesConfig(BaseModel):
    """Global notes settings."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    groups: dict[str, NoteGroupConfig] = Field(default_factory=dict)
    templates: dict[str, dict[str, str]] = Field(default_factory=dict)


class GlobalPresentationConfig(BaseModel):
    """Global presentation settings."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    emojis: dict[str, str] = Field(default_factory=dict)
    default_failure_template: str = "Failed: {error_message}"
    next_instruction_texts: dict[str, str] = Field(default_factory=dict)
    formatting: FormattingConfig = Field(default_factory=FormattingConfig)
    notes: GlobalNotesConfig = Field(default_factory=GlobalNotesConfig)
    failures: dict[str, str] = Field(default_factory=dict)


class ToolPresentationConfig(BaseModel):
    """Presentation settings for a specific tool."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    category: str | None = None
    template_success: str | None = None
    template_failure: str | None = None
    next_instructions: list[str] = Field(default_factory=list)
    exclusions: dict[str, str] = Field(default_factory=dict)
    suggestions: dict[str, str] = Field(default_factory=dict)
    recoveries: dict[str, str] = Field(default_factory=dict)
    info: dict[str, str] = Field(default_factory=dict)


class PresentationConfig(BaseModel):
    """Unified configuration for declarative text presentation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    version: Literal["1.0.0"] = Field("1.0.0", description="Config schema version")
    global_settings: GlobalPresentationConfig = Field(alias="global")
    tools: dict[str, ToolPresentationConfig] = Field(default_factory=dict)
