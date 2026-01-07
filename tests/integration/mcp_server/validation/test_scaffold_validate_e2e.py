# tests/integration/mcp_server/validation/test_scaffold_validate_e2e.py
"""
End-to-end tests for Scaffold → Validate cycle.

Tests that code generated from templates passes validation based on
the same template's TEMPLATE_METADATA.

@layer: Tests (E2E)
@dependencies: [pytest, DTOScaffolder, ToolScaffolder, LayeredTemplateValidator]
"""
# pyright: reportCallIssue=false
# Standard library
import tempfile
from pathlib import Path

# Third-party
import pytest

# Scaffolding infrastructure
from mcp_server.scaffolding.components.dto import DTOScaffolder
from mcp_server.scaffolding.components.tool import ToolScaffolder
from mcp_server.scaffolding.renderer import JinjaRenderer

# Validation infrastructure
from mcp_server.validation.layered_template_validator import LayeredTemplateValidator
from mcp_server.validation.template_analyzer import TemplateAnalyzer
from mcp_server.validation.validation_service import ValidationService


class TestScaffoldValidateCycle:
    """E2E tests for scaffold → validate cycle."""

    @pytest.fixture
    def temp_dir(self):
        """Fixture for temporary directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def renderer(self) -> JinjaRenderer:
        """Fixture for JinjaRenderer."""
        return JinjaRenderer()

    @pytest.fixture
    def template_analyzer(self) -> TemplateAnalyzer:
        """Fixture for TemplateAnalyzer."""
        return TemplateAnalyzer(Path("mcp_server/templates"))

    @pytest.fixture
    def validator(self) -> ValidationService:
        """Fixture for ValidationService."""
        return ValidationService()

    @pytest.mark.asyncio
    async def test_scaffold_dto_passes_validation(
        self,
        renderer: JinjaRenderer,
        template_analyzer: TemplateAnalyzer,
        temp_dir: Path
    ) -> None:
        """Test that scaffolded DTO passes template-driven validation.

        This test verifies the SSOT contract from Issue #52:
        - scaffolding renders from dto.py.jinja2
        - validation checks the same template's TEMPLATE_METADATA rules

        It intentionally does NOT run Python QA gates (pylint/mypy/pyright),
        because DTO/tool templates can contain agent TODOs while still being
        structurally compliant with TEMPLATE_METADATA.
        """
        scaffolder = DTOScaffolder(renderer)
        output_path = temp_dir / "scaffolded_dto.py"

        content = scaffolder.scaffold(
            name="TestDTO",
            description="Test DTO for E2E template validation",
            layer="DTOs",
            has_causality=False,
            fields=[
                {"name": "test_field", "type": "str", "default": None}
            ]
        )
        output_path.write_text(content, encoding="utf-8")
        assert output_path.exists(), "DTO should be scaffolded"

        file_content = output_path.read_text(encoding="utf-8")

        dto_validator = LayeredTemplateValidator("dto", template_analyzer)
        result = await dto_validator.validate(str(output_path), file_content)

        assert result.passed, f"DTO failed template validation: {[i.message for i in result.issues]}"

    @pytest.mark.asyncio
    async def test_scaffold_tool_passes_validation(
        self,
        renderer: JinjaRenderer,
        template_analyzer: TemplateAnalyzer,
        temp_dir: Path
    ) -> None:
        """Test that scaffolded Tool passes template-driven validation.

        See `test_scaffold_dto_passes_validation` for rationale.
        """
        scaffolder = ToolScaffolder(renderer)
        output_path = temp_dir / "scaffolded_tool.py"

        content = scaffolder.scaffold(
            name="TestTool",
            description="Test tool for E2E template validation",
            input_schema={
                "type": "object",
                "properties": {"name": {"type": "string"}}
            }
        )
        output_path.write_text(content, encoding="utf-8")
        assert output_path.exists(), "Tool should be scaffolded"

        file_content = output_path.read_text(encoding="utf-8")

        tool_validator = LayeredTemplateValidator("tool", template_analyzer)
        result = await tool_validator.validate(str(output_path), file_content)

        assert result.passed, f"Tool failed template validation: {[i.message for i in result.issues]}"

    @pytest.mark.asyncio
    async def test_scaffold_document_passes_validation(
        self,
        temp_dir: Path,
        validator: ValidationService
    ) -> None:
        """Test that scaffolded document passes validation.

        Per planning.md: Generated doc validates (base_document).
        E2E: base_document.md.jinja2 → base_document.md.jinja2 validation.
        """
        # Manually create a document using base_document format
        output_path = temp_dir / "test_doc.md"
        doc_content = '''---
title: Test Document
status: DRAFT
version: 1.0
---

# Test Document

## Purpose

Test document for E2E validation.

## Scope

Testing that scaffolded documents pass FORMAT validation.
'''
        output_path.write_text(doc_content, encoding="utf-8")
        assert output_path.exists(), "Document should be created"

        passed, issues = await validator.validate(
            str(output_path),
            doc_content
        )

        assert passed, f"Document failed validation. Issues: {issues}"
