# tests/unit/dtos/test_causality.py
"""
Unit tests for CausalityChain DTO.

Tests the ID-only causality tracking container that flows through
the entire pipeline for Journal reconstruction.

@layer: Tests (Unit)
@dependencies: [pytest, backend.dtos.causality]
"""

# Standard Library Imports
import json

# Third-Party Imports
import pytest

# Our Application Imports
from backend.dtos.causality import CausalityChain


class TestCausalityChainCreation:
    """Test suite for CausalityChain instantiation."""

    def test_create_with_tick_birth(self):
        """Test creating CausalityChain with tick birth ID."""
        chain = CausalityChain(
            tick_id="TCK_20251026_100000_a1b2c3d4"
        )

        assert chain.tick_id == "TCK_20251026_100000_a1b2c3d4"
        assert chain.news_id is None
        assert chain.schedule_id is None

    def test_create_with_news_birth(self):
        """Test creating CausalityChain with news birth ID."""
        chain = CausalityChain(
            news_id="NWS_20251026_100000_b2c3d4e5"
        )

        assert chain.tick_id is None
        assert chain.news_id == "NWS_20251026_100000_b2c3d4e5"
        assert chain.schedule_id is None

    def test_create_with_schedule_birth(self):
        """Test creating CausalityChain with schedule birth ID."""
        chain = CausalityChain(
            schedule_id="SCH_20251026_100000_abc1d2e3"
        )

        assert chain.tick_id is None
        assert chain.news_id is None
        assert chain.schedule_id == "SCH_20251026_100000_abc1d2e3"

    def test_create_with_all_worker_ids_empty(self):
        """Test that worker output IDs default to empty."""
        chain = CausalityChain(
            tick_id="TCK_20251026_100000_a1b2c3d4"
        )

        assert chain.opportunity_signal_ids == []
        assert chain.threat_ids == []
        assert chain.context_assessment_id is None
        assert chain.strategy_directive_id is None
        assert chain.entry_plan_id is None
        assert chain.size_plan_id is None
        assert chain.exit_plan_id is None
        assert chain.execution_plan_id is None
        assert chain.execution_directive_id is None


class TestCausalityChainBirthValidation:
    """Test suite for birth ID validation (at least 1 required)."""

    def test_empty_chain_raises_validation_error(self):
        """Test that chain without birth ID raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            CausalityChain()

        error_msg = str(exc_info.value).lower()
        assert "causalitychain" in error_msg
        assert "birth id" in error_msg

    def test_all_birth_ids_none_raises_validation_error(self):
        """Test that explicit None for all birth IDs raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            CausalityChain(
                tick_id=None,
                news_id=None,
                schedule_id=None
            )

        error_msg = str(exc_info.value).lower()
        assert "causalitychain" in error_msg
        assert "birth id" in error_msg

    def test_single_birth_id_is_valid(self):
        """Test that single birth ID passes validation."""
        # Tick birth
        chain1 = CausalityChain(tick_id="TCK_20251026_100000_a1b2c3d4")
        assert chain1.tick_id is not None

        # News birth
        chain2 = CausalityChain(news_id="NWS_20251026_100000_b2c3d4e5")
        assert chain2.news_id is not None

        # Schedule birth
        chain3 = CausalityChain(schedule_id="SCH_20251026_100000_abc1d2e3")
        assert chain3.schedule_id is not None

    def test_multiple_birth_ids_is_valid(self):
        """Test that multiple birth IDs are allowed (edge case)."""
        chain = CausalityChain(
            tick_id="TCK_20251026_100000_a1b2c3d4",
            news_id="NWS_20251026_100000_b2c3d4e5"
        )

        assert chain.tick_id == "TCK_20251026_100000_a1b2c3d4"
        assert chain.news_id == "NWS_20251026_100000_b2c3d4e5"


