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
from pathlib import Path

import jinja2
from jinja2 import meta, nodes
from jinja2.exceptions import TemplateNotFound

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


def _find_imported_macro_names(ast: nodes.Template) -> set[str]:
    """Return macro import symbols to exclude from agent schema.

    Jinja2 `{% import ... as alias %}` and `{% from ... import ... as name %}`
    introduce symbols that are internal to the template, not agent-provided.

    Jinja2 meta introspection does not treat these as declared variables, so we
    filter them out explicitly.
    """
    imported: set[str] = set()

    for import_node in ast.find_all((nodes.Import, nodes.FromImport)):
        if isinstance(import_node, nodes.Import):
            # `{% import "x" as alias %}`
            target = import_node.target
            if isinstance(target, nodes.Name):
                imported.add(target.name)
            elif isinstance(target, str):
                imported.add(target)

        elif isinstance(import_node, nodes.FromImport):
            # `{% from "x" import a as b, c %}`
            for entry in import_node.names:
                if isinstance(entry, tuple) and len(entry) == 2:
                    name, alias = entry
                    imported.add(alias or name)
                else:
                    imported.add(str(entry))

    return imported


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
    undeclared = undeclared - _find_imported_macro_names(ast)

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


def _parse_template_ast(env: jinja2.Environment, template_file: Path) -> nodes.Template:
    """Parse a template file into a Jinja2 AST.

    Raises:
        ExecutionError: If template has invalid Jinja2 syntax
    """
    src = template_file.read_text(encoding="utf-8")
    try:
        return env.parse(src)
    except jinja2.TemplateSyntaxError as exc:
        raise ExecutionError(
            f"Template syntax error in {template_file}: {exc}",
            recovery=["Check template for valid Jinja2 syntax"],
        ) from exc


def introspect_template_with_inheritance(template_root: Path, template_path: str) -> TemplateSchema:
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
    full_path = template_root / template_path

    if not full_path.exists():
        raise TemplateNotFound(template_path)


    chain = TemplateAnalyzer(template_root).get_inheritance_chain(full_path)
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_root))

    all_vars: set[str] = set()
    for template_file in chain:
        ast = _parse_template_ast(env, template_file)
        undeclared = meta.find_undeclared_variables(ast) - _find_imported_macro_names(ast)
        all_vars.update(undeclared)

    agent_vars = all_vars - SYSTEM_FIELDS

    # Classify variables as required or optional.
    # NOTE: Use the CONCRETE template AST for classification (most specific)
    concrete_ast = _parse_template_ast(env, chain[0])
    required, optional = _classify_variables(concrete_ast, agent_vars)

    return TemplateSchema(
        required=sorted(required),
        optional=sorted(optional),
    )
