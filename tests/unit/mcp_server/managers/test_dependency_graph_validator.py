"""Tests for dependency graph validator."""
# Standard library
import pytest

# Project modules
from mcp_server.managers.dependency_graph_validator import DependencyGraphValidator
from mcp_server.state.project import PhaseSpec


class TestDependencyGraphValidator:
    """Tests for DependencyGraphValidator."""

    def test_valid_linear_graph(self) -> None:
        """Test validation of linear dependency chain."""
        phases = [
            PhaseSpec(phase_id="A", title="Phase A", depends_on=[]),
            PhaseSpec(phase_id="B", title="Phase B", depends_on=["A"]),
            PhaseSpec(phase_id="C", title="Phase C", depends_on=["B"])
        ]
        validator = DependencyGraphValidator()
        is_valid, cycle = validator.validate_acyclic(phases)
        assert is_valid is True
        assert cycle is None

    def test_valid_parallel_graph(self) -> None:
        """Test validation of parallel dependencies."""
        phases = [
            PhaseSpec(phase_id="A", title="Phase A", depends_on=[]),
            PhaseSpec(phase_id="B", title="Phase B", depends_on=["A"]),
            PhaseSpec(phase_id="C", title="Phase C", depends_on=["A"])
        ]
        validator = DependencyGraphValidator()
        is_valid, cycle = validator.validate_acyclic(phases)
        assert is_valid is True
        assert cycle is None

    def test_valid_diamond_graph(self) -> None:
        """Test validation of diamond dependency pattern."""
        phases = [
            PhaseSpec(phase_id="A", title="Phase A", depends_on=[]),
            PhaseSpec(phase_id="B", title="Phase B", depends_on=["A"]),
            PhaseSpec(phase_id="C", title="Phase C", depends_on=["A"]),
            PhaseSpec(phase_id="D", title="Phase D", depends_on=["B", "C"])
        ]
        validator = DependencyGraphValidator()
        is_valid, cycle = validator.validate_acyclic(phases)
        assert is_valid is True
        assert cycle is None

    def test_simple_cycle_detected(self) -> None:
        """Test detection of simple 2-node cycle."""
        phases = [
            PhaseSpec(phase_id="A", title="Phase A", depends_on=["B"]),
            PhaseSpec(phase_id="B", title="Phase B", depends_on=["A"])
        ]
        validator = DependencyGraphValidator()
        is_valid, cycle = validator.validate_acyclic(phases)
        assert is_valid is False
        assert cycle is not None
        assert len(cycle) >= 2

    def test_three_node_cycle_detected(self) -> None:
        """Test detection of 3-node cycle."""
        phases = [
            PhaseSpec(phase_id="A", title="Phase A", depends_on=["C"]),
            PhaseSpec(phase_id="B", title="Phase B", depends_on=["A"]),
            PhaseSpec(phase_id="C", title="Phase C", depends_on=["B"])
        ]
        validator = DependencyGraphValidator()
        is_valid, cycle = validator.validate_acyclic(phases)
        assert is_valid is False
        assert cycle is not None
        assert len(cycle) >= 3

    def test_self_loop_detected(self) -> None:
        """Test detection of self-loop (already caught by DTO validation)."""
        # Note: PhaseSpec validation already prevents self-loops
        # This test documents that behavior
        with pytest.raises(ValueError, match="cannot depend on itself"):
            PhaseSpec(phase_id="A", title="Phase A", depends_on=["A"])

    def test_topological_sort_linear(self) -> None:
        """Test topological sort produces correct order for linear chain."""
        phases = [
            PhaseSpec(phase_id="C", title="Phase C", depends_on=["B"]),
            PhaseSpec(phase_id="A", title="Phase A", depends_on=[]),
            PhaseSpec(phase_id="B", title="Phase B", depends_on=["A"])
        ]
        validator = DependencyGraphValidator()
        sorted_ids = validator.topological_sort(phases)
        assert sorted_ids == ["A", "B", "C"]

    def test_topological_sort_parallel(self) -> None:
        """Test topological sort with parallel dependencies."""
        phases = [
            PhaseSpec(phase_id="A", title="Phase A", depends_on=[]),
            PhaseSpec(phase_id="B", title="Phase B", depends_on=["A"]),
            PhaseSpec(phase_id="C", title="Phase C", depends_on=["A"])
        ]
        validator = DependencyGraphValidator()
        sorted_ids = validator.topological_sort(phases)
        assert sorted_ids[0] == "A"
        assert set(sorted_ids[1:]) == {"B", "C"}

    def test_topological_sort_raises_on_cycle(self) -> None:
        """Test topological sort raises ValueError on cycle."""
        phases = [
            PhaseSpec(phase_id="A", title="Phase A", depends_on=["B"]),
            PhaseSpec(phase_id="B", title="Phase B", depends_on=["A"])
        ]
        validator = DependencyGraphValidator()
        with pytest.raises(ValueError, match="Circular dependency detected"):
            validator.topological_sort(phases)
