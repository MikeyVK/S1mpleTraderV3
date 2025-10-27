"""
Unit tests for SizePlan DTO.

Tests creation, validation, and edge cases for lean position sizing output.
SizePlan represents HOW MUCH (absolute position sizing only).
"""
# pyright: reportCallIssue=false, reportAttributeAccessIssue=false
# Suppress Pydantic FieldInfo false positives for optional fields
# type: ignore[union-attr]

from decimal import Decimal

import pytest
from pydantic import ValidationError

from backend.dtos.strategy.size_plan import SizePlan


class TestSizePlanCreation:
    """Test SizePlan instantiation with lean spec."""

    def test_minimal_size_plan(self):
        """Can create minimal size plan with required fields."""
        plan = SizePlan(
            position_size=Decimal("0.5"),
            position_value=Decimal("50000.00"),
            risk_amount=Decimal("1000.00")
        )

        assert plan.position_size == Decimal("0.5")
        assert plan.position_value == Decimal("50000.00")
        assert plan.risk_amount == Decimal("1000.00")
        assert plan.leverage == Decimal("1.0")  # Default
        # Check plan_id prefix
        plan_id = str(plan.plan_id)
        assert plan_id.startswith("SIZ_")

    def test_complete_size_plan_with_leverage(self):
        """Can create complete size plan with custom leverage."""
        plan = SizePlan(
            position_size=Decimal("1.0"),
            position_value=Decimal("100000.00"),
            risk_amount=Decimal("2000.00"),
            leverage=Decimal("2.0")
        )

        assert plan.position_size == Decimal("1.0")
        assert plan.position_value == Decimal("100000.00")
        assert plan.risk_amount == Decimal("2000.00")
        assert plan.leverage == Decimal("2.0")


class TestSizePlanValidation:
    """Test SizePlan validation rules."""

    def test_requires_position_size(self):
        """position_size is required."""
        with pytest.raises(ValidationError) as exc_info:
            SizePlan(
                position_value=Decimal("50000.00"),
                risk_amount=Decimal("1000.00")
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("position_size",) for e in errors)

    def test_requires_position_value(self):
        """position_value is required."""
        with pytest.raises(ValidationError) as exc_info:
            SizePlan(
                position_size=Decimal("0.5"),
                risk_amount=Decimal("1000.00")
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("position_value",) for e in errors)

    def test_requires_risk_amount(self):
        """risk_amount is required."""
        with pytest.raises(ValidationError) as exc_info:
            SizePlan(
                position_size=Decimal("0.5"),
                position_value=Decimal("50000.00")
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("risk_amount",) for e in errors)

    def test_position_size_must_be_positive(self):
        """position_size must be > 0."""
        with pytest.raises(ValidationError):
            SizePlan(
                position_size=Decimal("0.0"),
                position_value=Decimal("50000.00"),
                risk_amount=Decimal("1000.00")
            )

        with pytest.raises(ValidationError):
            SizePlan(
                position_size=Decimal("-0.5"),
                position_value=Decimal("50000.00"),
                risk_amount=Decimal("1000.00")
            )

    def test_position_value_must_be_positive(self):
        """position_value must be > 0."""
        with pytest.raises(ValidationError):
            SizePlan(
                position_size=Decimal("0.5"),
                position_value=Decimal("0.0"),
                risk_amount=Decimal("1000.00")
            )

    def test_risk_amount_must_be_positive(self):
        """risk_amount must be > 0."""
        with pytest.raises(ValidationError):
            SizePlan(
                position_size=Decimal("0.5"),
                position_value=Decimal("50000.00"),
                risk_amount=Decimal("0.0")
            )

    def test_leverage_must_be_positive(self):
        """leverage must be >= 1.0."""
        with pytest.raises(ValidationError):
            SizePlan(
                position_size=Decimal("0.5"),
                position_value=Decimal("50000.00"),
                risk_amount=Decimal("1000.00"),
                leverage=Decimal("0.5")
            )


