"""Test case for Issue #67: LabelConfig singleton stale cache bug.

This test reproduces the bug where LabelConfig.load() returns a stale
cached instance after the schema file has been modified.

NOTE: Tests use protected _instance access to demonstrate the bug.
This is intentional test code that should trigger the protected-access warning.
"""
import time
from pathlib import Path

from mcp_server.config.label_config import LabelConfig


class TestLabelConfigSingletonFix:
    """Verify Issue #67 fix: Singleton cache invalidation works correctly."""

    def test_singleton_automatically_reloads_after_file_change(
        self, tmp_path: Path
    ) -> None:
        """
        FIX VERIFICATION:
        1. Load LabelConfig from labels.yaml (cached in _instance)
        2. Modify labels.yaml to add new labels and patterns
        3. Call load() again - should detect mtime change and reload
        4. Result: Fresh data returned
        """
        # Create initial labels.yaml
        config_file = tmp_path / "labels.yaml"
        initial_yaml = """
version: "1.0"
labels:
  - name: "type:feature"
    color: "1D76DB"
    description: "New feature"
  - name: "type:bug"
    color: "D73A4A"
    description: "Bug fix"
freeform_exceptions:
  - "good first issue"
"""
        config_file.write_text(initial_yaml, encoding="utf-8")

        # STEP 1: Load config (caches in _instance)
        type(LabelConfig)._instance = None  # type: ignore[attr-defined]
        config1 = LabelConfig.load(config_file)
        assert len(config1.labels) == 2
        assert hasattr(config1, "label_patterns")  # Field exists in model
        assert not config1.label_patterns  # Default empty list

        # STEP 2: Modify file - add label_patterns field
        updated_yaml = """
version: "1.0"
labels:
  - name: "type:feature"
    color: "1D76DB"
    description: "New feature"
  - name: "type:bug"
    color: "D73A4A"
    description: "Bug fix"
  - name: "type:enhancement"
    color: "A2EEEF"
    description: "Enhancement"
freeform_exceptions:
  - "good first issue"
label_patterns:
  - pattern: "^parent:issue-\\\\d+$"
    description: "Parent issue reference"
    color: "EDEDED"
    example: "parent:issue-18"
"""
        config_file.write_text(updated_yaml, encoding="utf-8")

        # STEP 3: Load again - FIX: detects mtime change and reloads
        config2 = LabelConfig.load(config_file)

        # FIXED: config2 should have 3 labels and 1 pattern
        assert len(config2.labels) == 3  # ✅ Reloaded!
        assert len(config2.label_patterns) == 1  # ✅ Pattern loaded!

        # Different object (fresh load)
        assert config1 is not config2  # Different objects in memory

    def test_singleton_reset_allows_reload(self, tmp_path: Path) -> None:
        """
        Workaround: Manually reset _instance to force reload.
        This test verifies the workaround works.
        """
        config_file = tmp_path / "labels.yaml"
        initial_yaml = """
version: "1.0"
labels:
  - name: "type:feature"
    color: "1D76DB"
freeform_exceptions: []
"""
        config_file.write_text(initial_yaml, encoding="utf-8")

        # Load first time
        type(LabelConfig)._instance = None  # type: ignore[attr-defined]
        config1 = LabelConfig.load(config_file)
        assert len(config1.labels) == 1

        # Modify file
        updated_yaml = """
version: "1.0"
labels:
  - name: "type:feature"
    color: "1D76DB"
  - name: "type:bug"
    color: "D73A4A"
freeform_exceptions: []
"""
        config_file.write_text(updated_yaml, encoding="utf-8")

        # WORKAROUND: Manually reset singleton
        type(LabelConfig)._instance = None  # type: ignore[attr-defined]

        # Load again - should now have 2 labels
        config2 = LabelConfig.load(config_file)
        assert len(config2.labels) == 2  # ✅ Works after reset
        assert config1 is not config2  # Different objects

    def test_label_tools_get_fresh_data_after_file_change(
        self, tmp_path: Path
    ) -> None:
        """
        FIX VERIFICATION: Tools using label_exists() get fresh data.
        """
        config_file = tmp_path / "labels.yaml"
        initial_yaml = """
version: "1.0"
labels:
  - name: "type:feature"
    color: "1D76DB"
freeform_exceptions: []
"""
        config_file.write_text(initial_yaml, encoding="utf-8")

        # Load config
        type(LabelConfig)._instance = None  # type: ignore[attr-defined]
        config = LabelConfig.load(config_file)
        assert config.label_exists("type:feature") is True
        assert config.label_exists("type:bug") is False

        # Add new label to file
        updated_yaml = """
version: "1.0"
labels:
  - name: "type:feature"
    color: "1D76DB"
  - name: "type:bug"
    color: "D73A4A"
freeform_exceptions: []
"""
        config_file.write_text(updated_yaml, encoding="utf-8")

        # Re-load (detects change and reloads)
        config2 = LabelConfig.load(config_file)

        # FIXED: type:bug was added to file and label_exists returns True
        assert config2.label_exists("type:bug") is True  # ✅ Works!


