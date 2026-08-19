# tests\mcp_server\unit\managers\test_typescript_dto_scaffold.py
# template=unit_test version=3d15d309 created=2026-07-15T21:39Z updated=
"""
Unit tests for mcp_server.managers.artifact_manager.

Test scaffolding of TypeScript DTO artifact.

@layer: Tests (Unit)
@dependencies: [pytest, mcp_server.managers.artifact_manager]
@responsibilities:
    - Test TestTypeScriptDTOScaffold functionality
    - Verify None
    - None
"""

# Third-party
from pathlib import Path

import pytest

# Project modules
from tests.mcp_server.test_support import make_artifact_manager


class TestTypeScriptDTOScaffold:
    @pytest.mark.asyncio
    async def test_scaffold_typescript_dto(self, tmp_path: Path) -> None:
        """Test scaffolding of a TypeScript DTO using the tiered template structure."""
        # Arrange
        workspace_root = tmp_path / "workspace"
        config_root = workspace_root / ".pgmcp" / "config"
        templates_dir = workspace_root / ".pgmcp" / "templates"
        templates_config_dir = templates_dir / "config"
        concrete_dir = templates_dir / "concrete"

        # Create directories
        config_root.mkdir(parents=True)
        templates_config_dir.mkdir(parents=True)
        concrete_dir.mkdir(parents=True)

        # Write index configuration file
        (config_root / "artifacts.yaml").write_text(
            "version: '1.0.0'\nartifact_types: []\n", encoding="utf-8"
        )
        (config_root / "git.yaml").write_text("branch_types: []\n", encoding="utf-8")
        project_struct = (
            "version: '1.0.0'\n"
            "directories:\n"
            "  src/dtos:\n"
            "    parent: null\n"
            "    description: 'TS DTOs'\n"
            "    allowed_artifact_types:\n"
            "      - typescript_dto\n"
            "    allowed_extensions:\n"
            "      - '.ts'\n"
        )
        (config_root / "project_structure.yaml").write_text(project_struct, encoding="utf-8")

        dto_yaml = (
            "type: code\n"
            "type_id: typescript_dto\n"
            "template_version: 1.0.0\n"
            "name: TypeScript DTO\n"
            "description: TypeScript DTO class\n"
            "output_type: file\n"
            "scaffolder_class: GenericScaffolder\n"
            "scaffolder_module: mcp_server.scaffolders.generic_scaffolder\n"
            "template_path: concrete/typescript_dto.ts.jinja2\n"
            "fallback_template: null\n"
            "name_suffix: null\n"
            "file_extension: .ts\n"
            "generate_test: false\n"
            "base_path: src/dtos/\n"
            "context_schema:\n"
            "  fields:\n"
            "    type: array\n"
            "    title: Fields\n"
            "    description: List of DTO properties\n"
            "    required: true\n"
            "    items:\n"
            "      type: string\n"
            "  implements:\n"
            "    type: string\n"
            "    title: Implements interface\n"
            "    description: Optional interface to implement\n"
            "    required: false\n"
            "state_machine:\n"
            "  states: [CREATED]\n"
            "  initial_state: CREATED\n"
            "  valid_transitions: []\n"
        )
        (templates_config_dir / "typescript_dto.yaml").write_text(dto_yaml, encoding="utf-8")

        # Write tiered templates
        tier0_content = (
            "{% if format == 'typescript' %}\n"
            "// template={{ artifact_type }} version={{ version_hash }}\n"
            "{% endif %}\n"
            "{% block content %}{% endblock %}\n"
        )
        (templates_dir / "tier0_base_artifact.jinja2").write_text(tier0_content, encoding="utf-8")

        tier1_content = (
            "{% extends 'tier0_base_artifact.jinja2' %}\n"
            "{% block content %}\n"
            "{% block module_docstring %}{% endblock %}\n"
            "{% block imports_section %}{% endblock %}\n"
            "{% block class_structure %}{% endblock %}\n"
            "{% endblock %}\n"
        )
        (templates_dir / "tier1_base_code.jinja2").write_text(tier1_content, encoding="utf-8")

        tier2_content = (
            "{% extends 'tier1_base_code.jinja2' %}\n"
            "{% set format = 'typescript' %}\n"
            "{% block module_docstring %}\n"
            "/**\n"
            " * {{ test_description | default('TypeScript DTO') }}\n"
            " */\n"
            "{% endblock %}\n"
            "{% block class_structure %}\n"
            "export class {{ name }} {%%\n"
            "  {% block class_body %}{% endblock %}\n"
            "}\n"
            "{% endblock %}\n"
        )
        # Note: replace {%% with {% to avoid jinja escaping issues during template writing
        tier2_content = tier2_content.replace("{%%", "{%")
        (templates_dir / "tier2_base_typescript.jinja2").write_text(tier2_content, encoding="utf-8")

        tier3_content = (
            "{% extends 'tier2_base_typescript.jinja2' %}\n"
            "{% block class_body %}\n"
            "{% for field_str in fields %}\n"
            "  {%- set parts = field_str.strip().split() -%}\n"
            "  {%- if parts[0] == 'readonly' -%}\n"
            "    {%- set is_readonly = true -%}\n"
            "    {%- set field_decl = parts[1:] | join(' ') -%}\n"
            "  {%- else -%}\n"
            "    {%- set is_readonly = false -%}\n"
            "    {%- set field_decl = parts | join(' ') -%}\n"
            "  {%- endif -%}\n"
            "  {%- set name_type = field_decl.split(':') -%}\n"
            "  {%- set f_name = name_type[0] | trim -%}\n"
            "  {%- set f_type = name_type[1] | trim if name_type | length > 1 else 'string' -%}\n"
            "  public {% if is_readonly %}readonly {% endif %}{{ f_name }}: {{ f_type }};\n"
            "{% endfor %}\n"
            "{% endblock %}\n"
        )
        (templates_dir / "tier3_pattern_typescript_dto.jinja2").write_text(
            tier3_content, encoding="utf-8"
        )

        concrete_content = (
            "{#- Version: 1.0.0 -#}\n" + "{% extends 'tier3_pattern_typescript_dto.jinja2' %}\n"
        )
        (concrete_dir / "typescript_dto.ts.jinja2").write_text(concrete_content, encoding="utf-8")

        # Initialize manager
        manager = make_artifact_manager(workspace_root)

        # Act
        result = await manager.scaffold_artifact(
            artifact_type="typescript_dto",
            output_path="src/dtos/user.ts",
            name="UserDTO",
            fields=["readonly id: string", "name: string"],
        )

        # Assert
        output_file = Path(result)
        assert output_file.exists()
        content = output_file.read_text(encoding="utf-8")
        assert "template=typescript_dto" in content
        assert "export class UserDTO" in content
        assert "public readonly id: string;" in content
        assert "public name: string;" in content
