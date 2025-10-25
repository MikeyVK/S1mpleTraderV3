# tests/unit/core/test_context_factors.py
"""
Unit tests for context factor registry.

Tests base factor types, custom registration, and validation logic.
Ensures breaking changes to factor registry are detected.

@layer: Tests (Unit)
@dependencies: [pytest, backend.core.context_factors]
"""

# Standard Library Imports
import re

# Third-Party Imports
import pytest

# Our Application Imports
from backend.core.context_factors import (
    BaseFactorType,
    FactorPolarity,
    FactorRegistry
)


class TestBaseFactorType:
    """Test suite for BaseFactorType enum."""

    def test_all_base_factors_defined(self):
        """Test that platform base factors are complete."""
        # This test will fail if factors are added/removed
        expected_count = 36  # Update if base factors change
        actual_count = len(BaseFactorType)

        assert actual_count == expected_count, (
            f"BaseFactorType count changed! "
            f"Expected {expected_count}, got {actual_count}. "
            f"Update test if intentional."
        )

    def test_base_factor_categories_present(self):
        """Test that all major categories are represented."""
        # Extract unique prefixes to verify categories
        prefixes: set[str] = set()
        for factor in BaseFactorType:
            parts = factor.value.split('_')
            if len(parts) > 1:
                prefixes.add(parts[0])

        # We expect diverse category coverage across regime, structure,
        # indicator, microstructure, temporal, sentiment, and fundamental
        # Not all categories will be first word, so lenient check
        assert len(prefixes) >= 10, (
            f"Expected diverse category coverage, got {len(prefixes)} prefixes"
        )

    def test_base_factors_are_uppercase_snake_case(self):
        """Test that all base factors follow naming convention."""
        pattern = re.compile(r'^[A-Z][A-Z0-9_]*$')

        for factor in BaseFactorType:
            assert pattern.match(factor.value), (
                f"BaseFactorType.{factor.name} value '{factor.value}' "
                f"is not UPPER_SNAKE_CASE"
            )


class TestFactorPolarity:
    """Test suite for FactorPolarity enum."""

    def test_polarity_values(self):
        """Test that polarity enum has expected values."""
        expected = {"strength", "weakness", "both"}
        actual = {p.value for p in FactorPolarity}

        assert actual == expected, (
            f"FactorPolarity changed! "
            f"Added: {actual - expected}, "
            f"Removed: {expected - actual}"
        )


class TestFactorRegistryInitialization:
    """Test suite for FactorRegistry initialization."""

    def setup_method(self):
        """Reset registry before each test."""
        FactorRegistry.reset()

    def test_registry_initializes_with_base_factors(self):
        """Test that initialization registers all base factors."""
        FactorRegistry.initialize()

        for base_factor in BaseFactorType:
            assert FactorRegistry.is_registered(base_factor.value)

    def test_registry_initialization_is_idempotent(self):
        """Test that multiple initializations don't cause issues."""
        FactorRegistry.initialize()
        count_1 = len(FactorRegistry.get_all_registered())

        FactorRegistry.initialize()
        count_2 = len(FactorRegistry.get_all_registered())

        assert count_1 == count_2

    def test_base_factors_marked_as_platform_source(self):
        """Test that base factors have correct metadata."""
        FactorRegistry.initialize()

        for base_factor in BaseFactorType:
            assert FactorRegistry.is_base_factor(base_factor.value)
            assert not FactorRegistry.is_custom_factor(base_factor.value)

            metadata = FactorRegistry.get_metadata(base_factor.value)
            assert metadata is not None
            assert metadata['source'] == 'platform'
            assert metadata['custom'] is False


class TestFactorRegistryCustomRegistration:
    """Test suite for custom factor registration."""

    def setup_method(self):
        """Reset registry before each test."""
        FactorRegistry.reset()
        FactorRegistry.initialize()

    def test_register_valid_custom_factor(self):
        """Test successful custom factor registration."""
        FactorRegistry.register_custom_factor(
            factor_type="CUSTOM_ML_SIGNAL",
            plugin_name="ml_predictor_v1",
            description="ML-based sentiment signal"
        )

        assert FactorRegistry.is_registered("CUSTOM_ML_SIGNAL")
        assert FactorRegistry.is_custom_factor("CUSTOM_ML_SIGNAL")
        assert not FactorRegistry.is_base_factor("CUSTOM_ML_SIGNAL")

    def test_custom_factor_metadata(self):
        """Test that custom factor metadata is stored correctly."""
        FactorRegistry.register_custom_factor(
            factor_type="PROPRIETARY_EDGE",
            plugin_name="quant_strategy_alpha",
            description="Proprietary quant signal"
        )

        metadata = FactorRegistry.get_metadata("PROPRIETARY_EDGE")
        assert metadata is not None
        assert metadata['source'] == 'plugin'
        assert metadata['plugin_name'] == "quant_strategy_alpha"
        assert metadata['description'] == "Proprietary quant signal"
        assert metadata['custom'] is True

    def test_register_multiple_custom_factors(self):
        """Test registering multiple custom factors."""
        factors = [
            ("CUSTOM_FACTOR_1", "plugin_a"),
            ("CUSTOM_FACTOR_2", "plugin_b"),
            ("CUSTOM_FACTOR_3", "plugin_a"),  # Same plugin, different factor
        ]

        for factor_type, plugin_name in factors:
            FactorRegistry.register_custom_factor(
                factor_type=factor_type,
                plugin_name=plugin_name
            )

        for factor_type, _ in factors:
            assert FactorRegistry.is_registered(factor_type)


