# backend/utils/id_generators.py
"""
Typed ID generation utilities.

Provides standardized ID generation with type prefixes for causal
traceability across the trading system. All IDs follow the pattern:
{PREFIX}_{uuid}

Prefix Convention:
    Flow Initiators (what started the strategy flow):
        TCK_ - Raw market tick from ExecutionEnvironment
        SCH_ - Scheduled task from Scheduler (weekly_dca, daily_open, etc.)
        NWS_ - News/external event from NewsAdapter
        MAN_ - Manual trigger from UI/operator

    Causal Chain (strategy execution flow):
        OPP_ - Opportunity detected by OpportunityWorker
        THR_ - Threat detected by ThreatWorker
        TRD_ - Trade executed by ExecutionWorker
        ASS_ - Context assessment aggregated by ContextAggregator

Causal Traceability Examples:
    Tick-based flow:
        TCK_abc-123 → OPP_def-456 → TRD_ghi-789 → THR_jkl-012

    Scheduled flow:
        SCH_mno-345 → OPP_pqr-678 → TRD_stu-901

@layer: Backend (Utils)
@dependencies: [uuid]
@responsibilities:
    - Generate typed IDs with consistent prefixes
    - Extract ID type from typed ID string
    - Maintain ID format consistency
"""

from uuid import uuid4


__all__ = [
    'generate_tick_id',
    'generate_schedule_id',
    'generate_news_id',
    'generate_manual_id',
    'generate_opportunity_id',
    'generate_threat_id',
    'generate_trade_id',
    'generate_assessment_id',
    'generate_strategy_directive_id',
    'generate_entry_plan_id',
    'generate_size_plan_id',
    'generate_exit_plan_id',
    'generate_routing_plan_id',
    'generate_execution_directive_id',
    'extract_id_type',
]


# === Flow Initiators ===

def generate_tick_id() -> str:
    """Generate tick-based flow initiator ID."""
    return f"TCK_{uuid4()}"


def generate_schedule_id() -> str:
    """Generate scheduled task flow initiator ID."""
    return f"SCH_{uuid4()}"


def generate_news_id() -> str:
    """Generate news-based flow initiator ID."""
    return f"NWS_{uuid4()}"


def generate_manual_id() -> str:
    """Generate manual trigger flow initiator ID."""
    return f"MAN_{uuid4()}"


# === Causal Chain ===

def generate_opportunity_id() -> str:
    """Generate opportunity ID."""
    return f"OPP_{uuid4()}"


def generate_threat_id() -> str:
    """Generate threat ID."""
    return f"THR_{uuid4()}"


def generate_trade_id() -> str:
    """Generate trade ID."""
    return f"TRD_{uuid4()}"


def generate_assessment_id() -> str:
    """Generate context assessment ID."""
    return f"ASS_{uuid4()}"


def generate_strategy_directive_id() -> str:
    """Generate strategy directive ID."""
    return f"STR_{uuid4()}"


# === Planning Chain ===

def generate_entry_plan_id() -> str:
    """Generate entry plan ID."""
    return f"ENT_{uuid4()}"


def generate_size_plan_id() -> str:
    """Generate size plan ID."""
    return f"SIZ_{uuid4()}"


def generate_exit_plan_id() -> str:
    """Generate exit plan ID."""
    return f"EXT_{uuid4()}"


def generate_routing_plan_id() -> str:
    """Generate routing plan ID."""
    return f"ROU_{uuid4()}"


def generate_execution_directive_id() -> str:
    """Generate execution directive ID."""
    return f"EXE_{uuid4()}"


# === ID Utilities ===

def extract_id_type(typed_id: str) -> str:
    """
    Extract type prefix from typed ID.

    Args:
        typed_id: Typed ID string (e.g., "OPP_abc-123")

    Returns:
        Type prefix (e.g., "OPP")

    Raises:
        ValueError: If ID format is invalid or prefix is unknown

    Examples:
        >>> extract_id_type("OPP_550e8400-e29b-41d4-a716-446655440000")
        'OPP'
        >>> extract_id_type("TCK_abc-def")
        'TCK'
    """
    if '_' not in typed_id:
        raise ValueError(f"Invalid typed ID format: {typed_id}")

    prefix = typed_id.split('_')[0]
    valid_prefixes = [
        'TCK', 'SCH', 'NWS', 'MAN',  # Flow initiators
        'OPP', 'THR', 'TRD', 'ASS',  # Causal chain
        'STR',  # Strategy directive
        'ENT', 'SIZ', 'EXT', 'ROU', 'EXE'  # Planning chain
    ]

    if prefix not in valid_prefixes:
        raise ValueError(f"Unknown ID prefix: {prefix}")

    return prefix