class TestCausalityChainWorkerIDs:
    """Test suite for worker output ID accumulation."""

    def test_add_single_opportunity_signal_id(self):
        """Test adding single opportunity signal ID."""
        chain = CausalityChain(
            tick_id="TCK_20251026_100000_a1b2c3d4",
            opportunity_signal_ids=["OPP_20251026_100001_def5e6f7"]
        )

        assert len(chain.opportunity_signal_ids) == 1
        assert chain.opportunity_signal_ids[0] == "OPP_20251026_100001_def5e6f7"

    def test_add_multiple_opportunity_signal_ids(self):
        """Test adding multiple opportunity signal IDs (confluence)."""
        chain = CausalityChain(
            tick_id="TCK_20251026_100000_a1b2c3d4",
            opportunity_signal_ids=[
                "OPP_20251026_100001_def5e6f7",
                "OPP_20251026_100002_abc1d2e3"
            ]
        )

        assert len(chain.opportunity_signal_ids) == 2
        assert "OPP_20251026_100001_def5e6f7" in chain.opportunity_signal_ids
        assert "OPP_20251026_100002_abc1d2e3" in chain.opportunity_signal_ids

    def test_add_threat_ids(self):
        """Test adding threat IDs (CriticalEvent)."""
        chain = CausalityChain(
            tick_id="TCK_20251026_100000_a1b2c3d4",
            threat_ids=["THR_20251026_100001_b2c3d4e5"]
        )

        assert len(chain.threat_ids) == 1
        assert chain.threat_ids[0] == "THR_20251026_100001_b2c3d4e5"

    def test_add_context_assessment_id(self):
        """Test adding context assessment ID (SWOT)."""
        chain = CausalityChain(
            tick_id="TCK_20251026_100000_a1b2c3d4",
            context_assessment_id="CTX_20251026_100001_abc1d2e3"
        )

        assert chain.context_assessment_id == "CTX_20251026_100001_abc1d2e3"

    def test_add_strategy_directive_id(self):
        """Test adding strategy directive ID."""
        chain = CausalityChain(
            tick_id="TCK_20251026_100000_a1b2c3d4",
            strategy_directive_id="STR_20251026_100002_def5e6f7"
        )

        assert chain.strategy_directive_id == "STR_20251026_100002_def5e6f7"

    def test_add_all_plan_ids(self):
        """Test adding all planning stage IDs."""
        chain = CausalityChain(
            tick_id="TCK_20251026_100000_a1b2c3d4",
            entry_plan_id="ENT_20251026_100003_abc1d2e3",
            size_plan_id="SIZ_20251026_100004_def5e6f7",
            exit_plan_id="EXT_20251026_100005_abc1d2e3",
            execution_plan_id="EXP_20251026_100006_def5e6f7"
        )

        assert chain.entry_plan_id == "ENT_20251026_100003_abc1d2e3"
        assert chain.size_plan_id == "SIZ_20251026_100004_def5e6f7"
        assert chain.exit_plan_id == "EXT_20251026_100005_abc1d2e3"
        assert chain.execution_plan_id == "EXP_20251026_100006_def5e6f7"

    def test_add_execution_directive_id(self):
        """Test adding execution directive ID (final stage)."""
        chain = CausalityChain(
            tick_id="TCK_20251026_100000_a1b2c3d4",
            execution_directive_id="EXE_20251026_100007_abc1d2e3"
        )

        assert chain.execution_directive_id == "EXE_20251026_100007_abc1d2e3"


class TestCausalityChainModelCopyPattern:
    """Test suite for immutability and model_copy() pattern."""

    def test_model_copy_preserves_birth_ids(self):
        """Test that model_copy preserves birth IDs."""
        original = CausalityChain(
            tick_id="TCK_20251026_100000_a1b2c3d4"
        )

        copy = original.model_copy(update={
            "opportunity_signal_ids": ["OPP_20251026_100001_def5e6f7"]
        })

        assert copy.tick_id == "TCK_20251026_100000_a1b2c3d4"
        assert copy.opportunity_signal_ids == ["OPP_20251026_100001_def5e6f7"]

    def test_model_copy_extends_worker_ids(self):
        """Test that model_copy can extend worker IDs."""
        original = CausalityChain(
            tick_id="TCK_20251026_100000_a1b2c3d4",
            opportunity_signal_ids=["OPP_20251026_100001_def5e6f7"]
        )

        extended = original.model_copy(update={
            "strategy_directive_id": "STR_20251026_100002_abc1d2e3"
        })

        assert extended.tick_id == "TCK_20251026_100000_a1b2c3d4"
        assert extended.opportunity_signal_ids == ["OPP_20251026_100001_def5e6f7"]
        assert extended.strategy_directive_id == "STR_20251026_100002_abc1d2e3"

    def test_model_copy_chain_accumulation(self):
        """Test full pipeline chain accumulation via model_copy."""
        # Birth
        birth = CausalityChain(
            tick_id="TCK_20251026_100000_a1b2c3d4"
        )

        # OpportunityWorker
        after_opp = birth.model_copy(update={
            "opportunity_signal_ids": ["OPP_20251026_100001_def5e6f7"]
        })

        # StrategyPlanner
        after_strategy = after_opp.model_copy(update={
            "strategy_directive_id": "STR_20251026_100002_abc1d2e3"
        })

        # EntryPlanner
        after_entry = after_strategy.model_copy(update={
            "entry_plan_id": "ENT_20251026_100003_def5e6f7"
        })

        # Verify full chain
        assert after_entry.tick_id == "TCK_20251026_100000_a1b2c3d4"
        assert after_entry.opportunity_signal_ids == ["OPP_20251026_100001_def5e6f7"]
        assert after_entry.strategy_directive_id == "STR_20251026_100002_abc1d2e3"
        assert after_entry.entry_plan_id == "ENT_20251026_100003_def5e6f7"


