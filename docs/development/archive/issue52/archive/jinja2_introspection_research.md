# Jinja2 Template Introspection Research
## Comprehensive Analysis of Native Capabilities for Template Validation

**Research Date:** December 30, 2025  
**Purpose:** Understand Jinja2's native template introspection for building validation rules  
**Context:** SimpleTraderV3 template scaffolding validation

---

## Executive Summary

**Key Finding:** Jinja2 provides powerful AST (Abstract Syntax Tree) introspection that allows analysis of templates WITHOUT rendering them. However, there are important limitations:

### ✅ What Jinja2 CAN Tell Us (Static Analysis)
- All variables a template expects (`meta.find_undeclared_variables()`)
- All templates referenced (extends, includes, imports)
- All blocks, macros, filters, and tests used
- Control flow structures (for loops, if statements)
- Static string content in template
- AST node tree structure

### ❌ What Jinja2 CANNOT Tell Us (Dynamic Analysis Required)
- **Exact output without rendering** (e.g., "this will generate a class named 'FooWorker'")
- Conditional logic results (depends on runtime values)
- Dynamic template names (e.g., `{% include dynamic_var %}`)
- Complex string interpolations (e.g., `class {{name}}Worker`)

### 🎯 Answer to Your Key Question
> "Can Jinja2 tell us 'this template will generate a class with suffix Worker and method execute' WITHOUT rendering?"

**Partial Yes:** We can extract:
- Template expects variable `name`
- Template has static text containing `class ` and `Worker`
- Template contains method definitions like `def execute`
- BUT: We cannot know the final class name without providing `name` value

**Recommendation:** Use hybrid approach:
1. Static introspection for structure validation
2. Lightweight rendering with mock data for output validation
3. Regular expressions on template source for pattern matching

---

## 1. Jinja2 Environment & Template Objects

### 1.1 Parsing Without Rendering

```python
from jinja2 import Environment, FileSystemLoader

# Create environment
env = Environment(loader=FileSystemLoader('templates'))

# Method 1: Parse from file
with open('worker.py.jinja2', 'r') as f:
    source = f.read()

# Parse to AST (does NOT render)
ast = env.parse(source)
# Returns: jinja2.nodes.Template object

# Method 2: Parse from string
template_str = "Hello {{name}}"
ast = env.parse(template_str)
```

### 1.2 Template AST Access

The parsed AST is a tree of nodes. Root is always `jinja2.nodes.Template`:

```python
# Explore AST structure
ast.body  # List of statement nodes
ast.filename  # None for string templates
ast.lineno  # Always 1 for root

# Tree representation
print(repr(ast))  # Shows full node tree
```

### 1.3 Node Types

All nodes inherit from `jinja2.nodes.Node`. Major categories:

- **Stmt** (statements): Block, For, If, Assign, Macro, etc.
- **Expr** (expressions): Name, Const, Filter, Call, etc.
- **Helper**: Keyword, Pair, Operand
- **Literal**: Const, List, Dict, Tuple
- **Template**: Root node

---

## 2. Template Introspection Methods

### 2.1 `meta.find_undeclared_variables(ast)`

**Purpose:** Find all variables the template will look up from context.

```python
from jinja2 import meta

# Example template
template = "{{name}}Worker extends {{base}} with {{method}}"
ast = env.parse(template)

variables = meta.find_undeclared_variables(ast)
# Returns: {'name', 'base', 'method'}
```

**Use Case for Your Project:**
```python
# Validate worker template expects correct vars
expected_vars = {'name', 'input_dto', 'output_dto', 'dependencies'}
actual_vars = meta.find_undeclared_variables(ast)

missing = expected_vars - actual_vars
if missing:
    raise ValidationError(f"Template missing variables: {missing}")
```

### 2.2 `meta.find_referenced_templates(ast)`

**Purpose:** Find all template inheritance/inclusion relationships.

```python
# Template with references
template = """
{% extends "base.html" %}
{% include "header.html" %}
{% import "macros.html" as m %}
"""

ast = env.parse(template)
refs = list(meta.find_referenced_templates(ast))
# Returns: ['base.html', 'header.html', 'macros.html']
```

**Limitation:** Dynamic references return `None`:
```python
# This returns: [None]
template = "{% include dynamic_name %}"
```

### 2.3 `Template.module` Property

