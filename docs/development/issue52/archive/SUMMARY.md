# Jinja2 Introspection Research - Quick Summary

**See full document:** jinja2_introspection_research.md (37KB)

## Key Answer

**Q:** Can Jinja2 tell us "template generates class with suffix Worker" WITHOUT rendering?

**A:** Partial Yes - Use hybrid approach:
1. Static AST analysis for structure
2. Regex on source for patterns  
3. Mock rendering for verification

## What Jinja2 CAN Do

- `Environment.parse()` - Parse to AST without rendering
- `meta.find_undeclared_variables()` - Extract required variables
- `meta.find_referenced_templates()` - Find template dependencies
- AST traversal - Find blocks, macros, filters, loops

## What Jinja2 CANNOT Do

- Determine final output without rendering
- Resolve dynamic content
- Evaluate conditional logic
- Interpolate variables (e.g., {{name}}Worker needs name value)

## Recommended Implementation

```python
class TemplateAnalyzer:
    def __init__(self, template_path):
        self.source = open(template_path).read()
        self.ast = Environment().parse(self.source)
    
    def get_variables(self):
        return meta.find_undeclared_variables(self.ast)
    
    def get_class_pattern(self):
        match = re.search(r'class\s+\{\{(\w+)\}\}(\w*)', self.source)
        return match.groups() if match else None
```

## Files Created

1. jinja2_introspection_research.md - Full research (10 sections)
2. examples/demo.py - Runnable examples
3. SUMMARY.md - This file

## Next Steps

1. Review full research document
2. Choose metadata format
3. Implement TemplateAnalyzer
4. Add validation to scaffolding
5. Create tests
