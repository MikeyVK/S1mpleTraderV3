# src\copilot_orchestration\contracts\interfaces.py
# template=generic version=f35abd82 created=2026-03-21T12:21Z updated=
"""interfaces module.

Contracts for the copilot sub-role orchestration system.

Defines ``ISubRoleRequirementsLoader`` Protocol and shared TypedDicts.
Zero runtime I/O.

@layer: Package Contracts
@dependencies: [None]
@responsibilities:
    - Define ISubRoleRequirementsLoader Protocol with runtime_checkable for structural typing
    - Expose SubRoleSpec TypedDict for individual sub-role configuration
    - Expose SessionSubRoleState TypedDict for persisted sub-role state
"""

# Standard library
from typing import Protocol, TypedDict, runtime_checkable


class SubRoleSpec(TypedDict):
    """Configuration for one (role, sub_role) pair."""

    requires_crosschat_block: bool
    heading: str
    markers: list[str]
    block_template: str
    description: str


class SessionSubRoleState(TypedDict):
    """Persisted state written by the detect_sub_role hook."""

    session_id: str
    role: str
    sub_role: str
    detected_at: str


@runtime_checkable
class ISubRoleRequirementsLoader(Protocol):
    """Protocol for loaders that provide sub-role configuration."""

    def valid_sub_roles(self, role: str) -> frozenset[str]:
        """Return the set of valid sub-roles for *role*."""
        ...  # pragma: no cover

    def default_sub_role(self, role: str) -> str:
        """Return the default sub-role name for *role*."""
        ...  # pragma: no cover

    def requires_crosschat_block(self, role: str, sub_role: str) -> bool:
        """Return True when *sub_role* requires a crosschat STOP block."""
        ...  # pragma: no cover

    def get_requirement(self, role: str, sub_role: str) -> SubRoleSpec:
        """Return the full spec for *(role, sub_role)*."""
        ...  # pragma: no cover

    def max_sub_role_name_len(self) -> int:
        """Return maximum character length for a valid sub-role name (from config)."""
        ...  # pragma: no cover


@runtime_checkable
class ILoggingConfig(Protocol):
    """Protocol for logging configuration objects."""

    def apply(self) -> None:
        """Configure Python logging (basicConfig) and create log directory if absent."""
        ...  # pragma: no cover