**Important:** This is NOT static introspection - it renders the template!

```python
template = env.get_template('worker.py.jinja2')

# This RENDERS the template with empty context
module = template.module

# Access exported macros/variables
if hasattr(module, 'my_macro'):
    result = module.my_macro()
```

**Use Case:** Access template macros for reuse, not for validation.

---

## 3. AST Node Traversal

### 3.1 Basic Traversal Methods

```python
def traverse_ast(node, depth=0):
    """Visit every node in the AST."""
    print("  " * depth + type(node).__name__)
    
    for child in node.iter_child_nodes():
        traverse_ast(child, depth + 1)

# Example usage
ast = env.parse(template_source)
traverse_ast(ast)
```

### 3.2 Finding Specific Node Types

```python
# Find all Name nodes (variable references)
names = list(ast.find_all(jinja2.nodes.Name))
for name_node in names:
    print(f"Variable: {name_node.name} at line {name_node.lineno}")

# Find all Filter nodes
filters = list(ast.find_all(jinja2.nodes.Filter))
for filt in filters:
    print(f"Filter: {filt.name}")

# Find first occurrence
first_if = ast.find(jinja2.nodes.If)
```

### 3.3 Comprehensive Template Analysis

```python
from typing import Dict, Set, List

def analyze_template(template_path: str) -> Dict:
    """Extract all introspectable data from template."""
    with open(template_path) as f:
        source = f.read()
    
    env = Environment()
    ast = env.parse(source)
    
    analysis = {
        # Variables template expects
        'variables': meta.find_undeclared_variables(ast),
        
        # Referenced templates
        'templates': list(meta.find_referenced_templates(ast)),
        
        # Blocks (for inheritance)
        'blocks': [],
        
        # Macros (reusable functions)
        'macros': [],
        
        # Filters used
        'filters': set(),
        
        # Tests used (is defined, is none, etc.)
        'tests': set(),
        
        # For loops
        'loops': [],
        
        # Assignments
        'assignments': [],
    }
    
    # Traverse and collect
    for node in ast.find_all(jinja2.nodes.Block):
        analysis['blocks'].append({
            'name': node.name,
            'lineno': node.lineno
        })
    
    for node in ast.find_all(jinja2.nodes.Macro):
        analysis['macros'].append({
            'name': node.name,
            'args': [arg.name for arg in node.args]
        })
    
    for node in ast.find_all(jinja2.nodes.Filter):
        analysis['filters'].add(node.name)
    
    for node in ast.find_all(jinja2.nodes.Test):
        analysis['tests'].add(node.name)
    
    for node in ast.find_all(jinja2.nodes.For):
        analysis['loops'].append({
            'target': getattr(node.target, 'name', str(node.target)),
            'lineno': node.lineno
        })
    
    for node in ast.find_all(jinja2.nodes.Assign):
        analysis['assignments'].append({
            'target': getattr(node.target, 'name', str(node.target)),
            'lineno': node.lineno
        })
    
    return analysis
```

---

## 4. Metadata Patterns in Templates

### 4.1 Comment-Based Metadata

Jinja2 comments are stripped during parsing and NOT available in AST:

```jinja
{# This comment is lost during parsing #}
{# metadata: worker_type=signal_detector #}
```

**Workaround:** Parse source text with regex before Jinja2:

```python
import re

def extract_metadata_comments(source: str) -> Dict:
    """Extract metadata from Jinja2 comments."""
    pattern = r'\{#\s*@(\w+):\s*(.+?)\s*#\}'
    matches = re.findall(pattern, source)
    return {key: value for key, value in matches}

# In template:
# {# @category: worker #}
# {# @output_class_suffix: Worker #}

metadata = extract_metadata_comments(template_source)
# {'category': 'worker', 'output_class_suffix': 'Worker'}
```

### 4.2 Front Matter Metadata

Use Python comment blocks at top of template:

```python
# TEMPLATE METADATA
# output_class_pattern: {{name}}Worker
# required_variables: name, input_dto, output_dto
# generates_methods: execute, validate
# END METADATA

class {{name}}Worker:
    def execute(self): pass
```

