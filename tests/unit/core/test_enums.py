# tests/unit/core/test_enums.py
"""
Unit tests for core enums.

Tests enum definitions and detects breaking changes to enum values.
Any change to enum members will cause tests to fail, forcing impact analysis.

@layer: Tests (Unit)
@dependencies: [pytest, backend.core.enums]
"""

# Standard Library Imports
import re
from enum import Enum
from typing import Type

# Our Application Imports
from backend.core.enums import (
    ContextType,
    OpportunityType,
    ThreatType,
    PlanningPhase,
    ExecutionType
)


class TestContextType:
    """Test suite for ContextType enum."""

    def test_all_context_types_present(self):
        """Test that all expected context types are defined."""
        expected = {
            "REGIME_CLASSIFICATION",
            "STRUCTURAL_ANALYSIS",
            "INDICATOR_CALCULATION",
            "MICROSTRUCTURE_ANALYSIS",
            "TEMPORAL_CONTEXT",
            "SENTIMENT_ENRICHMENT",
            "FUNDAMENTAL_ENRICHMENT"
        }

        actual = {ct.value for ct in ContextType}
        assert actual == expected, (
            f"ContextType enum changed! "
            f"Added: {actual - expected}, "
            f"Removed: {expected - actual}"
        )

    def test_context_type_is_string_enum(self):
        """Test that ContextType values are strings."""
        for context_type in ContextType:
            assert isinstance(context_type.value, str)

    def test_context_type_members_accessible(self):
        """Test that all members are accessible."""
        assert ContextType.REGIME_CLASSIFICATION
        assert ContextType.STRUCTURAL_ANALYSIS
        assert ContextType.INDICATOR_CALCULATION
        assert ContextType.MICROSTRUCTURE_ANALYSIS
        assert ContextType.TEMPORAL_CONTEXT
        assert ContextType.SENTIMENT_ENRICHMENT
        assert ContextType.FUNDAMENTAL_ENRICHMENT


class TestOpportunityType:
    """Test suite for OpportunityType enum."""

    def test_all_opportunity_types_present(self):
        """Test that all expected opportunity types are defined."""
        expected = {
            "BREAKOUT_DETECTION",
            "PULLBACK_DETECTION",
            "REVERSAL_DETECTION",
            "CONTINUATION_DETECTION",
            "ARBITRAGE_DETECTION",
            "STATISTICAL_EDGE",
            "SENTIMENT_EXTREME"
        }

        actual = {ot.value for ot in OpportunityType}
        assert actual == expected, (
            f"OpportunityType enum changed! "
            f"Added: {actual - expected}, "
            f"Removed: {expected - actual}"
        )

    def test_opportunity_type_is_string_enum(self):
        """Test that OpportunityType values are strings."""
        for opp_type in OpportunityType:
            assert isinstance(opp_type.value, str)


class TestThreatType:
    """Test suite for ThreatType enum."""

    def test_all_threat_types_present(self):
        """Test that all expected threat types are defined."""
        expected = {
            "RISK_LIMIT_MONITORING",
            "DRAWDOWN_MONITORING",
            "VOLATILITY_MONITORING",
            "CORRELATION_MONITORING",
            "SYSTEMIC_RISK_DETECTION"
        }

        actual = {tt.value for tt in ThreatType}
        assert actual == expected, (
            f"ThreatType enum changed! "
            f"Added: {actual - expected}, "
            f"Removed: {expected - actual}"
        )

    def test_threat_type_is_string_enum(self):
        """Test that ThreatType values are strings."""
        for threat_type in ThreatType:
            assert isinstance(threat_type.value, str)


class TestPlanningPhase:
    """Test suite for PlanningPhase enum."""

    def test_all_planning_phases_present(self):
        """Test that all expected planning phases are defined."""
        expected = {
            "ENTRY_PLANNING",
            "RISK_SIZING",
            "EXIT_PLANNING",
            "EXECUTION_ROUTING"
        }

        actual = {pp.value for pp in PlanningPhase}
        assert actual == expected, (
            f"PlanningPhase enum changed! "
            f"Added: {actual - expected}, "
            f"Removed: {expected - actual}"
        )

    def test_planning_phase_is_string_enum(self):
        """Test that PlanningPhase values are strings."""
        for phase in PlanningPhase:
            assert isinstance(phase.value, str)


class TestExecutionType:
    """Test suite for ExecutionType enum."""

    def test_all_execution_types_present(self):
        """Test that all expected execution types are defined."""
        expected = {
            "ORDER_PLACEMENT",
            "ORDER_MANAGEMENT",
            "POSITION_MANAGEMENT",
            "REPORTING"
        }

        actual = {et.value for et in ExecutionType}
        assert actual == expected, (
            f"ExecutionType enum changed! "
            f"Added: {actual - expected}, "
            f"Removed: {expected - actual}"
        )

    def test_execution_type_is_string_enum(self):
        """Test that ExecutionType values are strings."""
        for exec_type in ExecutionType:
            assert isinstance(exec_type.value, str)


class TestEnumCrossCutting:
    """Cross-cutting tests for all enums."""

    def test_no_duplicate_values_within_enums(self):
        """Test that each enum has unique values."""
        enums_to_test: list[Type[Enum]] = [
            ContextType,
            OpportunityType,
            ThreatType,
            PlanningPhase,
            ExecutionType
        ]

        for enum_class in enums_to_test:
            values = [e.value for e in enum_class]
            assert len(values) == len(set(values)), (
                f"{enum_class.__name__} has duplicate values"
            )

    def test_all_enum_values_uppercase_snake_case(self):
        """Test that all enum values follow UPPER_SNAKE_CASE."""
        pattern = re.compile(r'^[A-Z][A-Z0-9_]*$')

        enums_to_test: list[Type[Enum]] = [
            ContextType,
            OpportunityType,
            ThreatType,
            PlanningPhase,
            ExecutionType
        ]

        for enum_class in enums_to_test:
            for member in enum_class:
                assert pattern.match(member.value), (
                    f"{enum_class.__name__}.{member.name} value "
                    f"'{member.value}' is not UPPER_SNAKE_CASE"
                )
