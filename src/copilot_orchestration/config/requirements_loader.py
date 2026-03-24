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
from pydantic import BaseModel, model_validator

# Project modules
from copilot_orchestration.contracts.interfaces import SubRoleSpec

logger = logging.getLogger(__name__)


class ConfigError(Exception):
    """Raised when an unknown (role, sub_role) pair is requested."""


class _SubRoleSchema(BaseModel):
    requires_crosschat_block: bool
    heading: str
    markers: list[str]
    block_template: str = ""

    @model_validator(mode="after")
    def _validate_template_required(self) -> "_SubRoleSchema":
        if self.requires_crosschat_block and not self.block_template.strip():
            raise ValueError(
                "block_template may not be empty when requires_crosschat_block=True"
            )
        return self


class _RoleSchema(BaseModel):
    default_sub_role: str
    sub_roles: dict[str, _SubRoleSchema]


class _RootSchema(BaseModel):
    roles: dict[str, _RoleSchema]
    max_sub_role_name_len: int = 40


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
        self._max_sub_role_name_len = parsed.max_sub_role_name_len
        self._warn_invalid_fence_targets()
        logger.debug("loaded sub-role config from %s", requirements_path)

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
        role_data = self._roles.get(role)
        if role_data is None:
            raise ConfigError(f"Unknown role: {role!r}")
        return frozenset(role_data.sub_roles.keys())

    def default_sub_role(self, role: str) -> str:
        """Default sub-role when none detected from the user prompt."""
        role_data = self._roles.get(role)
        if role_data is None:
            raise ConfigError(f"Unknown role: {role!r}")
        return role_data.default_sub_role

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
            markers=list(spec.markers),
            block_template=spec.block_template,
        )

    def max_sub_role_name_len(self) -> int:
        """Maximum character length for a valid sub-role name (from YAML config)."""
        return self._max_sub_role_name_len

    def _warn_invalid_fence_targets(self) -> None:
        """Best-effort: warn when a block_template fence first word is not a known sub-role."""
        all_sub_roles: set[str] = set()
        for role_data in self._roles.values():
            all_sub_roles.update(role_data.sub_roles.keys())

        for role_name, role_data in self._roles.items():
            for sub_role_name, spec in role_data.sub_roles.items():
                if not spec.requires_crosschat_block or not spec.block_template.strip():
                    continue
                first_word = self._fence_first_word(spec.block_template)
                if first_word and first_word not in all_sub_roles:
                    logger.warning(
                        "block_template for (%r, %r): fence first word %r is not a known"
                        " sub-role name",
                        role_name,
                        sub_role_name,
                        first_word,
                    )

    @staticmethod
    def _fence_first_word(block_template: str) -> str:
        """Return first non-empty word inside the opening code fence, or '' if not found."""
        inside_fence = False
        for line in block_template.splitlines():
            stripped = line.strip()
            if not inside_fence:
                if stripped.startswith("```"):
                    inside_fence = True
                continue
            if stripped:
                return stripped.split()[0]
        return ""
