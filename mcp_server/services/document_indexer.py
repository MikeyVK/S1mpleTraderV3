"""DocumentIndexer builds searchable index from documentation (Cycle 10).

Stateless service pattern - follows SearchService approach.
Extracts metadata and content from markdown files.
"""

from pathlib import Path
from typing import Any


class DocumentIndexer:
    """Stateless service for building documentation index.

    All methods are static - no instance state required.
    Scans filesystem for markdown files and extracts metadata.
    """

    @staticmethod
    def build_index(docs_dir: Path | str) -> list[dict[str, Any]]:
        """Build searchable index from documentation directory.

        Args:
            docs_dir: Root documentation directory to scan

        Returns:
            List of document metadata dicts:
            [
                {
                    "title": str,      # Document title
                    "path": str,       # Relative path from docs_dir
                    "content": str,    # Full document content
                    "scope": str       # Directory-based scope
                },
                ...
            ]
        """
        docs_path = Path(docs_dir)
        index = []

        # Scan filesystem recursively for .md files
        for md_file in docs_path.rglob("*.md"):
            try:
                # Read file content
                content = md_file.read_text(encoding="utf-8")

                # Extract metadata
                doc_entry = {
                    "title": DocumentIndexer._extract_title(content, md_file.name),
                    "path": str(md_file.relative_to(docs_path)),
                    "content": content,
                    "scope": DocumentIndexer._determine_scope(md_file, docs_path),
                    "type": DocumentIndexer._determine_scope(md_file, docs_path)  # Alias for scope
                }

                index.append(doc_entry)

            except (IOError, UnicodeDecodeError):
                # Skip files that can't be read
                continue

        return index

    @staticmethod
    def get_index_statistics(index: list[dict[str, Any]]) -> dict[str, Any]:
        """Calculate statistics about documentation index.

        Args:
            index: List of document metadata from build_index()

        Returns:
            Dictionary with index statistics:
            {
                "total_documents": int,
                "total_size": int,       # Total content bytes
                "scopes": dict[str, int] # Document count per scope
            }
        """
        if not index:
            return {"total_documents": 0, "total_size": 0, "scopes": {}}

        total_size = sum(len(doc.get("content", "")) for doc in index)
        scopes: dict[str, int] = {}

        for doc in index:
            scope = doc.get("scope", "all")
            scopes[scope] = scopes.get(scope, 0) + 1

        return {
            "total_documents": len(index),
            "total_size": total_size,
            "scopes": scopes
        }

    @staticmethod
    def _extract_title(content: str, filename: str) -> str:
        """Extract title from markdown content or filename.

        Args:
            content: Markdown file content
            filename: File name as fallback

        Returns:
            Document title
        """
        lines = content.split("\n")

        # Look for first # heading
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("# "):
                return stripped[2:].strip()

        # Fallback to filename without extension
        name_without_ext = filename.rsplit(".", 1)[0]
        return name_without_ext.replace("_", " ").title()

    @staticmethod
    def _determine_scope(file_path: Path, docs_root: Path) -> str:
        """Determine document scope from directory structure.

        Args:
            file_path: Full file path
            docs_root: Documentation root directory

        Returns:
            Scope identifier (first directory name or "all")
        """
        try:
            relative = file_path.relative_to(docs_root)
            parts = relative.parts

            if len(parts) > 1:
                # Use first directory as scope
                return parts[0]  # e.g., "architecture", "development"

            return "all"

        except ValueError:
            # File not under docs_root
            return "all"
