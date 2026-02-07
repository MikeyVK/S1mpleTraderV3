"""Integration tests for SearchService with DocumentIndexer (Cycle 10)."""

import pytest

from mcp_server.services.document_indexer import DocumentIndexer
from mcp_server.services.search_service import SearchService


class TestSearchServiceIntegration:
    """Integration tests for SearchService with DocumentIndexer."""

    @pytest.fixture
    def sample_docs_dir(self, tmp_path):
        """Create sample documentation structure for testing."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        # Create architecture doc
        arch_dir = docs_dir / "architecture"
        arch_dir.mkdir()
        (arch_dir / "system.md").write_text(
            "# System Architecture\n\nPython-based microservices architecture."
        )

        # Create development doc
        dev_dir = docs_dir / "development"
        dev_dir.mkdir()
        (dev_dir / "python_guide.md").write_text(
            "# Python Development Guide\n\nBest practices for Python development."
        )

        # Create reference doc
        ref_dir = docs_dir / "reference"
        ref_dir.mkdir()
        (ref_dir / "api.md").write_text(
            "# API Reference\n\nJavaScript API documentation."
        )

        return docs_dir

    def test_end_to_end_search_flow(self, sample_docs_dir):
        """Test complete flow from indexing to search results."""
        # Build index
        index = DocumentIndexer.build_index(sample_docs_dir)

        # Search for "Python"
        results = SearchService.search_index(index, "Python")

        # Should find 2 documents containing "Python"
        assert len(results) == 2
        assert all("Python" in r["title"] or "Python" in r["content"]
                  for r in results)

    def test_scope_filtering_works_with_real_docs(self, sample_docs_dir):
        """Test scope filtering with real directory structure."""
        # Build index
        index = DocumentIndexer.build_index(sample_docs_dir)

        # Search only in architecture scope
        results = SearchService.search_index(
            index, "architecture", scope="architecture"
        )

        # Should only return architecture docs
        assert len(results) >= 1
        assert all(r["scope"] == "architecture" for r in results)

    def test_relevance_sorting_with_real_content(self, sample_docs_dir):
        """Test relevance scoring with actual document content."""
        # Build index
        index = DocumentIndexer.build_index(sample_docs_dir)

        # Search for "Python"
        results = SearchService.search_index(index, "Python")

        # Verify sorted by relevance
        scores = [r["_relevance"] for r in results]
        assert scores == sorted(scores, reverse=True)

        # Document with "Python" in title should rank higher
        top_result = results[0]
        assert "Python" in top_result["title"]

    def test_snippet_extraction_from_real_docs(self, sample_docs_dir):
        """Test snippet extraction with real document content."""
        # Build index
        index = DocumentIndexer.build_index(sample_docs_dir)

        # Search for "Python"
        results = SearchService.search_index(index, "Python")

        # All results should have snippets
        assert all("_snippet" in r for r in results)
        assert all("Python" in r["_snippet"] or "python" in r["_snippet"]
                  for r in results)

    def test_empty_directory_returns_empty_index(self, tmp_path):
        """Test indexing empty directory."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        index = DocumentIndexer.build_index(empty_dir)
        results = SearchService.search_index(index, "Python")

        assert results == []

    def test_handles_non_markdown_files(self, tmp_path):
        """Test that non-.md files are ignored."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        # Create .md and .txt files
        (docs_dir / "valid.md").write_text("# Valid Doc\n\nPython content")
        (docs_dir / "invalid.txt").write_text("This should be ignored")

        index = DocumentIndexer.build_index(docs_dir)

        # Should only index .md files
        assert len(index) == 1
        assert index[0]["path"] == "valid.md"

    def test_nested_directory_structure(self, tmp_path):
        """Test indexing deeply nested directories."""
        docs_dir = tmp_path / "docs"
        nested_dir = docs_dir / "level1" / "level2" / "level3"
        nested_dir.mkdir(parents=True)

        (nested_dir / "deep.md").write_text("# Deep Document\n\nPython testing")

        index = DocumentIndexer.build_index(docs_dir)
        results = SearchService.search_index(index, "Python")

        assert len(results) == 1
        # Platform-agnostic path check
        assert "level1" in results[0]["path"]
        assert "level2" in results[0]["path"]
        assert "level3" in results[0]["path"]
        assert "deep.md" in results[0]["path"]
