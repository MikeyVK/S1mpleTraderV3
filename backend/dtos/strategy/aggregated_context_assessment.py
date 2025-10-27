# backend/dtos/strategy/aggregated_context_assessment.py
"""
AggregatedContextAssessment DTO - Consolidated SWOT assessment.

Aggregates multiple ContextFactors into strengths and weaknesses quadrants.
Output of ContextAggregator, input for OpportunityDetector and ThreatDetector.

@layer: DTOs (Strategy Output)
@dependencies: [pydantic, backend.dtos.strategy.context_factor, backend.utils.id_generators,
                backend.dtos.causality]
"""

# Standard Library Imports
from datetime import datetime
from typing import Any, Dict, Optional

# Third-Party Imports
from pydantic import BaseModel, Field, field_validator

# Our Application Imports
from backend.dtos.strategy.context_factor import ContextFactor
from backend.utils.id_generators import generate_assessment_id
from backend.dtos.causality import CausalityChain


class AggregatedContextAssessment(BaseModel):
    """
    Aggregated SWOT assessment combining multiple context factors.

    The ContextAggregator collects ContextFactors from various ContextWorkers
    and groups them into strengths and weaknesses. This assessment forms the
    foundation for opportunity and threat detection.

    **SWOT Quadrants:** Strengths + Weaknesses → Opportunities + Threats

    **Key Constraints:**
    - At least one of strengths or weaknesses must be non-empty
    - All factors in strengths list must have strength scores
    - All factors in weaknesses list must have weakness scores
    - Assessment ID follows ASS_ prefix convention
    - Timestamp must be timezone-aware (UTC)

    **Usage Example:**
    ```python
    strength1 = ContextFactor(
        factor_type=BaseFactorType.TRENDING_REGIME.value,
        strength=0.75,
        weakness=None,
        source_plugin="trend_analyzer",
        source_context_type=ContextType.REGIME_CLASSIFICATION.value
    )

    weakness1 = ContextFactor(
        factor_type=BaseFactorType.HIGH_VOLATILITY.value,
        strength=None,
        weakness=0.60,
        source_plugin="volatility_detector",
        source_context_type=ContextType.VOLATILITY_ASSESSMENT.value
    )

    assessment = AggregatedContextAssessment(
        timestamp=datetime.now(timezone.utc),
        strengths=[strength1],
        weaknesses=[weakness1],
        metadata={"total_workers": 5, "aggregation_method": "weighted_avg"}
    )
    ```

    **Philosophy:**
    This DTO is a "dumb" container - it validates structure but doesn't
    interpret meaning. The OpportunityDetector and ThreatDetector workers
    are "smart" - they analyze the factors to identify actionable signals.

    Attributes:
        causality: CausalityChain tracking IDs from birth through workers
        assessment_id: Unique identifier with ASS_ prefix
        timestamp: When this assessment was created (UTC timezone-aware)
        strengths: List of strength factors (can be empty)
        weaknesses: List of weakness factors (can be empty)
        metadata: Optional aggregator-specific additional context
    """

    causality: CausalityChain = Field(
        description="Causality tracking - IDs from birth (tick/news/schedule)"
    )

    assessment_id: str = Field(
        default_factory=generate_assessment_id,
        pattern=r'^CTX_\d{8}_\d{6}_[0-9a-f]{8}$',
        description="Unique assessment identifier (military datetime format)"
    )

    timestamp: datetime = Field(
        ...,
        description="Assessment creation timestamp (UTC timezone-aware)"
    )

    strengths: list[ContextFactor] = Field(  # type: ignore[valid-type]
        default_factory=list,
        description="List of strength factors"
    )

    weaknesses: list[ContextFactor] = Field(  # type: ignore[valid-type]
        default_factory=list,
        description="List of weakness factors"
    )

    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional aggregator-specific additional context"
    )

    model_config = {
        "frozen": True,
        "extra": "forbid",
        "str_strip_whitespace": True,
        "json_schema_extra": {
            "examples": [
                {
                    "description": "Balanced SWOT assessment (strengths + weaknesses)",
                    "assessment_id": "CTX_20251027_100001_a1b2c3d4",
                    "timestamp": "2025-10-27T10:00:01Z",
                    "strengths": [
                        {
                            "factor_type": "TREND_ALIGNMENT",
                            "strength": 0.85,
                            "source_plugin": "trend_analyzer",
                            "source_context_type": "TECHNICAL"
                        },
                        {
                            "factor_type": "MOMENTUM_CONFIRMATION",
                            "strength": 0.78,
                            "source_plugin": "momentum_tracker",
                            "source_context_type": "TECHNICAL"
                        }
                    ],
                    "weaknesses": [
                        {
                            "factor_type": "LIQUIDITY_RISK",
                            "weakness": 0.45,
                            "source_plugin": "risk_monitor",
                            "source_context_type": "RISK"
                        }
                    ]
                },
                {
                    "description": "Strengths-only assessment (strong setup)",
                    "assessment_id": "CTX_20251027_143000_e5f6g7h8",
                    "timestamp": "2025-10-27T14:30:00Z",
                    "strengths": [
                        {
                            "factor_type": "VOLUME_SURGE",
                            "strength": 0.92,
                            "source_plugin": "volume_analyzer",
                            "source_context_type": "TECHNICAL"
                        }
                    ],
                    "weaknesses": []
                },
                {
                    "description": "Weaknesses-only assessment (threat scenario)",
                    "assessment_id": "CTX_20251027_150500_i9j0k1l2",
                    "timestamp": "2025-10-27T15:05:00Z",
                    "strengths": [],
                    "weaknesses": [
                        {
                            "factor_type": "MARKET_VOLATILITY",
                            "weakness": 0.88,
                            "source_plugin": "volatility_monitor",
                            "source_context_type": "RISK"
                        },
                        {
                            "factor_type": "CORRELATION_BREAKDOWN",
                            "weakness": 0.72,
                            "source_plugin": "correlation_tracker",
                            "source_context_type": "RISK"
                        }
                    ]
                }
            ]
        }
    }

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, v: datetime) -> datetime:
        """Validate timestamp is timezone-aware."""
        if v.tzinfo is None:
            raise ValueError(
                "timestamp must be timezone-aware (use datetime.now(timezone.utc))"
            )
        return v
