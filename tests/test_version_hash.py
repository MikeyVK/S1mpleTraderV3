"""
Tests for compute_version_hash utility (Issue #72 Task 1.2).

RED phase: Tests for version hash computation with collision safety,
artifact_type prefix, and tier chain hashing.
"""

import pytest

# Module under test does not exist yet (RED phase)
from mcp_server.scaffolding.version_hash import compute_version_hash


class TestComputeVersionHashBasic:
    """Test basic hash computation."""

    def test_compute_hash_returns_8_chars(self):
        """Should return 8-character hex string."""
        result = compute_version_hash(
            artifact_type="worker",
            template_file="worker.py.jinja2",
            tier_chain=[
                ("tier0_base_artifact", "1.0.0"),
                ("tier1_base_code", "1.1.0"),
                ("tier2_base_python", "2.0.0"),
            ]
        )

        assert len(result) == 8
        assert all(c in "0123456789abcdef" for c in result)

    def test_compute_hash_deterministic(self):
        """Should return same hash for same inputs."""
        tier_chain = [
            ("tier0_base_artifact", "1.0.0"),
            ("tier1_base_code", "1.1.0"),
        ]

        hash1 = compute_version_hash("worker", "worker.py.jinja2", tier_chain)
        hash2 = compute_version_hash("worker", "worker.py.jinja2", tier_chain)

        assert hash1 == hash2

    def test_compute_hash_different_artifact_types_different_hash(self):
        """Should produce different hashes for different artifact types."""
        tier_chain = [("tier0_base_artifact", "1.0.0")]

        worker_hash = compute_version_hash("worker", "worker.py.jinja2", tier_chain)
        research_hash = compute_version_hash("research", "research.py.jinja2", tier_chain)

        assert worker_hash != research_hash


class TestComputeVersionHashVersionSensitivity:
    """Test hash changes when versions change."""

    def test_compute_hash_changes_when_tier_version_changes(self):
        """Should produce different hash when tier version changes."""
        tier_chain_v1 = [
            ("tier0_base_artifact", "1.0.0"),
            ("tier1_base_code", "1.1.0"),
        ]
        tier_chain_v2 = [
            ("tier0_base_artifact", "1.0.0"),
            ("tier1_base_code", "1.2.0"),  # Version bumped
        ]

        hash_v1 = compute_version_hash("worker", "worker.py.jinja2", tier_chain_v1)
        hash_v2 = compute_version_hash("worker", "worker.py.jinja2", tier_chain_v2)

        assert hash_v1 != hash_v2

    def test_compute_hash_changes_when_tier_added(self):
        """Should produce different hash when tier added to chain."""
        tier_chain_short = [
            ("tier0_base_artifact", "1.0.0"),
        ]
        tier_chain_long = [
            ("tier0_base_artifact", "1.0.0"),
            ("tier1_base_code", "1.1.0"),
        ]

        hash_short = compute_version_hash("worker", "worker.py.jinja2", tier_chain_short)
        hash_long = compute_version_hash("worker", "worker.py.jinja2", tier_chain_long)

        assert hash_short != hash_long

    def test_compute_hash_changes_when_template_file_changes(self):
        """Should produce different hash when concrete template changes."""
        tier_chain = [("tier0_base_artifact", "1.0.0")]

        hash1 = compute_version_hash("worker", "worker.py.jinja2", tier_chain)
        hash2 = compute_version_hash("worker", "research.py.jinja2", tier_chain)

        assert hash1 != hash2


class TestComputeVersionHashEdgeCases:
    """Test edge cases and error handling."""

    def test_compute_hash_with_empty_tier_chain(self):
        """Should handle empty tier chain (Tier 4 concrete only)."""
        result = compute_version_hash(
            artifact_type="worker",
            template_file="worker.py.jinja2",
            tier_chain=[]
        )

        assert len(result) == 8
        assert all(c in "0123456789abcdef" for c in result)

    def test_compute_hash_with_long_tier_chain(self):
        """Should handle full 5-tier chain."""
        tier_chain = [
            ("tier0_base_artifact", "1.0.0"),
            ("tier1_base_code", "1.1.0"),
            ("tier2_base_python", "2.0.0"),
            ("tier3_base_python_component", "1.2.0"),
        ]

        result = compute_version_hash("worker", "worker.py.jinja2", tier_chain)

        assert len(result) == 8

    def test_compute_hash_artifact_type_not_derived_from_template(self):
        """Should use explicit artifact_type, not derive from template_file."""
        # Regression test for design bug:
        # Previously: artifact_type = template_file.replace(".jinja2", "").split("/")[-1]
        # Bug: "worker.py.jinja2" → "worker.py" (not "worker")

        tier_chain = [("tier0_base_artifact", "1.0.0")]

        # Same template file, different explicit artifact_type
        hash1 = compute_version_hash("worker", "worker.py.jinja2", tier_chain)
        hash2 = compute_version_hash("component", "worker.py.jinja2", tier_chain)

        # Should be different because artifact_type prefix differs
        assert hash1 != hash2


class TestComputeVersionHashCollisionSafety:
    """Test collision avoidance through artifact_type prefix."""

    def test_different_types_same_tiers_different_hash(self):
        """Should avoid collisions across artifact types."""
        tier_chain = [
            ("tier0_base_artifact", "1.0.0"),
            ("tier1_base_code", "1.1.0"),
            ("tier2_base_python", "2.0.0"),
        ]

        worker_hash = compute_version_hash("worker", "worker.py.jinja2", tier_chain)
        dto_hash = compute_version_hash("dto", "dto.py.jinja2", tier_chain)
        tool_hash = compute_version_hash("tool", "tool.py.jinja2", tier_chain)

        # All should be unique despite identical tier chains
        assert len({worker_hash, dto_hash, tool_hash}) == 3

    def test_hash_input_format_includes_artifact_type(self):
        """Should verify artifact_type is included in hash calculation."""
        # This is a white-box test to ensure correct format
        # Expected format: "artifact_type|tier0@v1|tier1@v2|...|concrete@vN"

        tier_chain = [("tier0_base_artifact", "1.0.0")]

        # Hash should differ based on artifact_type prefix
        hash1 = compute_version_hash("type_a", "template.jinja2", tier_chain)
        hash2 = compute_version_hash("type_b", "template.jinja2", tier_chain)

        assert hash1 != hash2
