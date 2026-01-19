# mcp_server/services/search_service.py
"""
SearchService - Stateless documentation search.

Provides stateless search algorithms for documentation indexing and retrieval.

@layer: Backend (Services)
@dependencies: [typing]
@responsibilities:
    - Index searching (stateless)
    - Relevance calculation
    - Snippet extraction
"""

from typing import Any


class SearchService:
    """Stateless search service.

    All methods are static - no instance state required.
    Pure functions for maximum testability.
    """

    @staticmethod
    def calculate_relevance(doc: dict[str, Any], query: str) -> float:
        """Calculate relevance score for document.

        Scoring weights:
        - Title matches: 3.0 per occurrence
        - Path matches: 1.0 per occurrence
        - Content matches: 0.5 per occurrence

        Args:
            doc: Document with 'title', 'path', 'content' fields
            query: Search query (case-insensitive)

        Returns:
            Relevance score (higher = more relevant)
        """
        score = 0.0
        query_lower = query.lower()

        # Title matches (weight: 3.0)
        if "title" in doc:
            title_lower = doc["title"].lower()
            count = title_lower.count(query_lower)
            score += count * 3.0

        # Path matches (weight: 1.0)
        if "path" in doc:
            path_lower = doc["path"].lower()
            count = path_lower.count(query_lower)
            score += count * 1.0

        # Content matches (weight: 0.5)
        if "content" in doc:
            content_lower = doc["content"].lower()
            count = content_lower.count(query_lower)
            score += count * 0.5

        return score

    @staticmethod
    def extract_snippet(
        content: str, query: str, context_chars: int = 150
    ) -> str:
        """Extract snippet with context around query match.

        Args:
            content: Full content text
            query: Search query to find
            context_chars: Characters to include before/after match

        Returns:
            Snippet with "..." for truncation
        """
        # Find query position (case-insensitive)
        content_lower = content.lower()
        query_lower = query.lower()
        pos = content_lower.find(query_lower)

        if pos == -1:
            # No match - return beginning
            if len(content) <= context_chars * 2:
                return content
            return content[:context_chars * 2] + "..."

        # Calculate snippet bounds
        start = max(0, pos - context_chars)
        end = min(len(content), pos + len(query) + context_chars)

        # Extract snippet
        snippet = content[start:end]

        # Add ellipsis if truncated
        if start > 0:
            snippet = "..." + snippet
        if end < len(content):
            snippet = snippet + "..."

        return snippet

    @staticmethod
    def search_index(
        index: list[dict[str, Any]],
        query: str,
        max_results: int = 10,
        scope: str | None = None
    ) -> list[dict[str, Any]]:
        """Search document index.

        Args:
            index: List of documents with 'title', 'path', 'content'
            query: Search query
            max_results: Maximum results to return
            scope: Optional filter by 'type' field

        Returns:
            List of documents sorted by relevance (descending)
            with added '_relevance' and '_snippet' fields
        """
        results = []

        for doc in index:
            # Filter by scope if provided
            if scope and doc.get("type") != scope:
                continue

            # Calculate relevance
            relevance = SearchService.calculate_relevance(doc, query)

            # Skip documents with no matches
            if relevance <= 0.0:
                continue

            # Create result with relevance and snippet
            result = {**doc}
            result["_relevance"] = relevance
            result["_snippet"] = SearchService.extract_snippet(
                doc.get("content", ""), query
            )
            results.append(result)

        # Sort by relevance (descending)
        results.sort(key=lambda x: x["_relevance"], reverse=True)

        # Limit results
        return results[:max_results]
