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
# pylint: disable=too-many-locals

from dataclasses import dataclass, field
from pathlib import Path

import jinja2
from jinja2 import meta, nodes

from mcp_server.core.exceptions import ExecutionError
from mcp_server.validation.template_analyzer import TemplateAnalyzer

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


def introspect_template_with_inheritance(
    template_root: Path, template_path: str
) -> TemplateSchema:
    """Extract validation schema from template WITH inheritance chain resolution.

    This is the Task 2.1 implementation - resolves entire inheritance chain
    and merges variables from all parent templates.

    Algorithm:
    1. Resolve inheritance chain (concrete → tier2 → tier1 → tier0)
    2. Load and parse each template in chain
    3. Extract variables from each template
    4. Merge all variables (union)
    5. Filter system fields
    6. Classify as required/optional
    7. Sort alphabetically

    Args:
        template_root: Root directory containing templates
        template_path: Relative path to template (e.g., "concrete/worker.py.jinja2")

    Returns:
        TemplateSchema with merged variables from entire inheritance chain

    Raises:
        ExecutionError: If template has invalid syntax or chain cannot be resolved
    """
    # Resolve full path
    full_path = template_root / template_path

    if not full_path.exists():
        raise ExecutionError(
            f"Template not found: {full_path}",
            recovery=["Check template path", "Verify template_root is correct"],
        )

    # Get inheritance chain using TemplateAnalyzer
    analyzer = TemplateAnalyzer(template_root)
    chain = analyzer.get_inheritance_chain(full_path)

    # Create Jinja2 environment with template loader
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(template_root),
    )

    # Collect all variables from entire chain
    all_vars: set[str] = set()

    for template_file in chain:
        # Read template source
        src = template_file.read_text(encoding="utf-8")

        # Parse and extract variables
        try:
            ast = env.parse(src)
        except jinja2.TemplateSyntaxError as e:
            raise ExecutionError(
                f"Template syntax error in {template_file}: {e}",
                recovery=["Check template for valid Jinja2 syntax"],
            ) from e

        # Extract undeclared variables from this template
        undeclared = meta.find_undeclared_variables(ast)
        all_vars.update(undeclared)

    # Filter out system fields
    agent_vars = all_vars - SYSTEM_FIELDS

    # Classify variables as required or optional
    # NOTE: We use the CONCRETE template AST for classification (most specific)
    # This is because parent templates may have different usage patterns
    concrete_src = chain[0].read_text(encoding="utf-8")
    concrete_ast = env.parse(concrete_src)
    required, optional = _classify_variables(concrete_ast, agent_vars)

    # Sort alphabetically
    return TemplateSchema(
        required=sorted(required),
        optional=sorted(optional),
    )
