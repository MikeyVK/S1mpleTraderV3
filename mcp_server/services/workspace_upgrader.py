# mcp_server/services/workspace_upgrader.py
"""WorkspaceUpgrader service — orchestrates fail-safe workspace upgrades.

@layer: Services
@dependencies: [pathlib, shutil, datetime, settings, upgrade_log]
@responsibilities:
    - Create timestamped fail-safe backup (.pgmcp_backup_YYYYMMDD_HHMMSS)
    - Perform Smart Version-Aware Preservation of configuration and templates
    - Preserve dynamic state files (state.json, deliverables.json, registry, logs/)
    - Update workspace .version file
    - Write structured upgrade log (.pgmcp/logs/upgrade_YYYYMMDD_HHMMSS.json)
"""

from __future__ import annotations

import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from mcp_server.core.logging import get_logger
from mcp_server.dtos.upgrade_log import UpgradeLogDTO

if TYPE_CHECKING:
    from mcp_server.config.settings import Settings

logger = get_logger("workspace_upgrader")


class WorkspaceUpgrader:
    """Orchestrates workspace upgrades with backup creation and state preservation."""

    DYNAMIC_STATE_FILES = {
        "state.json",
        "deliverables.json",
        "template_registry.json",
        ".version",
    }

    def __init__(
        self,
        settings: Settings,
        assets_dir: Path | None = None,
    ) -> None:
        """Initialize upgrader with injected settings and optional assets path."""
        self._settings = settings
        self._server_root = Path(settings.server.resolved_server_root)
        self._workspace_root = Path(settings.server.workspace_root)

        if assets_dir is not None:
            self._assets_dir = assets_dir
        else:
            package_root = Path(__file__).resolve().parent.parent
            self._assets_dir = package_root / "assets"

    def get_current_workspace_version(self) -> str:
        """Query current version string from .pgmcp/.version file."""
        version_file = self._server_root / ".version"
        if version_file.exists():
            try:
                version_str = version_file.read_text(encoding="utf-8").strip()
                if version_str:
                    return version_str
            except Exception as e:
                logger.warning(f"Could not read workspace version file: {e}")
        return "0.0.0"

    def create_backup(self, timestamp_str: str) -> Path:
        """Create timestamped backup directory of .pgmcp."""
        backup_dir_name = f"{self._server_root.name}_backup_{timestamp_str}"
        backup_path = self._workspace_root / backup_dir_name
        if self._server_root.exists():
            shutil.copytree(self._server_root, backup_path)
            logger.info(f"Created workspace backup at '{backup_path}'")
        else:
            backup_path.mkdir(parents=True, exist_ok=True)
        return backup_path

    def _is_dynamic_state_path(self, relative_path: Path) -> bool:
        """Check if relative path corresponds to dynamic runtime state."""
        parts = relative_path.parts
        if not parts:
            return False
        if parts[0] in self.DYNAMIC_STATE_FILES:
            return True
        if parts[0] == "logs":
            return True
        return False

    def renew_workspace_assets(self) -> tuple[list[str], list[str]]:
        """Perform Smart Version-Aware Preservation of templates and assets.

        Returns:
            Tuple of (renewed_files, preserved_files) relative path strings.
        """
        renewed: list[str] = []
        preserved: list[str] = []

        if not self._assets_dir.exists():
            logger.warning(f"Assets directory '{self._assets_dir}' does not exist.")
            return renewed, preserved

        for asset_path in self._assets_dir.rglob("*"):
            if asset_path.is_dir():
                continue

            rel_path = asset_path.relative_to(self._assets_dir)
            if self._is_dynamic_state_path(rel_path):
                continue

            target_path = self._server_root / rel_path

            if target_path.exists():
                # If file exists in config/ and is a valid YAML configuration, preserve it
                if "config" in rel_path.parts and rel_path.suffix in (".yaml", ".yml"):
                    preserved.append(rel_path.as_posix())
                    continue

                # Renew outdated asset
                target_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(asset_path, target_path)
                renewed.append(rel_path.as_posix())
            else:
                # Copy missing asset
                target_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(asset_path, target_path)
                renewed.append(rel_path.as_posix())

        return renewed, preserved

    def update_version_file(self, target_version: str) -> None:
        """Write target version string to .pgmcp/.version."""
        self._server_root.mkdir(parents=True, exist_ok=True)
        version_file = self._server_root / ".version"
        version_file.write_text(f"{target_version}\n", encoding="utf-8")

    def write_upgrade_log(self, log_dto: UpgradeLogDTO, timestamp_str: str) -> Path:
        """Write structured UpgradeLogDTO to .pgmcp/logs/upgrade_YYYYMMDD_HHMMSS.json."""
        logs_dir = self._server_root / self._settings.server.logs_dir
        logs_dir.mkdir(parents=True, exist_ok=True)
        log_file = logs_dir / f"upgrade_{timestamp_str}.json"
        log_file.write_text(log_dto.model_dump_json(indent=2), encoding="utf-8")
        return log_file

    def execute_upgrade(self) -> UpgradeLogDTO:
        """Execute complete workspace upgrade flow and return UpgradeLogDTO.

        Raises:
            ConfigError / OSError: If backup creation or asset renewal fails.
        """
        timestamp_str = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        from_version = self.get_current_workspace_version()
        to_version = self._settings.server.version

        backup_path = self.create_backup(timestamp_str)
        renewed_files, preserved_files = self.renew_workspace_assets()
        self.update_version_file(to_version)

        log_dto = UpgradeLogDTO(
            timestamp=datetime.now(UTC).isoformat(),
            from_version=from_version,
            to_version=to_version,
            backup_path=backup_path.as_posix(),
            renewed_files=renewed_files,
            preserved_files=preserved_files,
            status="success",
            details="Workspace upgraded successfully.",
        )

        self.write_upgrade_log(log_dto, timestamp_str)
        return log_dto
