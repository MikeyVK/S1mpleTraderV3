# backend/core/enums.py
"""
Central enumeration definitions.

All Literal types and enums used across DTOs and platform components.
Single source of truth for categorical values.

@layer: Core
@dependencies: []
@responsibilities: [enum definitions, type safety, documentation]
"""

# Standard Library Imports
from enum import Enum


class ContextType(str, Enum):
    """
    Context worker categorization by analysis domain.

    Maps to worker subtypes for context enrichment.
    """
    REGIME_CLASSIFICATION = "REGIME_CLASSIFICATION"
    STRUCTURAL_ANALYSIS = "STRUCTURAL_ANALYSIS"
    INDICATOR_CALCULATION = "INDICATOR_CALCULATION"
    MICROSTRUCTURE_ANALYSIS = "MICROSTRUCTURE_ANALYSIS"
    TEMPORAL_CONTEXT = "TEMPORAL_CONTEXT"
    SENTIMENT_ENRICHMENT = "SENTIMENT_ENRICHMENT"
    FUNDAMENTAL_ENRICHMENT = "FUNDAMENTAL_ENRICHMENT"

class OpportunityType(str, Enum):
    """Opportunity worker categorization by strategic approach."""
    BREAKOUT_DETECTION = "BREAKOUT_DETECTION"
    PULLBACK_DETECTION = "PULLBACK_DETECTION"
    REVERSAL_DETECTION = "REVERSAL_DETECTION"
    CONTINUATION_DETECTION = "CONTINUATION_DETECTION"
    ARBITRAGE_DETECTION = "ARBITRAGE_DETECTION"
    STATISTICAL_EDGE = "STATISTICAL_EDGE"
    SENTIMENT_EXTREME = "SENTIMENT_EXTREME"


class ThreatType(str, Enum):
    """Threat worker categorization by risk domain."""
    RISK_LIMIT_MONITORING = "RISK_LIMIT_MONITORING"
    DRAWDOWN_MONITORING = "DRAWDOWN_MONITORING"
    VOLATILITY_MONITORING = "VOLATILITY_MONITORING"
    CORRELATION_MONITORING = "CORRELATION_MONITORING"
    SYSTEMIC_RISK_DETECTION = "SYSTEMIC_RISK_DETECTION"


class PlanningPhase(str, Enum):
    """Planning worker categorization by planning stage."""
    ENTRY_PLANNING = "ENTRY_PLANNING"
    RISK_SIZING = "RISK_SIZING"
    EXIT_PLANNING = "EXIT_PLANNING"
    EXECUTION_ROUTING = "EXECUTION_ROUTING"


class ExecutionType(str, Enum):
    """Execution worker categorization by action type."""
    ORDER_PLACEMENT = "ORDER_PLACEMENT"
    ORDER_MANAGEMENT = "ORDER_MANAGEMENT"
    POSITION_MANAGEMENT = "POSITION_MANAGEMENT"
    REPORTING = "REPORTING"
