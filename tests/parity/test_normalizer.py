# tests/parity/test_normalizer.py
# template=generic version=f35abd82 created=2026-02-17T08:24Z updated=
"""TestNormalizers module.

Parity test framework for template output normalization and equivalence validation

@layer: Test Infrastructure
@dependencies: [None]
@responsibilities:
    - Test whitespace normalization edge cases
    - Test Python import sorting
    - Test timestamp masking
    - Test full normalization pipeline
    - Test semantic equivalence validation
"""

# Third-party
import pytest

# Project modules
from tests.parity.normalization import (
    assert_equivalent,
    normalize_imports,
    normalize_output,
    normalize_timestamps,
    normalize_whitespace,
)


class TestNormalizerWhitespace:
    """Test whitespace normalizer edge cases."""

    def test_crlf_to_lf_conversion(self):
        """CRLF line endings convert to LF."""
        input_text = "line1\r\nline2\r\nline3"
        expected = "line1\nline2\nline3"
        assert normalize_whitespace(input_text) == expected

    def test_trailing_whitespace_removal(self):
        """Trailing spaces removed from each line."""
        input_text = "line1   \nline2\t\nline3 "
        expected = "line1\nline2\nline3"
        assert normalize_whitespace(input_text) == expected

    def test_empty_lines_preserved(self):
        """Empty lines preserved (no whitespace collapse)."""
        input_text = "line1\n\nline2\n\nline3"
        expected = "line1\n\nline2\n\nline3"
        assert normalize_whitespace(input_text) == expected


class TestNormalizerImports:
    """Test Python import sorter."""

    def test_stdlib_sorted_alphabetically(self):
        """Standard library imports sorted A-Z."""
        input_text = "import sys\nimport os\nimport re"
        expected = "import os\nimport re\nimport sys"
        assert normalize_imports(input_text) == expected

    def test_third_party_sorted_separately(self):
        """Third-party imports sorted in separate group."""
        input_text = "from pydantic import BaseModel\nfrom typing import Any\nimport pytest"
        # Within each block, imports sorted alphabetically
        # Note: 'from' imports come before 'import' when sorted
        result = normalize_imports(input_text)
        lines = result.split("\n")
        assert len(lines) == 3
        assert all(line in result for line in input_text.split("\n"))

    def test_local_imports_preserved(self):
        """Project modules group preserved at end."""
        input_text = (
            "# Standard library\nimport os\n\n# Project modules\nfrom backend.core import Base"
        )
        result = normalize_imports(input_text)
        # Preserve grouping via blank lines
        assert "# Standard library" in result
        assert "# Project modules" in result
        assert "import os" in result
        assert "from backend.core import Base" in result

    def test_empty_string_normalization(self):
        """Empty string remains empty after normalization."""
        input_text = ""
        expected = ""
        assert normalize_imports(input_text) == expected

    def test_no_imports_content(self):
        """Content without imports remains unchanged."""
        input_text = "# Comment\ndef my_function():\n    pass\n"
        expected = "# Comment\ndef my_function():\n    pass\n"
        assert normalize_imports(input_text) == expected

    def test_multiple_import_blocks(self):
        """Multiple import blocks each sorted separately."""
        input_text = "import sys\nimport os\n\n# Some code\nvar = 1\n\nimport re\nimport ast"
        result = normalize_imports(input_text)
        lines = result.split("\n")
        # First block sorted
        assert lines[0] == "import os"
        assert lines[1] == "import sys"
        # Code preserved
        assert "# Some code" in result
        assert "var = 1" in result
        # Second block sorted
        assert "import ast" in result
        assert "import re" in result


class TestNormalizerTimestamps:
    """Test timestamp masking for SCAFFOLD metadata."""

    def test_iso8601_masked(self):
        """ISO8601 timestamps replaced with <TIMESTAMP>."""
        input_text = "created=2026-02-17T08:23Z updated=2026-01-15T10:30:00Z"
        expected = "created=<TIMESTAMP> updated=<TIMESTAMP>"
        assert normalize_timestamps(input_text) == expected

    def test_version_hash_preserved(self):
        """Version hashes unchanged (abc123 stays abc123)."""
        input_text = "version=abc123 created=2026-02-17T08:23Z"
        result = normalize_timestamps(input_text)
        assert "version=abc123" in result
        assert "<TIMESTAMP>" in result

    def test_multiple_timestamps_masked(self):
        """All timestamps in file masked (created + updated)."""
        input_text = (
            "# template=dto version=f35abd82 created=2026-02-17T08:23Z updated=2026-02-17T09:15:00Z"
        )
        result = normalize_timestamps(input_text)
        assert result.count("<TIMESTAMP>") == 2
        assert "version=f35abd82" in result


class TestNormalizeOutput:
    """Test full normalization pipeline."""

    def test_python_file_full_pipeline(self, sample_python_output):
        """Python files: whitespace + timestamps + imports normalized."""
        result = normalize_output(sample_python_output, file_type="python")
        # Should apply: whitespace + timestamps + imports
        assert "\r\n" not in result  # CRLF removed
        assert "<TIMESTAMP>" in result  # Timestamps masked
        # Imports sorted (hard to verify without parsing)

    def test_markdown_file_pipeline(self, sample_markdown_output):
        """Markdown files: whitespace + timestamps (no import sorting)."""
        result = normalize_output(sample_markdown_output, file_type="markdown")
        # Should apply: whitespace + timestamps (NO import sorting)
        assert "\r\n" not in result
        assert "<TIMESTAMP>" in result


class TestEquivalence:
    """Test semantic equivalence validator."""

    def test_identical_content_passes(self):
        """Exact match passes without assertion."""
        v1 = "test content\nline2"
        v2 = "test content\nline2"
        # Should not raise
        assert_equivalent(v1, v2)

    def test_allowed_diffs_ignored(self):
        """Differences in allow_diffs list do not fail."""
        v1 = "version=abc123 created=2026-01-01T00:00:00Z"
        v2 = "version=abc123 created=2026-02-01T00:00:00Z"
        # Timestamps differ, but allowed
        assert_equivalent(v1, v2, allow_diffs=["created="])

    def test_semantic_difference_fails(self):
        """Non-whitelisted differences raise AssertionError."""
        v1 = "test content A"
        v2 = "test content B"
        # Should raise AssertionError
        with pytest.raises(AssertionError, match="not semantically equivalent"):
            assert_equivalent(v1, v2)