class TestLabelConfigCacheInvalidation:
    """Test cache invalidation based on file modification time (Issue #67 fix)."""

    def test_load_detects_file_modification_and_reloads(
        self, tmp_path: Path
    ) -> None:
        """RED: Test that load() reloads when file mtime changes."""
        config_file = tmp_path / "labels.yaml"
        initial_yaml = """
version: "1.0"
labels:
  - name: "type:feature"
    color: "1D76DB"
  - name: "type:bug"
    color: "D73A4A"
freeform_exceptions: []
"""
        config_file.write_text(initial_yaml, encoding="utf-8")

        # Load first time
        LabelConfig.reset()  # Clean slate
        config1 = LabelConfig.load(config_file)
        assert len(config1.labels) == 2

        # Modify file - add new label
        time.sleep(0.01)  # Ensure mtime changes
        updated_yaml = """
version: "1.0"
labels:
  - name: "type:feature"
    color: "1D76DB"
  - name: "type:bug"
    color: "D73A4A"
  - name: "type:enhancement"
    color: "A2EEEF"
freeform_exceptions: []
"""
        config_file.write_text(updated_yaml, encoding="utf-8")

        # Load again - should detect file change and reload
        config2 = LabelConfig.load(config_file)
        assert len(config2.labels) == 3  # ✅ Reloaded!
        assert config1 is not config2  # Different objects

    def test_load_reuses_cache_when_file_unchanged(self, tmp_path: Path) -> None:
        """RED: Test that load() returns cached instance when file unchanged."""
        config_file = tmp_path / "labels.yaml"
        yaml_content = """
version: "1.0"
labels:
  - name: "type:feature"
    color: "1D76DB"
freeform_exceptions: []
"""
        config_file.write_text(yaml_content, encoding="utf-8")

        # Load twice without modifying file
        LabelConfig.reset()
        config1 = LabelConfig.load(config_file)
        config2 = LabelConfig.load(config_file)

        # Should return same cached instance
        assert config1 is config2  # ✅ Same object

    def test_reset_invalidates_cache(self, tmp_path: Path) -> None:
        """RED: Test that reset() forces reload on next load()."""
        config_file = tmp_path / "labels.yaml"
        yaml_content = """
version: "1.0"
labels:
  - name: "type:feature"
    color: "1D76DB"
freeform_exceptions: []
"""
        config_file.write_text(yaml_content, encoding="utf-8")

        # Load, reset, load again
        LabelConfig.reset()
        config1 = LabelConfig.load(config_file)

        LabelConfig.reset()  # Force invalidation

        config2 = LabelConfig.load(config_file)

        # Should be different objects (fresh load after reset)
        assert config1 is not config2

    def test_different_config_paths_independent(self, tmp_path: Path) -> None:
        """RED: Test that different config paths don't share cache."""
        config1_file = tmp_path / "config1.yaml"
        config2_file = tmp_path / "config2.yaml"

        config1_yaml = """
version: "1.0"
labels:
  - name: "type:feature"
    color: "1D76DB"
freeform_exceptions: []
"""
        config2_yaml = """
version: "1.0"
labels:
  - name: "type:bug"
    color: "D73A4A"
  - name: "priority:high"
    color: "FF0000"
freeform_exceptions: []
"""
        config1_file.write_text(config1_yaml, encoding="utf-8")
        config2_file.write_text(config2_yaml, encoding="utf-8")

        # Load different configs
        LabelConfig.reset()
        cfg1 = LabelConfig.load(config1_file)
        cfg2 = LabelConfig.load(config2_file)

        # Should be different instances with different data
        assert cfg1 is not cfg2
        assert len(cfg1.labels) == 1
        assert len(cfg2.labels) == 2