Parse with:
```python
def parse_frontmatter(source: str) -> Dict:
    """Extract YAML-like frontmatter."""
    lines = source.split('\n')
    metadata = {}
    in_metadata = False
    
    for line in lines:
        if '# TEMPLATE METADATA' in line:
            in_metadata = True
        elif '# END METADATA' in line:
            break
        elif in_metadata and line.startswith('# '):
            parts = line[2:].split(':', 1)
            if len(parts) == 2:
                key, value = parts
                metadata[key.strip()] = value.strip()
    
    return metadata
```

### 4.3 Structured Docstrings

Put metadata in template docstrings:

```jinja
"""
Worker Template

@generates: {{name}}Worker class
@methods: execute, validate
@inherits: BaseWorker[{{input_dto}}, {{output_dto}}]
@layer: Workers
"""
```

---

## 5. Practical Use Cases

### 5.1 Validating Template Structure

```python
def validate_worker_template(template_path: str) -> List[str]:
    """Validate worker template has required structure."""
    errors = []
    
    with open(template_path) as f:
        source = f.read()
    
    env = Environment()
    ast = env.parse(source)
    
    # Check required variables
    variables = meta.find_undeclared_variables(ast)
    required = {'name', 'input_dto', 'output_dto', 'dependencies'}
    
    missing_vars = required - variables
    if missing_vars:
        errors.append(f"Missing variables: {missing_vars}")
    
    # Check for class definition in static content
    has_class_def = False
    for node in ast.find_all(jinja2.nodes.TemplateData):
        if 'class ' in node.data:
            has_class_def = True
            break
    
    if not has_class_def:
        errors.append("Template does not define a class")
    
    # Check for execute method
    has_execute = False
    for node in ast.find_all(jinja2.nodes.TemplateData):
        if 'def execute' in node.data:
            has_execute = True
            break
    
    if not has_execute:
        errors.append("Template missing execute method")
    
    return errors
```

### 5.2 Extracting Template Patterns

```python
import re

def extract_template_patterns(source: str) -> Dict:
    """Extract what the template generates using regex + AST."""
    env = Environment()
    ast = env.parse(source)
    
    patterns = {
        'class_name_pattern': None,
        'methods': [],
        'imports': [],
        'inherits_from': None
    }
    
    # Variables used in output (not comprehensive)
    variables = meta.find_undeclared_variables(ast)
    
    # Pattern match static content
    for node in ast.find_all(jinja2.nodes.TemplateData):
        data = node.data
        
        # Class definition
        class_match = re.search(r'class\s+(\\w+)', data)
        if class_match:
            patterns['class_name_pattern'] = class_match.group(1)
        
        # Methods
        method_matches = re.findall(r'def\s+(\\w+)', data)
        patterns['methods'].extend(method_matches)
        
        # Inheritance
        inherit_match = re.search(r'class\s+\\w+\\(([^)]+)\\)', data)
        if inherit_match:
            patterns['inherits_from'] = inherit_match.group(1)
    
    return patterns
```

### 5.3 Template-to-Code Validation

**Problem:** Validate generated code matches template structure.

**Solution:** Hybrid approach:

1. **Static validation** (template structure)
2. **Mock rendering** (with fake data)
3. **AST comparison** (rendered output vs. expected)

```python
def validate_generated_code(template_path: str, generated_code: str) -> List[str]:
    """Validate generated code matches template expectations."""
    errors = []
    
    # 1. Analyze template
    template_patterns = extract_template_patterns(open(template_path).read())
    
    # 2. Parse generated code with ast module (Python AST, not Jinja2)
    import ast as python_ast
    try:
        tree = python_ast.parse(generated_code)
    except SyntaxError as e:
        return [f"Generated code is not valid Python: {e}"]
    
    # 3. Validate class exists
    classes = [node for node in tree.body if isinstance(node, python_ast.ClassDef)]
    if not classes:
        errors.append("Generated code missing class definition")
    
    # 4. Validate methods exist
    if classes:
        class_methods = [f.name for f in classes[0].body if isinstance(f, python_ast.FunctionDef)]
        for expected_method in template_patterns['methods']:
            if expected_method not in class_methods:
                errors.append(f"Generated class missing method: {expected_method}")
    
    return errors
```

---

## 6. Real-World Examples: Ansible & Salt

### 6.1 Ansible Template Analysis

Ansible uses Jinja2 extensively and validates templates:

```python
# From ansible/playbook/template.py (simplified)
def validate_template(template_path):
    env = Environment()
    with open(template_path) as f:
        source = f.read()
    
    try:
        ast = env.parse(source)
    except TemplateSyntaxError as e:
        raise AnsibleError(f"Template syntax error: {e}")
    
    # Check for undefined variables
    undefined = meta.find_undeclared_variables(ast)
    # Ansible allows this but warns
    
    return ast
```

### 6.2 Salt Template Introspection

Salt State files use Jinja2 and extract metadata:

```python
# From salt/template.py
def get_template_context(template):
    """Extract required context variables from template."""
    env = Environment()
    ast = env.parse(template)
    
    variables = meta.find_undeclared_variables(ast)
    
    # Salt provides these automatically
    builtin_vars = {'grains', 'pillar', 'salt', 'opts'}
    
    # User must provide these
    required_vars = variables - builtin_vars
    
    return required_vars
```

---

## 7. Answering Your Key Question

### Can We Extract "This Template Generates a Class with Suffix 'Worker'"?

**Short Answer:** Not perfectly, but we can get close.

#### Approach 1: Regex on Template Source

```python
def analyze_worker_template(template_path: str) -> Dict:
    """Extract worker template patterns."""
    with open(template_path) as f:
        source = f.read()
    
    result = {
        'class_suffix': None,
        'class_name_variable': None,
        'methods': [],
        'base_class': None
    }
    
    # Find class definition pattern
    # Pattern: class {{variable}}Suffix(Base):
    class_pattern = r'class\s+\{\{\s*(\w+)\s*\}\}(\w+)\('
    match = re.search(class_pattern, source)
    if match:
        result['class_name_variable'] = match.group(1)  # e.g., 'name'
        result['class_suffix'] = match.group(2)  # e.g., 'Worker'
    
    # Find methods
    method_pattern = r'def\s+(\w+)\s*\('
    result['methods'] = re.findall(method_pattern, source)
    
    return result

# Usage
info = analyze_worker_template('worker.py.jinja2')
# {
#   'class_suffix': 'Worker',
#   'class_name_variable': 'name',
#   'methods': ['__init__', 'execute', 'validate']
# }
```

#### Approach 2: Mock Rendering

```python
def analyze_with_mock_render(template_path: str) -> Dict:
    """Render template with mock data and analyze output."""
    env = Environment(loader=FileSystemLoader('.'))
    template = env.get_template(template_path)
    
    # Provide mock values
    mock_context = {
        'name': 'TEST',
        'input_dto': 'MockInput',
        'output_dto': 'MockOutput',
        'dependencies': []
    }
    
    try:
        output = template.render(**mock_context)
    except Exception as e:
        return {'error': str(e)}
    
    # Parse rendered Python code
    import ast as python_ast
    tree = python_ast.parse(output)
    
    result = {
        'classes': [],
        'methods': {},
        'imports': []
    }
    
    for node in tree.body:
        if isinstance(node, python_ast.ClassDef):
            result['classes'].append(node.name)
            result['methods'][node.name] = [
                f.name for f in node.body 
                if isinstance(f, python_ast.FunctionDef)
            ]
        elif isinstance(node, python_ast.Import):
            result['imports'].extend([alias.name for alias in node.names])
        elif isinstance(node, python_ast.ImportFrom):
            result['imports'].append(f"{node.module}.{node.names[0].name}")
    
    return result

# Usage
info = analyze_with_mock_render('worker.py.jinja2')
# {
#   'classes': ['TESTWorker'],
#   'methods': {'TESTWorker': ['__init__', 'execute']},
#   'imports': ['BaseWorker', 'IStrategyCache', ...]
# }

# Extract pattern
if info['classes']:
    class_name = info['classes'][0]
    if class_name.endswith('Worker'):
        suffix = 'Worker'
        name_part = class_name[:-len(suffix)]
        # Now we know: template adds 'Worker' suffix to {{name}}
```

#### Approach 3: Combined Static + Dynamic

