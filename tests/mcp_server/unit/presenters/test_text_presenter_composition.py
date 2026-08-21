# tests/mcp_server/unit/presenters/test_text_presenter_composition.py
# template=unit_test version=8825c0bb created=2026-08-22T00:00Z updated=2026-08-22
"""Generic TextPresenter composition and boundary contract tests.

@layer: Tests (Unit)
@dependencies: [pydantic, text_presenter, response_presenter]
@responsibilities:
    - Verify semantic block order and final byte enforcement
    - Verify cache-publication fallback remains truthful and sanitized
    - Prove source DTOs and separately embedded resources remain complete
"""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel

from mcp_server.core.operation_notes import Note
from mcp_server.presenters.response_presenter import ResponsePresenter
from mcp_server.presenters.text_presenter import TextPresenter
from mcp_server.presenters.validation_resource_presenter import (
    ValidationResourcePresenter,
)
from mcp_server.schemas.cache_publication import CachePublication
from mcp_server.schemas.error_outputs import ValidationErrorOutput


class _Status(StrEnum):
    AVAILABLE = "available"
    MISSING = "missing"


class _Item(BaseModel):
    name: str
    tags: tuple[str, ...]


class _Output(BaseModel):
    success: bool = True
    name: str
    labels: tuple[str, ...]
    items: list[_Item]
    status: _Status
    payload: str


def _config(
    *,
    max_bytes: int = 800,
    tool_name: str = "synthetic_tool",
    template_success: str = "SCALAR {name}: {labels}",
) -> dict[str, Any]:
    return {
        "global": {
            "max_text_response_bytes": max_bytes,
            "emojis": {"query": "Q", "failure": "X"},
            "formatting": {
                "none_value": "-",
                "inline_sequence_separator": ", ",
                "inline_sequence_omission_template": "… {omitted_count} more",
                "collection_omission_template": "- … {omitted_count} more {field}",
                "truncation_notice": "[TRUNCATED]",
                "cache_unavailable_truncation_notice": "[CACHE UNAVAILABLE]",
            },
            "next_instruction_texts": {
                "instruction": "INSTRUCTION {name}",
                "uri_reference": "CACHE pgmcp://cache/runs/{run_id}",
                "cache_publication_failed": "FALLBACK",
            },
            "notes": {
                "groups": {
                    "suggestions": {
                        "emoji": "N",
                        "header": "NOTES",
                    }
                }
            },
        },
        "tools": {
            tool_name: {
                "category": "query",
                "max_items": 2,
                "template_success": template_success,
                "template_failure": "ERROR {error_message}",
                "collections": [
                    {
                        "field": "items",
                        "heading": "COLLECTION",
                        "item_template": "- ITEM {name}: {tags}",
                    }
                ],
                "enum_cases": [
                    {
                        "field": "status",
                        "cases": {"missing": "ENUM {name}"},
                    }
                ],
                "next_instructions": ["instruction"],
                "suggestions": {"composition_note": "NOTE {value}"},
            }
        },
    }


def _output(*, payload: str = "short") -> _Output:
    return _Output(
        name="sample",
        labels=("bug", "priority", "backend"),
        items=[
            _Item(name="first", tags=("a", "b", "c")),
            _Item(name="second", tags=("d",)),
        ],
        status=_Status.MISSING,
        payload=payload,
    )


class TestTextPresenterComposition:
    """Generic semantic block composition."""

    def test_orders_generic_blocks_and_preserves_source_dto(self) -> None:
        presenter = TextPresenter(config_data=_config())
        data = _output()
        before = data.model_dump()
        cache_pub = CachePublication(run_id="a" * 32, success=True)

        text = presenter.present_text(
            tool_name="synthetic_tool",
            data=data,
            notes=[Note(key="composition_note", params={"value": "present"})],
            cache_pub=cache_pub,
        )

        markers = [
            "SCALAR",
            "ENUM",
            "COLLECTION",
            "INSTRUCTION",
            "NOTES",
            "CACHE pgmcp://cache/runs/",
        ]
        positions = [text.index(marker) for marker in markers]
        assert positions == sorted(positions)
        assert "bug, priority, … 1 more" in text
        assert "- ITEM first: a, b, … 1 more" in text
        assert data.model_dump() == before

    def test_final_limiter_keeps_one_complete_cache_uri(self) -> None:
        presenter = TextPresenter(
            config_data=_config(
                max_bytes=180,
                template_success="SCALAR {payload}",
            )
        )
        cache_pub = CachePublication(run_id="b" * 32, success=True)

        text = presenter.present_text(
            tool_name="synthetic_tool",
            data=_output(payload="🚀" * 300),
            cache_pub=cache_pub,
        )

        cache_reference = "CACHE pgmcp://cache/runs/" + "b" * 32
        assert len(text.encode("utf-8")) <= 180
        assert text.count(cache_reference) == 1
        assert "[TRUNCATED]" in text
        assert "�" not in text

    def test_large_cache_failure_fallback_is_last_and_truthful(self) -> None:
        presenter = TextPresenter(
            config_data=_config(
                max_bytes=160,
                template_success="SCALAR {payload}",
            )
        )

        text = presenter.present_text(
            tool_name="synthetic_tool",
            data=_output(payload="secret-safe " * 200),
            cache_pub=CachePublication(
                run_id=None,
                success=False,
                error_code="write_failed",
            ),
        )

        assert len(text.encode("utf-8")) <= 160
        assert "[CACHE UNAVAILABLE]" in text
        assert "[TRUNCATED]" not in text
        assert "pgmcp://cache/runs/" not in text

    def test_response_resource_remains_complete_outside_text_budget(self) -> None:
        tool_name = "validation_tool"
        config = _config(
            max_bytes=150,
            tool_name=tool_name,
            template_success="UNUSED",
        )
        config["tools"][tool_name]["collections"] = []
        config["tools"][tool_name]["enum_cases"] = []
        config["tools"][tool_name]["next_instructions"] = []
        config["tools"][tool_name]["max_items"] = None
        presenter = ResponsePresenter(
            text_presenter=TextPresenter(config_data=config),
            resource_presenter=ValidationResourcePresenter(),
        )
        schema = {
            "type": "object",
            "properties": {f"field_{index}": {"type": "string"} for index in range(100)},
        }
        data = ValidationErrorOutput(
            error_message="x" * 1_000,
            validation_errors=[],
            input_schema=schema,
        )

        output = presenter.present(
            tool_name=tool_name,
            data=data,
            success=False,
            cache_pub=CachePublication(run_id="c" * 32, success=True),
        )

        assert len(output.text.encode("utf-8")) <= 150
        assert output.resources[0].content
        assert '"field_99"' in output.resources[0].content
        assert data.input_schema == schema
