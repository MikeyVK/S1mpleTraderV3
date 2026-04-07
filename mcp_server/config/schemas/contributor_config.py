# mcp_server/config/schemas/contributor_config.py
"""
Contributor configuration schema definitions.

Defines typed value objects for contributor metadata used by issue and
milestone workflows.

@layer: Backend (Config)
@dependencies: [pydantic]
@responsibilities:
    - Define contributor entry and root config schema contracts
    - Validate contributor metadata loaded from YAML
    - Provide assignee lookup helpers for workflow consumers
"""

from pydantic import BaseModel, Field


class ContributorEntry(BaseModel):
    """Single contributor entry from contributors.yaml."""

    login: str
    name: str | None = None


class ContributorConfig(BaseModel):
    """Contributor validation configuration value object."""

    version: str
    contributors: list[ContributorEntry] = Field(default_factory=list)

    def validate_assignee(self, login: str) -> bool:
        if not self.contributors:
            return True
        return any(contributor.login == login for contributor in self.contributors)
