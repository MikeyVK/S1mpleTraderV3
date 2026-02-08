<!-- docs/development/issue121/design.md -->
<!-- template=design version=5827e841 created=2026-02-08 updated= -->
# Content-aware editing: segment-based editing met automatische indentation

**Status:** DRAFT  
**Version:** 1.0  
**Last Updated:** 2026-02-08

---

## Scope

**In Scope:**
['SegmentEdit API design (Pydantic models)', 'Indentation preservation algorithm', 'Markdown segment detection (heading-based)', 'Python segment detection (AST-based)', 'Template block detection (Issue #120 integration)', 'Integration met safe_edit_tool', 'Validation rules']

**Out of Scope:**
['Character offset editing (Deeltaak 2 - SKIP per research.md)', 'Non-Python language support', 'Multi-file segment edits', 'Segment renaming', 'Segment deletion (apart van editing)']

## Prerequisites

Read these first:
1. Issue #120 TemplateIntrospector (COMPLETE)
2. ScaffoldMetadataParser (COMPLETE)
3. safe_edit_tool base implementation (COMPLETE)
---

## 1. Context & Requirements

### 1.1. Problem Statement

Huidige edit tools (line-based en pattern matching) zijn te fragiel voor agents. Agents worstelen met exacte line numbers en string matches. Issue #54 documenteert deze fragility. VS Code native tools hebben hetzelfde probleem. Agents hebben een intelligentere edit interface nodig die werkt met semantische code units (functies, classes, markdown secties) in plaats van low-level primitives.

### 1.2. Requirements

