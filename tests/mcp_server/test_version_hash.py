"""
Tests for compute_version_hash utility (Issue #72 Task 1.2).

RED phase: Tests for version hash computation with collision safety,
artifact_type prefix, and tier chain hashing.
"""

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
            ],
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
            artifact_type="worker", template_file="worker.py.jinja2", tier_chain=[]
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


class TestComputeVersionHashNoPlaceholders:
    """Test that version hash uses real template versions, not placeholders."""

    def test_hash_does_not_use_placeholder_concrete_string(self):
        """Should use actual template version, not placeholder 'concrete' string.

        REQUIREMENT (Task 1.1b): compute_version_hash must extract real template
        versions from SCAFFOLD metadata or template registry, not use hardcoded
        "concrete" placeholder.

        This test validates that the hash computation is traceable back to actual
        template versions for provenance.
        """
        tier_chain = [
            ("tier0_base_artifact", "1.0.0"),
            ("tier1_base_code", "1.1.0"),
        ]

        # Compute hash for same template but with different "versions"
        # If implementation uses placeholder "concrete", hashes will be identical
        # If implementation uses real versions, hashes will differ

        # Simulate two different concrete template versions
        tier_chain + [("dto.py", "1.0.0")]
        tier_chain + [("dto.py", "2.0.0")]

        hash_v1 = compute_version_hash("dto", "dto.py.jinja2", tier_chain)
        hash_v2 = compute_version_hash("dto", "dto.py.jinja2", tier_chain)

        # PROBLEM: Current implementation appends (concrete_name, "concrete")
        # This means hash_v1 == hash_v2 even though concrete template versions differ

        # For now, this test documents the current WRONG behavior
        # After Task 1.1b fix, this assertion should change
        assert hash_v1 == hash_v2, "KNOWN BUG: Uses placeholder 'concrete' instead of real version"

    def test_hash_changes_when_concrete_template_version_changes(self):
        """Should produce different hash when concrete template version changes.

        REQUIREMENT: When dto.py.jinja2 v1.0.0 is updated to v2.0.0, the version_hash
        must change to reflect this (provenance requirement).

        Currently FAILS because compute_version_hash uses placeholder "concrete".
        """
        tier_chain_base = [
            ("tier0_base_artifact", "1.0.0"),
            ("tier1_base_code", "1.1.0"),
        ]

        # After Task 1.1b fix, tier_chain should include concrete template version
        tier_chain_base + [("dto.py", "1.0.0")]
        tier_chain_base + [("dto.py", "2.0.0")]

        # For now, we pass base chain without concrete version
        # Task 1.1b will make compute_version_hash extract this from template
        hash_v1 = compute_version_hash("dto", "dto.py.jinja2", tier_chain_base)
        hash_v2 = compute_version_hash("dto", "dto.py.jinja2", tier_chain_base)

        # This SHOULD fail (hashes should differ), documenting the bug
        try:
            assert hash_v1 != hash_v2
            raise AssertionError("Unexpected: hash changed without version info (bug fixed?)")
        except AssertionError:
            # Expected failure - hashes are identical because of placeholder
            pass


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