class TestSizePlanDefaultValues:
    """Test SizePlan default value behavior."""

    def test_auto_generates_plan_id(self):
        """plan_id is auto-generated with SIZ_ prefix."""
        plan1 = SizePlan(
            position_size=Decimal("0.5"),
            position_value=Decimal("50000.00"),
            risk_amount=Decimal("1000.00")
        )
        plan2 = SizePlan(
            position_size=Decimal("0.5"),
            position_value=Decimal("50000.00"),
            risk_amount=Decimal("1000.00")
        )

        # Check unique plan IDs
        plan1_id = str(plan1.plan_id)
        plan2_id = str(plan2.plan_id)
        assert plan1_id.startswith("SIZ_")
        assert plan2_id.startswith("SIZ_")
        assert plan1_id != plan2_id

    def test_leverage_defaults_to_one(self):
        """leverage defaults to 1.0 (no leverage)."""
        plan = SizePlan(
            position_size=Decimal("0.5"),
            position_value=Decimal("50000.00"),
            risk_amount=Decimal("1000.00")
        )

        assert plan.leverage == Decimal("1.0")


class TestSizePlanSerialization:
    """Test SizePlan serialization."""

    def test_can_serialize_to_dict(self):
        """Can serialize SizePlan to dict."""
        plan = SizePlan(
            position_size=Decimal("0.5"),
            position_value=Decimal("50000.00"),
            risk_amount=Decimal("1000.00"),
            leverage=Decimal("2.0")
        )

        data = plan.model_dump()

        assert data["position_size"] == Decimal("0.5")
        assert data["position_value"] == Decimal("50000.00")
        assert data["risk_amount"] == Decimal("1000.00")
        assert data["leverage"] == Decimal("2.0")
        assert "plan_id" in data
        assert data["plan_id"].startswith("SIZ_")

    def test_can_serialize_to_json(self):
        """Can serialize SizePlan to JSON."""
        plan = SizePlan(
            position_size=Decimal("0.5"),
            position_value=Decimal("50000.00"),
            risk_amount=Decimal("1000.00")
        )

        json_str = plan.model_dump_json()

        assert isinstance(json_str, str)
        assert "0.5" in json_str
        assert "50000" in json_str

    def test_can_deserialize_from_dict(self):
        """Can deserialize SizePlan from dict."""
        data = {
            "plan_id": "SIZ_20251027_120000_abc12345",
            "position_size": "0.5",
            "position_value": "50000.00",
            "risk_amount": "1000.00",
            "leverage": "1.0"
        }

        plan = SizePlan.model_validate(data)

        assert plan.plan_id == "SIZ_20251027_120000_abc12345"
        assert plan.position_size == Decimal("0.5")


class TestSizePlanUseCases:
    """Test real-world SizePlan use cases (lean spec)."""

    def test_fixed_risk_sizing(self):
        """Fixed 1% account risk sizing."""
        plan = SizePlan(
            position_size=Decimal("0.25"),
            position_value=Decimal("25000.00"),
            risk_amount=Decimal("1000.00"),  # 1% of 100k account
            leverage=Decimal("1.0")
        )

        assert plan.risk_amount == Decimal("1000.00")
        assert plan.leverage == Decimal("1.0")

    def test_leveraged_position_sizing(self):
        """Position sizing with 2x leverage."""
        plan = SizePlan(
            position_size=Decimal("1.0"),
            position_value=Decimal("100000.00"),
            risk_amount=Decimal("2000.00"),
            leverage=Decimal("2.0")
        )

        assert plan.leverage == Decimal("2.0")
        assert plan.position_value == Decimal("100000.00")

    def test_conservative_sizing_low_confidence(self):
        """Conservative sizing for low confidence signal."""
        plan = SizePlan(
            position_size=Decimal("0.1"),
            position_value=Decimal("10000.00"),
            risk_amount=Decimal("500.00"),  # 0.5% risk
            leverage=Decimal("1.0")
        )

        assert plan.risk_amount == Decimal("500.00")
        # Note: confidence drives sizing in SizePlanner worker, not in DTO
