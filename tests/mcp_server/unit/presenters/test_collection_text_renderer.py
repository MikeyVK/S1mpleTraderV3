# tests/mcp_server/unit/presenters/test_collection_text_renderer.py
# template=unit_test version=8825c0bb created=2026-08-21T21:57Z updated=2026-08-21
"""Generic ordered-sequence and collection presentation contract tests.

@layer: Tests (Unit)
@dependencies: [pytest, pydantic, collection_text_renderer]
@responsibilities:
    - Verify shared list and variadic-tuple annotation classification
    - Verify bounded flat scalar formatting
    - Verify depth-first scalar/model collection rendering
    - Reject malformed runtime shapes with field, path, and item-index context
"""

from enum import StrEnum
from typing import Any

import pytest
from pydantic import BaseModel

from mcp_server.config.schemas.presentation_config import (
    CollectionPresentationConfig,
    FormattingConfig,
)
from mcp_server.core.exceptions import ConfigError
from mcp_server.presenters.collection_text_renderer import (
    CollectionTextRenderer,
    SafeNoneFormatter,
    SequenceKind,
    classify_sequence_annotation,
)


class _State(StrEnum):
    OPEN = "open"
    CLOSED = "closed"


class _Task(BaseModel):
    name: str
    tags: tuple[str, ...]


class _Phase(BaseModel):
    name: str
    tasks: list[_Task]


def _formatting() -> FormattingConfig:
    return FormattingConfig(
        none_value="-",
        inline_sequence_separator=" | ",
        inline_sequence_omission_template="… {omitted_count} more",
        collection_omission_template="- … {omitted_count} more {field}",
        truncation_notice="Output truncated.",
        cache_unavailable_truncation_notice="Output unavailable.",
    )


def _collection(**overrides: Any) -> CollectionPresentationConfig:
    values: dict[str, Any] = {
        "field": "phases",
        "heading": "Phases",
        "item_template": "- {name}",
        "children": [
            {
                "field": "tasks",
                "heading": "  Tasks",
                "item_template": "  - {name}: {tags}",
            }
        ],
    }
    values.update(overrides)
    return CollectionPresentationConfig.model_validate(values)


class TestSequenceClassification:
    """Shared annotation classification."""

    @pytest.mark.parametrize(
        ("annotation", "kind", "item_type"),
        [
            (list[str], SequenceKind.SCALAR, str),
            (tuple[_State, ...], SequenceKind.SCALAR, _State),
            (list[_Phase], SequenceKind.MODEL, _Phase),
            (tuple[_Task, ...], SequenceKind.MODEL, _Task),
        ],
    )
    def test_classifies_only_supported_ordered_sequences(
        self,
        annotation: object,
        kind: SequenceKind,
        item_type: type[object],
    ) -> None:
        shape = classify_sequence_annotation(annotation, path="result.items")

        assert shape.kind is kind
        assert shape.item_type is item_type

    @pytest.mark.parametrize(
        "annotation",
        [set[str], dict[str, str], tuple[str, str], list[list[str]], str],
    )
    def test_rejects_unsupported_annotations(self, annotation: object) -> None:
        with pytest.raises(ConfigError, match="result.items"):
            classify_sequence_annotation(annotation, path="result.items")


class TestSafeNoneFormatter:
    """Generic scalar and flat-sequence formatting."""

    @pytest.mark.parametrize("value", [["α", "β", "γ"], ("α", "β", "γ")])
    def test_bounds_list_and_tuple_without_losing_source_order(
        self,
        value: list[str] | tuple[str, ...],
    ) -> None:
        formatter = SafeNoneFormatter(
            formatting=_formatting(),
            max_items=2,
        )

        assert formatter.format("{value}", value=value) == "α | β | … 1 more"

    def test_handles_none_empty_and_exact_limit_without_repr_noise(self) -> None:
        formatter = SafeNoneFormatter(formatting=_formatting(), max_items=2)

        assert formatter.format("{value}", value=None) == "-"
        assert formatter.format("{value}", value=[]) == "-"
        assert formatter.format("{value}", value=("a", "b")) == "a | b"

    @pytest.mark.parametrize("value", [{"a", "b"}, [{"nested": "value"}]])
    def test_rejects_unsupported_runtime_values(self, value: object) -> None:
        formatter = SafeNoneFormatter(formatting=_formatting(), max_items=2)

        with pytest.raises(ConfigError, match="flat scalar"):
            formatter.format("{value}", value=value)


class TestCollectionTextRenderer:
    """Depth-first configured collection rendering."""

    def test_renders_nested_models_depth_first_for_list_and_tuple(self) -> None:
        phases = (
            _Phase(
                name="Research",
                tasks=[
                    _Task(name="Inspect", tags=("code", "docs", "tests")),
                    _Task(name="Decide", tags=("strategy",)),
                ],
            ),
            _Phase(name="Design", tasks=[]),
        )
        renderer = CollectionTextRenderer(_formatting())

        text = renderer.render(
            {"phases": phases},
            collections=(_collection(),),
            max_items=2,
        )

        assert text.splitlines() == [
            "Phases",
            "- Research",
            "  Tasks",
            "  - Inspect: code | docs | … 1 more",
            "  - Decide: strategy",
            "- Design",
        ]

    def test_renders_sibling_scalar_collections_with_independent_limits(self) -> None:
        renderer = CollectionTextRenderer(_formatting())
        collections = (
            CollectionPresentationConfig(
                field="labels",
                heading="Labels",
                item_template="- {item}",
            ),
            CollectionPresentationConfig(
                field="codes",
                heading="Codes",
                item_template="- {item}",
            ),
        )

        text = renderer.render(
            {"labels": ["bug", "high", "backend"], "codes": ("A", "B", "C")},
            collections=collections,
            max_items=2,
        )

        assert text.splitlines() == [
            "Labels",
            "- bug",
            "- high",
            "- … 1 more labels",
            "Codes",
            "- A",
            "- B",
            "- … 1 more codes",
        ]

    def test_omits_empty_collection_and_heading(self) -> None:
        renderer = CollectionTextRenderer(_formatting())

        assert (
            renderer.render(
                {"labels": []},
                collections=(
                    CollectionPresentationConfig(
                        field="labels",
                        heading="Labels",
                        item_template="- {item}",
                    ),
                ),
                max_items=2,
            )
            == ""
        )

    @pytest.mark.parametrize(
        ("data", "declaration", "match"),
        [
            ({}, _collection(), "phases"),
            ({"phases": {"not": "ordered"}}, _collection(), "phases"),
            (
                {"labels": ["ok", {"wrong": "type"}]},
                CollectionPresentationConfig(
                    field="labels",
                    item_template="- {item}",
                ),
                r"labels\[1\]",
            ),
            (
                {"phases": ["wrong"]},
                _collection(),
                r"phases\[0\]",
            ),
            (
                {
                    "phases": [
                        {
                            "name": "Research",
                            "tasks": [42],
                        }
                    ]
                },
                _collection(),
                r"phases\[0\]\.tasks\[0\]",
            ),
        ],
    )
    def test_rejects_missing_invalid_and_wrongly_typed_runtime_shapes(
        self,
        data: dict[str, object],
        declaration: CollectionPresentationConfig,
        match: str,
    ) -> None:
        renderer = CollectionTextRenderer(_formatting())

        with pytest.raises(ConfigError, match=match):
            renderer.render(
                data,
                collections=(declaration,),
                max_items=2,
            )
