# backend/core/context_factors.py
"""
Context Factor Registry - Standardized factor type definitions.

Provides platform-defined base factor types and extension mechanism for
plugin-specific custom factors. Ensures consistency while allowing flexibility.

Architecture:
    - BaseFactorType: Platform-defined core factors (enum)
    - FactorRegistry: Runtime registry for validation
    - Plugins can register custom factors via manifest

@layer: Core
@dependencies: [enum, re]
@responsibilities: [factor type definitions, registration, validation]
"""

# Standard Library Imports
import re
from enum import Enum
from typing import Set, Optional, Dict, Any


class BaseFactorType(str, Enum):
    """
    Platform-defined core context factor types.

    These are the standardized factors that the platform recognizes and
    can reason about in SWOT confrontation logic. Plugins should prefer
    these when applicable, but can register custom types when needed.

    Categories:
        Regime: Market regime classification
        Structure: Technical structure analysis
        Indicator: Indicator-based signals
        Microstructure: Orderbook/execution quality
        Temporal: Time-based context
        Sentiment: Market sentiment factors
        Fundamental: On-chain/fundamental metrics
    """

    # === Regime Factors ===
    TRENDING_REGIME = "TRENDING_REGIME"
    RANGING_REGIME = "RANGING_REGIME"
    VOLATILE_REGIME = "VOLATILE_REGIME"
    BREAKOUT_REGIME = "BREAKOUT_REGIME"
    CONSOLIDATION_REGIME = "CONSOLIDATION_REGIME"

    # === Structural Factors ===
    SUPPORT_ZONE = "SUPPORT_ZONE"
    RESISTANCE_ZONE = "RESISTANCE_ZONE"
    SUPPLY_DEMAND_IMBALANCE = "SUPPLY_DEMAND_IMBALANCE"
    MARKET_STRUCTURE_BREAK = "MARKET_STRUCTURE_BREAK"
    FAIR_VALUE_GAP = "FAIR_VALUE_GAP"
    ORDER_BLOCK = "ORDER_BLOCK"

    # === Indicator Factors ===
    MOMENTUM_ALIGNMENT = "MOMENTUM_ALIGNMENT"
    MOMENTUM_DIVERGENCE = "MOMENTUM_DIVERGENCE"
    OVERSOLD_CONDITION = "OVERSOLD_CONDITION"
    OVERBOUGHT_CONDITION = "OVERBOUGHT_CONDITION"
    TREND_CONFIRMATION = "TREND_CONFIRMATION"
    MEAN_REVERSION_SIGNAL = "MEAN_REVERSION_SIGNAL"

    # === Microstructure Factors ===
    HIGH_LIQUIDITY = "HIGH_LIQUIDITY"
    LOW_LIQUIDITY = "LOW_LIQUIDITY"
    ORDERBOOK_IMBALANCE = "ORDERBOOK_IMBALANCE"
    TIGHT_SPREAD = "TIGHT_SPREAD"
    WIDE_SPREAD = "WIDE_SPREAD"
    EXECUTION_QUALITY = "EXECUTION_QUALITY"

    # === Temporal Factors ===
    FAVORABLE_SESSION = "FAVORABLE_SESSION"
    UNFAVORABLE_SESSION = "UNFAVORABLE_SESSION"
    HIGH_VOLUME_PERIOD = "HIGH_VOLUME_PERIOD"
    LOW_VOLUME_PERIOD = "LOW_VOLUME_PERIOD"
    KILLZONE_ACTIVE = "KILLZONE_ACTIVE"

    # === Sentiment Factors ===
    EXTREME_FEAR = "EXTREME_FEAR"
    EXTREME_GREED = "EXTREME_GREED"
    SENTIMENT_REVERSAL = "SENTIMENT_REVERSAL"
    FUNDING_RATE_EXTREME = "FUNDING_RATE_EXTREME"

    # === Fundamental Factors ===
    STRONG_FUNDAMENTALS = "STRONG_FUNDAMENTALS"
    WEAK_FUNDAMENTALS = "WEAK_FUNDAMENTALS"
    ONCHAIN_ACCUMULATION = "ONCHAIN_ACCUMULATION"
    ONCHAIN_DISTRIBUTION = "ONCHAIN_DISTRIBUTION"


class FactorPolarity(str, Enum):
    """Expected polarity for a factor type."""
    STRENGTH = "strength"
    WEAKNESS = "weakness"
    BOTH = "both"  # Can be either depending on context


