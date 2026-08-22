# mcp_server/presenters/collection_text_renderer.py
# template=service version=5d5b489a created=2026-08-21T21:57Z updated=2026-08-21
"""Generic ordered-sequence presentation primitives.

@layer: Presenters
@responsibilities:
    - Classify supported list and variadic-tuple annotations
    - Format bounded flat scalar sequences
    - Render configured scalar and model collections depth-first
"""

from __future__ import annotations

import string
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum, StrEnum
from typing import Any, TypeGuard, get_args, get_origin

from pydantic import BaseModel

from mcp_server.config.schemas.presentation_config import (
    CollectionPresentationConfig,
    FormattingConfig,
)
from mcp_server.core.exceptions import ConfigError


class SequenceKind(StrEnum):
    """Supported ordered-sequence item categories."""

    SCALAR = "scalar"
    MODEL = "model"


@dataclass(frozen=True)
class SequenceShape:
    """Resolved category and item type for a supported annotation."""

    kind: SequenceKind
    item_type: type[object]


def _is_model_type(annotation: object) -> TypeGuard[type[BaseModel]]:
    return isinstance(annotation, type) and issubclass(annotation, BaseModel)


def _is_scalar_type(annotation: object) -> TypeGuard[type[object]]:
    if not isinstance(annotation, type):
        return False
    return annotation in {str, int, float, bool} or issubclass(annotation, Enum)


def classify_sequence_annotation(
    annotation: object,
    *,
    path: str,
) -> SequenceShape:
    """Classify an exact list[T] or variadic tuple[T, ...] annotation."""
    origin = get_origin(annotation)
    args = get_args(annotation)
    if (
        origin is list
        and len(args) == 1
        or origin is tuple
        and len(args) == 2
        and args[1] is Ellipsis
    ):
        item_type = args[0]
    else:
        raise ConfigError(
            f"Presentation field '{path}' must be annotated as list[T] or tuple[T, ...]"
        )

    if _is_scalar_type(item_type):
        return SequenceShape(SequenceKind.SCALAR, item_type)
    if _is_model_type(item_type):
        return SequenceShape(SequenceKind.MODEL, item_type)
    raise ConfigError(
        f"Presentation field '{path}' has unsupported ordered-sequence item type '{item_type}'"
    )


def _is_runtime_scalar(value: object) -> bool:
    return isinstance(value, (str, int, float, bool, Enum))


class SafeNoneFormatter(string.Formatter):
    """Format None and bounded flat scalar sequences without Python repr output."""

    def __init__(
        self,
        none_value: str = "-",
        *,
        formatting: FormattingConfig | None = None,
        max_items: int | None = None,
    ) -> None:
        super().__init__()
        self._formatting = formatting
        self._none_value = formatting.none_value if formatting else none_value
        self._max_items = max_items

    def format_field(self, value: object, format_spec: str) -> str:
        """Format one scalar value or supported ordered scalar sequence."""
        if value is None:
            return self._none_value
        if isinstance(value, (list, tuple)):
            return self._format_sequence(value)
        if isinstance(value, (set, dict, BaseModel)):
            raise ConfigError(
                "SafeNoneFormatter accepts only scalar values or flat scalar list/tuple sequences"
            )
        try:
            return str(super().format_field(value, format_spec))
        except (ValueError, TypeError):
            return str(value)

    def _format_sequence(self, values: Sequence[object]) -> str:
        if self._formatting is None or self._max_items is None:
            raise ConfigError(
                "Flat scalar sequence formatting requires formatting policy and max_items"
            )
        if not values:
            return self._none_value

        for index, value in enumerate(values):
            if not _is_runtime_scalar(value):
                raise ConfigError(
                    "SafeNoneFormatter accepts only flat scalar sequence items; "
                    f"invalid item at index {index}"
                )

        retained = [str(super().format_field(value, "")) for value in values[: self._max_items]]
        omitted_count = len(values) - len(retained)
        if omitted_count:
            retained.append(
                string.Formatter().format(
                    self._formatting.inline_sequence_omission_template,
                    omitted_count=omitted_count,
                )
            )
        return self._formatting.inline_sequence_separator.join(retained)


