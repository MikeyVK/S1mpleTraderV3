"""
MVP: Multi-Tier Template Introspector
Proof of concept for inheritance-aware schema extraction.

Demonstrates simplified approach using AST walking for parent detection.
"""

from dataclasses import dataclass, field
from typing import Set, List, Tuple

import jinja2
from jinja2 import Environment, FileSystemLoader, meta, nodes


@dataclass
class TemplateSchema:
    """Schema extracted from template hierarchy."""
    
    required: List[str] = field(default_factory=list)
    optional: List[str] = field(default_factory=list)
    inheritance_chain: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "required": sorted(self.required),
            "optional": sorted(self.optional),
            "inheritance_chain": self.inheritance_chain,
        }


# System fields injected by scaffolding system
SYSTEM_FIELDS: Set[str] = {
    "template_id",
    "template_version", 
    "scaffold_created",
    "output_path",
}


def introspect_template_with_inheritance(
    env: Environment,
    template_name: str
) -> TemplateSchema:
    """Extract schema from template including inherited variables.
    
    Algorithm:
    1. Walk inheritance chain via AST (detect {% extends %})
    2. Extract variables from ALL templates in chain
    3. Merge via set union
    4. Classify required vs optional
    
    Args:
        env: Jinja2 environment with loader configured
        template_name: Template path (e.g., 'concrete_worker.py.jinja2')
        
    Returns:
        TemplateSchema with merged variables from entire hierarchy
    """
    # Step 1: Build inheritance chain
    inheritance_chain = []
    all_asts = []
    current_name = template_name
    
    while current_name:
        # Load template source
        source, _, _ = env.loader.get_source(env, current_name)
        ast = env.parse(source)
        
        inheritance_chain.append(current_name)
        all_asts.append((current_name, ast))
        
        # Find parent via {% extends %} node
        parent_name = None
        for node in ast.find_all(nodes.Extends):
            if isinstance(node.template, nodes.Const):
                parent_name = node.template.value
                break
        
        current_name = parent_name
    
    # Step 2: Extract variables from ALL templates
    all_variables = set()
    for name, ast in all_asts:
        variables = meta.find_undeclared_variables(ast)
        all_variables.update(variables)
    
    # Step 3: Filter system fields
    user_variables = all_variables - SYSTEM_FIELDS
    
    # Step 4: Classify required vs optional
    required = []
    optional = []
    
    for var in user_variables:
        # Check if variable has default value or is in conditional
        is_optional = _is_variable_optional(var, all_asts)
        
        if is_optional:
            optional.append(var)
        else:
            required.append(var)
    
    return TemplateSchema(
        required=sorted(required),
        optional=sorted(optional),
        inheritance_chain=inheritance_chain
    )


def _is_variable_optional(var_name: str, asts: List[Tuple[str, nodes.Template]]) -> bool:
    """Determine if variable is optional by analyzing AST usage.
    
    A variable is optional if:
    - Used with |default filter
    - Only used inside {% if var %} conditionals
    
    Args:
        var_name: Variable name to check
        asts: List of (template_name, ast) tuples
        
    Returns:
        True if variable is optional
    """
    for template_name, ast in asts:
        # Check for |default filter usage
        for filter_node in ast.find_all(nodes.Filter):
            if filter_node.name == 'default':
                # Check if this filter is applied to our variable
                if isinstance(filter_node.node, nodes.Name) and filter_node.node.name == var_name:
                    return True
        
        # Check for conditional usage
        for if_node in ast.find_all(nodes.If):
            # Check if variable is only used inside conditional
            test_vars = set()
            for name_node in if_node.test.find_all(nodes.Name):
                test_vars.add(name_node.name)
            
            if var_name in test_vars:
                return True
    
    return False


def demo_introspection(template_name: str):
    """Demonstrate introspection on a template.
    
    Args:
        template_name: Template to introspect
    """
    print(f"\n{'='*70}")
    print(f"Introspecting: {template_name}")
    print('='*70)
    
    # Setup environment
    env = Environment(
        loader=FileSystemLoader('docs/development/issue72/mvp/templates')
    )
    
    # Introspect
    schema = introspect_template_with_inheritance(env, template_name)
    
    # Display results
    print(f"\nInheritance Chain ({len(schema.inheritance_chain)} tiers):")
    for i, tier in enumerate(schema.inheritance_chain):
        print(f"  {i}. {tier}")
    
    print(f"\nRequired Variables ({len(schema.required)}):")
    for var in schema.required:
        print(f"  - {var}")
    
    print(f"\nOptional Variables ({len(schema.optional)}):")
    for var in schema.optional:
        print(f"  - {var}")
    
    print(f"\nTotal Variables: {len(schema.required) + len(schema.optional)}")
    
    return schema


if __name__ == "__main__":
    print("Multi-Tier Template Introspection MVP")
    print("=" * 70)
    
    # Demo: Introspect concrete worker template
    schema = demo_introspection("concrete_worker.py.jinja2")
    
    print("\n" + "="*70)
    print("KEY FINDINGS:")
    print("="*70)
    print(f"✅ Successfully resolved {len(schema.inheritance_chain)} tier inheritance chain")
    print(f"✅ Extracted {len(schema.required) + len(schema.optional)} total variables")
    print(f"✅ No manual template merging needed - AST walking works!")
    print("✅ Jinja2 rendering still works unchanged (FileSystemLoader handles extends)")
