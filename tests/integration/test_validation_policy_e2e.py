# tests/integration/test_validation_policy_e2e.py
"""
E2E tests for validation policy enforcement in ArtifactManager.

Tests verify:
- Code artifacts: BLOCK on validation errors (no file written)
- Doc artifacts: WARN on validation errors (file written + warning logged)

@layer: Tests (Integration E2E)
@test_type: Integration / End-to-End
"""

import logging

import pytest

from mcp_server.config.artifact_registry_config import ArtifactRegistryConfig
from mcp_server.core.exceptions import ValidationError
from tests.fixtures.artifact_test_harness import (
    ArtifactIdentity,
    ArtifactSpec,
    TemplateFields,
    add_artifact_to_yaml,
    create_template,
)


@pytest.mark.asyncio
async def test_invalid_code_artifact_blocks_no_file(
    temp_workspace, artifacts_yaml_file, artifact_manager
):
    """
    GIVEN: Code artifact with template generating invalid Python
    WHEN: scaffold_artifact() called
    THEN: ValidationError raised AND no output file written (BLOCK policy)
    """
    # Add dto_invalid artifact type
    add_artifact_to_yaml(
        artifacts_yaml_path=artifacts_yaml_file,
        spec=ArtifactSpec(
            identity=ArtifactIdentity(type_id="dto_invalid", artifact_type="code"),
            name="Invalid DTO",
            template_path="components/dto_invalid.py.jinja2",
            file_extension=".py",
        )
    )

    # Create template with INVALID Python (syntax error)
    invalid_template = """# Generated DTO with syntax error
class {{ name }}DTO:
    def __init__(self
        # Missing closing parenthesis!
    pass
"""
    create_template(temp_workspace, "components/dto_invalid.py.jinja2", invalid_template)

    # Reload registry
    ArtifactRegistryConfig.reset_instance()
    fresh_registry = ArtifactRegistryConfig.from_file(artifacts_yaml_file)

    # Update manager registry
    artifact_manager.registry = fresh_registry
    artifact_manager.scaffolder.registry = fresh_registry

    # Expected output path
    output_path = temp_workspace / "mcp_server" / "dtos" / "test_dto.py"

    # WHEN: scaffold invalid code artifact
    with pytest.raises(ValidationError) as exc_info:
        await artifact_manager.scaffold_artifact(
            artifact_type="dto_invalid",
            output_path=str(output_path),
            name="Test",
        )

    # THEN: ValidationError raised
    assert "failed validation" in str(exc_info.value).lower()

    # THEN: No file written (BLOCK policy)
    assert not output_path.exists(), (
        f"Code artifact should NOT be written when invalid (BLOCK). Found: {output_path}"
    )


@pytest.mark.asyncio
async def test_invalid_doc_artifact_warns_writes_file(
    temp_workspace, artifacts_yaml_file, artifact_manager, caplog
):
    """
    GIVEN: Doc artifact with potentially invalid content
    WHEN: scaffold_artifact() called
    THEN: No exception AND file IS written AND warning logged (WARN policy)
    """
    # Add design_minimal artifact type
    add_artifact_to_yaml(
        artifacts_yaml_path=artifacts_yaml_file,
        spec=ArtifactSpec(
            identity=ArtifactIdentity(type_id="design_minimal", artifact_type="doc"),
            name="Minimal Design",
            template_path="documents/design_minimal.md.jinja2",
            file_extension=".md",
            template_fields=TemplateFields(required=["title"]),
        )
    )

    # Create minimal doc template (MISSING H1 - will trigger validation error)
    minimal_template = """## {{ title }}

<!-- INTENTIONALLY MISSING H1 TITLE (starts with ## instead of #) -->
<!-- This will trigger MarkdownValidator error but WARN policy allows writing -->
"""
    create_template(temp_workspace, "documents/design_minimal.md.jinja2", minimal_template)

    # Reload registry
    ArtifactRegistryConfig.reset_instance()
    fresh_registry = ArtifactRegistryConfig.from_file(artifacts_yaml_file)

    artifact_manager.registry = fresh_registry
    artifact_manager.scaffolder.registry = fresh_registry

    # Expected output path
    output_path = temp_workspace / "docs" / "design" / "test_design.md"

    caplog.set_level(logging.WARNING)

    # WHEN: scaffold doc artifact (WARN policy)
    result_path = await artifact_manager.scaffold_artifact(
        artifact_type="design_minimal",
        output_path=str(output_path),
        title="Test Design",
    )

    # THEN: File IS written (WARN policy allows writing)
    assert output_path.exists(), (
        f"Doc artifact SHOULD be written even with warnings (WARN). Missing: {output_path}"
    )

    # THEN: WARNING is explicitly logged (DoD requirement)
    warning_records = [r for r in caplog.records if r.levelname == "WARNING"]
    assert len(warning_records) > 0, (
        "Expected explicit WARNING log for doc artifact validation issues (WARN policy). "
        f"Got {len(warning_records)} warnings"
    )

    # THEN: Warning message mentions validation and artifact type
    warning_text = " ".join([r.message for r in warning_records])
    assert "validation" in warning_text.lower(), (
        f"Expected 'validation' in warning message. Got: {warning_text}"
    )
    assert "design_minimal" in warning_text or "doc" in warning_text, (
        f"Expected artifact type in warning message. Got: {warning_text}"
    )

    # THEN: Returned path matches what was written
    assert result_path == str(output_path.resolve())


@pytest.mark.asyncio
async def test_valid_code_artifact_writes_successfully(
    temp_workspace, artifacts_yaml_file, artifact_manager
):
    """
    GIVEN: Code artifact with valid Python template
    WHEN: scaffold_artifact() called
    THEN: No exception AND file written (control test - happy path)
    """
    # Add dto_valid artifact type
    add_artifact_to_yaml(
        artifacts_yaml_path=artifacts_yaml_file,
        spec=ArtifactSpec(
            identity=ArtifactIdentity(type_id="dto_valid", artifact_type="code"),
            name="Valid DTO",
            template_path="components/dto_valid.py.jinja2",
            file_extension=".py",
        )
    )

    # Create VALID Python template (with SCAFFOLD header for validation)
    scaffold_header = (
        "# SCAFFOLD: template={{ template_id }} version={{ template_version }} "
        "created={{ scaffold_created }}{% if output_path %} path={{ output_path }}{% endif %}"
    )
    valid_template = f"""{scaffold_header}
'''{{{{ description }}}}'''
from pydantic import BaseModel

class {{{{ name }}}}DTO(BaseModel):
    '''{{{{ description }}}}'''
    pass
"""
    create_template(temp_workspace, "components/dto_valid.py.jinja2", valid_template)

    # Reload registry
    ArtifactRegistryConfig.reset_instance()
    fresh_registry = ArtifactRegistryConfig.from_file(artifacts_yaml_file)

    artifact_manager.registry = fresh_registry
    artifact_manager.scaffolder.registry = fresh_registry

    # Expected output path
    output_path = temp_workspace / "mcp_server" / "dtos" / "test_dto.py"

    # WHEN: scaffold valid code artifact
    result_path = await artifact_manager.scaffold_artifact(
        artifact_type="dto_valid",
        output_path=str(output_path),
        name="Test",
        description="Valid test DTO",
    )

    # THEN: File written successfully
    assert output_path.exists(), f"Valid code should be written. Missing: {output_path}"

    # THEN: Content is valid Python
    content = output_path.read_text()
    compile(content, str(output_path), "exec")

    # THEN: Returned path matches
    assert result_path == str(output_path.resolve())
