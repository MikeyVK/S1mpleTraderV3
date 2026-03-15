"""Pure contributor config schema definitions."""

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