class TestCausalityChainSerialization:
    """Test suite for JSON/dict serialization."""

    def test_model_dump_includes_all_fields(self):
        """Test that model_dump includes all 12 fields."""
        chain = CausalityChain(
            tick_id="TCK_20251026_100000_a1b2c3d4",
            opportunity_signal_ids=["OPP_20251026_100001_def5e6f7"]
        )

        data = chain.model_dump()

        # Birth IDs
        assert "tick_id" in data
        assert "news_id" in data
        assert "schedule_id" in data

        # Worker output IDs
        assert "opportunity_signal_ids" in data
        assert "threat_ids" in data
        assert "context_assessment_id" in data
        assert "strategy_directive_id" in data
        assert "entry_plan_id" in data
        assert "size_plan_id" in data
        assert "exit_plan_id" in data
        assert "execution_plan_id" in data
        assert "execution_directive_id" in data

    def test_model_dump_json_serializable(self):
        """Test that model_dump produces JSON-serializable dict."""
        chain = CausalityChain(
            tick_id="TCK_20251026_100000_a1b2c3d4",
            opportunity_signal_ids=["OPP_20251026_100001_def5e6f7"],
            strategy_directive_id="STR_20251026_100002_abc1d2e3"
        )

        data = chain.model_dump()
        json_str = json.dumps(data)  # Should not raise

        assert isinstance(json_str, str)

    def test_model_validate_from_dict(self):
        """Test creating CausalityChain from dict."""
        data = {
            "tick_id": "TCK_20251026_100000_a1b2c3d4",
            "news_id": None,
            "schedule_id": None,
            "opportunity_signal_ids": ["OPP_20251026_100001_def5e6f7"],
            "threat_ids": [],
            "context_assessment_id": None,
            "strategy_directive_id": "STR_20251026_100002_abc1d2e3",
            "entry_plan_id": None,
            "size_plan_id": None,
            "exit_plan_id": None,
            "execution_plan_id": None,
            "execution_directive_id": None
        }

        chain = CausalityChain.model_validate(data)

        assert chain.tick_id == "TCK_20251026_100000_a1b2c3d4"
        assert chain.opportunity_signal_ids == ["OPP_20251026_100001_def5e6f7"]
        assert chain.strategy_directive_id == "STR_20251026_100002_abc1d2e3"


class TestCausalityChainEdgeCases:
    """Test suite for edge cases and error conditions."""

    def test_empty_opportunity_signal_ids_list(self):
        """Test that empty list is valid for opportunity_signal_ids."""
        chain = CausalityChain(
            tick_id="TCK_20251026_100000_a1b2c3d4",
            opportunity_signal_ids=[]
        )

        assert chain.opportunity_signal_ids == []

    def test_empty_threat_ids_list(self):
        """Test that empty list is valid for threat_ids."""
        chain = CausalityChain(
            tick_id="TCK_20251026_100000_a1b2c3d4",
            threat_ids=[]
        )

        assert chain.threat_ids == []

    def test_none_values_for_optional_ids(self):
        """Test that None is valid for all optional worker IDs."""
        chain = CausalityChain(
            tick_id="TCK_20251026_100000_a1b2c3d4",
            context_assessment_id=None,
            strategy_directive_id=None,
            entry_plan_id=None,
            size_plan_id=None,
            exit_plan_id=None,
            execution_plan_id=None,
            execution_directive_id=None
        )

        assert chain.context_assessment_id is None
        assert chain.strategy_directive_id is None
        assert chain.entry_plan_id is None

    def test_full_chain_all_ids_populated(self):
        """Test full chain with all IDs populated."""
        chain = CausalityChain(
            tick_id="TCK_20251026_100000_a1b2c3d4",
            opportunity_signal_ids=["OPP_20251026_100001_def5e6f7"],
            threat_ids=["THR_20251026_100002_abc1d2e3"],
            context_assessment_id="CTX_20251026_100003_def5e6f7",
            strategy_directive_id="STR_20251026_100004_abc1d2e3",
            entry_plan_id="ENT_20251026_100005_def5e6f7",
            size_plan_id="SIZ_20251026_100006_abc1d2e3",
            exit_plan_id="EXT_20251026_100007_def5e6f7",
            execution_plan_id="EXP_20251026_100008_abc1d2e3",
            execution_directive_id="EXE_20251026_100009_def5e6f7"
        )

        # Verify all 12 fields populated
        assert chain.tick_id is not None
        assert len(chain.opportunity_signal_ids) == 1
        assert len(chain.threat_ids) == 1
        assert chain.context_assessment_id is not None
        assert chain.strategy_directive_id is not None
        assert chain.entry_plan_id is not None
        assert chain.size_plan_id is not None
        assert chain.exit_plan_id is not None
        assert chain.execution_plan_id is not None
        assert chain.execution_directive_id is not None
