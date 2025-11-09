# tests/unit/dtos/shared/test_origin.py
"""
Tests for Origin DTO - Platform data origin tracking.

Tests creation, validation, and type-safe origin reference functionality.

@layer: Tests
@dependencies: [pytest, backend.dtos.shared.origin]
"""

import pytest
from backend.dtos.shared.origin import Origin, OriginType


class TestOriginCreation:
    """Test Origin DTO instantiation with valid data."""

    def test_create_tick_origin(self):
        """Test creating a TICK origin with valid ID."""
        origin = Origin(
            id="TCK_20251109_143022_abc123",
            type=OriginType.TICK
        )
        assert origin.id == "TCK_20251109_143022_abc123"
        assert origin.type == OriginType.TICK

    def test_create_news_origin(self):
        """Test creating a NEWS origin with valid ID."""
        origin = Origin(
            id="NWS_20251109_143022_def456",
            type=OriginType.NEWS
        )
        assert origin.id == "NWS_20251109_143022_def456"
        assert origin.type == OriginType.NEWS

    def test_create_schedule_origin(self):
        """Test creating a SCHEDULE origin with valid ID."""
        origin = Origin(
            id="SCH_20251109_143022_ghi789",
            type=OriginType.SCHEDULE
        )
        assert origin.id == "SCH_20251109_143022_ghi789"
        assert origin.type == OriginType.SCHEDULE


class TestOriginTypeEnum:
    """Test OriginType enum values."""

    def test_origin_type_values(self):
        """Test that OriginType has correct enum values."""
        assert OriginType.TICK.value == "TICK"
        assert OriginType.NEWS.value == "NEWS"
        assert OriginType.SCHEDULE.value == "SCHEDULE"

    def test_origin_type_count(self):
        """Test that OriginType has exactly 3 values."""
        assert len(OriginType) == 3


class TestOriginValidation:
    """Test Origin DTO validation rules."""

    def test_tick_id_must_have_tck_prefix(self):
        """Test that TICK type requires TCK_ prefix."""
        with pytest.raises(ValueError, match="ID prefix 'NWS' doesn't match type"):
            Origin(
                id="NWS_20251109_143022_abc123",  # Wrong prefix
                type=OriginType.TICK
            )

    def test_news_id_must_have_nws_prefix(self):
        """Test that NEWS type requires NWS_ prefix."""
        with pytest.raises(ValueError, match="ID prefix 'TCK' doesn't match type"):
            Origin(
                id="TCK_20251109_143022_def456",  # Wrong prefix
                type=OriginType.NEWS
            )

    def test_schedule_id_must_have_sch_prefix(self):
        """Test that SCHEDULE type requires SCH_ prefix."""
        with pytest.raises(ValueError, match="ID prefix 'TCK' doesn't match type"):
            Origin(
                id="TCK_20251109_143022_ghi789",  # Wrong prefix
                type=OriginType.SCHEDULE
            )

    def test_invalid_id_format_no_underscore(self):
        """Test that ID without underscore fails validation."""
        with pytest.raises((ValueError, IndexError)):
            Origin(
                id="TCK20251109143022abc123",  # No underscore
                type=OriginType.TICK
            )


class TestOriginImmutability:
    """Test Origin DTO immutability (if frozen=True)."""

    def test_origin_fields_are_immutable(self):
        """Test that Origin fields cannot be modified after creation."""
        origin = Origin(
            id="TCK_20251109_143022_abc123",
            type=OriginType.TICK
        )
        # Pydantic raises ValidationError on assignment if frozen=True
        with pytest.raises((AttributeError, ValueError)):
            origin.id = "NWS_20251109_143022_def456"  # type: ignore


class TestOriginEquality:
    """Test Origin DTO equality comparisons."""

    def test_origins_with_same_values_are_equal(self):
        """Test that two Origin instances with same values are equal."""
        origin1 = Origin(
            id="TCK_20251109_143022_abc123",
            type=OriginType.TICK
        )
        origin2 = Origin(
            id="TCK_20251109_143022_abc123",
            type=OriginType.TICK
        )
        assert origin1 == origin2

    def test_origins_with_different_ids_are_not_equal(self):
        """Test that Origin instances with different IDs are not equal."""
        origin1 = Origin(
            id="TCK_20251109_143022_abc123",
            type=OriginType.TICK
        )
        origin2 = Origin(
            id="TCK_20251109_143022_xyz789",
            type=OriginType.TICK
        )
        assert origin1 != origin2

    def test_origins_with_different_types_are_not_equal(self):
        """Test that Origin instances with different types are not equal."""
        origin1 = Origin(
            id="TCK_20251109_143022_abc123",
            type=OriginType.TICK
        )
        origin2 = Origin(
            id="NWS_20251109_143022_abc123",
            type=OriginType.NEWS
        )
        assert origin1 != origin2


class TestOriginEdgeCases:
    """Test Origin DTO edge cases and boundary conditions."""

    def test_id_with_multiple_underscores(self):
        """Test that ID with multiple underscores still validates correctly."""
        origin = Origin(
            id="TCK_20251109_143022_abc_123_def",
            type=OriginType.TICK
        )
        assert origin.id == "TCK_20251109_143022_abc_123_def"

    def test_minimum_valid_id(self):
        """Test that minimal valid ID works."""
        origin = Origin(
            id="TCK_1",
            type=OriginType.TICK
        )
        assert origin.id == "TCK_1"

    def test_very_long_id(self):
        """Test that very long ID is accepted."""
        long_id = "TCK_" + "a" * 200
        origin = Origin(
            id=long_id,
            type=OriginType.TICK
        )
        assert origin.id == long_id
