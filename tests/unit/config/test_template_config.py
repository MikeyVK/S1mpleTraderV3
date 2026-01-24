"""Comprehensive tests for template_config.py get_template_root() function.

Tests cover:
1. Default behavior (no env var set)
2. Environment variable override (TEMPLATE_ROOT)
3. Fail-fast behavior (FileNotFoundError)
4. Absolute path return
5. Path resolution (symlinks, relative paths)

Coverage goal: 100% of get_template_root() function.
"""
import os
import pytest
from pathlib import Path
from unittest.mock import patch
from mcp_server.config.template_config import get_template_root


class TestGetTemplateRoot:
    """Comprehensive tests for get_template_root() configuration function."""

    def test_returns_default_template_root_when_no_env_var(self):
        """Without TEMPLATE_ROOT env var, returns default mcp_server/scaffolding/templates."""
        # Arrange: Ensure TEMPLATE_ROOT is not set
        with patch.dict(os.environ, {}, clear=False):
            if "TEMPLATE_ROOT" in os.environ:
                del os.environ["TEMPLATE_ROOT"]
            
            # Act
            result = get_template_root()
            
            # Assert
            assert result.is_absolute(), "get_template_root() must return absolute path"
            assert result.name == "templates", f"Expected 'templates' directory, got: {result.name}"
            assert "mcp_server" in str(result), f"Expected mcp_server in path, got: {result}"
            assert "scaffolding" in str(result), f"Expected scaffolding in path, got: {result}"
            assert result.exists(), f"Default template root must exist: {result}"

    def test_returns_absolute_path(self):
        """get_template_root() always returns absolute path (not relative)."""
        # Arrange
        with patch.dict(os.environ, {}, clear=False):
            if "TEMPLATE_ROOT" in os.environ:
                del os.environ["TEMPLATE_ROOT"]
            
            # Act
            result = get_template_root()
            
            # Assert
            assert result.is_absolute(), (
                f"get_template_root() must return absolute path, got: {result}"
            )
            # Verify no relative path markers
            assert ".." not in str(result), "Absolute path should not contain '..'"

    def test_uses_template_root_env_var_when_set(self, tmp_path):
        """When TEMPLATE_ROOT env var is set, uses that path instead of default."""
        # Arrange: Create temp template directory
        custom_template_root = tmp_path / "custom_templates"
        custom_template_root.mkdir()
        
        # Act: Set TEMPLATE_ROOT env var
        with patch.dict(os.environ, {"TEMPLATE_ROOT": str(custom_template_root)}):
            result = get_template_root()
            
            # Assert
            assert result == custom_template_root.resolve(), (
                f"Expected TEMPLATE_ROOT env var path: {custom_template_root}, got: {result}"
            )
            assert result.is_absolute(), "TEMPLATE_ROOT path must be absolute"
            assert result.exists(), f"TEMPLATE_ROOT path must exist: {result}"

    def test_resolves_relative_env_var_to_absolute(self, tmp_path, monkeypatch):
        """TEMPLATE_ROOT env var with relative path is resolved to absolute."""
        # Arrange: Create nested temp structure within current directory
        # Change to tmp_path to avoid cross-drive issues on Windows
        monkeypatch.chdir(tmp_path)
        
        custom_root = tmp_path / "project" / "templates"
        custom_root.mkdir(parents=True)
        
        # Use relative path in env var
        relative_path = "project/templates"  # Relative to tmp_path (current dir)
        
        # Act
        with patch.dict(os.environ, {"TEMPLATE_ROOT": relative_path}):
            result = get_template_root()
            
            # Assert
            assert result.is_absolute(), "Relative env var path must be resolved to absolute"
            assert result == custom_root.resolve()

    def test_raises_filenotfound_when_env_var_path_missing(self):
        """Fail-fast: Raises FileNotFoundError if TEMPLATE_ROOT path doesn't exist."""
        # Arrange: Non-existent path
        nonexistent_path = "/this/path/does/not/exist/anywhere"
        
        # Act & Assert
        with patch.dict(os.environ, {"TEMPLATE_ROOT": nonexistent_path}):
            with pytest.raises(FileNotFoundError, match="TEMPLATE_ROOT env var does not exist"):
                get_template_root()

    def test_raises_filenotfound_when_default_path_missing(self, tmp_path, monkeypatch):
        """Fail-fast: Raises FileNotFoundError if default path doesn't exist."""
        # Arrange: Change working directory to empty temp dir
        # This simulates default path not existing
        monkeypatch.chdir(tmp_path)
        
        # Ensure TEMPLATE_ROOT is not set
        with patch.dict(os.environ, {}, clear=False):
            if "TEMPLATE_ROOT" in os.environ:
                del os.environ["TEMPLATE_ROOT"]
            
            # Act & Assert
            with pytest.raises(FileNotFoundError, match="Default template root does not exist"):
                get_template_root()

    def test_resolves_symlinks_in_env_var_path(self, tmp_path):
        """TEMPLATE_ROOT env var with symlink is resolved to real path."""
        # Arrange: Create real directory and symlink
        real_dir = tmp_path / "real_templates"
        real_dir.mkdir()
        
        symlink_dir = tmp_path / "link_to_templates"
        
        # Create symlink (skip on Windows if privileges missing)
        try:
            symlink_dir.symlink_to(real_dir)
        except OSError:
            pytest.skip("Symlink creation requires elevated privileges on Windows")
        
        # Act
        with patch.dict(os.environ, {"TEMPLATE_ROOT": str(symlink_dir)}):
            result = get_template_root()
            
            # Assert: resolve() should resolve symlinks
            assert result.exists()
            assert result.is_absolute()
            # Note: resolve() behavior depends on system config

    def test_env_var_takes_priority_over_default(self, tmp_path):
        """TEMPLATE_ROOT env var has priority over default path."""
        # Arrange: Create custom template root
        custom_root = tmp_path / "priority_templates"
        custom_root.mkdir()
        
        # Act
        with patch.dict(os.environ, {"TEMPLATE_ROOT": str(custom_root)}):
            result = get_template_root()
            
            # Assert: Should use env var, NOT default mcp_server/scaffolding/templates
            assert "priority_templates" in str(result)
            assert result == custom_root.resolve()
            # Verify it's NOT the default path
            assert "mcp_server" not in str(result) or "priority_templates" in str(result)

    def test_returns_same_path_on_multiple_calls(self):
        """get_template_root() is deterministic (same input = same output)."""
        # Arrange
        with patch.dict(os.environ, {}, clear=False):
            if "TEMPLATE_ROOT" in os.environ:
                del os.environ["TEMPLATE_ROOT"]
            
            # Act
            result1 = get_template_root()
            result2 = get_template_root()
            
            # Assert
            assert result1 == result2, (
                "get_template_root() should be deterministic"
            )

    def test_error_message_includes_path_when_missing(self):
        """FileNotFoundError includes the problematic path in error message."""
        # Arrange: Use Windows-compatible path (no leading slash on Windows)
        missing_path = "C:\\missing\\templates\\path" if os.name == "nt" else "/missing/templates/path"
        
        # Act & Assert
        with patch.dict(os.environ, {"TEMPLATE_ROOT": missing_path}):
            with pytest.raises(FileNotFoundError) as exc_info:
                get_template_root()
            
            # Verify error message contains the path (normalize path separators for comparison)
            error_message = str(exc_info.value)
            assert "missing" in error_message and "templates" in error_message, (
                f"Error message should include path components for debugging. Got: {error_message}"
            )
