# tests/unit/dtos/strategy/test_context_factor.py
"""
Unit tests for ContextFactor DTO.

Tests the individual context factor output from ContextWorkers,
capturing strengths or weaknesses with validated factor types.

@layer: Tests (Unit)
@dependencies: [pytest, backend.dtos.strategy.context_factor, backend.core.context_factors]
"""

# Third-Party Imports
import pytest

# Our Application Imports
from backend.dtos.strategy.context_factor import ContextFactor
from backend.core.enums import ContextType
from backend.core.context_factors import BaseFactorType, FactorRegistry


class TestContextFactorCreation:
    """Test basic ContextFactor creation."""

    def test_create_strength_factor(self):
        """Test creating a factor with strength only."""
        factor = ContextFactor(
            factor_type=BaseFactorType.TRENDING_REGIME.value,
            strength=0.75,
            weakness=None,
            source_plugin="trend_analyzer",
            source_context_type=ContextType.REGIME_CLASSIFICATION.value
        )

        assert factor.factor_type == "TRENDING_REGIME"
        assert factor.strength == 0.75
        assert factor.weakness is None
        assert factor.source_plugin == "trend_analyzer"
        assert factor.source_context_type == "REGIME_CLASSIFICATION"
        assert factor.metadata is None

    def test_create_weakness_factor(self):
        """Test creating a factor with weakness only."""
        factor = ContextFactor(
            factor_type=BaseFactorType.VOLATILE_REGIME.value,
            strength=None,
            weakness=0.60,
            source_plugin="volatility_detector",
            source_context_type=ContextType.REGIME_CLASSIFICATION.value
        )

        assert factor.factor_type == "VOLATILE_REGIME"
        assert factor.strength is None
        assert factor.weakness == 0.60
        assert factor.source_plugin == "volatility_detector"

    def test_create_factor_with_metadata(self):
        """Test creating a factor with optional metadata."""
        metadata = {
            "regime_duration_bars": 42,
            "trend_slope": 0.023,
            "confidence_level": "high"
        }

        factor = ContextFactor(
            factor_type=BaseFactorType.TRENDING_REGIME.value,
            strength=0.85,
            weakness=None,
            source_plugin="trend_analyzer",
            source_context_type=ContextType.REGIME_CLASSIFICATION.value,
            metadata=metadata
        )

        assert factor.metadata == metadata
        assert factor.metadata["regime_duration_bars"] == 42


class TestContextFactorTypeValidation:
    """Test factor_type validation."""

    def test_valid_base_factor_type(self):
        """Test that base factor types are accepted."""
        factor = ContextFactor(
            factor_type=BaseFactorType.RANGING_REGIME.value,
            strength=0.70,
            weakness=None,
            source_plugin="test_plugin",
            source_context_type=ContextType.REGIME_CLASSIFICATION.value
        )

        assert factor.factor_type == "RANGING_REGIME"

    def test_valid_custom_factor_type(self):
        """Test that registered custom factor types are accepted."""
        # Register custom factor
        FactorRegistry.register_custom_factor(
            "ELLIOTT_WAVE_COUNT",
            "elliott_wave_plugin",
            "Custom Elliott Wave analysis factor"
        )

        factor = ContextFactor(
            factor_type="ELLIOTT_WAVE_COUNT",
            strength=0.65,
            weakness=None,
            source_plugin="elliott_wave_plugin",
            source_context_type=ContextType.STRUCTURAL_ANALYSIS.value
        )

        assert factor.factor_type == "ELLIOTT_WAVE_COUNT"

    def test_unregistered_factor_type_rejected(self):
        """Test that unregistered factor types are rejected."""
        with pytest.raises(ValueError) as exc_info:
            ContextFactor(
                factor_type="UNKNOWN_FACTOR",
                strength=0.50,
                weakness=None,
                source_plugin="test_plugin",
                source_context_type=ContextType.REGIME_CLASSIFICATION.value
            )

        assert "not registered" in str(exc_info.value).lower()

    def test_factor_type_too_short_rejected(self):
        """Test that factor_type under 3 chars is rejected."""
        with pytest.raises(ValueError) as exc_info:
            ContextFactor(
                factor_type="AB",
                strength=0.50,
                weakness=None,
                source_plugin="test_plugin",
                source_context_type=ContextType.REGIME_CLASSIFICATION.value
            )

        assert "3" in str(exc_info.value) or "length" in str(exc_info.value).lower()

    def test_factor_type_lowercase_rejected(self):
        """Test that lowercase factor_type is rejected."""
        with pytest.raises(ValueError) as exc_info:
            ContextFactor(
                factor_type="trending_regime",
                strength=0.50,
                weakness=None,
                source_plugin="test_plugin",
                source_context_type=ContextType.REGIME_CLASSIFICATION.value
            )

        error_msg = str(exc_info.value)
        assert "UPPER_SNAKE_CASE" in error_msg or "uppercase" in error_msg.lower()


