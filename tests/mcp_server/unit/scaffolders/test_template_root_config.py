"""
Tests for template root configuration with fail-fast behavior.

RED phase: Issue #72 Clean Break - Tier templates as default.
Tests that template root is configurable but fails fast on invalid config.
"""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from tests.mcp_server.test_support import make_template_scaffolder


class TestTemplateRootConfiguration:
    """Tests for template root configuration behavior."""

    def test_default_uses_tier_root(self):
        """When no config set, should use mcp_server/scaffolding/templates."""
        scaffolder = make_template_scaffolder()

        # Expected: mcp_server/scaffolding/templates (tier-root) - resolved
        expected_tier_root = Path("mcp_server/scaffolding/templates").resolve()
        actual_root = scaffolder._renderer.template_dir  # pylint: disable=protected-access

        assert actual_root == expected_tier_root, (
            f"Expected tier-root {expected_tier_root}, got {actual_root}"
        )

    def test_env_variable_overrides_default(self):
        """When TEMPLATE_ROOT env var set, should use that path."""
        custom_path = Path("custom/template/path").resolve()

        with patch.dict(os.environ, {"TEMPLATE_ROOT": str(custom_path)}):
            with patch("pathlib.Path.exists", return_value=True):
                scaffolder = make_template_scaffolder()

                # pylint: disable=protected-access
                assert scaffolder._renderer.template_dir == custom_path

    def test_fail_fast_on_nonexistent_path(self):
        """When configured path doesn't exist, raise FileNotFoundError."""
        nonexistent_path = Path("/does/not/exist/templates")

        with patch.dict(os.environ, {"TEMPLATE_ROOT": str(nonexistent_path)}):
            with pytest.raises(FileNotFoundError, match="Template root.*does not exist"):
                make_template_scaffolder()

    def test_no_fallback_to_legacy_templates_dir(self):
        """Should NEVER fall back to mcp_server/templates (legacy)."""
        scaffolder = make_template_scaffolder()

        # Legacy location should NOT be used
        legacy_path = Path("mcp_server/templates")
        actual_root = scaffolder._renderer.template_dir  # pylint: disable=protected-access

        assert actual_root != legacy_path, (
            f"Should not use legacy templates/ dir, but got {actual_root}"
        )

    def test_validation_service_uses_same_root(self):
        """ValidationService should use same template root as scaffolder."""
        # Import in test to avoid module-level import
        from mcp_server.validation.validation_service import ValidationService

        scaffolder = make_template_scaffolder()
        validation_service = ValidationService()

        # pylint: disable=protected-access
        assert (
            scaffolder._renderer.template_dir == validation_service.template_analyzer.template_root
        ), "Scaffolder and ValidationService must use same template root"