```python
class TemplateAnalyzer:
    """Comprehensive template analysis."""
    
    def __init__(self, template_path: str):
        self.template_path = template_path
        with open(template_path) as f:
            self.source = f.read()
        self.env = Environment()
        self.ast = self.env.parse(self.source)
    
    def get_static_analysis(self) -> Dict:
        """What we can know without rendering."""
        return {
            'variables': meta.find_undeclared_variables(self.ast),
            'templates': list(meta.find_referenced_templates(self.ast)),
            'has_class_def': 'class ' in self.source,
            'has_method_execute': 'def execute' in self.source,
            'source_patterns': self._extract_source_patterns()
        }
    
    def _extract_source_patterns(self) -> Dict:
        """Regex patterns from source."""
        patterns = {}
        
        # Class name pattern
        class_match = re.search(
            r'class\s+\{\{\s*(\w+)\s*\}\}(\w*)\s*\(',
            self.source
        )
        if class_match:
            patterns['class_variable'] = class_match.group(1)
            patterns['class_suffix'] = class_match.group(2)
        
        # Method names (static)
        patterns['static_methods'] = re.findall(
            r'def\s+(\w+)\s*\(',
            self.source
        )
        
        return patterns
    
    def get_dynamic_analysis(self, mock_context: Dict) -> Dict:
        """What we can know by rendering with mock data."""
        template = self.env.from_string(self.source)
        output = template.render(**mock_context)
        
        # Parse rendered Python
        import ast as python_ast
        tree = python_ast.parse(output)
        
        return {
            'rendered_classes': [
                node.name for node in tree.body 
                if isinstance(node, python_ast.ClassDef)
            ],
            'rendered_methods': {
                node.name: [f.name for f in node.body if isinstance(f, python_ast.FunctionDef)]
                for node in tree.body 
                if isinstance(node, python_ast.ClassDef)
            }
        }
    
    def validate_output(self, generated_code: str) -> List[str]:
        """Validate generated code against template expectations."""
        errors = []
        
        # Get expectations
        static = self.get_static_analysis()
        
        # Parse generated code
        import ast as python_ast
        try:
            tree = python_ast.parse(generated_code)
        except SyntaxError as e:
            return [f"Invalid Python syntax: {e}"]
        
        # Check class exists
        classes = [n for n in tree.body if isinstance(n, python_ast.ClassDef)]
        if not classes:
            errors.append("Missing class definition")
            return errors
        
        # Check class name suffix
        if static['source_patterns'].get('class_suffix'):
            expected_suffix = static['source_patterns']['class_suffix']
            actual_name = classes[0].name
            if not actual_name.endswith(expected_suffix):
                errors.append(
                    f"Class name '{actual_name}' should end with '{expected_suffix}'"
                )
        
        # Check methods
        actual_methods = [f.name for f in classes[0].body if isinstance(f, python_ast.FunctionDef)]
        expected_methods = static['source_patterns'].get('static_methods', [])
        
        for expected in expected_methods:
            if expected not in actual_methods:
                errors.append(f"Missing method: {expected}")
        
        return errors
```

---

## 8. Recommendations for Your Project

### 8.1 Template Metadata Strategy

**Option 1: Structured Comments (Recommended)**

Add metadata block at top of each template:

```jinja
{# TEMPLATE_METADATA
category: worker
output_class_pattern: "{{name}}Worker"
output_class_suffix: "Worker"
required_methods: [execute, validate]
required_variables: [name, input_dto, output_dto, dependencies]
base_class: "BaseWorker[{{input_dto}}, {{output_dto}}]"
layer: Workers
END_METADATA #}

class {{name}}Worker(BaseWorker[{{input_dto}}, {{output_dto}}]):
    def execute(self): pass
    def validate(self): pass
```

**Option 2: Separate Metadata Files**

Create `worker.py.jinja2.meta` file:

```yaml
template: worker.py.jinja2
category: worker
output:
  class_pattern: "{{name}}Worker"
  class_suffix: Worker
  methods:
    - execute
    - validate
  base_class: "BaseWorker[{{input_dto}}, {{output_dto}}]"
requires:
  variables:
    - name
    - input_dto
    - output_dto
    - dependencies
layer: Workers
```

### 8.2 Validation Workflow