class TestContextFactorStrengthWeaknessValidation:
    """Test strength/weakness mutual exclusivity and range validation."""

    def test_both_strength_and_weakness_rejected(self):
        """Test that having both strength AND weakness is rejected."""
        with pytest.raises(ValueError) as exc_info:
            ContextFactor(
                factor_type=BaseFactorType.TRENDING_REGIME.value,
                strength=0.75,
                weakness=0.30,
                source_plugin="test_plugin",
                source_context_type=ContextType.REGIME_CLASSIFICATION.value
            )

        error_msg = str(exc_info.value).lower()
        assert "one of" in error_msg or "mutually exclusive" in error_msg

    def test_neither_strength_nor_weakness_rejected(self):
        """Test that having NEITHER strength nor weakness is rejected."""
        with pytest.raises(ValueError) as exc_info:
            ContextFactor(
                factor_type=BaseFactorType.TRENDING_REGIME.value,
                strength=None,
                weakness=None,
                source_plugin="test_plugin",
                source_context_type=ContextType.REGIME_CLASSIFICATION.value
            )

        error_msg = str(exc_info.value).lower()
        assert "at least one" in error_msg or "required" in error_msg

    def test_strength_valid_range(self):
        """Test that strength accepts valid 0.0-1.0 range."""
        # Test boundaries
        factor_zero = ContextFactor(
            factor_type=BaseFactorType.TRENDING_REGIME.value,
            strength=0.0,
            weakness=None,
            source_plugin="test_plugin",
            source_context_type=ContextType.REGIME_CLASSIFICATION.value
        )
        assert factor_zero.strength == 0.0

        factor_one = ContextFactor(
            factor_type=BaseFactorType.TRENDING_REGIME.value,
            strength=1.0,
            weakness=None,
            source_plugin="test_plugin",
            source_context_type=ContextType.REGIME_CLASSIFICATION.value
        )
        assert factor_one.strength == 1.0

    def test_strength_below_zero_rejected(self):
        """Test that strength < 0.0 is rejected."""
        with pytest.raises(ValueError) as exc_info:
            ContextFactor(
                factor_type=BaseFactorType.TRENDING_REGIME.value,
                strength=-0.1,
                weakness=None,
                source_plugin="test_plugin",
                source_context_type=ContextType.REGIME_CLASSIFICATION.value
            )

        assert "0.0" in str(exc_info.value) and "1.0" in str(exc_info.value)

    def test_strength_above_one_rejected(self):
        """Test that strength > 1.0 is rejected."""
        with pytest.raises(ValueError) as exc_info:
            ContextFactor(
                factor_type=BaseFactorType.TRENDING_REGIME.value,
                strength=1.1,
                weakness=None,
                source_plugin="test_plugin",
                source_context_type=ContextType.REGIME_CLASSIFICATION.value
            )

        assert "0.0" in str(exc_info.value) and "1.0" in str(exc_info.value)

    def test_weakness_valid_range(self):
        """Test that weakness accepts valid 0.0-1.0 range."""
        factor_zero = ContextFactor(
            factor_type=BaseFactorType.LOW_LIQUIDITY.value,
            strength=None,
            weakness=0.0,
            source_plugin="test_plugin",
            source_context_type=ContextType.MICROSTRUCTURE_ANALYSIS.value
        )
        assert factor_zero.weakness == 0.0

        factor_one = ContextFactor(
            factor_type=BaseFactorType.LOW_LIQUIDITY.value,
            strength=None,
            weakness=1.0,
            source_plugin="test_plugin",
            source_context_type=ContextType.MICROSTRUCTURE_ANALYSIS.value
        )
        assert factor_one.weakness == 1.0

    def test_weakness_below_zero_rejected(self):
        """Test that weakness < 0.0 is rejected."""
        with pytest.raises(ValueError) as exc_info:
            ContextFactor(
                factor_type=BaseFactorType.LOW_LIQUIDITY.value,
                strength=None,
                weakness=-0.1,
                source_plugin="test_plugin",
                source_context_type=ContextType.MICROSTRUCTURE_ANALYSIS.value
            )

        assert "0.0" in str(exc_info.value) and "1.0" in str(exc_info.value)

    def test_weakness_above_one_rejected(self):
        """Test that weakness > 1.0 is rejected."""
        with pytest.raises(ValueError) as exc_info:
            ContextFactor(
                factor_type=BaseFactorType.LOW_LIQUIDITY.value,
                strength=None,
                weakness=1.5,
                source_plugin="test_plugin",
                source_context_type=ContextType.MICROSTRUCTURE_ANALYSIS.value
            )

        assert "0.0" in str(exc_info.value) and "1.0" in str(exc_info.value)


