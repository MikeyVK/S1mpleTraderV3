# mcp_server/config/schemas/scope_config.py
"""
Scope configuration schema definitions.

Defines typed value objects for issue and workflow scopes loaded by the
configuration layer.

@layer: Backend (Config)
@dependencies: [pydantic]
@responsibilities:
    - Define scope config schema contracts
    - Validate configured scope values
    - Provide scope lookup helpers for issue tooling
"""

from pydantic import BaseModel


class ScopeConfig(BaseModel):
    """Scope conventions configuration value object."""

    version: str
    scopes: list[str]

    def has_scope(self, name: str) -> bool:
        return name in self.scopes
