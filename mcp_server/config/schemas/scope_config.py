"""Pure ScopeConfig schema for ConfigLoader-managed YAML loading."""

from pydantic import BaseModel


class ScopeConfig(BaseModel):
    """Scope conventions configuration value object."""

    version: str
    scopes: list[str]

    def has_scope(self, name: str) -> bool:
        return name in self.scopes