class TestContextFactorSourcePluginValidation:
    """Test source_plugin validation."""

    def test_valid_plugin_name(self):
        """Test that valid plugin names are accepted."""
        factor = ContextFactor(
            factor_type=BaseFactorType.TRENDING_REGIME.value,
            strength=0.75,
            weakness=None,
            source_plugin="trend_analyzer_v2",
            source_context_type=ContextType.REGIME_CLASSIFICATION.value
        )

        assert factor.source_plugin == "trend_analyzer_v2"

    def test_plugin_name_too_short_rejected(self):
        """Test that plugin name under 3 chars is rejected."""
        with pytest.raises(ValueError) as exc_info:
            ContextFactor(
                factor_type=BaseFactorType.TRENDING_REGIME.value,
                strength=0.75,
                weakness=None,
                source_plugin="ab",
                source_context_type=ContextType.REGIME_CLASSIFICATION.value
            )

        assert "3" in str(exc_info.value) or "length" in str(exc_info.value).lower()

    def test_plugin_name_too_long_rejected(self):
        """Test that plugin name over 100 chars is rejected."""
        long_name = "a" * 101

        with pytest.raises(ValueError) as exc_info:
            ContextFactor(
                factor_type=BaseFactorType.TRENDING_REGIME.value,
                strength=0.75,
                weakness=None,
                source_plugin=long_name,
                source_context_type=ContextType.REGIME_CLASSIFICATION.value
            )

        assert "100" in str(exc_info.value) or "length" in str(exc_info.value).lower()

    def test_plugin_name_invalid_format_rejected(self):
        """Test that plugin name with invalid chars is rejected."""
        with pytest.raises(ValueError) as exc_info:
            ContextFactor(
                factor_type=BaseFactorType.TRENDING_REGIME.value,
                strength=0.75,
                weakness=None,
                source_plugin="invalid plugin!",
                source_context_type=ContextType.REGIME_CLASSIFICATION.value
            )

        error_msg = str(exc_info.value).lower()
        assert "alphanumeric" in error_msg or "invalid" in error_msg


