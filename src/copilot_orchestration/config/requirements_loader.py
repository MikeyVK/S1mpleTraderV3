# src\copilot_orchestration\config\requirements_loader.py
# template=generic version=f35abd82 created=2026-03-21T12:38Z updated=
"""SubRoleRequirementsLoader module.

Loads sub-role requirements from YAML, validates with Pydantic,
caches result. Raises ConfigError for unknown (role, sub_role) pairs.

@layer: copilot_orchestration (Config)
@dependencies: [None]
@responsibilities:
    - Parse sub-role-requirements.yaml at construction using PyYAML
    - Validate YAML structure with Pydantic BaseModel
    - Raise FileNotFoundError if YAML file does not exist
    - Cache parsed data; subsequent calls read from cache
    - Raise ConfigError for unknown (role, sub_role) pairs
    - Support from_copilot_dir factory classmethod
"""

# Standard library
import logging
from pathlib import Path
from typing import Any

# Third-party
import yaml
from pydantic import BaseModel

# Project modules
from copilot_orchestration.contracts.interfaces import SubRoleSpec

logger = logging.getLogger(__name__)


class ConfigError(Exception):
    """Raised when an unknown (role, sub_role) pair is requested."""


class _SubRoleSchema(BaseModel):
    requires_crosschat_block: bool
    heading: str
    block_prefix: str
    guide_line: str
    markers: list[str]


class _RoleSchema(BaseModel):
    default_sub_role: str
    sub_roles: dict[str, _SubRoleSchema]


class _RootSchema(BaseModel):
    roles: dict[str, _RoleSchema]


class SubRoleRequirementsLoader:
    """Loads sub-role requirements from YAML, validates with Pydantic,
    caches result. Raises ConfigError for unknown (role, sub_role) pairs."""

    def __init__(self, requirements_path: Path) -> None:
        """Parse and cache YAML at construction. Raises FileNotFoundError / ValidationError."""
        if not requirements_path.exists():
            raise FileNotFoundError(f"Sub-role requirements config not found: {requirements_path}")
        raw: Any = yaml.safe_load(requirements_path.read_text(encoding="utf-8"))
        parsed = _RootSchema.model_validate(raw)
        self._roles = parsed.roles

    @classmethod
    def from_copilot_dir(cls, workspace_root: Path) -> "SubRoleRequirementsLoader":
        """Factory: project .copilot YAML first, then package default."""
        project_yaml = workspace_root / ".copilot" / "sub-role-requirements.yaml"
        if project_yaml.exists():
            return cls(project_yaml)

        package_default = Path(__file__).parent / "_default_requirements.yaml"
        if package_default.exists():
            return cls(package_default)

        raise FileNotFoundError(
            f"No sub-role requirements config found. Checked: {project_yaml}, {package_default}"
        )

    def valid_sub_roles(self, role: str) -> frozenset[str]:
        """All valid sub-role names for the given role."""
        return frozenset(self._roles[role].sub_roles.keys())

    def default_sub_role(self, role: str) -> str:
        """Default sub-role when none detected from the user prompt."""
        return self._roles[role].default_sub_role

    def requires_crosschat_block(self, role: str, sub_role: str) -> bool:
        """True only for sub-roles that must produce a cross-chat handover block."""
        return self.get_requirement(role, sub_role)["requires_crosschat_block"]

    def get_requirement(self, role: str, sub_role: str) -> SubRoleSpec:
        """Full spec for (role, sub_role). Raises ConfigError if unknown."""
        role_data = self._roles.get(role)
        if role_data is None or sub_role not in role_data.sub_roles:
            raise ConfigError(f"Unknown (role, sub_role): ({role!r}, {sub_role!r})")
        spec = role_data.sub_roles[sub_role]
        return SubRoleSpec(
            requires_crosschat_block=spec.requires_crosschat_block,
            heading=spec.heading,
            block_prefix=spec.block_prefix,
            guide_line=spec.guide_line,
            markers=list(spec.markers),
        )