**Functional:**
- [ ] Edit markdown secties by heading name (## Section Title)
- [ ] Edit Python functies/methodes by naam (edit_function, MyClass.my_method)
- [ ] Edit template blocks by naam uit Issue #120 metadata
- [ ] Automatische indentation preservation zonder agent awareness
- [ ] Validatie van segment edits met pylint/mypy
- [ ] Graceful degradation als template metadata ontbreekt

**Non-Functional:**
- [ ] Agent hoeft geen line numbers te kennen
- [ ] Agent hoeft geen exacte string patterns te matchen
- [ ] Agent hoeft geen indentation te managen
- [ ] Tool moet garanties geven voor correcte indentation
- [ ] Extendable naar andere segment types (future)
- [ ] Performance: segment detectie binnen 100ms voor files tot 5000 lines

### 1.3. Constraints

['Moet compatible blijven met bestaande safe_edit_tool modes', 'Indentation detection moet tabs vs spaces onderscheid maken', 'Template block detection afhankelijk van Issue #120 completion', 'Performance: <100ms voor files tot 5000 lines']

### 1.4. Risks & Dependencies

**Risk 1: Template Introspection Fragility (DEFERRED to Issue #72)**

During research for Issue #121, critical fragility was discovered in template introspection algorithm (`_classify_variables()`):
- **71 templates analyzed**
- **40% false positive rate** (80-120 variables misclassified as required when optional)
- **7 undetected edge case categories** (for loops, nested fields, "is defined" checks, etc.)

**📄 Complete Analysis:** [Issue #72: template-introspection-classification-fragility.md](../issue72/template-introspection-classification-fragility.md)

**Impact on Issue #121:** ✅ **NOT A BLOCKER**

Template block detection is **OPTIONAL** for Issue #121. Segment-based editing works independently using:
1. **Python AST detection** (primary) - function/method/class names
2. **Markdown regex detection** (primary) - heading-based sections
3. **Template block detection** (optional bonus) - only if metadata available

**Mitigation Strategy:**

```
IF template metadata exists AND introspection succeeds:
    Use template block names for prettier agent messages
ELSE:
    Fall back to Python AST / Markdown regex (always works)
```

**Agent Experience:**
- ✅ **With template blocks:** "Editing method_process in Worker template"
- ✅ **Without template blocks:** "Editing MyWorker.process method"
- ❌ **NEVER:** "Template introspection failed" (invisible to agent)

**Decision:** Template block detection is a "nice-to-have" optimization, not a requirement. Issue #121 MVP proceeds with Python AST + Markdown regex. Template introspection fixes tracked in Issue #72 (estimated 2.5-3 days effort).

---

**Risk 2: Indentation Detection Edge Cases**
---

## 2. Design Options

### 2.1. Option A: Optie A: Extend safe_edit_tool met 5e mode



**Pros:**
- ✅ Hergebruik bestaande validatie
- ✅ Consistency met huidige tools
- ✅ Backwards compatible

**Cons:**
- ❌ Meer complexity in één tool

### 2.2. Option B: Optie B: Nieuwe dedicated segment_edit_tool



**Pros:**
- ✅ Cleaner separation
- ✅ Dedicated focus

**Cons:**
- ❌ Duplicatie van validatie logic
- ❌ Meer tools om te onderhouden
---

## 3. Chosen Design

**Decision:** Extend safe_edit_tool met 5e mode 'segment_edit' (Optie A). Segment detection gebeurt in dedicated detectoren (MarkdownSegmentDetector, PythonSegmentDetector, TemplateBlockDetector). Indentation preservation via 3-step strategie (detect-normalize-apply) geïntegreerd in segment edit logic.

**Rationale:** Optie A gekozen omdat: (1) alle validatie/diff logic al bestaat, (2) consistency met bestaande tools verhoogt developer experience, (3) backwards compatible met huidige workflows, (4) minder code duplication. Indentation auto-detection gekozen omdat agents niet betrouwbaar zijn met indentation management - tool moet deze verantwoordelijkheid nemen.

### 3.1. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Segment detection via dedicated detector classes | Separation of concerns, testability, extendability voor nieuwe segment types |
| Indentation preservation via auto-detection | Agent moet zich geen zorgen maken over indentation - tool neemt verantwoordelijkheid |
| Template blocks als primary, markdown/python als fallback | Graceful degradation: gebruik structuur metadata als beschikbaar, val terug op content detection |
| AST-based Python detection | Robuust tegen formatting variaties, detecteert nested structures correct |
| Regex-based Markdown detection | Performance: sneller dan parsing, voldoende voor heading detection |
| Reuse LineEdit conversion | Backwards compatibility: segment edit converteert naar line edits intern |

## Related Documentation
- **[docs/development/issue121/research.md][related-1]**
- **[docs/development/issue121/feasibility-analysis.md][related-2]**
- **[docs/reference/issue-54-pattern-matching-fragility.md][related-3]**

<!-- Link definitions -->

[related-1]: docs/development/issue121/research.md
[related-2]: docs/development/issue121/feasibility-analysis.md
[related-3]: docs/reference/issue-54-pattern-matching-fragility.md

---

## 4. Architecture Overview

### 4.1. Component Structure

```
safe_edit_tool.py
├── SafeEditInput (Pydantic model)
│   ├── content: str | None          # Mode 1: Full rewrite
│   ├── line_edits: list[LineEdit]   # Mode 2: Line-based
│   ├── insert_lines: list[InsertLine] # Mode 3: Insert
│   ├── search/replace: str          # Mode 4: Pattern matching
│   └── segment_edit: SegmentEdit    # Mode 5: NEW - Segment-based
│
├── SegmentEdit (Pydantic model)
│   ├── segment_type: SegmentType (enum: markdown_section, python_function, python_method, template_block)
│   ├── segment_name: str            # e.g. "## Introduction", "calculate_risk", "MyClass.process"
│   ├── new_content: str             # Replacement content (indentation-agnostic)
│   ├── indentation_strategy: IndentationStrategy (enum: AUTO, PRESERVE_AGENT, EXPLICIT)
│   └── explicit_indent: int | None  # Only for EXPLICIT strategy
│
└── Segment Detectors (dedicated classes)
    ├── MarkdownSegmentDetector
    │   └── detect_sections(content) -> dict[str, MarkdownSection]
    ├── PythonSegmentDetector
    │   └── detect_segments(content) -> dict[str, PythonSegment]
    └── TemplateBlockDetector
        └── detect_blocks(content, path) -> dict[str, TemplateBlock]
```

### 4.2. Data Flow

```
Agent Request
    ↓
SegmentEdit(segment_type="python_method", segment_name="Worker.process", new_content="...")
    ↓
Segment Detector (gebaseerd op segment_type)
    ↓
Locate segment in file → (start_line, end_line, original_indentation)
    ↓
Indentation Preservation Pipeline
    ├── 1. Detect base indentation (original_indentation)
    ├── 2. Normalize new_content (strip agent's indentation)
    └── 3. Apply original indentation (add prefix to all lines)
    ↓
Convert to LineEdit(start_line, end_line, normalized_content)
    ↓
Existing safe_edit_tool validation & application
    ↓
File written with correct indentation
```

---

## 5. API Specification

### 5.1. SegmentEdit Model

```python
from pydantic import BaseModel, Field, model_validator
from enum import Enum

class SegmentType(str, Enum):
    """Type of code segment to edit."""
    MARKDOWN_SECTION = "markdown_section"
    PYTHON_FUNCTION = "python_function"
    PYTHON_METHOD = "python_method"
    PYTHON_CLASS = "python_class"
    TEMPLATE_BLOCK = "template_block"

class IndentationStrategy(str, Enum):
    """Strategy for handling indentation."""
    AUTO = "auto"              # Detect from original segment (default)
    PRESERVE_AGENT = "preserve_agent"  # Keep agent's indentation
    EXPLICIT = "explicit"      # Use explicit_indent value

class SegmentEdit(BaseModel):
    """Segment-based edit operation."""
    
    segment_type: SegmentType = Field(
        ...,
        description="Type of segment to edit (markdown_section, python_function, etc.)"
    )
    
    segment_name: str = Field(
        ...,
        description="Name/identifier of segment. Examples: '## Introduction', 'calculate_risk', 'Worker.process'"
    )
    
    new_content: str = Field(
        ...,
        description="Replacement content. Write at indentation level 0 - tool will adjust automatically."
    )
    
    indentation_strategy: IndentationStrategy = Field(
        default=IndentationStrategy.AUTO,
        description="How to handle indentation. AUTO (recommended): detect from original segment."
    )
    
    explicit_indent: int | None = Field(
        default=None,
        description="Explicit indentation in spaces. Only used when indentation_strategy=EXPLICIT."
    )
    
    @model_validator(mode="after")
    def validate_explicit_indent(self):
        """Validate that explicit_indent is provided when strategy is EXPLICIT."""
        if self.indentation_strategy == IndentationStrategy.EXPLICIT:
            if self.explicit_indent is None:
                raise ValueError("explicit_indent required when indentation_strategy=EXPLICIT")
        return self
```

### 5.2. Segment Detector Interface

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class SegmentLocation:
    """Location of a detected segment in file."""
    name: str               # Segment identifier
    start_line: int         # 1-based start line
    end_line: int           # 1-based end line (inclusive)
    base_indentation: int   # Number of leading spaces
    content: str            # Original segment content

class SegmentDetector(ABC):
    """Abstract base for segment detectors."""
    
    @abstractmethod
    def detect(self, content: str, file_path: str | None = None) -> dict[str, SegmentLocation]:
        """
        Detect all segments in content.
        
        Returns:
            Dict mapping segment names to their locations.
            Keys are user-facing identifiers (e.g., "## Introduction", "Worker.process").
        """
        pass
```

### 5.3. Usage Examples

**Example 1: Edit Python method**
```python
segment_edit = SegmentEdit(
    segment_type=SegmentType.PYTHON_METHOD,
    segment_name="Worker.process",
    new_content="""
async def process(self, data: dict) -> Result:
    # New implementation
    validated = self.validate(data)
    return await self.execute(validated)
"""
)
# Tool detects method is indented 4 spaces (inside class)
# Automatically applies 4-space indent to all lines of new_content
```

**Example 2: Edit markdown section**
```python
segment_edit = SegmentEdit(
    segment_type=SegmentType.MARKDOWN_SECTION,
    segment_name="## Installation",
    new_content="""
## Installation

Install via pip:
```bash
pip install simple-trader
```
"""
)
# Markdown sections start at indentation 0
# Tool preserves this
```

**Example 3: Edit template block**
```python
segment_edit = SegmentEdit(
    segment_type=SegmentType.TEMPLATE_BLOCK,
    segment_name="payload_models",  # Block name from template metadata
    new_content="""
@dataclass
class RequestPayload:
    symbol: str
    quantity: int
"""
)
# Tool uses template metadata to locate block
# Falls back to Python detection if metadata missing
```

---

## 6. Indentation Preservation Algorithm

### 6.1. Design Rationale

**Problem:** Agents consistently struggle with indentation management. When editing a method inside a class, agents often provide code at indentation level 0, expecting the tool to apply the correct level (4 spaces). This is error-prone and cognitive overhead for the agent.

**Solution:** Tool takes full responsibility for indentation. Agent writes code at level 0, tool auto-detects and applies correct indentation.

**Guarantee:** Agent can forget about indentation completely. Tool ensures correctness.

### 6.2. Algorithm Steps

```python
def _apply_segment_edit(file_path: str, segment: SegmentEdit) -> str:
    """Apply segment edit with automatic indentation preservation."""
    
    # Step 1: Detect segment location
    detector = _get_detector(segment.segment_type)
    segments = detector.detect(file_content, file_path)
    
    if segment.segment_name not in segments:
        raise SegmentNotFoundError(f"Segment '{segment.segment_name}' not found")
    
    location = segments[segment.segment_name]
    
    # Step 2: Determine target indentation
    if segment.indentation_strategy == IndentationStrategy.AUTO:
        target_indent = location.base_indentation
    elif segment.indentation_strategy == IndentationStrategy.PRESERVE_AGENT:
        target_indent = _detect_base_indentation(segment.new_content.splitlines())
    else:  # EXPLICIT
        target_indent = segment.explicit_indent
    
    # Step 3: Normalize new content (strip agent's indentation)
    normalized_lines = _strip_indentation(
        segment.new_content.splitlines(),
        _detect_base_indentation(segment.new_content.splitlines())
    )
    
    # Step 4: Apply target indentation
    indented_lines = _apply_indentation(normalized_lines, target_indent)
    
    # Step 5: Convert to LineEdit and apply
    line_edit = LineEdit(
        start_line=location.start_line,
        end_line=location.end_line,
        new_content="\n".join(indented_lines)
    )
    
    return _apply_line_edit(file_path, line_edit)
```

### 6.3. Helper Functions

```python
def _detect_base_indentation(lines: list[str]) -> int:
    """
    Detect base indentation level of code block.
    
    Returns:
        Number of leading spaces in first non-empty, non-comment line.
    """
    for line in lines:
        stripped = line.lstrip()
        if stripped and not stripped.startswith("#"):
            return len(line) - len(stripped)
    return 0

def _strip_indentation(lines: list[str], indent: int) -> list[str]:
    """
    Remove indentation prefix from all lines.
    
    Args:
        lines: Lines to process
        indent: Number of spaces to remove from each line
    
    Returns:
        Lines with indentation removed
    """
    result = []
    prefix = " " * indent
    
    for line in lines:
        if line.startswith(prefix):
            result.append(line[indent:])
        elif line.strip() == "":  # Empty line
            result.append("")
        else:
            # Line has less indentation than expected - keep as-is
            result.append(line.lstrip())
    
    return result

def _apply_indentation(lines: list[str], indent: int) -> list[str]:
    """
    Add indentation prefix to all non-empty lines.
    
    Args:
        lines: Lines to process
        indent: Number of spaces to add to each line
    
    Returns:
        Lines with indentation applied
    """
    prefix = " " * indent
    result = []
    
    for line in lines:
        if line.strip() == "":  # Empty line - keep as-is
            result.append("")
        else:
            result.append(prefix + line)
    
    return result
```

### 6.4. Indentation Detection Strategies

**For Python segments:**
- Module-level functions: 0 spaces
- Class-level methods: 4 spaces (standard PEP 8)
- Nested functions: Detect from AST node depth
- Use `ast.parse()` to determine exact indentation from context

**For Markdown segments:**
- Always 0 spaces (no indentation in markdown)

**For Template blocks:**
- Use TemplateIntrospector to determine block's indentation
- Falls back to Python/Markdown detection if metadata missing

### 6.5. Validation Rules

**Indentation consistency:**
```python
def _validate_indentation(original: str, new: str, segment_type: SegmentType) -> ValidationResult:
    """Validate indentation correctness after edit."""
    
    # Check 1: No mixed tabs/spaces
    if "\t" in new and " " in new[:new.index("\t") if "\t" in new else len(new)]:
        return ValidationResult(
            valid=False,
            error="Mixed tabs and spaces detected"
        )
    
    # Check 2: Python-specific validation
    if segment_type in [SegmentType.PYTHON_FUNCTION, SegmentType.PYTHON_METHOD]:
        try:
            ast.parse(new)  # Must be valid Python
        except SyntaxError as e:
            return ValidationResult(
                valid=False,
                error=f"Invalid Python syntax: {e}"
            )
    
    # Check 3: Indentation level matches context
    original_indent = _detect_base_indentation(original.splitlines())
    new_indent = _detect_base_indentation(new.splitlines())
    
    if original_indent != new_indent:
        return ValidationResult(
            valid=False,
            error=f"Indentation mismatch: expected {original_indent} spaces, got {new_indent}"
        )
    
    return ValidationResult(valid=True)
```

### 6.6. Edge Cases

| Edge Case | Handling Strategy |
|-----------|------------------|
| Empty lines in segment | Preserve as empty (no indentation added) |
| Trailing newlines | Preserve trailing newline behavior from original |
| Mixed tabs/spaces | Reject edit with validation error |
| Agent provides already-indented code | Strip agent's indentation, apply detected indentation |
| Python docstring indentation | Preserve relative indentation within docstring |
| Nested classes/functions | Use AST to detect correct depth-based indentation |

---

## 7. Segment Detection Implementation

### 7.1. Markdown Segment Detector

**Strategy:** Regex-based heading detection for performance.

```python
import re

class MarkdownSegmentDetector(SegmentDetector):
    """Detect markdown sections by heading."""
    
    HEADING_PATTERN = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)
    
    def detect(self, content: str, file_path: str | None = None) -> dict[str, SegmentLocation]:
        """Detect all markdown sections."""
        segments = {}
        lines = content.splitlines()
        
        matches = list(self.HEADING_PATTERN.finditer(content))
        
        for i, match in enumerate(matches):
            level = len(match.group(1))  # Number of #
            title = match.group(2).strip()
            
            # Calculate line numbers
            start_line = content[:match.start()].count('\n') + 1
            
            # End line is before next heading of same/higher level
            end_line = len(lines)
            for next_match in matches[i+1:]:
                next_level = len(next_match.group(1))
                if next_level <= level:
                    end_line = content[:next_match.start()].count('\n')
                    break
            
            # Segment name includes heading markers for clarity
            segment_name = f"{'#' * level} {title}"
            
            segments[segment_name] = SegmentLocation(
                name=segment_name,
                start_line=start_line,
                end_line=end_line,
                base_indentation=0,  # Markdown has no indentation
                content="\n".join(lines[start_line-1:end_line])
            )
        
        return segments
```

### 7.2. Python Segment Detector

**Strategy:** AST-based parsing for robustness.

```python
import ast

class PythonSegmentDetector(SegmentDetector):
    """Detect Python functions, methods, and classes via AST."""
    
    def detect(self, content: str, file_path: str | None = None) -> dict[str, SegmentLocation]:
        """Detect all Python code segments."""
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return {}  # Not valid Python
        
        segments = {}
        lines = content.splitlines()
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Module-level function
                segment_name = node.name
                segments[segment_name] = self._create_location(node, lines, indent=0)
                
            elif isinstance(node, ast.ClassDef):
                # Class definition
                class_name = node.name
                segments[class_name] = self._create_location(node, lines, indent=0)
                
                # Methods inside class
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        method_name = f"{class_name}.{item.name}"
                        segments[method_name] = self._create_location(item, lines, indent=4)
        
        return segments
    
    def _create_location(self, node: ast.AST, lines: list[str], indent: int) -> SegmentLocation:
        """Create SegmentLocation from AST node."""
        start_line = node.lineno
        end_line = node.end_lineno or start_line
        
        # Extract content
        content_lines = lines[start_line-1:end_line]
        content = "\n".join(content_lines)
        
        # Detect actual indentation (may differ from expected)
        actual_indent = _detect_base_indentation(content_lines)
        
        return SegmentLocation(
            name=node.name if hasattr(node, 'name') else "unknown",
            start_line=start_line,
            end_line=end_line,
            base_indentation=actual_indent,
            content=content
        )
```

### 7.3. Template Block Detector

**Strategy:** Integration with Issue #120 TemplateIntrospector with graceful degradation.

```python
from backend.assembly.introspection import TemplateIntrospector
from mcp_server.scaffolding.template_introspector import introspect_template_with_inheritance

class TemplateBlockDetector(SegmentDetector):
    """Detect template blocks using scaffold metadata.
    
    CRITICAL: Uses introspect_template_with_inheritance() for robustness
    against multi-tier template inheritance classification issues.
    """
    
    def detect(self, content: str, file_path: str) -> dict[str, SegmentLocation]:
        """Detect all template blocks in scaffolded file."""
        if not file_path:
            return {}
        
        try:
            # Use TemplateIntrospector from Issue #120
            # NOTE: Try to extract template metadata from SCAFFOLD header
            inspector = TemplateIntrospector()
            blocks = inspector.get_template_blocks(file_path)
            
            if not blocks:
                # Graceful degradation: fall back to Python/Markdown detection
                logger.info(f"No template blocks found for {file_path}, using fallback detection")
                return {}
            
            segments = {}
            lines = content.splitlines()
            
            for block in blocks:
                segments[block.name] = SegmentLocation(
                    name=block.name,
                    start_line=block.start_line,
                    end_line=block.end_line,
                    base_indentation=block.indentation,
                    content="\n".join(lines[block.start_line-1:block.end_line])
                )
            
            return segments
            
        except Exception as e:
            # CRITICAL: Graceful degradation on ANY introspection failure
            # Common failures:
            # - Template metadata missing (non-scaffolded file)
            # - Template metadata corrupt (invalid SCAFFOLD header)
            # - Introspection classification error (Issue #72 edge cases)
            logger.warning(
                f"Template introspection failed for {file_path}: {e}. "
                "Falling back to Python/Markdown detection."
            )
            return {}
```

**Error Handling Strategy:**

| Error Scenario | Handling | User Impact |
|----------------|----------|-------------|
| No SCAFFOLD header | Return empty dict → Python/Markdown fallback | Agent uses function/section names instead of template block names |
| Corrupt SCAFFOLD metadata | Catch exception → Python/Markdown fallback | Same as above + warning logged |
| Template file not found | Return empty dict → Python/Markdown fallback | Works for non-scaffolded files |
| Introspection classification error | Catch exception → Python/Markdown fallback | Agent oblivious - tool handles gracefully |

**Validation Requirements:**
- Test with scaffolded files (should use template blocks)
- Test with non-scaffolded files (should use Python/Markdown fallback)
- Test with corrupt SCAFFOLD headers (should gracefully degrade)
- Test with multi-tier templates (Issue #72 edge cases)

---

## 8. Integration with safe_edit_tool

### 8.1. SafeEditInput Extension

```python
class SafeEditInput(BaseModel):
    """Extended with 5th mode: segment_edit."""
    
    path: str
    mode: str = "strict"  # or "interactive"
    show_diff: bool = True
    
    # Existing modes (mutually exclusive)
    content: str | None = None
    line_edits: list[LineEdit] | None = None
    insert_lines: list[InsertLine] | None = None
    search: str | None = None
    replace: str | None = None
    
    # NEW: 5th mode
    segment_edit: SegmentEdit | None = None
    
    @model_validator(mode="after")
    def validate_single_mode(self):
        """Ensure exactly one edit mode is specified."""
        modes = [
            self.content, self.line_edits, self.insert_lines,
            (self.search and self.replace), self.segment_edit
        ]
        if sum(m is not None for m in modes) != 1:
            raise ValueError("Exactly one edit mode must be specified")
        return self
```

### 8.2. Tool Execution Flow

```python
def _execute_safe_edit(input: SafeEditInput) -> str:
    """Execute safe edit with segment_edit support."""
    
    # Read current file content
    content = Path(input.path).read_text()
    
    # Route to appropriate handler
    if input.segment_edit:
        new_content = _apply_segment_edit(input.path, content, input.segment_edit)
    elif input.line_edits:
        new_content = _apply_line_edits(content, input.line_edits)
    # ... other modes
    
    # Common validation pipeline
    if input.mode == "strict":
        validation = _validate_code(input.path, new_content)
        if not validation.valid:
            raise ValidationError(validation.error)
    
    # Show diff
    if input.show_diff:
        diff = unified_diff(content.splitlines(), new_content.splitlines())
        print("\n".join(diff))
    
    # Write file
    Path(input.path).write_text(new_content)
    
    return "✅ File edited successfully"
```

---

## 9. Testing Strategy

### 9.1. Unit Tests

**Indentation preservation:**
- Test `_detect_base_indentation()` with various code styles
- Test `_strip_indentation()` with edge cases (empty lines, partial indent)
- Test `_apply_indentation()` with nested structures
- Test validation of mixed tabs/spaces

**Segment detection:**
- Markdown: nested sections, multiple heading levels
- Python: module functions, class methods, nested functions, decorators
- Template blocks: with/without metadata, fallback behavior

**Template introspection robustness (CRITICAL):**
- Test `introspect_template_with_inheritance()` with multi-tier templates (tier0 → concrete)
- Test optional field detection across inheritance chain
- Test import alias filtering (should NOT appear in required fields)
- Test SCAFFOLD header parsing (valid, missing, corrupt)
- Test graceful degradation when introspection fails

### 9.2. Integration Tests

**End-to-end segment editing:**
- Edit method in class → verify indentation preserved (4 spaces)
- Edit module function → verify indentation preserved (0 spaces)
- Edit markdown section → verify structure preserved
- Edit template block → verify metadata consistency

**Error handling:**
- Segment not found → clear error message
- Invalid segment name → suggestions for similar names
- Ambiguous segment name → list all matches
- Invalid Python after edit → syntax error with line number

### 9.3. Performance Tests

- Segment detection on 5000-line file → <100ms
- Multiple segment edits in single file → batching optimization
- Memory usage with large files → streaming if needed
- Template introspection caching → avoid repeated AST parsing

---

## 10. Implementation Effort Estimation

### Core Features (5-8 days total)

| Component | Effort | Priority | Dependencies |
|-----------|--------|----------|--------------|
| Indentation preservation algorithm | 1 day | HIGH | None |
| SegmentEdit API + models | 0.5 day | HIGH | None |
| Markdown segment detector | 0.5 day | MEDIUM | None |
| Python AST segment detector | 1 day | MEDIUM | None |
| Template block detector | 1 day | LOW | Issue #120 (optional) |
| Integration met safe_edit_tool | 1 day | HIGH | Above components |
| Unit tests | 1.5 days | HIGH | Above components |
| Integration tests | 1 day | HIGH | Above components |
| Documentation | 0.5 day | MEDIUM | Above components |

**Note:** Template introspection fixes tracked separately in **Issue #72** (estimated 2.5-3 days). Not a blocker for Issue #121 MVP - template block detection is optional.

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|----------|
| 1.0 | 2026-02-08 | Agent | Initial draft |
| 1.1 | 2026-02-08 | Agent | Added template introspection robustness analysis (Issue #72 dependency) |
| 1.2 | 2026-02-08 | Agent | **CRITICAL:** Comprehensive fragility analysis - 80-120 misclassified variables (40% false positive rate). Analyzed 71 templates, identified 7 undetected edge case categories. Decision: Python AST + Markdown regex as PRIMARY detection, template blocks as optional optimization. |
| 1.3 | 2026-02-08 | Agent | **CLEANUP:** Deferred template introspection work to Issue #72. Removed detailed analysis from this document - now tracked in [Issue #72: template-introspection-classification-fragility.md](../issue72/template-introspection-classification-fragility.md). Issue #121 proceeds independently with Python AST + Markdown regex detection. |

---

## 11. Open Questions

### Segment-Based Editing

1. **Multi-segment edits:** Should we support editing multiple segments in one tool call? (Batch optimization)
2. **Segment renaming:** Should segment_edit also support renaming (e.g., rename method)?
3. **Cross-file segments:** Could template blocks span multiple files? (Out of scope for now)
4. **Fuzzy matching:** If segment name not exact match, should we suggest similar names? (Nice-to-have)

### Template Introspection Robustness

5. **Classification algorithm improvement (Issue #72):**
   - Should `_classify_variables()` analyze ENTIRE inheritance chain, not just concrete template AST?
   - How to handle import aliases (`{% import ... as alias %}`) in undeclared variables?
   - Should we use TEMPLATE_METADATA as SSOT instead of Jinja-meta (DRY principle)?

6. **Fallback detection priority:**
   - When template introspection fails, what order: Template → Python AST → Markdown regex?
   - Should we cache detection results per file to avoid repeated introspection?
   - How to handle hybrid files (Python + Markdown in same file)?

7. **Agent error messages:**
   - When falling back to Python/Markdown detection, should agent be notified?
   - Should error messages explain WHY template blocks couldn't be used?
   - Format: Silent fallback vs informative warning?

8. **Multi-tier template testing:**
   - What test coverage needed for tier0 → tier1 → tier2 → concrete chain?
   - Edge cases: optional fields in base templates, required in concrete?
   - Performance: introspection latency with 4-tier inheritance?

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-08 | Agent | Initial draft |
| 1.1 | 2026-02-08 | Agent | Added template introspection robustness analysis (Issue #72 dependency) |