"""RED/GREEN TEST: Service artifact moet template_path uit artifacts.yaml gebruiken.

Issue: template_scaffolder.py had hardcoded fallback naar "components/" - nu verwijderd.

Expected: Service artifact gebruikt template_path uit artifacts.yaml:
- "concrete/service_command.py.jinja2" (default)
- Geen hardcoded fallback naar oude "components/" locatie

Allowed edge case: ALLEEN generic artifact mag template_name uit context gebruiken.
"""
import pytest
from mcp_server.scaffolders.template_scaffolder import TemplateScaffolder
from mcp_server.config.artifact_registry_config import (
    ArtifactRegistryConfig,
    ArtifactDefinition,
)


class TestNoHardcodedServiceFallback:
    """GREEN: Service artifact heeft geen hardcoded fallback meer."""

    def test_service_uses_template_path_from_artifacts_yaml(self):
        """Service artifact moet template_path uit artifacts.yaml gebruiken."""
        # Arrange: Service artifact zoals in artifacts.yaml
        artifact = ArtifactDefinition(
            type="code",
            type_id="service",
            name="Service",
            description="Service artifact",
            output_type="file",
            scaffolder_class="ServiceScaffolder",
            scaffolder_module="mcp_server.scaffolders.service_scaffolder",
            template_path="concrete/service_command.py.jinja2",  # Default uit artifacts.yaml
            fallback_template=None,
            name_suffix="Service",
            file_extension=".py",
            generate_test=True,
            state_machine={
                "states": ["CREATED"],
                "initial_state": "CREATED",
                "valid_transitions": [],
            },
        )

        registry = ArtifactRegistryConfig(
            version="1.0",
            artifact_types=[artifact],
        )

        scaffolder = TemplateScaffolder(registry=registry)

        # Act: Resolve template path (internal method)
        context = {"service_type": "orchestrator"}  # Service type context (ignored!)
        resolved_path = scaffolder._resolve_template_path(
            artifact_type="service",
            artifact=artifact,
            context=context,
        )

        # Assert: Moet template_path uit artifacts.yaml gebruiken
        # NIET de hardcoded fallback "components/service_orchestrator.py.jinja2"
        assert resolved_path == "concrete/service_command.py.jinja2"
        assert "components/" not in resolved_path, (
            "Service artifact mag geen hardcoded fallback naar components/ hebben!"
        )

    def test_service_without_template_path_returns_none(self):
        """Service met template_path=None returnt None (moet uit artifacts.yaml komen)."""
        # Arrange: Service met template_path=None
        artifact = ArtifactDefinition(
            type="code",
            type_id="service",
            name="Service",
            description="Service artifact",
            output_type="file",
            scaffolder_class="ServiceScaffolder",
            scaffolder_module="mcp_server.scaffolders.service_scaffolder",
            template_path=None,  # Geen default!
            fallback_template=None,
            name_suffix="Service",
            file_extension=".py",
            generate_test=True,
            state_machine={
                "states": ["CREATED"],
                "initial_state": "CREATED",
                "valid_transitions": [],
            },
        )

        registry = ArtifactRegistryConfig(
            version="1.0",
            artifact_types=[artifact],
        )

        scaffolder = TemplateScaffolder(registry=registry)

        # Act: Resolve met service_type in context
        context = {"service_type": "orchestrator"}
        resolved_path = scaffolder._resolve_template_path(
            artifact_type="service",
            artifact=artifact,
            context=context,
        )

        # Assert: Moet None returnen - service heeft GEEN hardcoded fallback meer
        # Alle template paths moeten uit artifacts.yaml komen
        assert resolved_path is None, (
            "Service zonder template_path in artifacts.yaml moet None returnen. "
            "Geen hardcoded fallbacks toegestaan!"
        )

    def test_generic_template_name_overrides_artifact_yaml(self):
        """Generic: template_name uit context krijgt PRIORITY over artifact.template_path."""
        # Arrange: Generic artifact met default template_path
        artifact = ArtifactDefinition(
            type="code",
            type_id="generic",
            name="Generic Component",
            description="Generic component from custom template",
            output_type="file",
            scaffolder_class="GenericScaffolder",
            scaffolder_module="mcp_server.scaffolders.generic_scaffolder",
            template_path="concrete/generic.py.jinja2",  # Default uit artifacts.yaml
            fallback_template=None,
            name_suffix=None,
            file_extension=".py",
            generate_test=False,
            state_machine={
                "states": ["CREATED"],
                "initial_state": "CREATED",
                "valid_transitions": [],
            },
        )

        registry = ArtifactRegistryConfig(
            version="1.0",
            artifact_types=[artifact],
        )

        scaffolder = TemplateScaffolder(registry=registry)

        # Act: Resolve met template_name override in context
        context = {"template_name": "custom/my_special_template.py.jinja2"}
        resolved_path = scaffolder._resolve_template_path(
            artifact_type="generic",
            artifact=artifact,
            context=context,
        )

        # Assert: template_name uit context moet PRIORITY krijgen
        # Zelfs als artifact.template_path een default heeft!
        assert resolved_path == "custom/my_special_template.py.jinja2", (
            "Generic moet template_name uit context als PRIORITY override gebruiken!"
        )

    def test_generic_falls_back_to_artifact_yaml_without_context(self):
        """Generic: Zonder template_name in context, gebruik artifact.template_path."""
        # Arrange: Generic met default template_path
        artifact = ArtifactDefinition(
            type="code",
            type_id="generic",
            name="Generic Component",
            description="Generic component from custom template",
            output_type="file",
            scaffolder_class="GenericScaffolder",
            scaffolder_module="mcp_server.scaffolders.generic_scaffolder",
            template_path="concrete/generic.py.jinja2",
            fallback_template=None,
            name_suffix=None,
            file_extension=".py",
            generate_test=False,
            state_machine={
                "states": ["CREATED"],
                "initial_state": "CREATED",
                "valid_transitions": [],
            },
        )

        registry = ArtifactRegistryConfig(
            version="1.0",
            artifact_types=[artifact],
        )

        scaffolder = TemplateScaffolder(registry=registry)

        # Act: Resolve ZONDER template_name in context
        context = {}  # Geen template_name!
        resolved_path = scaffolder._resolve_template_path(
            artifact_type="generic",
            artifact=artifact,
            context=context,
        )

        # Assert: Moet artifact.template_path gebruiken als fallback
        assert resolved_path == "concrete/generic.py.jinja2"

    def test_generic_requires_template_name_when_artifact_yaml_null(self):
        """Generic: Met artifact.template_path=None vereist template_name in context."""
        # Arrange: Generic zonder default template_path
        artifact = ArtifactDefinition(
            type="code",
            type_id="generic",
            name="Generic Component",
            description="Generic component from custom template",
            output_type="file",
            scaffolder_class="GenericScaffolder",
            scaffolder_module="mcp_server.scaffolders.generic_scaffolder",
            template_path=None,  # Geen default!
            fallback_template=None,
            name_suffix=None,
            file_extension=".py",
            generate_test=False,
            state_machine={
                "states": ["CREATED"],
                "initial_state": "CREATED",
                "valid_transitions": [],
            },
        )

        registry = ArtifactRegistryConfig(
            version="1.0",
            artifact_types=[artifact],
        )

        scaffolder = TemplateScaffolder(registry=registry)

        # Act & Assert: Moet ValidationError geven zonder template_name
        from mcp_server.core.exceptions import ValidationError

        with pytest.raises(ValidationError, match="require.*template_name"):
            scaffolder._resolve_template_path(
                artifact_type="generic",
                artifact=artifact,
                context={},  # Geen template_name!
            )
