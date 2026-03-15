"""Pure scaffold metadata schema definitions."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class CommentPattern(BaseModel):
    """Defines how to detect 2-line SCAFFOLD metadata in one comment syntax."""

    syntax: Literal["hash", "double_slash", "html_comment", "jinja_comment"] = Field(
        description="Comment syntax identifier"
    )
    prefix: str = Field(min_length=1, description="Regex pattern matching comment prefix")
    filepath_line_regex: str = Field(min_length=1, description="Regex pattern matching line 1")
    metadata_line_regex: str = Field(min_length=1, description="Regex pattern matching line 2")
    extensions: list[str] = Field(default_factory=list)

    @field_validator("prefix", "filepath_line_regex", "metadata_line_regex")
    @classmethod
    def validate_regex_pattern(cls, value: str) -> str:
        try:
            re.compile(value)
        except re.error as exc:
            raise ValueError(f"Invalid regex pattern: {value}\nError: {exc}") from exc
        return value


class MetadataField(BaseModel):
    """Defines one metadata field with validation rules."""

    name: str = Field(min_length=1, description="Field name")
    format_regex: str = Field(min_length=1, description="Regex pattern for field value validation")
    required: bool = Field(description="Whether field must be present")

    @field_validator("format_regex")
    @classmethod
    def validate_regex_pattern(cls, value: str) -> str:
        try:
            re.compile(value)
        except re.error as exc:
            raise ValueError(f"Invalid regex pattern: {value}\nError: {exc}") from exc
        return value


class ScaffoldMetadataConfig(BaseModel):
    """Configuration value object for scaffold metadata."""

    version: str = Field(
        default="1.0",
        description="Config schema version for future migrations",
    )
    comment_patterns: list[CommentPattern] = Field(
        min_length=1,
        description="Supported comment syntaxes",
    )
    metadata_fields: list[MetadataField] = Field(
        min_length=1,
        description="Metadata field definitions",
    )

    def get_pattern(self, syntax: str) -> CommentPattern | None:
        return next(
            (pattern for pattern in self.comment_patterns if pattern.syntax == syntax),
            None,
        )

    def get_field(self, name: str) -> MetadataField | None:
        return next(
            (field for field in self.metadata_fields if field.name == name),
            None,
        )
