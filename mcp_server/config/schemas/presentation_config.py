# mcp_server/config/schemas/presentation_config.py
# template=schema version=74378193 created=2026-06-12T20:49Z updated=2026-08-21
"""PresentationConfig schema.

@layer: Config
"""

from __future__ import annotations

import string
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


def _validate_placeholders(
    template: str,
    *,
    allowed: frozenset[str],
    field_name: str,
) -> None:
    """Reject invalid or unsupported placeholders in a presentation template."""
    try:
        placeholders = {
            placeholder.split(".")[0].split("[")[0]
            for _, placeholder, _, _ in string.Formatter().parse(template)
            if placeholder is not None
        }
    except ValueError as exc:
        raise ValueError(f"{field_name} has invalid placeholder syntax: {exc}") from exc

    unsupported = placeholders - allowed
    if unsupported:
        rendered = ", ".join(sorted(unsupported))
        raise ValueError(f"{field_name} contains unsupported placeholder(s): {rendered}")


class FormattingConfig(BaseModel):
    """Formatting settings for text presentation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    none_value: str = "-"
    inline_sequence_separator: str = ", "
    inline_sequence_omission_template: str
    collection_omission_template: str
    truncation_notice: str
    cache_unavailable_truncation_notice: str

    @model_validator(mode="after")
    def validate_templates(self) -> FormattingConfig:
        """Validate the deliberately small generic formatting vocabulary."""
        _validate_placeholders(
            self.inline_sequence_omission_template,
            allowed=frozenset({"omitted_count"}),
            field_name="inline_sequence_omission_template",
        )
        _validate_placeholders(
            self.collection_omission_template,
            allowed=frozenset({"omitted_count", "field"}),
            field_name="collection_omission_template",
        )
        _validate_placeholders(
            self.truncation_notice,
            allowed=frozenset(),
            field_name="truncation_notice",
        )
        _validate_placeholders(
            self.cache_unavailable_truncation_notice,
            allowed=frozenset(),
            field_name="cache_unavailable_truncation_notice",
        )
        return self


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


class CollectionPresentationConfig(BaseModel):
    """Declarative rendering policy for one direct ordered-sequence field."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    field: str = Field(min_length=1)
    heading: str | None = None
    item_template: str
    children: tuple[CollectionPresentationConfig, ...] = ()

    @model_validator(mode="after")
    def validate_children(self) -> CollectionPresentationConfig:
        """Require unique direct child declarations."""
        child_fields = [child.field for child in self.children]
        if len(child_fields) != len(set(child_fields)):
            raise ValueError(f"Collection '{self.field}' has duplicate child field declarations")
        return self


class EnumCasePresentationConfig(BaseModel):
    """Declarative text blocks selected by a serialized enum value."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    field: str = Field(min_length=1)
    cases: dict[str, str] = Field(min_length=1)


class GlobalPresentationConfig(BaseModel):
    """Global presentation settings."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    emojis: dict[str, str] = Field(default_factory=dict)
    default_failure_template: str = "Failed: {error_message}"
    next_instruction_texts: dict[str, str] = Field(default_factory=dict)
    formatting: FormattingConfig
    notes: GlobalNotesConfig = Field(default_factory=GlobalNotesConfig)
    failures: dict[str, str] = Field(default_factory=dict)
    max_text_response_bytes: int = Field(default=8_000, gt=0)

    @model_validator(mode="after")
    def validate_text_budget(self) -> GlobalPresentationConfig:
        """Ensure the byte ceiling can always retain the mandatory cache tail."""
        uri_template = self.next_instruction_texts.get("uri_reference", "")
        try:
            cache_reference = uri_template.format(run_id="x" * 32)
        except (KeyError, ValueError) as exc:
            raise ValueError(
                f"next_instruction_texts.uri_reference has invalid placeholder syntax: {exc}"
            ) from exc

        mandatory_tail = (
            f"{self.formatting.truncation_notice}\n\n{cache_reference}"
            if cache_reference
            else self.formatting.truncation_notice
        )
        if len(mandatory_tail.encode("utf-8")) > self.max_text_response_bytes:
            raise ValueError(
                "max_text_response_bytes budget cannot contain the truncation notice "
                "and fixed-shape cache reference"
            )
        return self


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
    max_items: int | None = Field(default=None, gt=0)
    collections: tuple[CollectionPresentationConfig, ...] = ()
    enum_cases: tuple[EnumCasePresentationConfig, ...] = ()

    @model_validator(mode="after")
    def validate_declaration_identity(self) -> ToolPresentationConfig:
        """Reject ambiguous sibling declarations before runtime assembly."""
        collection_fields = [collection.field for collection in self.collections]
        if len(collection_fields) != len(set(collection_fields)):
            raise ValueError("Tool has duplicate collection field declarations")

        enum_fields = [enum_case.field for enum_case in self.enum_cases]
        if len(enum_fields) != len(set(enum_fields)):
            raise ValueError("Tool has duplicate enum-case field declarations")
        return self


class PresentationConfig(BaseModel):
    """Unified configuration for declarative text presentation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    version: Literal["1.0.0"] = Field("1.0.0", description="Config schema version")
    global_settings: GlobalPresentationConfig = Field(alias="global")
    tools: dict[str, ToolPresentationConfig] = Field(default_factory=dict)
