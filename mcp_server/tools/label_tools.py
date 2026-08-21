"""GitHub label tools."""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from mcp_server.config.schemas.label_config import validate_phase_label
from mcp_server.core.exceptions import ExecutionError
from mcp_server.core.interfaces import ICoreTool
from mcp_server.core.operation_notes import NoteContext
from mcp_server.managers.github_manager import GitHubManager
from mcp_server.schemas import LabelConfig, WorkphasesConfig
from mcp_server.schemas.tool_outputs import (
    CreateLabelOutput,
    DeleteLabelOutput,
    LabelOperationOutput,
    LabelOutputModel,
    ListLabelsOutput,
)


class ListLabelsInput(BaseModel):
    """Input for ListLabelsTool."""

    model_config = ConfigDict(extra="forbid")

    # No input fields needed currently, but model required for consistency


class ListLabelsTool(ICoreTool[ListLabelsInput, ListLabelsOutput]):
    """Tool to list all labels in the repository."""

    @property
    def name(self) -> str:
        return "list_labels"

    @property
    def description(self) -> str:
        return "List all labels in the repository"

    @property
    def args_model(self) -> type[BaseModel] | None:
        return ListLabelsInput

    def __init__(self, manager: GitHubManager, label_config: LabelConfig) -> None:
        self.manager = manager
        self._label_config = label_config

    @property
    def input_schema(self) -> dict[str, Any]:
        assert self.args_model is not None
        return self.args_model.model_json_schema()

    async def execute(self, params: ListLabelsInput, context: NoteContext) -> ListLabelsOutput:
        del context  # Not used
        del params
        try:
            labels = self.manager.list_labels()
            label_dtos = [
                LabelOutputModel(
                    name=label.name,
                    color=label.color,
                    description=label.description or None,
                )
                for label in labels
            ]
            return ListLabelsOutput(
                total_labels=len(label_dtos),
                labels=label_dtos,
            )
        except Exception as e:
            raise ExecutionError(str(e)) from e


class CreateLabelInput(BaseModel):
    """Input for CreateLabelTool."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(
        ...,
        description="Label name (e.g., 'type:feature')",
        pattern=r"^(type|priority|status|phase|scope|component|effort|parent):[a-z0-9-]+$",
    )
    color: str = Field(
        ...,
        description="Color hex code without # (e.g., '0e8a16')",
        pattern=r"^[0-9A-Fa-f]{6}$",
    )
    description: str | None = Field(default="", description="Label description")


class CreateLabelTool(ICoreTool[CreateLabelInput, CreateLabelOutput]):
    """Tool to create a new label in the repository."""

    @property
    def name(self) -> str:
        return "create_label"

    @property
    def description(self) -> str:
        return "Create a new label in the repository"

    @property
    def args_model(self) -> type[BaseModel] | None:
        return CreateLabelInput

    def __init__(
        self,
        manager: GitHubManager,
        label_config: LabelConfig,
        workphases_config: WorkphasesConfig,
    ) -> None:
        self.manager = manager
        self._label_config = label_config
        self._workphases_config = workphases_config

    @property
    def input_schema(self) -> dict[str, Any]:
        assert self.args_model is not None
        return self.args_model.model_json_schema()

    async def execute(self, params: CreateLabelInput, context: NoteContext) -> CreateLabelOutput:
        del context  # Not used
        # Validate label name pattern
        is_valid, error_msg = self._label_config.validate_label_name(params.name)
        if not is_valid:
            raise ExecutionError(error_msg)

        # Validate phase:* labels against known workphases
        phase_valid, phase_reason = validate_phase_label(params.name, self._workphases_config)
        if not phase_valid:
            raise ExecutionError(
                f"Label '{params.name}' rejected: unknown workphase. {phase_reason}"
            )

        # Validate color format (no # prefix)
        if params.color.startswith("#"):
            raise ExecutionError(
                f"Color must not include # prefix. Use '{params.color[1:]}' instead."
            )

        # Validate hex format
        if not re.match(r"^[0-9A-Fa-f]{6}$", params.color):
            raise ExecutionError(
                f"Invalid color format '{params.color}'. "
                f"Must be 6-character hex code (e.g., '1D76DB')."
            )

        # Create label
        try:
            label = self.manager.create_label(
                name=params.name, color=params.color, description=params.description or ""
            )
            return CreateLabelOutput(label_name=label.name, color=params.color)
        except Exception as e:
            raise ExecutionError(str(e)) from e


class DeleteLabelInput(BaseModel):
    """Input for DeleteLabelTool."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., description="Label name to delete")


