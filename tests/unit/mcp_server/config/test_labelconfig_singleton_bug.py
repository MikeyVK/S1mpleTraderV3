"""Test case for Issue #67: LabelConfig singleton stale cache bug.

This test reproduces the bug where LabelConfig.load() returns a stale
cached instance after the schema file has been modified.

NOTE: Tests use protected _instance access to demonstrate the bug.
This is intentional test code that should trigger the protected-access warning.
"""
from pathlib import Path

from mcp_server.config.label_config import LabelConfig


class TestLabelConfigSingletonBug:
    """Reproduce Issue #67: Singleton returns stale cache after schema changes."""

    def test_singleton_returns_stale_instance_after_file_change(
        self, tmp_path: Path
    ) -> None:
        """
        Bug reproduction:
        1. Load LabelConfig from labels.yaml (cached in _instance)
        2. Modify labels.yaml to add new field (label_patterns)
        3. Call load() again - should reload, but returns stale cache
        4. Result: Stale data returned
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
        # Reset singleton to simulate first load
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

        # STEP 3: Load again - BUG: returns stale cached instance
        config2 = LabelConfig.load(config_file)

        # EXPECTED: config2 should have 3 labels and 1 pattern
        # ACTUAL: config2 has 2 labels (stale) and pattern access fails
        assert len(config2.labels) == 2  # BUG: Still has old data!
        assert not config2.label_patterns  # BUG: Pattern not loaded!

        # Verify it's the same object (cached)
        assert config1 is config2  # Same object in memory

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

    def test_impact_on_label_tools(self, tmp_path: Path) -> None:
        """
        Demonstrate impact: Tools using label_exists() fail on stale cache.
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

        # Re-load (gets stale cache)
        config2 = LabelConfig.load(config_file)

        # BUG: type:bug was added to file but label_exists returns False
        assert config2.label_exists("type:bug") is False  # ❌ Should be True!
