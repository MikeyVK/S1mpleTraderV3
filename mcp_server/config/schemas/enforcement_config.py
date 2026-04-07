# mcp_server/config/schemas/enforcement_config.py
"""
Enforcement configuration schema definitions.

Defines typed value objects for pre and post-operation enforcement rules
loaded by the config layer.

@layer: Backend (Config)
@dependencies: [pydantic, typing]
@responsibilities:
    - Define enforcement rule and action schema contracts
    - Validate enforcement configuration structure
    - Represent policy hooks for runtime enforcement execution
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator


class EnforcementAction(BaseModel):
    """One configured enforcement action."""

    model_config = ConfigDict(extra="forbid")

    type: str
    policy: str | None = None
    rules: dict[str, list[str]] = Field(default_factory=dict)
    path: str | None = None
    message: str | None = None

    @model_validator(mode="after")
    def validate_required_fields(self) -> EnforcementAction:
        if self.type == "check_branch_policy" and not self.rules:
            raise ValueError("check_branch_policy requires non-empty rules")
        if self.type == "delete_file" and not self.path:
            raise ValueError("delete_file requires path")
        return self


class EnforcementRule(BaseModel):
    """One configured enforcement rule."""

    model_config = ConfigDict(extra="forbid")

    event_source: str
    timing: str
    tool: str | None = None
    phase: str | None = None
    actions: list[EnforcementAction] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_target(self) -> EnforcementRule:
        if self.event_source == "tool" and not self.tool:
            raise ValueError("tool event_source requires tool")
        if self.event_source == "phase" and not self.phase:
            raise ValueError("phase event_source requires phase")
        return self


class EnforcementConfig(BaseModel):
    """Typed root object for enforcement.yaml."""

    model_config = ConfigDict(extra="forbid")

    enforcement: list[EnforcementRule] = Field(default_factory=list)
