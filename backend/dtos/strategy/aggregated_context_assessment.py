# backend/dtos/strategy/aggregated_context_assessment.py
"""
AggregatedContextAssessment DTO - Consolidated SWOT assessment.

Aggregates multiple ContextFactors into strengths and weaknesses quadrants.
Output of ContextAggregator, input for OpportunityDetector and ThreatDetector.

@layer: DTOs (Strategy Output)
@dependencies: [pydantic, backend.dtos.strategy.context_factor, backend.utils.id_generators]
"""

# Standard Library Imports
from datetime import datetime
from typing import Any, Dict, Optional

# Third-Party Imports
from pydantic import BaseModel, Field, field_validator

# Our Application Imports
from backend.dtos.strategy.context_factor import ContextFactor
from backend.utils.id_generators import generate_assessment_id


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
        assessment_id: Unique identifier with ASS_ prefix
        timestamp: When this assessment was created (UTC timezone-aware)
        strengths: List of strength factors (can be empty)
        weaknesses: List of weakness factors (can be empty)
        metadata: Optional aggregator-specific additional context
    """

    assessment_id: str = Field(
        default_factory=generate_assessment_id,
        description="Unique assessment identifier with ASS_ prefix"
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
        "str_strip_whitespace": True
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
