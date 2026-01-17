"""Directory policy resolution utility.

Purpose: Resolve directory policies with parent inheritance
Responsibility: Single source of WAAR (where) knowledge
Used by: PolicyEngine, ScaffoldArtifactTool (was ScaffoldComponentTool)
"""

from pathlib import Path
from typing import Dict, List, Optional

from mcp_server.config.project_structure import (
    DirectoryPolicy,
    ProjectStructureConfig,
)


class ResolvedDirectoryPolicy:
    """Directory policy with inheritance resolved."""

    def __init__(
        self,
        path: str,
        description: str,
        allowed_artifact_types: List[str],
        allowed_extensions: List[str],
        require_scaffold_for: List[str],
    ):
        self.path = path
        self.description = description
        self.allowed_artifact_types = allowed_artifact_types
        self.allowed_extensions = allowed_extensions
        self.require_scaffold_for = require_scaffold_for

    @property
    def allowed_component_types(self) -> List[str]:
        """DEPRECATED: Backwards compatibility alias for allowed_artifact_types."""
        return self.allowed_artifact_types

    def allows_artifact_type(self, artifact_type: str) -> bool:
        """Check if artifact type allowed in this directory."""
        if not self.allowed_artifact_types:  # Empty = all allowed
            return True
        return artifact_type in self.allowed_artifact_types

    def allows_component_type(self, component_type: str) -> bool:
        """DEPRECATED: Use allows_artifact_type() instead."""
        return self.allows_artifact_type(component_type)

    def allows_extension(self, file_path: str) -> bool:
        """Check if file extension allowed."""
        if not self.allowed_extensions:  # Empty = all allowed
            return True
        ext = Path(file_path).suffix
        return ext in self.allowed_extensions

    def requires_scaffold(self, file_path: str) -> bool:
        """Check if file path matches scaffold requirement patterns."""
        # Normalize paths for consistent comparison
        file_path_normalized = str(Path(file_path)).replace("\\", "/")
        policy_path_normalized = str(Path(self.path)).replace("\\", "/")

        # Calculate relative path
        if file_path_normalized.startswith(policy_path_normalized + "/"):
            relative_path = file_path_normalized[len(policy_path_normalized) + 1:]
        elif file_path_normalized.startswith(policy_path_normalized):
            relative_path = file_path_normalized[len(policy_path_normalized):]
        else:
            relative_path = file_path_normalized

        for pattern in self.require_scaffold_for:
            # Use Path.match for proper glob pattern support
            # Note: **/ means "zero or more directories" but Path.match requires
            # at least one separator, so we check both with and without **/ prefix
            path_obj = Path(relative_path)
            if path_obj.match(pattern):
                return True
            # If pattern starts with **/, also check without it for single-level paths
            if pattern.startswith("**/") and path_obj.match(pattern[3:]):
                return True
        return False


class DirectoryPolicyResolver:
    """Resolve directory policies with inheritance.

    Responsibilities:
    - Path matching (exact, parent walk)
    - Inheritance resolution (Q4 decision - implicit)
    - Policy lookup optimization

    NOT Responsible:
    - Policy enforcement (PolicyEngine does this)
    - Config validation (Pydantic does this)
    """

    def __init__(self, config: Optional[ProjectStructureConfig] = None):
        """Initialize resolver.

        Args:
            config: ProjectStructureConfig instance (loads default if None)
        """
        self._config = config or ProjectStructureConfig.from_file()
        self._cache: Dict[str, ResolvedDirectoryPolicy] = {}  # Q3: No caching for MVP

    def resolve(self, path: str) -> ResolvedDirectoryPolicy:
        """Resolve directory policy for given path with inheritance.

        Algorithm:
        1. Try exact match
        2. Walk up parent chain
        3. Fallback to workspace root policy (permissive)

        Args:
            path: Directory or file path (workspace-relative)

        Returns:
            ResolvedDirectoryPolicy with inheritance applied
        """
        # Normalize path
        normalized = Path(path).as_posix()

        # Detect if path is a file (has extension or physical file exists)
        path_obj = Path(normalized)
        is_file = path_obj.is_file() or bool(path_obj.suffix)

        if is_file:
            normalized = str(path_obj.parent).replace("\\", "/")

        # Try exact match first
        policy = self._config.get_directory(normalized)
        if policy:
            return self._resolve_with_inheritance(policy)

        # Walk up parent chain
        current = Path(normalized)
        while current != Path("."):
            parent_path = str(current.parent).replace("\\", "/")
            if parent_path == ".":
                break
            policy = self._config.get_directory(parent_path)
            if policy:
                return self._resolve_with_inheritance(policy)
            current = current.parent

        # Fallback: Permissive default (no restrictions)
        return ResolvedDirectoryPolicy(
            path=normalized,
            description="Workspace root (no restrictions)",
            allowed_artifact_types=[],  # Empty = all allowed
            allowed_extensions=[],  # Empty = all allowed
            require_scaffold_for=[],  # Empty = no requirements
        )

    def _resolve_with_inheritance(
        self, policy: DirectoryPolicy
    ) -> ResolvedDirectoryPolicy:
        """Apply inheritance rules to policy.

        Inheritance Rules (Q4 decision - implicit):
        - allowed_extensions: Inherit from parent unless overridden
        - allowed_artifact_types: Override (no merge)
        - require_scaffold_for: Cumulative (child adds to parent)
        """
        # Start with current policy values
        allowed_extensions = list(policy.allowed_extensions)
        allowed_artifact_types = list(policy.allowed_artifact_types)
        require_scaffold_for = list(policy.require_scaffold_for)

        # Walk up parent chain
        current_policy = policy
        while current_policy.parent:
            parent_policy = self._config.get_directory(current_policy.parent)
            if not parent_policy:
                break

            # Inherit allowed_extensions if not overridden
            if not allowed_extensions and parent_policy.allowed_extensions:
                allowed_extensions = list(parent_policy.allowed_extensions)

            # Cumulative require_scaffold_for
            require_scaffold_for.extend(parent_policy.require_scaffold_for)

            current_policy = parent_policy

        return ResolvedDirectoryPolicy(
            path=policy.path,
            description=policy.description,
            allowed_artifact_types=allowed_artifact_types,
            allowed_extensions=allowed_extensions,
            require_scaffold_for=require_scaffold_for,
        )
