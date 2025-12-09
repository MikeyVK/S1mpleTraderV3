"""Tests for DocManager."""
import pytest
from pathlib import Path
from mcp_server.managers.doc_manager import DocManager


class TestDocManagerInit:
    """Tests for DocManager initialization."""

    def test_init_with_default_docs_dir(self) -> None:
        """Should initialize with default docs directory."""
        manager = DocManager()
        assert manager.docs_dir is not None
        assert "docs" in str(manager.docs_dir)

    def test_init_with_custom_docs_dir(self, tmp_path: Path) -> None:
        """Should accept custom docs directory."""
        manager = DocManager(docs_dir=tmp_path)
        assert manager.docs_dir == tmp_path


class TestDocManagerSearch:
    """Tests for search functionality."""

    @pytest.fixture
    def docs_dir(self, tmp_path: Path) -> Path:
        """Create a test docs directory with sample files."""
        docs = tmp_path / "docs"
        docs.mkdir()

        # Create architecture doc
        arch_dir = docs / "architecture"
        arch_dir.mkdir()
        (arch_dir / "DATA_FLOW.md").write_text(
            "# Data Flow\n\nThis document describes the data flow architecture.\n"
            "DTOs move through the pipeline from source to sink."
        )

        # Create coding standards doc
        standards_dir = docs / "coding_standards"
        standards_dir.mkdir()
        (standards_dir / "CODE_STYLE.md").write_text(
            "# Code Style\n\nAll code must follow PEP8.\n"
            "Use type hints for all functions."
        )

        # Create development doc
        dev_dir = docs / "development"
        dev_dir.mkdir()
        (dev_dir / "WORKER_DESIGN.md").write_text(
            "# Worker Design\n\nWorkers process data using DTOs.\n"
            "Each worker has input and output DTOs."
        )

        return docs

    def test_search_returns_matching_results(self, docs_dir: Path) -> None:
        """Should return results matching the query."""
        manager = DocManager(docs_dir=docs_dir)
        results = manager.search("DTO")

        assert len(results) > 0
        assert any("DTO" in r["snippet"] for r in results)

    def test_search_returns_file_path(self, docs_dir: Path) -> None:
        """Should include file path in results."""
        manager = DocManager(docs_dir=docs_dir)
        results = manager.search("data flow")

        assert len(results) > 0
        assert "file_path" in results[0]
        assert "DATA_FLOW.md" in results[0]["file_path"]

    def test_search_returns_relevance_score(self, docs_dir: Path) -> None:
        """Should include relevance score between 0 and 1."""
        manager = DocManager(docs_dir=docs_dir)
        results = manager.search("architecture")

        assert len(results) > 0
        assert "relevance_score" in results[0]
        assert 0 <= results[0]["relevance_score"] <= 1

    def test_search_returns_line_number(self, docs_dir: Path) -> None:
        """Should include line number where match occurs."""
        manager = DocManager(docs_dir=docs_dir)
        results = manager.search("PEP8")

        assert len(results) > 0
        assert "line_number" in results[0]
        assert results[0]["line_number"] > 0

    def test_search_returns_snippet(self, docs_dir: Path) -> None:
        """Should return snippet with context around match."""
        manager = DocManager(docs_dir=docs_dir)
        results = manager.search("type hints")

        assert len(results) > 0
        assert "snippet" in results[0]
        assert len(results[0]["snippet"]) > 0

    def test_search_limits_results(self, docs_dir: Path) -> None:
        """Should respect max_results parameter."""
        manager = DocManager(docs_dir=docs_dir)
        results = manager.search("the", max_results=2)

        assert len(results) <= 2

    def test_search_with_scope_filters_results(self, docs_dir: Path) -> None:
        """Should filter by scope when specified."""
        manager = DocManager(docs_dir=docs_dir)
        results = manager.search("code", scope="coding_standards")

        assert len(results) > 0
        assert all("coding_standards" in r["file_path"] for r in results)

    def test_search_empty_query_returns_empty(self, docs_dir: Path) -> None:
        """Should return empty for empty query."""
        manager = DocManager(docs_dir=docs_dir)
        results = manager.search("")

        assert results == []

    def test_search_no_matches_returns_empty(self, docs_dir: Path) -> None:
        """Should return empty when no matches found."""
        manager = DocManager(docs_dir=docs_dir)
        results = manager.search("xyznonexistent123")

        assert results == []


class TestDocManagerIndexing:
    """Tests for document indexing."""

    @pytest.fixture
    def docs_dir(self, tmp_path: Path) -> Path:
        """Create test docs directory."""
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "README.md").write_text("# Documentation\nMain readme file.")
        return docs

    def test_get_document_count(self, docs_dir: Path) -> None:
        """Should count indexed documents."""
        manager = DocManager(docs_dir=docs_dir)
        count = manager.get_document_count()

        assert count >= 1

    def test_list_documents(self, docs_dir: Path) -> None:
        """Should list all indexed documents."""
        manager = DocManager(docs_dir=docs_dir)
        docs = manager.list_documents()

        assert len(docs) >= 1
        assert any("README.md" in d for d in docs)
