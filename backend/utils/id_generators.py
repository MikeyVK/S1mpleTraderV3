# backend/utils/id_generators.py
"""
Typed ID generation utilities.

Provides standardized ID generation with type prefixes for causal
traceability across the trading system. All IDs follow the pattern:
{PREFIX}_{YYYYMMDD}_{HHMMSS}_{hash}

ID Format:
    PREFIX: 3-letter type identifier (TCK, OPP, STR, etc.)
    YYYYMMDD: UTC date (military format)
    HHMMSS: UTC time (military format)
    hash: 8-character hex hash for uniqueness

Example: TCK_20251026_143052_a1b2c3d4

Benefits:
    - Temporal sortability (chronological ordering)
    - Human readability (know when ID was created)
    - Uniqueness (hash suffix prevents collisions)
    - Uniform format (all IDs follow same pattern)

Prefix Convention:
    Birth IDs (strategy run initiators):
        TCK_ - Market tick event
        SCH_ - Scheduled event (DCA, rebalancing, etc.)
        NWS_ - News/external event

    Worker Output IDs (Quant Framework):
        SIG_ - Signal (SignalDetector output)
        RSK_ - Risk (RiskMonitor output)

    Worker Output IDs (Planning pipeline):
        STR_ - StrategyDirective (StrategyPlanner output)
        ENT_ - EntryPlan (EntryPlanner output)
        SIZ_ - SizePlan (SizePlanner output)
        EXT_ - ExitPlan (ExitPlanner output)
        EXP_ - ExecutionPlan (FlowTerminator output)
        EXE_ - ExecutionDirective (DirectiveAssembler output)

Causal Traceability Examples:
    Tick-based quant flow:
        TCK_20251026_100000_abc123 (birth)
          → SIG_20251026_100001_def456 (SignalDetector)
          → STR_20251026_100002_jkl012 (StrategyPlanner)
          → ENT_20251026_100003_mno345 (EntryPlanner)
          → EXE_20251026_100010_pqr678 (DirectiveAssembler)

    Scheduled DCA flow:
        SCH_20251026_100000_stu901 (birth)
          → STR_20251026_100001_vwx234 (DCAPlanner)
          → ENT_20251026_100002_yza567 (EntryPlanner)
          → SIZ_20251026_100003_bcd890 (SizePlanner)
          → EXE_20251026_100010_efg123 (DirectiveAssembler)

@layer: Backend (Utils)
@dependencies: [datetime, hashlib]
@responsibilities:
    - Generate typed IDs with consistent military datetime format
    - Extract ID type from typed ID string
    - Maintain ID format consistency
"""

from datetime import datetime, timezone
from hashlib import sha256
from uuid import uuid4


__all__ = [
    'generate_tick_id',
    'generate_schedule_id',
    'generate_news_id',
    'generate_signal_id',
    'generate_risk_id',
    'generate_strategy_directive_id',
    'generate_entry_plan_id',
    'generate_size_plan_id',
    'generate_exit_plan_id',
    'generate_execution_plan_id',
    'generate_execution_directive_id',
    'generate_execution_group_id',
    'generate_batch_id',
    'extract_id_type',
    'extract_id_timestamp',
]


def _generate_id(prefix: str) -> str:
    """
    Generate uniform ID with military datetime format.
    
    Format: {PREFIX}_{YYYYMMDD}_{HHMMSS}_{hash}
    
    Args:
        prefix: 3-letter type identifier (e.g., 'TCK', 'OPP', 'STR')
    
    Returns:
        Formatted ID string
    
    Example:
        >>> _generate_id('TCK')
        'TCK_20251026_143052_a1b2c3d4'
    """
    now = datetime.now(timezone.utc)
    date_str = now.strftime('%Y%m%d')
    time_str = now.strftime('%H%M%S')

    # Generate 8-char hash for uniqueness
    hash_input = f"{prefix}{now.isoformat()}{uuid4()}".encode()
    hash_hex = sha256(hash_input).hexdigest()[:8]

    return f"{prefix}_{date_str}_{time_str}_{hash_hex}"


