"""
tests/unit/config/test_labels_yaml_conventions.py
==================================================
Cycle 2 — Verify .st3/labels.yaml conventions:

- No status:* labels should exist (removed in cycle 2)
- Parent label pattern must be "^parent:\\d+$" (not "^parent:issue-\\d+$")
- type:chore label must exist
"""

import re
from pathlib import Path

import pytest
import yaml

LABELS_PATH = Path(".st3/labels.yaml")


@pytest.fixture(name="labels_data")
def _labels_data() -> dict:  # type: ignore[return]
    with LABELS_PATH.open() as fh:
        return yaml.safe_load(fh)


# ---------------------------------------------------------------------------
# TestNoStatusLabels
# ---------------------------------------------------------------------------


class TestNoStatusLabels:
    def test_no_status_blocked_label(self, labels_data: dict) -> None:
        names = [lbl["name"] for lbl in labels_data["labels"]]
        assert "status:blocked" not in names

    def test_no_status_in_progress_label(self, labels_data: dict) -> None:
        names = [lbl["name"] for lbl in labels_data["labels"]]
        assert "status:in-progress" not in names

    def test_no_status_needs_info_label(self, labels_data: dict) -> None:
        names = [lbl["name"] for lbl in labels_data["labels"]]
        assert "status:needs-info" not in names

    def test_no_status_ready_label(self, labels_data: dict) -> None:
        names = [lbl["name"] for lbl in labels_data["labels"]]
        assert "status:ready" not in names

    def test_no_status_prefix_labels_at_all(self, labels_data: dict) -> None:
        names = [lbl["name"] for lbl in labels_data["labels"]]
        status_labels = [n for n in names if n.startswith("status:")]
        assert status_labels == [], f"Unexpected status labels: {status_labels}"


# ---------------------------------------------------------------------------
# TestParentLabelPattern
# ---------------------------------------------------------------------------


class TestParentLabelPattern:
    def test_parent_pattern_exists(self, labels_data: dict) -> None:
        patterns = [p["pattern"] for p in labels_data.get("label_patterns", [])]
        parent_patterns = [p for p in patterns if "parent" in p]
        assert len(parent_patterns) == 1, "Expected exactly one parent pattern"

    def test_parent_pattern_is_numeric_only(self, labels_data: dict) -> None:
        patterns = {p["pattern"] for p in labels_data.get("label_patterns", [])}
        assert r"^parent:\d+$" in patterns, f"Expected '^parent:\\d+$' but got: {patterns}"

    def test_old_parent_pattern_is_gone(self, labels_data: dict) -> None:
        patterns = {p["pattern"] for p in labels_data.get("label_patterns", [])}
        assert r"^parent:issue-\d+$" not in patterns

    def test_parent_pattern_matches_numeric(self, labels_data: dict) -> None:
        patterns = [p["pattern"] for p in labels_data.get("label_patterns", [])]
        parent_pattern = next(p for p in patterns if "parent" in p)
        assert re.fullmatch(parent_pattern, "parent:91") is not None

    def test_parent_pattern_rejects_old_format(self, labels_data: dict) -> None:
        patterns = [p["pattern"] for p in labels_data.get("label_patterns", [])]
        parent_pattern = next(p for p in patterns if "parent" in p)
        assert re.fullmatch(parent_pattern, "parent:issue-18") is None

    def test_parent_pattern_example_updated(self, labels_data: dict) -> None:
        parent_entry = next(
            p for p in labels_data.get("label_patterns", []) if "parent" in p["pattern"]
        )
        example = parent_entry.get("example", "")
        assert re.fullmatch(parent_entry["pattern"], example) is not None, (
            f"Pattern example '{example}' does not match pattern '{parent_entry['pattern']}'"
        )


# ---------------------------------------------------------------------------
# TestTypeChoreLabel
# ---------------------------------------------------------------------------


class TestTypeChoreLabel:
    def test_type_chore_label_exists(self, labels_data: dict) -> None:
        names = [lbl["name"] for lbl in labels_data["labels"]]
        assert "type:chore" in names

    def test_type_chore_has_color(self, labels_data: dict) -> None:
        chore = next(lbl for lbl in labels_data["labels"] if lbl["name"] == "type:chore")
        assert chore.get("color"), "type:chore must have a color"

    def test_type_chore_has_description(self, labels_data: dict) -> None:
        chore = next(lbl for lbl in labels_data["labels"] if lbl["name"] == "type:chore")
        assert chore.get("description"), "type:chore must have a description"
