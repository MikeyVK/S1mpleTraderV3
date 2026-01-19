"""E2E tests for SearchDocumentationTool with production docs."""
import pytest

from mcp_server.config.settings import settings
from mcp_server.tools.discovery_tools import SearchDocumentationInput, SearchDocumentationTool
from mcp_server.tools.tool_result import ToolResult

class TestSearchDocumentationE2E:
    """End-to-end tests for SearchDocumentationTool using real filesystem."""

    @pytest.fixture
    def sample_docs_dir(self, tmp_path):
        """Create sample documentation structure for testing."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        # Create architecture doc
        arch_dir = docs_dir / "architecture"
        arch_dir.mkdir()
        (arch_dir / "system.md").write_text(
            "# System Architecture\n\nPython-based microservices architecture using DTOs."
        )

        # Create development doc
        dev_dir = docs_dir / "development"
        dev_dir.mkdir()
        (dev_dir / "python_guide.md").write_text(
            "# Python Development Guide\n\nBest practices for Python development with DTOs."
        )

        # Create coding_standards doc
        coding_dir = docs_dir / "coding_standards"
        coding_dir.mkdir()
        (coding_dir / "style.md").write_text(
            "# Code Style\n\nFollow PEP 8 style guidelines."
        )

        # Create reference doc
        ref_dir = docs_dir / "reference"
        ref_dir.mkdir()
        (ref_dir / "api.md").write_text(
            "# API Reference\n\nJavaScript API documentation."
        )

        return docs_dir

    @pytest.mark.asyncio
    async def test_tool_execute_with_real_docs(self, sample_docs_dir, monkeypatch):
        """Test tool.execute() with real filesystem docs (no mocks)."""
        # Point settings to our temp docs
        monkeypatch.setattr(settings.server, "workspace_root", sample_docs_dir.parent)

        tool = SearchDocumentationTool()
        result = await tool.execute(SearchDocumentationInput(query="Python"))

        # Verify result structure
        assert isinstance(result, ToolResult)
        assert not result.is_error

        # Verify content
        output = result.content[0]["text"]
        assert "Found" in output
        assert "Python" in output
        assert "results" in output

        # Should find Python in both architecture and development docs
        assert "architecture" in output.lower() or "development" in output.lower()

    @pytest.mark.asyncio
    async def test_tool_execute_with_scope_filter(self, sample_docs_dir, monkeypatch):
        """Test tool.execute() with scope filter."""
        monkeypatch.setattr(settings.server, "workspace_root", sample_docs_dir.parent)

        tool = SearchDocumentationTool()
        result = await tool.execute(
            SearchDocumentationInput(query="style", scope="coding_standards")
        )

        assert not result.is_error
        output = result.content[0]["text"]

        # Should only find in coding_standards
        assert "style.md" in output
        # Should NOT include docs from other scopes
        assert "python_guide.md" not in output
        assert "api.md" not in output

    @pytest.mark.asyncio
    async def test_tool_execute_no_results(self, sample_docs_dir, monkeypatch):
        """Test tool.execute() when no results found."""
        monkeypatch.setattr(settings.server, "workspace_root", sample_docs_dir.parent)

        tool = SearchDocumentationTool()
        result = await tool.execute(SearchDocumentationInput(query="xyznonexistent"))

        assert not result.is_error
        output = result.content[0]["text"]
        assert "No results found" in output

    @pytest.mark.asyncio
    async def test_tool_execute_relevance_ranking(self, sample_docs_dir, monkeypatch):
        """Test that results are ranked by relevance."""
        monkeypatch.setattr(settings.server, "workspace_root", sample_docs_dir.parent)

        tool = SearchDocumentationTool()
        result = await tool.execute(SearchDocumentationInput(query="Python"))

        assert not result.is_error
        output = result.content[0]["text"]

        # Python Development Guide has "Python" in title → should rank first
        lines = output.split("\n")
        # Find first result (line starting with "1.")
        first_result = next(line for line in lines if line.strip().startswith("1."))
        assert "Python Development Guide" in first_result or "python_guide.md" in first_result

    @pytest.mark.asyncio
    async def test_tool_handles_missing_docs_dir(self, tmp_path, monkeypatch):
        """Test tool gracefully handles missing docs directory."""
        # Point to directory without docs/ subdirectory
        monkeypatch.setattr(settings.server, "workspace_root", tmp_path)

        tool = SearchDocumentationTool()
        result = await tool.execute(SearchDocumentationInput(query="Python"))

        # Should return error (docs dir not found)
        assert result.is_error or "No results found" in result.content[0]["text"]
