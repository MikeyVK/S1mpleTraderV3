# mcp_server/presenters/text_budget_limiter.py
# template=service version=5d5b489a created=2026-08-22T00:00Z updated=2026-08-22
"""UTF-8 text response budget enforcement.

@layer: Presenters
@responsibilities:
    - Preserve under-budget text byte-for-byte
    - Reserve truthful truncation notices and complete cache references
    - Truncate on readable Markdown and UTF-8-safe boundaries
"""

from __future__ import annotations

from mcp_server.config.schemas.presentation_config import FormattingConfig
from mcp_server.core.exceptions import ConfigError


class TextBudgetLimiter:
    """Enforce one final UTF-8 byte ceiling for presented tool text."""

    _BLOCK_SEPARATOR = "\n\n"
    _FENCE_CLOSURE = "\n```"

    def __init__(
        self,
        *,
        max_text_response_bytes: int,
        formatting: FormattingConfig,
    ) -> None:
        if max_text_response_bytes <= 0:
            raise ConfigError("Text response byte budget must be greater than zero")
        self._max_bytes = max_text_response_bytes
        self._formatting = formatting

    def limit(
        self,
        body: str,
        cache_reference: str | None,
    ) -> str:
        """Return body unchanged or a bounded, truthful truncated result."""
        if self._byte_length(body) <= self._max_bytes:
            return body

        source_body = body
        if cache_reference is not None:
            source_body = source_body.replace(cache_reference, "").rstrip()

        tail = self._mandatory_tail(cache_reference)
        tail_bytes = self._byte_length(tail)
        if tail_bytes > self._max_bytes:
            raise ConfigError("Configured budget cannot contain the mandatory truncation tail")

        separator_bytes = self._byte_length(self._BLOCK_SEPARATOR)
        available_body_bytes = max(
            self._max_bytes - tail_bytes - separator_bytes,
            0,
        )
        prefix = self._select_readable_prefix(source_body, available_body_bytes)
        prefix = self._close_intersected_fence(
            source_body,
            prefix,
            available_body_bytes,
        )
        result = f"{prefix}{self._BLOCK_SEPARATOR}{tail}" if prefix else tail
        if self._byte_length(result) > self._max_bytes:
            raise ConfigError("Text budget limiter exceeded its configured byte ceiling")
        return result

    def _mandatory_tail(self, cache_reference: str | None) -> str:
        if cache_reference is None:
            return self._formatting.cache_unavailable_truncation_notice
        return f"{self._formatting.truncation_notice}{self._BLOCK_SEPARATOR}{cache_reference}"

    def _close_intersected_fence(
        self,
        body: str,
        prefix: str,
        available_bytes: int,
    ) -> str:
        if not self._has_open_fence(prefix):
            return prefix

        closure_bytes = self._byte_length(self._FENCE_CLOSURE)
        shortened = self._select_readable_prefix(
            body,
            max(available_bytes - closure_bytes, 0),
        )
        if self._has_open_fence(shortened):
            return f"{shortened}{self._FENCE_CLOSURE}"
        return shortened

    @classmethod
    def _select_readable_prefix(cls, body: str, max_bytes: int) -> str:
        candidate = cls._utf8_prefix(body, max_bytes)
        if len(candidate) == len(body):
            return candidate

        block_boundary = candidate.rfind(cls._BLOCK_SEPARATOR)
        if block_boundary > 0:
            return candidate[:block_boundary].rstrip()

        line_boundary = candidate.rfind("\n")
        if line_boundary > 0:
            return candidate[:line_boundary].rstrip()

        return candidate.rstrip()

    @staticmethod
    def _utf8_prefix(text: str, max_bytes: int) -> str:
        if max_bytes <= 0:
            return ""
        encoded = text.encode("utf-8")
        if len(encoded) <= max_bytes:
            return text
        return encoded[:max_bytes].decode("utf-8", errors="ignore")

    @staticmethod
    def _has_open_fence(text: str) -> bool:
        fence_count = sum(1 for line in text.splitlines() if line.lstrip().startswith("```"))
        return fence_count % 2 == 1

    @staticmethod
    def _byte_length(text: str) -> int:
        return len(text.encode("utf-8"))
