# tests/mcp_server/unit/presenters/test_text_budget_limiter.py
# template=unit_test version=8825c0bb created=2026-08-22T00:00Z updated=2026-08-22
"""UTF-8 text response budget enforcement contract tests.

@layer: Tests (Unit)
@dependencies: [pytest, presentation_config, text_budget_limiter]
@responsibilities:
    - Preserve under-budget and exact-budget text byte-for-byte
    - Reserve truthful truncation tails and complete cache references
    - Prefer readable Markdown and UTF-8-safe boundaries
"""

import pytest

from mcp_server.config.schemas.presentation_config import FormattingConfig
from mcp_server.core.exceptions import ConfigError
from mcp_server.presenters.text_budget_limiter import TextBudgetLimiter


def _formatting() -> FormattingConfig:
    return FormattingConfig(
        inline_sequence_omission_template="… {omitted_count} more",
        collection_omission_template="- … {omitted_count} more {field}",
        truncation_notice="[TRUNCATED: COMPLETE CACHE]",
        cache_unavailable_truncation_notice="[TRUNCATED: CACHE UNAVAILABLE]",
    )


def _limiter(max_bytes: int) -> TextBudgetLimiter:
    return TextBudgetLimiter(
        max_text_response_bytes=max_bytes,
        formatting=_formatting(),
    )


class TestTextBudgetLimiter:
    """Final text byte-ceiling behavior."""

    @pytest.mark.parametrize("body", ["short body", "x" * 64])
    def test_returns_under_and_exact_budget_text_unchanged(self, body: str) -> None:
        limiter = _limiter(len(body.encode("utf-8")))

        assert limiter.limit(body, cache_reference=None) == body

    def test_overflow_keeps_complete_cache_reference_and_stays_bounded(self) -> None:
        body = "first block\n\nsecond block\n\n" + "x" * 100
        cache_reference = "View pgmcp://cache/runs/" + "a" * 32
        limiter = _limiter(125)

        result = limiter.limit(body, cache_reference=cache_reference)

        assert len(result.encode("utf-8")) <= 125
        assert cache_reference in result
        assert _formatting().truncation_notice in result
        assert result.startswith("first block")
        assert result != body

    def test_prefers_complete_block_then_complete_line(self) -> None:
        cache_reference = "cache:" + "b" * 32
        limiter = _limiter(100)

        block_result = limiter.limit(
            "block one\n\nblock two\n\npartial " + "x" * 100,
            cache_reference,
        )
        line_result = limiter.limit(
            "line one\nline two\npartial " + "x" * 100,
            cache_reference,
        )

        block_body = block_result.split(_formatting().truncation_notice)[0]
        line_body = line_result.split(_formatting().truncation_notice)[0]
        assert block_body.rstrip().endswith("block two")
        assert line_body.rstrip().endswith("line two")

    def test_multibyte_truncation_preserves_code_points(self) -> None:
        cache_reference = "cache:" + "c" * 32
        limiter = _limiter(96)

        result = limiter.limit("🚀" * 100, cache_reference)

        assert len(result.encode("utf-8")) <= 96
        assert "�" not in result
        result.encode("utf-8").decode("utf-8")

    def test_closes_intersected_fenced_markdown_before_tail(self) -> None:
        cache_reference = "cache:" + "d" * 32
        limiter = _limiter(135)
        body = "Before\n\n```text\n" + "inside\n" * 30

        result = limiter.limit(body, cache_reference)

        body_part = result.split(_formatting().truncation_notice)[0].rstrip()
        assert body_part.endswith("```")
        assert body_part.count("```") % 2 == 0
        assert len(result.encode("utf-8")) <= 135

    def test_cache_unavailable_overflow_is_truthful_and_bounded(self) -> None:
        limiter = _limiter(80)

        result = limiter.limit("details " * 100, cache_reference=None)

        assert len(result.encode("utf-8")) <= 80
        assert _formatting().cache_unavailable_truncation_notice in result
        assert _formatting().truncation_notice not in result
        assert "pgmcp://cache/runs/" not in result

    def test_rejects_budget_that_cannot_hold_mandatory_tail(self) -> None:
        limiter = _limiter(10)

        with pytest.raises(ConfigError, match="mandatory truncation tail"):
            limiter.limit("x" * 100, cache_reference="cache:" + "e" * 32)
