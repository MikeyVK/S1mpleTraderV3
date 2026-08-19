# mcp_server/config/schemas/milestone_config.py
"""
Milestone configuration schema definitions.

Defines typed value objects for milestone metadata loaded by the config layer.

@layer: Backend (Config)
@dependencies: [pydantic]
@responsibilities:
    - Define milestone entry and root config schema contracts
    - Validate milestone metadata loaded from YAML
    - Provide milestone lookup helpers for issue workflows
"""

from typing import Literal

from pydantic import BaseModel, Field


class MilestoneEntry(BaseModel):
    """Single milestone entry from milestones.yaml."""

    number: int
    title: str
    state: str = "open"


class MilestoneConfig(BaseModel):
    """Milestone validation configuration value object."""

    version: Literal["1.0.0"] = Field("1.0.0", description="Schema version")
    milestones: list[MilestoneEntry] = Field(default_factory=list)

    def validate_milestone(self, title: str) -> bool:
        if not self.milestones:
            return True
        return any(milestone.title == title for milestone in self.milestones)