class TestContextFactorSourceContextTypeValidation:
    """Test source_context_type validation."""

    def test_valid_context_types(self):
        """Test that all valid ContextType enum values are accepted."""
        valid_types = [
            ContextType.REGIME_CLASSIFICATION,
            ContextType.STRUCTURAL_ANALYSIS,
            ContextType.INDICATOR_CALCULATION,
            ContextType.MICROSTRUCTURE_ANALYSIS,
            ContextType.TEMPORAL_CONTEXT,
            ContextType.SENTIMENT_ENRICHMENT,
            ContextType.FUNDAMENTAL_ENRICHMENT
        ]

        for context_type in valid_types:
            factor = ContextFactor(
                factor_type=BaseFactorType.TRENDING_REGIME.value,
                strength=0.75,
                weakness=None,
                source_plugin="test_plugin",
                source_context_type=context_type.value
            )
            assert factor.source_context_type == context_type.value

    def test_invalid_context_type_rejected(self):
        """Test that non-ContextType values are rejected."""
        with pytest.raises(ValueError) as exc_info:
            ContextFactor(
                factor_type=BaseFactorType.TRENDING_REGIME.value,
                strength=0.75,
                weakness=None,
                source_plugin="test_plugin",
                source_context_type="INVALID_TYPE"
            )

        error_msg = str(exc_info.value).lower()
        assert "contexttype" in error_msg or "valid types" in error_msg

    def test_lowercase_context_type_rejected(self):
        """Test that lowercase context_type is rejected."""
        with pytest.raises(ValueError) as exc_info:
            ContextFactor(
                factor_type=BaseFactorType.TRENDING_REGIME.value,
                strength=0.75,
                weakness=None,
                source_plugin="test_plugin",
                source_context_type="regime_classification"
            )

        error_msg = str(exc_info.value)
        assert "UPPER_SNAKE_CASE" in error_msg or "uppercase" in error_msg.lower()


class TestContextFactorMetadataValidation:
    """Test metadata field validation."""

    def test_metadata_accepts_dict(self):
        """Test that metadata accepts valid dictionary."""
        metadata = {
            "key1": "value1",
            "key2": 123,
            "key3": [1, 2, 3],
            "nested": {"a": 1, "b": 2}
        }

        factor = ContextFactor(
            factor_type=BaseFactorType.TRENDING_REGIME.value,
            strength=0.75,
            weakness=None,
            source_plugin="test_plugin",
            source_context_type=ContextType.REGIME_CLASSIFICATION.value,
            metadata=metadata
        )

        assert factor.metadata == metadata

    def test_metadata_none_by_default(self):
        """Test that metadata is None when not provided."""
        factor = ContextFactor(
            factor_type=BaseFactorType.TRENDING_REGIME.value,
            strength=0.75,
            weakness=None,
            source_plugin="test_plugin",
            source_context_type=ContextType.REGIME_CLASSIFICATION.value
        )

        assert factor.metadata is None

    def test_metadata_rejects_non_dict(self):
        """Test that metadata rejects non-dictionary values."""
        with pytest.raises(ValueError) as exc_info:
            ContextFactor(
                factor_type=BaseFactorType.TRENDING_REGIME.value,
                strength=0.75,
                weakness=None,
                source_plugin="test_plugin",
                source_context_type=ContextType.REGIME_CLASSIFICATION.value,
                metadata="not a dict"
            )

        assert "dict" in str(exc_info.value).lower()


class TestContextFactorImmutability:
    """Test that ContextFactor instances are immutable."""

    def test_factor_is_frozen(self):
        """Test that ContextFactor cannot be modified after creation."""
        factor = ContextFactor(
            factor_type=BaseFactorType.TRENDING_REGIME.value,
            strength=0.75,
            weakness=None,
            source_plugin="test_plugin",
            source_context_type=ContextType.REGIME_CLASSIFICATION.value
        )

        with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
            factor.strength = 0.90

    def test_no_extra_fields_allowed(self):
        """Test that extra fields are rejected."""
        with pytest.raises(Exception):  # ValidationError or TypeError
            ContextFactor(
                factor_type=BaseFactorType.TRENDING_REGIME.value,
                strength=0.75,
                weakness=None,
                source_plugin="test_plugin",
                source_context_type=ContextType.REGIME_CLASSIFICATION.value,
                extra_field="not allowed"
            )
