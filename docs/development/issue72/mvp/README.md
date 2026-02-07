# MVP: 4-Tier Template Architecture + Introspection

**Issue #72 Research - Proof of Concept**

## Overview

This MVP demonstrates the proposed 4-tier template architecture and proves that inheritance-aware introspection is simple and effective.

## Structure

```
mvp/
├── templates/                         # 4-tier template hierarchy
│   ├── tier0_base_artifact.jinja2    # Universal base (SCAFFOLD metadata)
│   ├── tier1_base_code.jinja2        # Code format base
│   ├── tier2_base_python.jinja2      # Python language base
│   ├── tier3_base_python_component.jinja2  # Component specialization
│   └── concrete_worker.py.jinja2     # Concrete worker template
│
├── introspector_mvp.py               # Inheritance-aware introspection
├── demo.py                           # Comprehensive demonstration
└── README.md                         # This file
```

## Key Findings

### ✅ Rendering (NO BREAKING CHANGES)
- Jinja2 `FileSystemLoader` + `Environment.get_template()` automatically resolves `{% extends %}` chains
- **Zero changes needed** to rendering infrastructure
- Works perfectly with 4-tier (or N-tier) inheritance

### ✅ Introspection (SIMPLE SOLUTION)
- AST walking for parent detection: `ast.find_all(nodes.Extends)`
- Recursive chain resolution (~20 lines)
- Merge variables via set union
- **Much simpler than expected** (~60 lines total vs 200+ line complex solution)

### 🔴 Current Implementation Broken
- Single-template introspection misses ALL inherited variables
- Validation fails for templates using `{% extends %}`
- **Must be fixed** before 4-tier rollout

## Running the MVP

```bash
# From project root
cd docs/development/issue72/mvp

# Run comprehensive demo
python demo.py
```

## Demo Output

### Demo 1: Template Rendering
Proves that Jinja2 rendering works perfectly with 4-tier inheritance:
- Renders concrete worker template
- Automatically resolves 5 levels (Tier 0 → 1 → 2 → 3 → Concrete)
- Shows complete output

### Demo 2: Introspection Comparison
Compares single-template vs multi-tier introspection:
- Shows variables found by each method
- **Highlights missed variables** in current approach
- Proves multi-tier introspection is necessary

### Demo 3: Tier Contribution Analysis
Shows which variables come from which tier:
- Per-tier variable listing
- Cumulative effect through inheritance chain
- Helps understand variable propagation

## Technical Details

### Introspection Algorithm

```python
def introspect_template_with_inheritance(env, template_name):
    # 1. Build inheritance chain via AST walking
    chain = []
    current = template_name
    while current:
        source = env.loader.get_source(env, current)[0]
        ast = env.parse(source)
        chain.append((current, ast))
        
        # Find {% extends %} node
        parent = None
        for node in ast.find_all(nodes.Extends):
            if isinstance(node.template, nodes.Const):
                parent = node.template.value
        current = parent
    
    # 2. Extract variables from ALL templates
    all_vars = set()
    for name, ast in chain:
        vars = meta.find_undeclared_variables(ast)
        all_vars.update(vars)
    
    # 3. Classify required vs optional
    return classify_variables(all_vars, chain)
```

### Complexity Assessment

| Component | Effort | Change Type |
|-----------|--------|-------------|
| JinjaRenderer | 0h | No change |
| TemplateScaffolder | 0h | No change |
| TemplateIntrospector | 2-3h | Rewrite introspection logic |
| Variable Classification | 1h | Extend to handle multiple ASTs |
| **Total** | **3-4h** | Much less than estimated 4-6h! |

## Validation

This MVP validates:
- ✅ 4-tier architecture is technically sound
- ✅ Jinja2 handles inheritance automatically (rendering)
- ✅ AST walking provides simple introspection solution
- ✅ Current implementation is broken (misses inherited vars)
- ✅ Fix is simpler than initially estimated

## Next Steps

1. **Planning Phase**: Design production implementation based on MVP findings
2. **TDD Phase**: Implement introspection rewrite with tests
3. **Template Updates**: Create 4-tier base templates
4. **Migration**: Update 24 existing templates to use new hierarchy

## Lessons Learned

1. **Jinja2 is powerful** - auto-resolves inheritance, no manual merging needed
2. **AST walking is simple** - no complex loader manipulation required
3. **User insight was key** - "eenvoudiger methode" led to this elegant solution
4. **MVP validates assumptions** - proves architecture before full implementation