# === Birth IDs (Strategy Run Initiators) ===

def generate_tick_id() -> str:
    """Generate market tick event ID."""
    return _generate_id('TCK')


def generate_schedule_id() -> str:
    """Generate scheduled event ID."""
    return _generate_id('SCH')


def generate_news_id() -> str:
    """Generate news/external event ID."""
    return _generate_id('NWS')


# === Worker Output IDs (Quant Framework) ===

def generate_signal_id() -> str:
    """Generate Signal ID."""
    return _generate_id('SIG')


def generate_risk_id() -> str:
    """Generate Risk ID."""
    return _generate_id('RSK')


# === Worker Output IDs (Planning Pipeline) ===

def generate_strategy_directive_id() -> str:
    """Generate StrategyDirective ID."""
    return _generate_id('STR')


def generate_entry_plan_id() -> str:
    """Generate EntryPlan ID."""
    return _generate_id('ENT')


def generate_size_plan_id() -> str:
    """Generate SizePlan ID."""
    return _generate_id('SIZ')


def generate_exit_plan_id() -> str:
    """Generate ExitPlan ID."""
    return _generate_id('EXT')


def generate_execution_plan_id() -> str:
    """Generate ExecutionPlan ID."""
    return _generate_id('EXP')


def generate_execution_directive_id() -> str:
    """Generate ExecutionDirective ID."""
    return _generate_id('EXE')


def generate_execution_group_id() -> str:
    """Generate ExecutionGroup ID."""
    return _generate_id('EXG')


def generate_batch_id() -> str:
    """Generate ExecutionDirectiveBatch ID."""
    return _generate_id('BAT')


# === ID Utilities ===

def extract_id_type(typed_id: str) -> str:
    """
    Extract type prefix from typed ID.

    Args:
        typed_id: Typed ID string (e.g., "OPP_20251026_100000_abc123")

    Returns:
        Type prefix (e.g., "OPP")

    Raises:
        ValueError: If ID format is invalid or prefix is unknown

    Examples:
        >>> extract_id_type("SIG_20251026_100000_abc123")
        'SIG'
        >>> extract_id_type("TCK_20251026_143052_a1b2c3d4")
        'TCK'
    """
    if '_' not in typed_id:
        raise ValueError(f"Invalid typed ID format: {typed_id}")

    prefix = typed_id.split('_')[0]
    valid_prefixes = [
        'TCK', 'SCH', 'NWS',        # Birth IDs
        'SIG', 'RSK', 'CTX',        # Quant worker outputs
        'STR',                      # StrategyPlanner output
        'ENT', 'SIZ', 'EXT', 'EXP', 'EXE', 'EXG', 'BAT'  # Planning pipeline outputs
    ]

    if prefix not in valid_prefixes:
        raise ValueError(f"Unknown ID prefix: {prefix}")

    return prefix


def extract_id_timestamp(typed_id: str) -> datetime:
    """
    Extract UTC timestamp from typed ID.

    Args:
        typed_id: Typed ID string (e.g., "OPP_20251026_100000_abc123")

    Returns:
        UTC datetime of when ID was created

    Raises:
        ValueError: If ID format is invalid or timestamp cannot be parsed

    Examples:
        >>> extract_id_timestamp("SIG_20251026_100000_abc123")
        datetime.datetime(2025, 10, 26, 10, 0, 0, tzinfo=timezone.utc)
    """
    parts = typed_id.split('_')
    if len(parts) != 4:
        raise ValueError(
            f"Invalid typed ID format: {typed_id}. "
            f"Expected PREFIX_YYYYMMDD_HHMMSS_hash"
        )

    _prefix, date_str, time_str, _hash_str = parts

    try:
        # Parse YYYYMMDD_HHMMSS
        dt_str = f"{date_str}_{time_str}"
        dt = datetime.strptime(dt_str, '%Y%m%d_%H%M%S')
        return dt.replace(tzinfo=timezone.utc)
    except ValueError as e:
        raise ValueError(
            f"Invalid timestamp in ID {typed_id}: {date_str}_{time_str}"
        ) from e
