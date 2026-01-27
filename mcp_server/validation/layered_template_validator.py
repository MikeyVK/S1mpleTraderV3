# mcp_server/validation/layered_template_validator.py
"""
Layered template validator with three-tier enforcement model.

@layer: Validation
@dependencies: [template_analyzer, base]
"""
# Standard library
import re
from pathlib import Path
from typing import Any

# Module imports
from .base import BaseValidator, ValidationIssue, ValidationResult
from .template_analyzer import TemplateAnalyzer


class LayeredTemplateValidator(BaseValidator):  # pylint: disable=too-few-public-methods
    """
    Three-tier template validator enforcing format → architectural → guidelines.

    Tier 1 (Base Template Format): STRICT
        - Import order, docstrings, type hints, file structure
        - Severity: ERROR (blocks save)
        - Source: Base templates (base_component.py, base_document.md)

    Tier 2 (Architectural Rules): STRICT
        - Base class inheritance, required methods, protocol compliance
        - Severity: ERROR (blocks save)
        - Source: Specific templates strict section

    Tier 3 (Guidelines): LOOSE
        - Naming conventions, field ordering, docstring format
        - Severity: WARNING (saves with notification)
        - Source: Specific templates guidelines section
    """

    def __init__(
        self,
        template_type: str,
        template_analyzer: TemplateAnalyzer
    ) -> None:
        """
        Initialize validator for specific template type.

        Args:
            template_type: Template identifier (dto, tool, base_document, etc.)
            template_analyzer: Analyzer for extracting template metadata.
        """
        self.template_type = template_type
        self.analyzer = template_analyzer
        self.metadata = self._load_metadata()

    def _load_metadata(self) -> dict[str, Any]:
        """Load and merge metadata for template type."""
        # Find template file
        template_root = self.analyzer.template_root
        template_paths = list(template_root.rglob(f"*{self.template_type}*.jinja2"))

        if not template_paths:
            return {}

        template_path = template_paths[0]

        # Get inheritance chain and merge metadata
        chain = self.analyzer.get_inheritance_chain(template_path)
        merged: dict[str, Any] = {}

        # Merge from base to specific (reverse order)
        for tmpl_path in reversed(chain):
            tmpl_metadata = self.analyzer.extract_metadata(tmpl_path)
            if tmpl_metadata:
                merged = self.analyzer.merge_metadata(tmpl_metadata, merged)

        return merged

    async def validate(
        self,
        path: str,
        content: str | None = None
    ) -> ValidationResult:
        """
        Validate file against template rules using three-tier model.

        Validation flow:
        1. Validate format rules (base template) - stop on ERROR
        2. Validate architectural rules (specific template) - stop on ERROR
        3. Validate guidelines (all templates) - collect WARNINGs
        4. Return combined result with agent hints

        Args:
            path: File path to validate.
            content: Optional file content (reads from path if None).

        Returns:
            ValidationResult with issues, score, and optional agent hints.
        """
        # Read content if not provided
        if content is None:
            try:
                content = Path(path).read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as e:
                return ValidationResult(
                    passed=False,
                    score=0.0,
                    issues=[
                        ValidationIssue(
                            message=f"Failed to read file: {e}",
                            severity="error"
                        )
                    ]
                )

        # Tier 1: Format validation (base template) - STRICT
        format_issues = self._validate_format(content)
        if format_issues:
            # Fail-fast on format errors
            return self._create_result(format_issues)

        # Tier 2: Architectural validation (specific template) - STRICT
        arch_issues = self._validate_architectural(content)
        if arch_issues:
            # Fail-fast on architectural errors
            return self._create_result(arch_issues)

        # Tier 3: Guidelines validation - LOOSE (collect all warnings)
        guideline_issues = self._validate_guidelines(content)

        # Return combined result
        return self._create_result(guideline_issues)

    def _validate_format(self, content: str) -> list[ValidationIssue]:
        """
        Validate Tier 1: Format rules from base template.

        Checks:
        - Import order (stdlib → third-party → local)
        - Docstring presence
        - Type hints on functions
        - File header/frontmatter

        Returns:
            List of ValidationIssue with severity ERROR.
        """
        issues: list[ValidationIssue] = []
        validates = self.metadata.get("validates", {})
        strict_rules = validates.get("strict", [])

        # Group SCAFFOLD patterns for OR logic (any one must match)
        scaffold_patterns = [r for r in strict_rules if isinstance(r, str) and "SCAFFOLD:" in r]
        other_rules = [r for r in strict_rules if not (isinstance(r, str) and "SCAFFOLD:" in r)]

        # Check SCAFFOLD patterns with OR logic
        if scaffold_patterns:
            import re
            scaffold_found = any(
                re.search(pattern, content, re.MULTILINE)
                for pattern in scaffold_patterns
            )
            if not scaffold_found:
                patterns_list = ', '.join(scaffold_patterns)
                issues.append(ValidationIssue(
                    message=(
                        f"Required SCAFFOLD header not found "
                        f"(expected one of: {patterns_list})"
                    ),
                    code="scaffold_header_missing",
                    severity="error",
                    line=0
                ))

        # Check other rules individually (AND logic)
        for rule in other_rules:
            # Handle both string patterns and dict rules
            if isinstance(rule, str):
                # String pattern - check if content matches
                import re
                if not re.search(rule, content, re.MULTILINE):
                    issues.append(ValidationIssue(
                        message=f"Required pattern not found: {rule}",
                        code="pattern_match",
                        severity="error",
                        line=0
                    ))
            elif isinstance(rule, dict):
                rule_name = rule.get("rule", "")
                if rule_name in ["frontmatter_presence", "separator_structure",
                                 "required_sections", "link_definitions"]:
                    # Format rules for documents
                    issue = self._check_pattern(content, rule)
                    if issue:
                        issues.append(issue)

        return issues

    def _validate_architectural(self, content: str) -> list[ValidationIssue]:
        """
        Validate Tier 2: Architectural rules from specific template.

        Checks (from metadata.validates.strict):
        - Base class inheritance
        - Required methods with signatures
        - Required imports
        - Protocol compliance

        Returns:
            List of ValidationIssue with severity ERROR.
        """
        issues: list[ValidationIssue] = []
        validates = self.metadata.get("validates", {})
        strict_rules = validates.get("strict", [])

        for rule in strict_rules:
            # Skip string patterns (handled in _validate_format)
            if isinstance(rule, str):
                continue

            if isinstance(rule, dict):
                rule_name = rule.get("rule", "")
                if rule_name in ["base_class", "required_properties",
                                 "execute_method", "required_imports",
                                 "frozen_config", "field_validators"]:
                    # Architectural rules for components
                    issue = self._check_pattern(content, rule)
                    if issue:
                        issues.append(issue)

        return issues

    def _validate_guidelines(self, content: str) -> list[ValidationIssue]:
        """
        Validate Tier 3: Guidelines from all templates.

        Checks (from metadata.validates.guidelines):
        - Naming conventions
        - Field/section ordering
        - Docstring format
        - Content type (for documents)

        Returns:
            List of ValidationIssue with severity WARNING.
        """
        issues: list[ValidationIssue] = []
        validates = self.metadata.get("validates", {})
        guideline_rules = validates.get("guidelines", [])

        for rule in guideline_rules:
            # Skip string patterns (for now - guidelines typically use dict format)
            if isinstance(rule, str):
                continue

            if isinstance(rule, dict):
                issue = self._check_pattern(content, rule, severity="warning")
                if issue:
                    issues.append(issue)

        return issues

    def _check_pattern(
        self,
        content: str,
        rule: dict[str, Any],
        severity: str = "error"
    ) -> ValidationIssue | None:
        """
        Check if content matches rule pattern.

        Args:
            content: File content to check.
            rule: Rule dict with pattern and description.
            severity: Issue severity (error or warning).

        Returns:
            ValidationIssue if rule violated, None otherwise.
        """
        pattern = rule.get("pattern")
        if not pattern:
            return None

        if not re.search(pattern, content, re.MULTILINE):
            return ValidationIssue(
                message=f"{rule.get('description', 'Rule violation')}",
                severity=severity
            )

        return None

    def _create_result(
        self,
        issues: list[ValidationIssue]
    ) -> ValidationResult:
        """
        Create ValidationResult from issues.

        Calculates score:
        - 10.0 if no issues
        - 8.0 if only warnings
        - 0.0 if any errors

        Adds agent hints from metadata if present.

        Args:
            issues: List of validation issues.

        Returns:
            ValidationResult with score and hints.
        """
        has_errors = any(i.severity == "error" for i in issues)
        has_warnings = any(i.severity == "warning" for i in issues)

        if has_errors:
            score = 0.0
            passed = False
        elif has_warnings:
            score = 8.0
            passed = True
        else:
            score = 10.0
            passed = True

        return ValidationResult(
            passed=passed,
            score=score,
            issues=issues,
            agent_hint=self.metadata.get("agent_hint"),
            content_guidance=self.metadata.get("content_guidance")
        )
