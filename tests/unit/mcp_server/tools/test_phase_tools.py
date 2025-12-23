# tests/unit/mcp_server/tools/test_phase_tools.py
"""
Unit tests for TransitionPhaseTool - Phase B (RED phase).

Tests according to TDD principles with comprehensive coverage.

@layer: Tests (Unit)
@dependencies: [pytest, TransitionPhaseTool, PhaseStateEngine]
"""
# pylint: disable=redefined-outer-name
# Standard library
from pathlib import Path

# Third-party
import pytest

# Module under test
from mcp_server.tools.phase_tools import TransitionPhaseTool, TransitionPhaseInput
from mcp_server.core.phase_state_engine import PhaseStateEngine


@pytest.fixture(autouse=True)
def cleanup_state_file():
    """Clean up state file before and after each test."""
    state_file = Path(".") / ".st3" / "state.json"

    # Clean before test
    if state_file.exists():
        state_file.unlink()

    yield

    # Clean after test
    if state_file.exists():
        state_file.unlink()


@pytest.fixture
def engine():
    """Create PhaseStateEngine instance for testing."""
    return PhaseStateEngine(workspace_root=Path("."))


@pytest.fixture
def tool():
    """Create TransitionPhaseTool instance for testing."""
    return TransitionPhaseTool(workspace_root=Path("."))


class TestTransitionPhaseToolMetadata:
    """Test TransitionPhaseTool metadata and schema."""

    def test_tool_has_correct_name(self, tool: TransitionPhaseTool) -> None:
        """Should have correct tool name."""
        assert tool.name == "transition_phase"

    def test_tool_has_correct_description(self, tool: TransitionPhaseTool) -> None:
        """Should have descriptive text."""
        assert "transition" in tool.description.lower()
        assert "branch" in tool.description.lower()
        assert "phase" in tool.description.lower()

    def test_tool_input_schema_has_required_fields(
        self, tool: TransitionPhaseTool
    ) -> None:
        """Should define required input fields."""
        schema = tool.input_schema
        assert "properties" in schema
        properties = schema["properties"]

        # Required fields
        assert "branch" in properties
        assert "from_phase" in properties
        assert "to_phase" in properties

        # Optional field
        assert "human_approval" in properties


class TestTransitionPhaseToolExecution:
    """Test TransitionPhaseTool execution logic."""

    @pytest.mark.asyncio
    async def test_transition_valid_phase_change(
        self, tool: TransitionPhaseTool, engine: PhaseStateEngine
    ) -> None:
        """Should successfully transition between valid phases."""
        # Setup: initialize branch
        engine.initialize_branch("feature/32-test", "discovery", issue_number=32)

        # Execute transition
        params = TransitionPhaseInput(
            branch="feature/32-test",
            from_phase="discovery",
            to_phase="planning"
        )
        result = await tool.execute(params)

        # Verify
        assert not result.is_error
        assert "success" in result.content[0]["text"].lower()
        assert "planning" in result.content[0]["text"]

    @pytest.mark.asyncio
    async def test_transition_with_invalid_from_phase(
        self, tool: TransitionPhaseTool, engine: PhaseStateEngine
    ) -> None:
        """Should fail when from_phase doesn't match current phase."""
        # Setup
        engine.initialize_branch("feature/32-test", "discovery", issue_number=32)

        # Execute with wrong from_phase
        params = TransitionPhaseInput(
            branch="feature/32-test",
            from_phase="planning",  # Wrong - current is discovery
            to_phase="design"
        )
        result = await tool.execute(params)

        # Verify error
        assert result.is_error or "fail" in result.content[0]["text"].lower()

    @pytest.mark.asyncio
    async def test_transition_for_unknown_branch(
        self, tool: TransitionPhaseTool
    ) -> None:
        """Should fail for branch without state."""
        params = TransitionPhaseInput(
            branch="feature/unknown",
            from_phase="discovery",
            to_phase="planning"
        )
        result = await tool.execute(params)

        # Verify error
        assert result.is_error or "fail" in result.content[0]["text"].lower()

    @pytest.mark.asyncio
    async def test_transition_with_human_approval(
        self, tool: TransitionPhaseTool, engine: PhaseStateEngine
    ) -> None:
        """Should record human approval message."""
        # Setup
        engine.initialize_branch("feature/32-test", "discovery", issue_number=32)

        # Execute with human approval
        params = TransitionPhaseInput(
            branch="feature/32-test",
            from_phase="discovery",
            to_phase="planning",
            human_approval="Approved by user after review"
        )
        result = await tool.execute(params)

        # Verify approval recorded - load fresh engine to read updated state
        assert not result.is_error
        engine2 = PhaseStateEngine(workspace_root=Path("."))
        history = engine2.get_transition_history("feature/32-test")
        assert len(history) >= 1
        assert history[-1].get("human_approval") == "Approved by user after review"

    @pytest.mark.asyncio
    async def test_transition_records_all_phase_changes(
        self, tool: TransitionPhaseTool, engine: PhaseStateEngine
    ) -> None:
        """Should track multiple transitions correctly."""
        # Setup
        engine.initialize_branch("feature/32-test", "discovery", issue_number=32)

        # Execute multiple transitions
        transitions = [
            ("discovery", "planning"),
            ("planning", "design"),
            ("design", "component")
        ]

        for from_phase, to_phase in transitions:
            params = TransitionPhaseInput(
                branch="feature/32-test",
                from_phase=from_phase,
                to_phase=to_phase
            )
            result = await tool.execute(params)
            assert not result.is_error

        # Verify history - load fresh engine to read updated state
        engine2 = PhaseStateEngine(workspace_root=Path("."))
        history = engine2.get_transition_history("feature/32-test")
        assert len(history) == 3
        assert history[0]["from_phase"] == "discovery"
        assert history[2]["to_phase"] == "component"


class TestTransitionPhaseToolIntegration:
    """Test TransitionPhaseTool integration with PhaseStateEngine."""

    @pytest.mark.asyncio
    async def test_transition_updates_phase_state(
        self, tool: TransitionPhaseTool, engine: PhaseStateEngine
    ) -> None:
        """Should update PhaseStateEngine state after transition."""
        # Setup
        engine.initialize_branch("feature/32-test", "discovery", issue_number=32)

        # Execute
        params = TransitionPhaseInput(
            branch="feature/32-test",
            from_phase="discovery",
            to_phase="planning"
        )
        await tool.execute(params)

        # Verify state updated - load fresh engine to read updated state
        engine2 = PhaseStateEngine(workspace_root=Path("."))
        current_phase = engine2.get_phase("feature/32-test")
        assert current_phase == "planning"

    @pytest.mark.asyncio
    async def test_transition_persists_to_state_file(
        self, tool: TransitionPhaseTool, engine: PhaseStateEngine
    ) -> None:
        """Should persist transition to .st3/state.json."""
        # Setup
        engine.initialize_branch("feature/32-test", "discovery", issue_number=32)

        # Execute
        params = TransitionPhaseInput(
            branch="feature/32-test",
            from_phase="discovery",
            to_phase="planning"
        )
        await tool.execute(params)

        # Verify persistence by loading new engine
        engine2 = PhaseStateEngine(workspace_root=Path("."))
        phase = engine2.get_phase("feature/32-test")
        assert phase == "planning"
