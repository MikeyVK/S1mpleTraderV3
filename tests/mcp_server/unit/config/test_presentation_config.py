# tests/mcp_server/unit/config/test_presentation_config.py
# template=unit_test version=3d15d309 created=2026-08-21T00:00Z updated=2026-08-21
"""Presentation configuration and startup alignment contract tests.

@layer: Tests (Unit)
@dependencies: [pytest, pydantic, presentation_config, text_presenter]
@responsibilities:
    - Verify frozen declarative presentation policy
    - Verify complete supported-catalog startup alignment
    - Verify generic ordered-sequence, collection, enum, and budget contracts
"""

from enum import Enum
from typing import Any

import pytest
from pydantic import BaseModel, ValidationError

from mcp_server.bootstrap import SupportedToolContract
from mcp_server.config.schemas.presentation_config import PresentationConfig
from mcp_server.core.exceptions import ConfigError
from mcp_server.presenters.text_presenter import (
    TextPresenter,
    validate_presentation_alignment,
)


class _Status(str, Enum):
    AVAILABLE = "available"
    MISSING = "missing"


class _GrandChild(BaseModel):
    code: str


class _Child(BaseModel):
    name: str
    tags: tuple[str, ...]
    grandchildren: list[_GrandChild]


class _Output(BaseModel):
    title: str
    labels: list[str]
    codes: tuple[str, ...]
    children: list[_Child]
    status: _Status
    unsupported: set[str]


class _OtherOutput(BaseModel):
    value: str


def _global_config(max_bytes: int = 8_000) -> dict[str, Any]:
    return {
        "max_text_response_bytes": max_bytes,
        "formatting": {
            "none_value": "-",
            "inline_sequence_separator": ", ",
            "inline_sequence_omission_template": "… {omitted_count} more",
            "collection_omission_template": "- … {omitted_count} more {field}",
            "truncation_notice": "Output truncated; complete details are cached.",
            "cache_unavailable_truncation_notice": (
                "Output truncated; complete details are unavailable."
            ),
        },
        "next_instruction_texts": {
            "uri_reference": (
                "View resource: pgmcp://cache/runs/{run_id}"
            )
        },
    }


def _tool_config(**overrides: Any) -> dict[str, Any]:
    config: dict[str, Any] = {"template_success": "{title}"}
    config.update(overrides)
    return config


def _presenter(
    tools: dict[str, dict[str, Any]],
    *,
    max_bytes: int = 8_000,
) -> TextPresenter:
    return TextPresenter(
        config_data={
            "global": _global_config(max_bytes),
            "tools": tools,
        }
    )


def _contracts() -> tuple[SupportedToolContract, ...]:
    return (
        SupportedToolContract(name="sample", output_model=_Output),
        SupportedToolContract(name="other", output_model=_OtherOutput),
    )


class TestPresentationConfig:
    """Frozen schema and cross-field policy behavior."""

    def test_loads_recursive_list_tuple_and_enum_policy_as_frozen_models(self) -> None:
        config = PresentationConfig.model_validate(
            {
                "global": _global_config(),
                "tools": {
                    "sample": _tool_config(
                        max_items=3,
                        template_success="{title}: {labels} / {codes}",
                        collections=[
                            {
                                "field": "children",
                                "heading": "Children",
                                "item_template": "- {name}: {tags}",
                                "children": [
                                    {
                                        "field": "grandchildren",
                                        "item_template": "  - {code}",
                                    }
                                ],
                            }
                        ],
                        enum_cases=[
                            {
                                "field": "status",
                                "cases": {"missing": "Missing: {title}"},
                            }
                        ],
                    )
                },
            }
        )

        tool = config.tools["sample"]
        assert tool.max_items == 3
        assert tool.collections[0].children[0].field == "grandchildren"
        assert tool.enum_cases[0].cases == {"missing": "Missing: {title}"}
        with pytest.raises(ValidationError):
            tool.max_items = 4  # type: ignore[misc]

    @pytest.mark.parametrize(
        "formatting_update",
        [
            {"inline_sequence_omission_template": "{field}"},
            {"collection_omission_template": "{unknown}"},
            {"truncation_notice": "{run_id}"},
            {"cache_unavailable_truncation_notice": "{unknown}"},
        ],
    )
    def test_rejects_invalid_generic_formatting_placeholders(
        self,
        formatting_update: dict[str, str],
    ) -> None:
        global_config = _global_config()
        global_config["formatting"].update(formatting_update)

        with pytest.raises(ValidationError, match="placeholder"):
            PresentationConfig.model_validate(
                {"global": global_config, "tools": {}}
            )

    def test_rejects_budget_that_cannot_hold_notice_and_cache_reference(self) -> None:
        with pytest.raises(ValidationError, match="budget"):
            PresentationConfig.model_validate(
                {"global": _global_config(max_bytes=20), "tools": {}}
            )


