"""Tests for C2 A2 static Pydantic model-level constraints.

Covers:
- ForcePhaseTransitionInput: skip_reason and human_approval_message have minLength=1 in JSON schema
- CreateLabelInput: name pattern and color pattern constraints

@dependencies: phase_tools, label_tools, project_tools
"""

import pytest
from pydantic import ValidationError

from mcp_server.tools.cycle_tools import ForceCycleTransitionInput
from mcp_server.tools.label_tools import CreateLabelInput
from mcp_server.tools.phase_tools import ForcePhaseTransitionInput


class TestForcePhaseTransitionInputSchema:
    """C2.D1: skip_reason and human_approval_message have minLength=1 in JSON schema."""

    def test_skip_reason_has_min_length_in_schema(self) -> None:
        schema = ForcePhaseTransitionInput.model_json_schema()
        assert schema["properties"]["skip_reason"].get("minLength") == 1

    def test_human_approval_message_has_min_length_in_schema(self) -> None:
        schema = ForcePhaseTransitionInput.model_json_schema()
        assert schema["properties"]["human_approval_message"].get("minLength") == 1


class TestForceCycleTransitionInputSchema:
    """C3: skip_reason and human_approval_message have minLength=1 in JSON schema

    for cycle tools.
    """

    def test_skip_reason_has_min_length_in_schema(self) -> None:
        schema = ForceCycleTransitionInput.model_json_schema()
        assert schema["properties"]["skip_reason"].get("minLength") == 1

    def test_human_approval_message_has_min_length_in_schema(self) -> None:
        schema = ForceCycleTransitionInput.model_json_schema()
        assert schema["properties"]["human_approval_message"].get("minLength") == 1


class TestCreateLabelInputConstraints:
    """C2.D2+D3: CreateLabelInput name and color reject invalid patterns at model level."""

    def test_name_rejects_no_category_prefix(self) -> None:
        with pytest.raises(ValidationError, match="pattern"):
            CreateLabelInput(name="invalidnamenocategory", color="1D76DB")

    def test_name_rejects_unknown_category(self) -> None:
        with pytest.raises(ValidationError, match="pattern"):
            CreateLabelInput(name="unknown:feature", color="1D76DB")

    def test_name_rejects_uppercase_value(self) -> None:
        with pytest.raises(ValidationError, match="pattern"):
            CreateLabelInput(name="type:Feature", color="1D76DB")

    def test_color_rejects_non_hex_characters(self) -> None:
        with pytest.raises(ValidationError, match="pattern"):
            CreateLabelInput(name="type:feature", color="GGGGGG")

    def test_color_rejects_hash_prefix(self) -> None:
        with pytest.raises(ValidationError, match="pattern"):
            CreateLabelInput(name="type:feature", color="#1D76DB")

    def test_valid_name_and_color_accepted(self) -> None:
        label = CreateLabelInput(name="type:feature", color="1D76DB")
        assert label.name == "type:feature"
        assert label.color == "1D76DB"

    def test_all_valid_categories_accepted(self) -> None:
        categories = (
            "type",
            "priority",
            "status",
            "phase",
            "scope",
            "component",
            "effort",
            "parent",
        )
        for category in categories:
            label = CreateLabelInput(name=f"{category}:value", color="0e8a16")
            assert label.name.startswith(category)
