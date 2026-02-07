# mcp_server/validation/template_analyzer.py
"""
Template metadata analyzer for extracting validation rules from Jinja2 templates.

@layer: Validation
@dependencies: [jinja2, yaml]
"""
# Standard library
import re
from pathlib import Path
from typing import Any

# Third-party
import yaml
from jinja2 import Environment, meta


class TemplateAnalyzer:
    """Analyzes Jinja2 templates to extract validation metadata."""

    def __init__(self, template_root: Path) -> None:
        """
        Initialize analyzer with template directory root.

        Args:
            template_root: Root directory containing all templates.
        """
        self.template_root = Path(template_root)
        self.env = Environment()
        self._metadata_cache: dict[Path, dict[str, Any]] = {}

    def extract_metadata(self, template_path: Path) -> dict[str, Any]:
        """
        Extract validation metadata from template YAML frontmatter.

        Returns metadata dict with structure:
        {
            "enforcement": "STRICT" | "ARCHITECTURAL" | "GUIDELINE",
            "level": "format" | "content",
            "extends": "path/to/base.jinja2" | None,
            "validates": {
                "strict": [...],
                "guidelines": [...]
            },
            "variables": [..."name", "type", ...],
            "purpose": "...",
            "version": "2.0"
        }

        Returns empty dict if no metadata found.

        Args:
            template_path: Path to template file.

        Returns:
            Metadata dictionary or empty dict if no metadata.

        Raises:
            ValueError: If YAML metadata is malformed.
        """
        # Check cache first
        if template_path in self._metadata_cache:
            return self._metadata_cache[template_path]

        try:
            source = template_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            raise ValueError(
                f"Failed to read template {template_path}: {e}"
            ) from e

        # Extract TEMPLATE_METADATA from Jinja2 comment block
        # Supports both {# TEMPLATE_METADATA ... #} and {#- TEMPLATE_METADATA ... -#}
        # Pattern captures the full "TEMPLATE_METADATA: ..." YAML block
        pattern = r'\{#-?\s*(TEMPLATE_METADATA:.*?)\s*-?#\}'
        match = re.search(pattern, source, re.DOTALL)

        if not match:
            # No metadata found
            self._metadata_cache[template_path] = {}
            return {}

        metadata_yaml = match.group(1)

        # Parse YAML (will have TEMPLATE_METADATA as root key)
        try:
            yaml_dict = yaml.safe_load(metadata_yaml)
        except yaml.YAMLError as e:
            raise ValueError(
                f"Failed to parse TEMPLATE_METADATA in {template_path}: {e}"
            ) from e

        if not isinstance(yaml_dict, dict):
            raise ValueError(
                f"TEMPLATE_METADATA must be a dict, got {type(yaml_dict)}"
            )

        # Extract the actual metadata from under TEMPLATE_METADATA key
        metadata: dict[str, Any] = yaml_dict.get("TEMPLATE_METADATA", {})
        if not metadata:
            self._metadata_cache[template_path] = {}
            return {}

        # Extract Jinja2 variables
        metadata["variables"] = self.extract_jinja_variables(template_path)

        # Cache and return
        self._metadata_cache[template_path] = metadata
        return metadata

    def extract_jinja_variables(self, template_path: Path) -> list[str]:
        """
        Extract undeclared variables from Jinja2 template.

        Args:
            template_path: Path to template file.

        Returns:
            List of variable names used in template.
        """
        try:
            source = template_path.read_text(encoding="utf-8")
            ast = self.env.parse(source)
            variables = meta.find_undeclared_variables(ast)
            return sorted(variables)
        except (OSError, UnicodeDecodeError, ValueError):
            # If reading or parsing fails, return empty list
            return []

    def get_base_template(self, template_path: Path) -> Path | None:
        """
        Get the base template this template extends.

        Args:
            template_path: Path to template file.

        Returns:
            Path to base template or None if no inheritance.
        """
        try:
            source = template_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return None

        # Look for {% extends "path/to/base.jinja2" %}
        extends_pattern = r'\{%\s*extends\s+"([^"]+)"\s*%\}'
        match = re.search(extends_pattern, source)

        if not match:
            return None

        base_path_str = match.group(1)
        base_path = self.template_root / base_path_str

        if not base_path.exists():
            return None

        return base_path

    def get_inheritance_chain(self, template_path: Path) -> list[Path]:
        """
        Get complete inheritance chain from specific to base.

        Args:
            template_path: Path to template file.

        Returns:
            List of template paths from most specific to most general.
            Example: [worker.py.jinja2, base_component.py.jinja2]
        """
        chain = [template_path]
        current = template_path
        seen = {template_path}  # Prevent circular inheritance

        while True:
            base = self.get_base_template(current)
            if base is None or base in seen:
                break
            chain.append(base)
            seen.add(base)
            current = base

        return chain

    def merge_metadata(
        self,
        child: dict[str, Any],
        parent: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Merge child and parent metadata, with child taking precedence.

        Merging rules:
        - strict rules: concatenate (child + parent, no duplicates)
        - guidelines: concatenate (child + parent, no duplicates)
        - enforcement: child overrides parent
        - variables: union of both
        - purpose/hints: child overrides parent

        Args:
            child: Child template metadata.
            parent: Parent template metadata.

        Returns:
            Merged metadata dictionary.
        """
        merged: dict[str, Any] = {}

        # Child overrides for scalar values
        for key in ["enforcement", "level", "version", "purpose",
                    "agent_hint", "content_guidance"]:
            if key in child:
                merged[key] = child[key]
            elif key in parent:
                merged[key] = parent[key]

        # Merge validates section
        if "validates" in child or "validates" in parent:
            merged["validates"] = {}

            # Merge strict rules
            child_strict = child.get("validates", {}).get("strict", [])
            parent_strict = parent.get("validates", {}).get("strict", [])
            merged["validates"]["strict"] = child_strict + parent_strict

            # Merge guidelines
            child_guidelines = child.get("validates", {}).get("guidelines", [])
            parent_guidelines = parent.get("validates", {}).get(
                "guidelines", []
            )
            merged["validates"]["guidelines"] = (
                child_guidelines + parent_guidelines
            )

        # Union of variables
        child_vars = set(child.get("variables", []))
        parent_vars = set(parent.get("variables", []))
        merged["variables"] = sorted(child_vars | parent_vars)

        return merged
