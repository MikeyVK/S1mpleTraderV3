"""Unit tests for SearchService (Cycle 9)."""

import pytest

from mcp_server.services.search_service import SearchService


class TestCalculateRelevance:
    """Test relevance scoring algorithm."""

    def test_title_match_has_highest_weight(self):
        """Title matches should score 3.0 per occurrence."""
        doc = {
            "title": "Python Best Practices",
            "path": "docs/reference/style.md",
            "content": "Some content here"
        }
        score = SearchService.calculate_relevance(doc, "Python")
        assert score == 3.0  # 1 title match * 3.0 weight

    def test_path_match_has_medium_weight(self):
        """Path matches should score 1.0 per occurrence."""
        doc = {
            "title": "Style Guide",
            "path": "docs/python/coding.md",
            "content": "Some content here"
        }
        score = SearchService.calculate_relevance(doc, "python")
        assert score == 1.0  # 1 path match * 1.0 weight

    def test_content_match_has_lowest_weight(self):
        """Content matches should score 0.5 per occurrence."""
        doc = {
            "title": "Guide",
            "path": "docs/reference/style.md",
            "content": "Python is great. Python is powerful."
        }
        score = SearchService.calculate_relevance(doc, "Python")
        assert score == 1.0  # 2 content matches * 0.5 weight

    def test_multiple_matches_accumulate(self):
        """Matches in different fields should add up."""
        doc = {
            "title": "Python Guide",
            "path": "docs/python/best.md",
            "content": "Python coding standards"
        }
        score = SearchService.calculate_relevance(doc, "Python")
        assert score == 4.5  # Title (3.0) + Path (1.0) + Content (0.5)

    def test_case_insensitive_matching(self):
        """Query matching should be case-insensitive."""
        doc = {
            "title": "PYTHON Guide",
            "path": "docs/PYTHON/best.md",
            "content": "python coding"
        }
        score = SearchService.calculate_relevance(doc, "python")
        assert score == 4.5  # Should match regardless of case

    def test_no_match_returns_zero(self):
        """Documents with no matches should score 0."""
        doc = {
            "title": "JavaScript Guide",
            "path": "docs/js/best.md",
            "content": "JavaScript is great"
        }
        score = SearchService.calculate_relevance(doc, "Python")
        assert score == 0.0


class TestExtractSnippet:
    """Test snippet extraction."""

    def test_extracts_context_around_match(self):
        """Should extract text around the query match."""
        content = "This is some text before the Python keyword and some text after it."
        snippet = SearchService.extract_snippet(content, "Python", context_chars=20)

        # Should contain query and context
        assert "Python" in snippet
        # Verify it includes context text
        assert "text before" in snippet
        assert "keyword and" in snippet

    def test_adds_ellipsis_when_truncated(self):
        """Should add ... when content is truncated."""
        content = "A" * 200 + " Python " + "B" * 200
        snippet = SearchService.extract_snippet(content, "Python", context_chars=10)

        assert snippet.startswith("...")
        assert snippet.endswith("...")
        assert "Python" in snippet

    def test_no_ellipsis_when_at_start(self):
        """Should not add leading ... if match is at start."""
        content = "Python is great and wonderful"
        snippet = SearchService.extract_snippet(content, "Python", context_chars=10)

        assert not snippet.startswith("...")
        assert "Python" in snippet

    def test_no_ellipsis_when_at_end(self):
        """Should not add trailing ... if match is at end."""
        content = "This is all about Python"
        snippet = SearchService.extract_snippet(content, "Python", context_chars=10)

        assert not snippet.endswith("...")
        assert "Python" in snippet

    def test_returns_full_content_if_short(self):
        """Should return full content if shorter than context."""
        content = "Python"
        snippet = SearchService.extract_snippet(content, "Python", context_chars=100)

        assert snippet == "Python"
        assert "..." not in snippet

    def test_case_insensitive_search(self):
        """Should find query regardless of case."""
        content = "This is about PYTHON programming"
        snippet = SearchService.extract_snippet(content, "python", context_chars=10)

        assert "PYTHON" in snippet


class TestSearchIndex:
    """Test search_index method."""

    @pytest.fixture
    def sample_index(self):
        """Sample document index for testing."""
        return [
            {
                "title": "Python Best Practices",
                "path": "docs/coding/python.md",
                "content": "Python is a great language for beginners",
                "type": "coding_standards"
            },
            {
                "title": "JavaScript Guide",
                "path": "docs/coding/javascript.md",
                "content": "JavaScript is used for web development",
                "type": "coding_standards"
            },
            {
                "title": "Architecture Overview",
                "path": "docs/architecture/overview.md",
                "content": "System architecture uses Python microservices",
                "type": "architecture"
            },
            {
                "title": "Testing Python Code",
                "path": "docs/testing/python_testing.md",
                "content": "How to test Python applications",
                "type": "coding_standards"
            }
        ]

    def test_returns_relevant_documents(self, sample_index):
        """Should return documents matching query."""
        results = SearchService.search_index(sample_index, "Python")

        assert len(results) == 3  # 3 docs contain "Python"
        assert all("Python" in r["title"] or "Python" in r["content"]
                  or "python" in r["path"] for r in results)

    def test_sorts_by_relevance_descending(self, sample_index):
        """Should sort results by relevance score (highest first)."""
        results = SearchService.search_index(sample_index, "Python")

        # First result should have highest relevance
        scores = [r["_relevance"] for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_limits_max_results(self, sample_index):
        """Should respect max_results parameter."""
        results = SearchService.search_index(sample_index, "Python", max_results=2)

        assert len(results) == 2

    def test_filters_by_scope(self, sample_index):
        """Should filter results by scope when provided."""
        results = SearchService.search_index(
            sample_index, "Python", scope="architecture"
        )

        assert len(results) == 1
        assert results[0]["type"] == "architecture"

    def test_adds_relevance_score(self, sample_index):
        """Should add _relevance field to results."""
        results = SearchService.search_index(sample_index, "Python")

        assert all("_relevance" in r for r in results)
        assert all(isinstance(r["_relevance"], float) for r in results)

    def test_adds_snippet(self, sample_index):
        """Should add _snippet field to results."""
        results = SearchService.search_index(sample_index, "Python")

        assert all("_snippet" in r for r in results)
        assert all("Python" in r["_snippet"] or "python" in r["_snippet"]
                  for r in results)

    def test_returns_empty_for_no_matches(self, sample_index):
        """Should return empty list when no matches found."""
        results = SearchService.search_index(sample_index, "Rust")

        assert results == []

    def test_handles_empty_index(self):
        """Should handle empty index gracefully."""
        results = SearchService.search_index([], "Python")

        assert results == []