```python
class TemplateValidator:
    """Validate templates and generated code."""
    
    def __init__(self, template_dir: Path):
        self.template_dir = template_dir
    
    def validate_template_structure(self, template_path: Path) -> List[str]:
        """Validate template has required structure."""
        errors = []
        
        # 1. Parse metadata
        metadata = self._parse_metadata(template_path)
        
        # 2. Static AST analysis
        with open(template_path) as f:
            source = f.read()
        
        env = Environment()
        ast = env.parse(source)
        
        # 3. Check required variables
        actual_vars = meta.find_undeclared_variables(ast)
        required_vars = set(metadata.get('requires', {}).get('variables', []))
        
        missing = required_vars - actual_vars
        if missing:
            errors.append(f"Template missing variables: {missing}")
        
        # 4. Check output patterns
        if 'output' in metadata:
            output = metadata['output']
            
            # Check class suffix in source
            if 'class_suffix' in output:
                suffix = output['class_suffix']
                if f'}}{suffix}(' not in source:
                    errors.append(f"Template should generate class with suffix '{suffix}'")
            
            # Check methods in source
            if 'methods' in output:
                for method in output['methods']:
                    if f'def {method}(' not in source:
                        errors.append(f"Template missing method: {method}")
        
        return errors
    
    def validate_generated_code(
        self, 
        template_path: Path, 
        generated_code: str,
        context: Dict[str, Any]
    ) -> List[str]:
        """Validate generated code matches template + context."""
        errors = []
        
        # 1. Load metadata
        metadata = self._parse_metadata(template_path)
        
        # 2. Parse generated code
        import ast as python_ast
        try:
            tree = python_ast.parse(generated_code)
        except SyntaxError as e:
            return [f"Invalid Python: {e}"]
        
        # 3. Check class exists
        classes = [n for n in tree.body if isinstance(n, python_ast.ClassDef)]
        if not classes:
            errors.append("No class definition found")
            return errors
        
        actual_class = classes[0]
        
        # 4. Validate class name pattern
        if 'output' in metadata and 'class_pattern' in metadata['output']:
            pattern = metadata['output']['class_pattern']
            # Simple template substitution
            expected_name = pattern.replace('{{name}}', context.get('name', ''))
            if actual_class.name != expected_name:
                errors.append(
                    f"Expected class name '{expected_name}', got '{actual_class.name}'"
                )
        
        # 5. Validate methods
        if 'output' in metadata and 'methods' in metadata['output']:
            actual_methods = [
                f.name for f in actual_class.body 
                if isinstance(f, python_ast.FunctionDef)
            ]
            expected_methods = metadata['output']['methods']
            
            for method in expected_methods:
                if method not in actual_methods:
                    errors.append(f"Missing method: {method}")
        
        return errors
    
    def _parse_metadata(self, template_path: Path) -> Dict:
        """Extract metadata from template."""
        with open(template_path) as f:
            source = f.read()
        
        # Look for metadata block
        pattern = r'\{#\s*TEMPLATE_METADATA\s*(.*?)\s*END_METADATA\s*#\}'
        match = re.search(pattern, source, re.DOTALL)
        
        if not match:
            return {}
        
        meta_text = match.group(1)
        
        # Simple YAML-like parser
        metadata = {}
        current_key = None
        
        for line in meta_text.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            if ':' in line and not line.startswith('-'):
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()
                
                if value.startswith('['):
                    # List value
                    metadata[key] = eval(value)
                elif value.startswith('"'):
                    # String value
                    metadata[key] = value.strip('"')
                else:
                    metadata[key] = value
                
                current_key = key
        
        return metadata
```

### 8.3 Usage Example

```python
# Setup
validator = TemplateValidator(Path("mcp_server/templates/components"))

# 1. Validate template structure
errors = validator.validate_template_structure(
    Path("mcp_server/templates/components/worker.py.jinja2")
)
if errors:
    print("Template validation errors:", errors)

# 2. Validate generated code
context = {
    'name': 'SignalDetector',
    'input_dto': 'TickDTO',
    'output_dto': 'SignalDTO',
    'dependencies': []
}

with open("generated_worker.py") as f:
    generated_code = f.read()

errors = validator.validate_generated_code(
    Path("mcp_server/templates/components/worker.py.jinja2"),
    generated_code,
    context
)
if errors:
    print("Generated code validation errors:", errors)
```

---

## 9. Complete Working Example

Here's a full implementation you can use:

```python
# File: mcp_server/scaffolding/template_analyzer.py

from pathlib import Path
from typing import Dict, Set, List, Any
from jinja2 import Environment, FileSystemLoader, meta
from jinja2.nodes import Node
import re
import ast as python_ast


class TemplateAnalyzer:
    """Analyze Jinja2 templates without rendering.
    
    Extracts:
    - Required variables
    - Output patterns (class names, methods)
    - Template dependencies
    - Validation rules
    """
    
    def __init__(self, template_path: Path):
        self.template_path = template_path
        self.env = Environment(
            loader=FileSystemLoader(template_path.parent)
        )
        
        with open(template_path, 'r', encoding='utf-8') as f:
            self.source = f.read()
        
        self.ast = self.env.parse(self.source)
    
    def analyze(self) -> Dict[str, Any]:
        """Comprehensive template analysis."""
        return {
            'metadata': self.extract_metadata(),
            'variables': self.extract_variables(),
            'structure': self.analyze_structure(),
            'patterns': self.extract_patterns(),
            'validation_rules': self.build_validation_rules()
        }
    
    def extract_metadata(self) -> Dict[str, Any]:
        """Extract metadata from template comments."""
        pattern = r'\{#\s*@(\w+):\s*(.+?)\s*#\}'
        matches = re.findall(pattern, self.source)
        
        metadata = {}
        for key, value in matches:
            # Parse value
            value = value.strip()
            if value.startswith('[') and value.endswith(']'):
                # List
                metadata[key] = [
                    v.strip().strip('"').strip("'") 
                    for v in value[1:-1].split(',')
                ]
            else:
                metadata[key] = value.strip('"').strip("'")
        
        return metadata
    
    def extract_variables(self) -> Set[str]:
        """Extract all variables template expects."""
        return meta.find_undeclared_variables(self.ast)
    
    def analyze_structure(self) -> Dict[str, Any]:
        """Analyze template structure."""
        structure = {
            'blocks': [],
            'macros': [],
            'filters': set(),
            'loops': [],
            'conditionals': 0,
            'imports': [],
            'extends': None
        }
        
        # Traverse AST
        for node in self.ast.find_all(Node):
            node_type = type(node).__name__
            
            if node_type == 'Block':
                structure['blocks'].append(node.name)
            elif node_type == 'Macro':
                structure['macros'].append({
                    'name': node.name,
                    'args': [arg.name for arg in node.args]
                })
            elif node_type == 'Filter':
                structure['filters'].add(node.name)
            elif node_type == 'For':
                structure['loops'].append({
                    'target': getattr(node.target, 'name', str(node.target)),
                    'lineno': node.lineno
                })
            elif node_type == 'If':
                structure['conditionals'] += 1
            elif node_type == 'FromImport':
                structure['imports'].append({
                    'template': getattr(node.template, 'value', str(node.template)),
                    'names': node.names
                })
            elif node_type == 'Extends':
                structure['extends'] = getattr(node.template, 'value', str(node.template))
        
        # Convert set to list for JSON serialization
        structure['filters'] = sorted(list(structure['filters']))
        
        return structure
    
    def extract_patterns(self) -> Dict[str, Any]:
        """Extract output patterns from template."""
        patterns = {
            'class_name_pattern': None,
            'class_suffix': None,
            'class_variable': None,
            'methods': [],
            'base_class_pattern': None,
            'imports_pattern': []
        }
        
        # Class definition pattern
        class_match = re.search(
            r'class\s+\{\{\s*(\w+)\s*\}\}(\w*)\s*\(([^)]*)\)',
            self.source
        )
        if class_match:
            patterns['class_variable'] = class_match.group(1)
            patterns['class_suffix'] = class_match.group(2)
            patterns['base_class_pattern'] = class_match.group(3)
            patterns['class_name_pattern'] = f"{{{{{class_match.group(1)}}}}}{class_match.group(2)}"
        
        # Method definitions (static)
        method_matches = re.findall(r'def\s+(\w+)\s*\(', self.source)
        patterns['methods'] = list(set(method_matches))  # Deduplicate
        
        # Import patterns
        import_matches = re.findall(
            r'from\s+([\w.]+)\s+import\s+(\w+)',
            self.source
        )
        patterns['imports_pattern'] = [
            f"{module}.{name}" for module, name in import_matches
        ]
        
        return patterns
    
    def build_validation_rules(self) -> Dict[str, Any]:
        """Build validation rules from analysis."""
        patterns = self.extract_patterns()
        variables = self.extract_variables()
        
        return {
            'required_variables': sorted(list(variables)),
            'output_class_suffix': patterns.get('class_suffix'),
            'output_class_variable': patterns.get('class_variable'),
            'required_methods': patterns.get('methods', []),
            'base_class_pattern': patterns.get('base_class_pattern')
        }
    
    def validate_generated_code(
        self, 
        generated_code: str,
        context: Dict[str, Any]
    ) -> List[str]:
        """Validate generated code against template patterns."""
        errors = []
        
        # Parse generated code
        try:
            tree = python_ast.parse(generated_code)
        except SyntaxError as e:
            return [f"Invalid Python syntax: {e}"]
        
        # Get patterns
        patterns = self.extract_patterns()
        
        # Find class
        classes = [n for n in tree.body if isinstance(n, python_ast.ClassDef)]
        if not classes:
            errors.append("No class definition found in generated code")
            return errors
        
        actual_class = classes[0]
        
        # Validate class name
        if patterns['class_suffix'] and patterns['class_variable']:
            expected_suffix = patterns['class_suffix']
            if not actual_class.name.endswith(expected_suffix):
                errors.append(
                    f"Class name '{actual_class.name}' should end with '{expected_suffix}'"
                )
            
            # Check variable was used
            var_value = context.get(patterns['class_variable'])
            if var_value and not actual_class.name.startswith(var_value):
                errors.append(
                    f"Class name should start with '{var_value}' (from {{{{{{patterns['class_variable']}}}}}})"
                )
        
        # Validate methods
        actual_methods = [
            f.name for f in actual_class.body 
            if isinstance(f, python_ast.FunctionDef)
        ]
        
        for expected_method in patterns.get('methods', []):
            if expected_method not in actual_methods:
                errors.append(f"Missing method: {expected_method}")
        
        return errors


# Usage example
if __name__ == '__main__':
    analyzer = TemplateAnalyzer(
        Path("mcp_server/templates/components/worker.py.jinja2")
    )
    
    analysis = analyzer.analyze()
    
    print("=== TEMPLATE ANALYSIS ===")
    print(f"\nRequired Variables: {analysis['variables']}")
    print(f"\nOutput Pattern:")
    print(f"  Class: {analysis['patterns']['class_name_pattern']}")
    print(f"  Methods: {analysis['patterns']['methods']}")
    print(f"\nValidation Rules:")
    for key, value in analysis['validation_rules'].items():
        print(f"  {key}: {value}")
    
    # Validate generated code
    context = {
        'name': 'TestWorker',
        'input_dto': 'InputDTO',
        'output_dto': 'OutputDTO'
    }
    
    generated = '''
class TestWorkerWorker(BaseWorker):
    def execute(self): pass
    '''
    
    errors = analyzer.validate_generated_code(generated, context)
    if errors:
        print("\nValidation Errors:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("\n✓ Generated code is valid!")
```

