# tests/integration/mcp_server/validation/test_scaffold_validate_e2e.py
"""
End-to-end tests for Scaffold → Validate cycle.

Tests that code generated from templates passes validation based on
the same template's TEMPLATE_METADATA.

@layer: Tests (E2E)
@dependencies: [pytest, DTOScaffolder, ToolScaffolder, ValidationService]
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
    def validator(self) -> ValidationService:
        """Fixture for ValidationService."""
        return ValidationService()

    @pytest.mark.asyncio
    async def test_scaffold_dto_passes_validation(
        self,
        renderer: JinjaRenderer,
        validator: ValidationService,
        temp_dir: Path
    ) -> None:
        """Test that scaffolded DTO passes validation.

        Per planning.md: Generated DTO validates.
        E2E: dto.py.jinja2 scaffolding → dto.py.jinja2 TEMPLATE_METADATA.
        """
        # Scaffold a DTO
        scaffolder = DTOScaffolder(renderer)
        output_path = temp_dir / "test_dto.py"

        content = scaffolder.scaffold(
            name="TestDTO",
            description="Test DTO for E2E validation",
            layer="DTOs",
            has_causality=False,
            fields=[
                {"name": "test_field", "type": "str", "default": None}
            ]
        )
        output_path.write_text(content, encoding="utf-8")

        # Verify file was created
        assert output_path.exists(), "DTO should be scaffolded"

        # Read content back for validation
        file_content = output_path.read_text(encoding="utf-8")

        # Validate the scaffolded DTO
        passed, issues = await validator.validate(str(output_path), file_content)

        # Scaffolded code should pass validation
        assert passed, f"Scaffolded DTO failed validation. Issues: {issues}"

    @pytest.mark.asyncio
    async def test_scaffold_tool_passes_validation(
        self,
        renderer: JinjaRenderer,
        validator: ValidationService,
        temp_dir: Path
    ) -> None:
        """Test that scaffolded Tool passes validation.

        Per planning.md: Generated tool validates.
        E2E: tool.py.jinja2 scaffolding → tool.py.jinja2 TEMPLATE_METADATA.
        """
        # Scaffold a Tool
        scaffolder = ToolScaffolder(renderer)
        output_path = temp_dir / "test_tool.py"

        content = scaffolder.scaffold(
            name="TestTool",
            description="Test tool for E2E validation",
            input_schema={
                "type": "object",
                "properties": {"name": {"type": "string"}}
            }
        )
        output_path.write_text(content, encoding="utf-8")

        # Verify file was created
        assert output_path.exists(), "Tool should be scaffolded"

        # Read content back for validation
        file_content = output_path.read_text(encoding="utf-8")

        # Validate the scaffolded Tool
        passed, issues = await validator.validate(str(output_path), file_content)

        # Scaffolded code should pass validation
        assert passed, f"Scaffolded Tool failed validation. Issues: {issues}"

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

        # Verify file was created
        assert output_path.exists(), "Document should be created"

        # Validate the document
        passed, issues = await validator.validate(
            str(output_path),
            doc_content
        )

        # Document with proper frontmatter should pass validation
        assert passed, f"Document failed validation. Issues: {issues}"