class CollectionTextRenderer:
    """Render configured ordered collections without tool- or DTO-specific policy."""

    def __init__(self, formatting: FormattingConfig) -> None:
        self._formatting = formatting

    def render(
        self,
        data: Mapping[str, Any],
        collections: tuple[CollectionPresentationConfig, ...],
        max_items: int,
    ) -> str:
        """Render sibling collection declarations in configured order."""
        if max_items <= 0:
            raise ConfigError("Collection max_items must be greater than zero")

        lines: list[str] = []
        for declaration in collections:
            lines.extend(
                self._render_collection(
                    data,
                    declaration=declaration,
                    max_items=max_items,
                    path=declaration.field,
                )
            )
        return "\n".join(lines)

    def _render_collection(
        self,
        data: Mapping[str, Any] | BaseModel,
        *,
        declaration: CollectionPresentationConfig,
        max_items: int,
        path: str,
    ) -> list[str]:
        container = self._read_field(data, declaration.field, path)
        if not isinstance(container, (list, tuple)):
            raise ConfigError(f"Collection runtime field '{path}' must be a list or tuple")
        if not container:
            return []

        placeholders = self._placeholders(declaration.item_template)
        expects_model = bool(declaration.children or set(placeholders) - {"item"})
        if not placeholders and container:
            expects_model = isinstance(container[0], (Mapping, BaseModel))

        self._validate_items(
            container,
            expects_model=expects_model,
            path=path,
        )

        lines: list[str] = []
        if declaration.heading is not None:
            lines.append(declaration.heading)

        formatter = SafeNoneFormatter(
            formatting=self._formatting,
            max_items=max_items,
        )
        retained = container[:max_items]
        for index, item in enumerate(retained):
            item_path = f"{path}[{index}]"
            if expects_model:
                item_values = item.model_dump() if isinstance(item, BaseModel) else dict(item)
                try:
                    lines.append(
                        formatter.format(
                            declaration.item_template,
                            **item_values,
                        )
                    )
                except KeyError as exc:
                    raise ConfigError(
                        f"Collection runtime item '{item_path}' is missing field '{exc.args[0]}'"
                    ) from exc

                for child in declaration.children:
                    lines.extend(
                        self._render_collection(
                            item,
                            declaration=child,
                            max_items=max_items,
                            path=f"{item_path}.{child.field}",
                        )
                    )
            else:
                lines.append(
                    formatter.format(
                        declaration.item_template,
                        item=item,
                    )
                )

        omitted_count = len(container) - len(retained)
        if omitted_count:
            omission = string.Formatter().format(
                self._formatting.collection_omission_template,
                omitted_count=omitted_count,
                field=declaration.field,
            )
            leading_space_count = len(declaration.item_template) - len(
                declaration.item_template.lstrip(" ")
            )
            lines.append(" " * leading_space_count + omission)
        return lines

    @staticmethod
    def _read_field(
        data: Mapping[str, Any] | BaseModel,
        field: str,
        path: str,
    ) -> object:
        if isinstance(data, BaseModel):
            if field not in type(data).model_fields:
                raise ConfigError(f"Collection runtime field '{path}' is missing")
            return getattr(data, field)
        if field not in data:
            raise ConfigError(f"Collection runtime field '{path}' is missing")
        return data[field]

    @staticmethod
    def _placeholders(template: str) -> list[str]:
        try:
            return [
                field_name.split(".")[0].split("[")[0]
                for _, field_name, _, _ in string.Formatter().parse(template)
                if field_name is not None
            ]
        except ValueError as exc:
            raise ConfigError(f"Invalid collection item template: {exc}") from exc

    @staticmethod
    def _validate_items(
        items: Sequence[object],
        *,
        expects_model: bool,
        path: str,
    ) -> None:
        for index, item in enumerate(items):
            item_path = f"{path}[{index}]"
            if expects_model:
                if not isinstance(item, (Mapping, BaseModel)):
                    raise ConfigError(
                        f"Collection runtime item '{item_path}' must be a model or mapping"
                    )
            elif not _is_runtime_scalar(item):
                raise ConfigError(f"Collection runtime item '{item_path}' must be scalar")