class DeleteLabelTool(ICoreTool[DeleteLabelInput, DeleteLabelOutput]):
    """Tool to delete a label from the repository."""

    @property
    def name(self) -> str:
        return "delete_label"

    @property
    def description(self) -> str:
        return "Delete a label from the repository"

    @property
    def args_model(self) -> type[BaseModel] | None:
        return DeleteLabelInput

    def __init__(self, manager: GitHubManager, label_config: LabelConfig) -> None:
        self.manager = manager
        self._label_config = label_config

    @property
    def input_schema(self) -> dict[str, Any]:
        assert self.args_model is not None
        return self.args_model.model_json_schema()

    async def execute(self, params: DeleteLabelInput, context: NoteContext) -> DeleteLabelOutput:
        del context  # Not used
        try:
            self.manager.delete_label(params.name)
            return DeleteLabelOutput(label_name=params.name)
        except Exception as e:
            raise ExecutionError(str(e)) from e


class RemoveLabelsInput(BaseModel):
    """Input for RemoveLabelsTool."""

    model_config = ConfigDict(extra="forbid")

    issue_number: int = Field(..., description="Issue/PR number")
    labels: list[str] = Field(..., description="List of labels to remove")


class RemoveLabelsTool(ICoreTool[RemoveLabelsInput, LabelOperationOutput]):
    """Tool to remove labels from an issue or PR."""

    @property
    def name(self) -> str:
        return "remove_labels"

    @property
    def description(self) -> str:
        return "Remove labels from an issue or PR"

    @property
    def args_model(self) -> type[BaseModel] | None:
        return RemoveLabelsInput

    def __init__(self, manager: GitHubManager, label_config: LabelConfig) -> None:
        self.manager = manager
        self._label_config = label_config

    @property
    def input_schema(self) -> dict[str, Any]:
        assert self.args_model is not None
        return self.args_model.model_json_schema()

    async def execute(
        self, params: RemoveLabelsInput, context: NoteContext
    ) -> LabelOperationOutput:
        del context  # Not used
        try:
            self.manager.remove_labels(params.issue_number, params.labels)
            return LabelOperationOutput(
                issue_number=params.issue_number,
                labels=params.labels,
            )
        except Exception as e:
            raise ExecutionError(str(e)) from e


class AddLabelsInput(BaseModel):
    """Input for AddLabelsTool."""

    model_config = ConfigDict(extra="forbid")

    issue_number: int = Field(..., description="Issue/PR number")
    labels: list[str] = Field(
        ...,
        description="List of labels to add. Labels must follow the category:value naming pattern.",
    )


class AddLabelsTool(ICoreTool[AddLabelsInput, LabelOperationOutput]):
    """Tool to add labels to an issue or PR."""

    @property
    def name(self) -> str:
        return "add_labels"

    @property
    def description(self) -> str:
        return "Add labels to an issue or PR"

    @property
    def args_model(self) -> type[BaseModel] | None:
        return AddLabelsInput

    def __init__(
        self,
        manager: GitHubManager,
        label_config: LabelConfig,
        workphases_config: WorkphasesConfig,
    ) -> None:
        self.manager = manager
        self._label_config = label_config
        self._workphases_config = workphases_config

    @property
    def input_schema(self) -> dict[str, Any]:
        assert self.args_model is not None
        return self.args_model.model_json_schema()

    async def execute(self, params: AddLabelsInput, context: NoteContext) -> LabelOperationOutput:
        del context  # Not used
        # Load label config for validation
        # Validate all labels exist
        invalid = [
            label for label in params.labels if not self._label_config.validate_label_name(label)[0]
        ]
        if invalid:
            raise ExecutionError(f"Labels not valid per labels.yaml: {invalid}")

        # Validate phase:* labels against known workphases
        for label in params.labels:
            is_valid, reason = validate_phase_label(label, self._workphases_config)
            if not is_valid:
                raise ExecutionError(f"Label '{label}' rejected: unknown workphase. {reason}")

        # Add labels
        try:
            self.manager.add_labels(params.issue_number, params.labels)
            return LabelOperationOutput(
                issue_number=params.issue_number,
                labels=params.labels,
            )
        except Exception as e:
            raise ExecutionError(str(e)) from e