class TestPresentationAlignment:
    """Complete supported-catalog and recursive output-model alignment."""

    def test_accepts_complete_catalog_including_non_active_contract(self) -> None:
        presenter = _presenter(
            {
                "sample": _tool_config(),
                "other": {"template_success": "{value}"},
            }
        )

        validate_presentation_alignment(presenter, _contracts())

    @pytest.mark.parametrize(
        ("tools", "message"),
        [
            ({"sample": _tool_config()}, "other"),
            (
                {
                    "sample": _tool_config(),
                    "other": {"template_success": "{value}"},
                    "obsolete": {"template_success": "obsolete"},
                },
                "obsolete",
            ),
        ],
    )
    def test_rejects_missing_or_unknown_catalog_keys(
        self,
        tools: dict[str, dict[str, Any]],
        message: str,
    ) -> None:
        with pytest.raises(ConfigError, match=message):
            validate_presentation_alignment(_presenter(tools), _contracts())

    def test_rejects_duplicate_supported_identity(self) -> None:
        duplicate_contracts = (
            SupportedToolContract(name="sample", output_model=_Output),
            SupportedToolContract(name="sample", output_model=_OtherOutput),
        )

        with pytest.raises(ConfigError, match="Duplicate"):
            validate_presentation_alignment(
                _presenter({"sample": _tool_config()}),
                duplicate_contracts,
            )

    def test_validates_every_supported_model_even_when_not_active(self) -> None:
        presenter = _presenter(
            {
                "sample": _tool_config(),
                "other": {"template_success": "{missing_field}"},
            }
        )

        with pytest.raises(ConfigError, match="other"):
            validate_presentation_alignment(presenter, _contracts())

    def test_accepts_scalar_sequences_recursive_models_and_enum_cases(self) -> None:
        presenter = _presenter(
            {
                "sample": _tool_config(
                    max_items=2,
                    template_success="{title}: {labels} / {codes}",
                    collections=[
                        {
                            "field": "children",
                            "heading": "Children",
                            "item_template": "- {name}: {tags}",
                            "children": [
                                {
                                    "field": "grandchildren",
                                    "item_template": "  - {code}",
                                }
                            ],
                        }
                    ],
                    enum_cases=[
                        {
                            "field": "status",
                            "cases": {"missing": "Missing: {title}"},
                        }
                    ],
                ),
                "other": {"template_success": "{value}"},
            }
        )

        validate_presentation_alignment(presenter, _contracts())

    @pytest.mark.parametrize(
        "sample_config",
        [
            _tool_config(template_success="{labels}"),
            _tool_config(max_items=2),
            _tool_config(
                max_items=2,
                collections=[{"field": "title", "item_template": "{item}"}],
            ),
            _tool_config(
                max_items=2,
                collections=[{"field": "children.name", "item_template": "{item}"}],
            ),
            _tool_config(
                max_items=2,
                collections=[{"field": "children", "item_template": "{unknown}"}],
            ),
            _tool_config(max_items=2, template_success="{children}"),
            _tool_config(
                max_items=2,
                collections=[{"field": "unsupported", "item_template": "{item}"}],
            ),
            _tool_config(
                max_items=2,
                collections=[
                    {
                        "field": "labels",
                        "item_template": "{item}",
                        "children": [
                            {"field": "anything", "item_template": "{item}"}
                        ],
                    }
                ],
            ),
            _tool_config(
                enum_cases=[
                    {
                        "field": "status",
                        "cases": {"unknown": "Unknown: {title}"},
                    }
                ]
            ),
        ],
    )
    def test_rejects_invalid_sequence_collection_and_enum_contracts(
        self,
        sample_config: dict[str, Any],
    ) -> None:
        presenter = _presenter(
            {
                "sample": sample_config,
                "other": {"template_success": "{value}"},
            }
        )

        with pytest.raises(ConfigError):
            validate_presentation_alignment(presenter, _contracts())