---

## 10. Conclusion & Next Steps

### Summary of Findings

1. **Jinja2 provides robust AST introspection** via `Environment.parse()` and `jinja2.meta`

2. **Static analysis is powerful** but has limitations:
   - Can extract variables, structure, references
   - Cannot determine final output without rendering
   - Dynamic content requires runtime evaluation

3. **Best approach is hybrid**:
   - Static AST analysis for structure
   - Regex on source for patterns
   - Mock rendering for output validation
   - Metadata for explicit contracts

### Recommended Implementation

For your SimpleTraderV3 project:

1. **Add metadata comments** to all templates:
   ```jinja
   {# @output_class_suffix: Worker #}
   {# @required_methods: [execute, validate] #}
   ```

2. **Create TemplateAnalyzer** class (see section 9)

3. **Build validation workflow**:
   - Template creation: Validate structure
   - Code generation: Validate output
   - Tests: Validate mock rendering

4. **Document patterns** in template docstrings

### Future Enhancements

- **Template linting**: Check for common mistakes
- **Auto-generate validation rules**: From template metadata
- **Visual template explorer**: Show AST graphically
- **Template testing framework**: Unit tests for templates

---

## References

- [Jinja2 API Documentation](https://jinja.palletsprojects.com/en/3.1.x/api/)
- [Jinja2 Extensions Guide](https://jinja.palletsprojects.com/en/3.1.x/extensions/)
- [Ansible Template Module](https://github.com/ansible/ansible/blob/devel/lib/ansible/plugins/action/template.py)
- [Salt Template Engine](https://github.com/saltstack/salt/blob/master/salt/utils/templates.py)

