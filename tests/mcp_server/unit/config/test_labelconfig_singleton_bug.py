"""Regression tests for label config freshness after the C_LOADER migration."""

import time
from pathlib import Path

from mcp_server.config.loader import ConfigLoader
from mcp_server.config.schemas import LabelConfig


def _load_label_config(config_path: Path) -> LabelConfig:
    return ConfigLoader(config_path.parent).load_label_config(config_path=config_path)


class TestLabelConfigReloadBehavior:
    """Verify fresh loads reflect on-disk file changes."""

    def test_reloads_after_file_change(self, tmp_path: Path) -> None:
        config_file = tmp_path / "labels.yaml"
        config_file.write_text(
            """
version: "1.0"
labels:
  - name: "type:feature"
    color: "1D76DB"
freeform_exceptions: []
""",
            encoding="utf-8",
        )

        config1 = _load_label_config(config_file)
        assert len(config1.labels) == 1

        time.sleep(0.01)
        config_file.write_text(
            """
version: "1.0"
labels:
  - name: "type:feature"
    color: "1D76DB"
  - name: "type:bug"
    color: "D73A4A"
freeform_exceptions: []
""",
            encoding="utf-8",
        )

        config2 = _load_label_config(config_file)

        assert len(config2.labels) == 2
        assert config1 is not config2

    def test_reloads_label_patterns(self, tmp_path: Path) -> None:
        config_file = tmp_path / "labels.yaml"
        config_file.write_text(
            """
version: "1.0"
labels:
  - name: "type:feature"
    color: "1D76DB"
freeform_exceptions: []
""",
            encoding="utf-8",
        )

        config1 = _load_label_config(config_file)
        assert not config1.label_patterns

        time.sleep(0.01)
        config_file.write_text(
            """
version: "1.0"
labels:
  - name: "type:feature"
    color: "1D76DB"
freeform_exceptions: []
label_patterns:
  - pattern: "^parent:issue-\\d+$"
    description: "Parent issue reference"
    color: "EDEDED"
    example: "parent:issue-18"
""",
            encoding="utf-8",
        )

        config2 = _load_label_config(config_file)

        assert len(config2.label_patterns) == 1
        assert config2.label_patterns[0].example == "parent:issue-18"
        assert config1 is not config2

    def test_consecutive_loads_of_unchanged_file_are_equivalent(self, tmp_path: Path) -> None:
        config_file = tmp_path / "labels.yaml"
        config_file.write_text(
            """
version: "1.0"
labels:
  - name: "type:feature"
    color: "1D76DB"
freeform_exceptions: []
""",
            encoding="utf-8",
        )

        config1 = _load_label_config(config_file)
        config2 = _load_label_config(config_file)

        assert config1 == config2

    def test_different_config_paths_remain_independent(self, tmp_path: Path) -> None:
        config1_file = tmp_path / "config1.yaml"
        config2_file = tmp_path / "config2.yaml"

        config1_file.write_text(
            """
version: "1.0"
labels:
  - name: "type:feature"
    color: "1D76DB"
freeform_exceptions: []
""",
            encoding="utf-8",
        )
        config2_file.write_text(
            """
version: "1.0"
labels:
  - name: "type:bug"
    color: "D73A4A"
  - name: "priority:high"
    color: "FF0000"
freeform_exceptions: []
""",
            encoding="utf-8",
        )

        cfg1 = _load_label_config(config1_file)
        cfg2 = _load_label_config(config2_file)

        assert len(cfg1.labels) == 1
        assert len(cfg2.labels) == 2
        assert cfg1 != cfg2