class FactorRegistry:
    """
    Runtime registry for context factor types.

    Manages both platform-defined base factors and plugin-registered
    custom factors. Provides validation and metadata lookup.

    Thread-safety: Not thread-safe - registration happens during bootstrap
    which is single-threaded. Runtime validation is read-only.
    """

    # Class-level storage
    _registered_factors: Set[str] = set()
    _factor_metadata: Dict[str, Dict[str, Any]] = {}
    _initialized = False

    @classmethod
    def initialize(cls) -> None:
        """
        Initialize registry with base platform factors.

        Called once during bootstrap before any plugin loading.
        """
        if cls._initialized:
            return

        # Register all base factors
        for base_factor in BaseFactorType:
            cls._registered_factors.add(base_factor.value)
            cls._factor_metadata[base_factor.value] = {
                'source': 'platform',
                'base_type': base_factor,
                'custom': False
            }

        cls._initialized = True

    @classmethod
    def register_custom_factor(
        cls,
        factor_type: str,
        plugin_name: str,
        description: Optional[str] = None
    ) -> None:
        """
        Register a custom factor type from a plugin.

        Args:
            factor_type: Factor type identifier (UPPER_SNAKE_CASE)
            plugin_name: Name of plugin registering this factor
            description: Optional human-readable description

        Raises:
            ValueError: If factor_type format is invalid or already registered
        """
        if not cls._initialized:
            cls.initialize()

        # Validate format
        if not cls._validate_format(factor_type):
            raise ValueError(
                f"Invalid factor_type format: {factor_type}. "
                f"Must be UPPER_SNAKE_CASE (3-50 chars)"
            )

        # Check reserved prefixes
        reserved_prefixes = ('SYSTEM_', 'INTERNAL_', '_')
        if any(factor_type.startswith(prefix) for prefix in reserved_prefixes):
            raise ValueError(
                f"factor_type cannot start with reserved prefix: "
                f"{reserved_prefixes}"
            )

        # Check if already registered
        if factor_type in cls._registered_factors:
            existing = cls._factor_metadata[factor_type]
            if existing['source'] == 'platform':
                raise ValueError(
                    f"factor_type '{factor_type}' conflicts with "
                    f"platform base type"
                )
            else:
                raise ValueError(
                    f"factor_type '{factor_type}' already registered by "
                    f"plugin '{existing['plugin_name']}'"
                )

        # Register
        cls._registered_factors.add(factor_type)
        cls._factor_metadata[factor_type] = {
            'source': 'plugin',
            'plugin_name': plugin_name,
            'description': description,
            'custom': True
        }

    @classmethod
    def is_registered(cls, factor_type: str) -> bool:
        """Check if factor type is registered (base or custom)."""
        if not cls._initialized:
            return False
        return factor_type in cls._registered_factors

    @classmethod
    def is_base_factor(cls, factor_type: str) -> bool:
        """Check if factor type is a platform base type."""
        if not cls._initialized:
            return False

        if factor_type not in cls._registered_factors:
            return False

        return cls._factor_metadata[factor_type]['source'] == 'platform'

    @classmethod
    def is_custom_factor(cls, factor_type: str) -> bool:
        """Check if factor type is a plugin custom type."""
        if not cls._initialized:
            return False

        if factor_type not in cls._registered_factors:
            return False

        return cls._factor_metadata[factor_type]['source'] == 'plugin'

    @classmethod
    def get_metadata(cls, factor_type: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a registered factor type."""
        if not cls._initialized:
            return None
        return cls._factor_metadata.get(factor_type)

    @classmethod
    def get_all_registered(cls) -> Set[str]:
        """Get all registered factor types (base + custom)."""
        # Do NOT auto-initialize - return empty if not initialized
        if not cls._initialized:
            return set()
        return cls._registered_factors.copy()

    @classmethod
    def reset(cls) -> None:
        """Reset registry (for testing only). Does NOT auto-reinitialize."""
        cls._registered_factors.clear()
        cls._factor_metadata.clear()
        cls._initialized = False

    @staticmethod
    def _validate_format(factor_type: str) -> bool:
        """Validate factor_type format (UPPER_SNAKE_CASE, 3-50 chars)."""
        if not 3 <= len(factor_type) <= 50:
            return False

        pattern = re.compile(r'^[A-Z][A-Z0-9_]*$')
        return bool(pattern.match(factor_type))


# Initialize on module load
FactorRegistry.initialize()