class TestFactorRegistryValidation:
    """Test suite for factor validation logic."""

    def setup_method(self):
        """Reset registry before each test."""
        FactorRegistry.reset()
        FactorRegistry.initialize()

    def test_reject_invalid_format(self):
        """Test that invalid formats are rejected."""
        invalid_formats = [
            "lowercase_factor",  # Lowercase
            "Mixed_Case_Factor",  # Mixed case
            "AB",  # Too short
            "A" * 51,  # Too long
            "123_STARTS_WITH_NUMBER",  # Starts with number
            "FACTOR-WITH-DASHES",  # Contains dashes
        ]

        for invalid in invalid_formats:
            with pytest.raises(ValueError, match="Invalid factor_type format"):
                FactorRegistry.register_custom_factor(
                    factor_type=invalid,
                    plugin_name="test_plugin"
                )

    def test_reject_reserved_prefixes(self):
        """Test that reserved prefixes are blocked."""
        reserved = [
            "SYSTEM_CUSTOM_FACTOR",
            "INTERNAL_PROPRIETARY",
        ]

        for factor_type in reserved:
            with pytest.raises(ValueError, match="reserved prefix"):
                FactorRegistry.register_custom_factor(
                    factor_type=factor_type,
                    plugin_name="test_plugin"
                )

        # _PRIVATE fails on format check (starts with underscore)
        with pytest.raises(ValueError, match="Invalid factor_type format"):
            FactorRegistry.register_custom_factor(
                factor_type="_PRIVATE_SIGNAL",
                plugin_name="test_plugin"
            )

    def test_reject_duplicate_registration(self):
        """Test that duplicate custom factors are rejected."""
        FactorRegistry.register_custom_factor(
            factor_type="UNIQUE_FACTOR",
            plugin_name="plugin_a"
        )

        # Try to register same factor from different plugin
        with pytest.raises(ValueError, match="already registered"):
            FactorRegistry.register_custom_factor(
                factor_type="UNIQUE_FACTOR",
                plugin_name="plugin_b"
            )

    def test_reject_conflicting_with_base_factor(self):
        """Test that custom factors can't override base factors."""
        base_factor = BaseFactorType.TRENDING_REGIME.value

        with pytest.raises(ValueError, match="conflicts with platform base type"):
            FactorRegistry.register_custom_factor(
                factor_type=base_factor,
                plugin_name="evil_plugin"
            )


class TestFactorRegistryQueries:
    """Test suite for registry query methods."""

    def setup_method(self):
        """Reset and populate registry."""
        FactorRegistry.reset()
        FactorRegistry.initialize()

        # Add some custom factors
        FactorRegistry.register_custom_factor(
            "CUSTOM_A", "plugin_x"
        )
        FactorRegistry.register_custom_factor(
            "CUSTOM_B", "plugin_y"
        )

    def test_get_all_registered_includes_base_and_custom(self):
        """Test that get_all_registered returns both types."""
        all_factors = FactorRegistry.get_all_registered()

        # Should include base factors
        assert BaseFactorType.TRENDING_REGIME.value in all_factors

        # Should include custom factors
        assert "CUSTOM_A" in all_factors
        assert "CUSTOM_B" in all_factors

    def test_is_registered_for_unregistered_factor(self):
        """Test that unregistered factors return False."""
        assert not FactorRegistry.is_registered("NONEXISTENT_FACTOR")

    def test_get_metadata_for_unregistered_factor(self):
        """Test that metadata for unregistered factor returns None."""
        metadata = FactorRegistry.get_metadata("NONEXISTENT_FACTOR")
        assert metadata is None

    def test_is_base_factor_for_custom_factor(self):
        """Test that custom factors are not marked as base."""
        assert not FactorRegistry.is_base_factor("CUSTOM_A")

    def test_is_custom_factor_for_base_factor(self):
        """Test that base factors are not marked as custom."""
        assert not FactorRegistry.is_custom_factor(
            BaseFactorType.TRENDING_REGIME.value
        )


class TestFactorRegistryReset:
    """Test suite for registry reset functionality."""

    def test_reset_clears_all_registrations(self):
        """Test that reset removes all factors."""
        FactorRegistry.initialize()
        FactorRegistry.register_custom_factor("TEMP_FACTOR", "temp_plugin")

        FactorRegistry.reset()

        # Should be empty after reset
        assert len(FactorRegistry.get_all_registered()) == 0
        assert not FactorRegistry.is_registered("TEMP_FACTOR")
        assert not FactorRegistry.is_registered(
            BaseFactorType.TRENDING_REGIME.value
        )

    def test_reset_allows_reinitialization(self):
        """Test that registry can be reinitialized after reset."""
        FactorRegistry.initialize()
        FactorRegistry.reset()
        FactorRegistry.initialize()

        # Base factors should be back
        assert FactorRegistry.is_registered(
            BaseFactorType.TRENDING_REGIME.value
        )
