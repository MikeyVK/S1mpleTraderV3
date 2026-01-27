"""
Template introspection module for schema extraction.

Extracts validation schema from Jinja2 templates via AST parsing.
Templates are the Single Source of Truth - no manual field lists needed.

@layer: Backend (Scaffolding)
@dependencies: [jinja2.Environment, jinja2.meta]
@responsibilities:
    - Parse Jinja2 templates into AST
    - Extract undeclared variables from templates
    - Classify variables as required or optional
    - Filter system-injected fields from agent schema
    - Return structured TemplateSchema
"""

from dataclasses import dataclass, field

import jinja2
from jinja2 import meta, nodes

from mcp_server.core.exceptions import ExecutionError

# System fields injected by ArtifactManager - NOT agent responsibility
SYSTEM_FIELDS: set[str] = {
    "template_id",
    "template_version",
    "scaffold_created",
    "output_path",
}


@dataclass
class TemplateSchema:
    """Schema extracted from template via AST introspection.

    Represents agent-input requirements (system fields filtered out).
    """

    required: list[str] = field(default_factory=list)
    optional: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, list[str]]:
        """Convert to dictionary for JSON serialization."""
        return {
            "required": self.required,
            "optional": self.optional,
        }


def introspect_template(env: jinja2.Environment, template_source: str) -> TemplateSchema:
    """Extract validation schema from Jinja2 template source.

    Algorithm:
    1. Parse template into AST
    2. Extract undeclared variables
    3. Classify as required/optional via AST walking
    4. Filter system fields
    5. Sort alphabetically

    Args:
        env: Jinja2 environment for parsing
        template_source: Raw template string

    Returns:
        TemplateSchema with required/optional field lists

    Raises:
        ExecutionError: If template has invalid Jinja2 syntax
    """
    try:
        # Parse template into AST
        ast = env.parse(template_source)
    except jinja2.TemplateSyntaxError as e:
        raise ExecutionError(
            f"Template syntax error: {e}",
            recovery=[
                "Check template for valid Jinja2 syntax",
                "Verify all tags are properly closed",
            ],
        ) from e

    # Extract all undeclared variables
    undeclared = meta.find_undeclared_variables(ast)

    # Filter out system fields
    agent_vars = undeclared - SYSTEM_FIELDS

    # Classify variables as required or optional
    required, optional = _classify_variables(ast, agent_vars)

    # Sort alphabetically
    return TemplateSchema(
        required=sorted(required),
        optional=sorted(optional),
    )


def _classify_variables(
    ast: nodes.Template, variables: set[str]
) -> tuple[list[str], list[str]]:
    """Classify variables as required or optional based on AST usage patterns.

    Conservative algorithm - if unclear, mark as required (fail fast).

    Optional patterns:
    - {% if variable %} - used in conditional block
    - {{ variable|default(...) }} - has default filter

    Args:
        ast: Parsed Jinja2 AST
        variables: Set of variable names to classify

    Returns:
        Tuple of (required_list, optional_list)
    """
    optional_vars: set[str] = set()
    required_vars: set[str] = set()

    # Walk AST to detect optional patterns
    for node in ast.find_all((nodes.If, nodes.Filter)):
        # Variables used in {% if variable %} are optional
        if isinstance(node, nodes.If) and isinstance(node.test, nodes.Name):
            var_name = node.test.name
            if var_name in variables:
                optional_vars.add(var_name)

        # Variables with |default(...) filter are optional
        if isinstance(node, nodes.Filter) and node.name == "default":
            if isinstance(node.node, nodes.Name):
                var_name = node.node.name
                if var_name in variables:
                    optional_vars.add(var_name)

    # Remaining variables are required (conservative)
    required_vars = variables - optional_vars

    return list(required_vars), list(optional_vars)
