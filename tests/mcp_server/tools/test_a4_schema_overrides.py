"""Tests for C3 A4 config-driven schema overrides.

Covers:
- TransitionPhaseTool: to_phase.enum from WorkphasesConfig
- ForcePhaseTransitionTool: to_phase.enum from WorkphasesConfig
- InitializeProjectTool: workflow_name.enum from ContractsConfig
- CreateIssueTool: issue_type.enum, priority.enum, scope.enum, title.maxLength from configs
- ScaffoldArtifactTool: artifact_type.enum from registry

@dependencies: phase_tools, project_tools, issue_tools, scaffold_artifact
"""

from unittest.mock import MagicMock

import pytest

from mcp_server.tools.issue_tools import CreateIssueTool
from mcp_server.tools.phase_tools import ForcePhaseTransitionTool, TransitionPhaseTool
from mcp_server.tools.project_tools import InitializeProjectTool
from mcp_server.tools.scaffold_artifact import ScaffoldArtifactTool


def _make_workphases_config(phases: dict | None = None) -> MagicMock:
    config = MagicMock()
    config.phases = phases or {"research": None, "design": None, "planning": None}
    return config


def _make_contracts_config(workflows: dict | None = None) -> MagicMock:
    config = MagicMock()
    config.workflows = workflows or {"feature": None, "bug": None, "refactor": None}
    return config


def _make_issue_config(issue_type_names: list[str] | None = None) -> MagicMock:
    config = MagicMock()
    names = issue_type_names or ["feature", "bug", "hotfix", "chore", "docs", "epic"]
    config.issue_types = [MagicMock(name=n) for n in names]
    for mock_type, name in zip(config.issue_types, names, strict=True):
        mock_type.name = name
    return config


def _make_label_config(priority_values: list[str] | None = None) -> MagicMock:
    label_config = MagicMock()
    values = priority_values or ["critical", "high", "medium", "low"]
    priority_labels = [MagicMock() for _ in values]
    for mock_label, val in zip(priority_labels, values, strict=True):
        mock_label.name = f"priority:{val}"
    label_config.get_labels_by_category.return_value = priority_labels
    return label_config


def _make_scope_config(scopes: list[str] | None = None) -> MagicMock:
    config = MagicMock()
    config.scopes = scopes or ["architecture", "mcp-server", "platform"]
    return config


def _make_git_config(max_length: int = 72) -> MagicMock:
    config = MagicMock()
    config.issue_title_max_length = max_length
    return config


def _make_artifact_manager(type_ids: list[str] | None = None) -> MagicMock:
    manager = MagicMock()
    manager.registry.list_type_ids.return_value = type_ids or ["dto", "design", "worker"]
    return manager


class TestTransitionPhaseToolSchema:
    """C3: TransitionPhaseTool.input_schema injects to_phase.enum from WorkphasesConfig."""

    def test_to_phase_has_enum_from_workphases_config(
        self, tmp_path: pytest.TempPathFactory
    ) -> None:
        workphases_config = _make_workphases_config(
            {"research": None, "design": None, "planning": None}
        )
        tool = TransitionPhaseTool(
            workspace_root=tmp_path,
            server_root=tmp_path,
            workphases_config=workphases_config,
        )
        schema = tool.input_schema
        assert "enum" in schema["properties"]["to_phase"]
        assert set(schema["properties"]["to_phase"]["enum"]) == {"research", "design", "planning"}


class TestForcePhaseTransitionToolSchema:
    """C3: ForcePhaseTransitionTool.input_schema injects to_phase.enum from WorkphasesConfig."""

    def test_to_phase_has_enum_from_workphases_config(
        self, tmp_path: pytest.TempPathFactory
    ) -> None:
        workphases_config = _make_workphases_config({"research": None, "planning": None})
        tool = ForcePhaseTransitionTool(
            workspace_root=tmp_path,
            server_root=tmp_path,
            workphases_config=workphases_config,
        )
        schema = tool.input_schema
        assert "enum" in schema["properties"]["to_phase"]
        assert set(schema["properties"]["to_phase"]["enum"]) == {"research", "planning"}


class TestInitializeProjectToolSchema:
    """C3: InitializeProjectTool.input_schema injects workflow_name.enum from ContractsConfig."""

    def test_workflow_name_has_enum_from_contracts_config(
        self, tmp_path: pytest.TempPathFactory
    ) -> None:
        contracts_config = _make_contracts_config({"feature": None, "bug": None, "special": None})
        tool = InitializeProjectTool(
            workspace_root=tmp_path,
            manager=MagicMock(),
            git_manager=MagicMock(),
            state_engine=MagicMock(),
            contracts_config=contracts_config,
        )
        schema = tool.input_schema
        assert "enum" in schema["properties"]["workflow_name"]
        assert set(schema["properties"]["workflow_name"]["enum"]) == {"feature", "bug", "special"}


class TestCreateIssueToolSchema:
    """C3: CreateIssueTool.input_schema injects enums and maxLength from configs."""

    @pytest.fixture
    def tool(self) -> CreateIssueTool:
        return CreateIssueTool(
            manager=MagicMock(),
            issue_config=_make_issue_config(),
            milestone_config=MagicMock(),
            contracts_config=MagicMock(),
            label_config=_make_label_config(),
            scope_config=_make_scope_config(),
            git_config=_make_git_config(max_length=72),
        )

    def test_issue_type_has_enum(self, tool: CreateIssueTool) -> None:
        schema = tool.input_schema
        assert "enum" in schema["properties"]["issue_type"]
        assert set(schema["properties"]["issue_type"]["enum"]) == {
            "feature",
            "bug",
            "hotfix",
            "chore",
            "docs",
            "epic",
        }

    def test_priority_has_enum(self, tool: CreateIssueTool) -> None:
        schema = tool.input_schema
        assert "enum" in schema["properties"]["priority"]
        assert set(schema["properties"]["priority"]["enum"]) == {
            "critical",
            "high",
            "medium",
            "low",
        }

    def test_scope_has_enum(self, tool: CreateIssueTool) -> None:
        schema = tool.input_schema
        assert "enum" in schema["properties"]["scope"]
        assert set(schema["properties"]["scope"]["enum"]) == {
            "architecture",
            "mcp-server",
            "platform",
        }

    def test_title_has_max_length(self, tool: CreateIssueTool) -> None:
        schema = tool.input_schema
        assert schema["properties"]["title"].get("maxLength") == 72


class TestScaffoldArtifactToolSchema:
    """C3: ScaffoldArtifactTool.input_schema injects artifact_type.enum from registry."""

    @pytest.fixture
    def tool(self) -> ScaffoldArtifactTool:
        return ScaffoldArtifactTool(manager=_make_artifact_manager(["dto", "design", "worker"]))

    def test_artifact_type_has_enum(self, tool: ScaffoldArtifactTool) -> None:
        schema = tool.input_schema
        assert "enum" in schema["properties"]["artifact_type"]

    def test_artifact_type_enum_contains_known_types(self, tool: ScaffoldArtifactTool) -> None:
        schema = tool.input_schema
        enum_values = schema["properties"]["artifact_type"]["enum"]
        assert set(enum_values) == {"dto", "design", "worker"}
