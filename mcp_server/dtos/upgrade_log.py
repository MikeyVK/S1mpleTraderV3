# mcp_server/dtos/upgrade_log.py
"""UpgradeLogDTO — immutable read-side model for workspace upgrade logging."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class UpgradeLogDTO(BaseModel):
    """Immutable data transfer object representing a workspace upgrade run log."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    timestamp: str
    from_version: str
    to_version: str
    backup_path: str
    renewed_files: list[str]
    preserved_files: list[str]
    status: Literal["success", "failed"]
    details: str | None = None
