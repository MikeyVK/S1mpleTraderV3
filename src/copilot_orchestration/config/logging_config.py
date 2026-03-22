# src\copilot_orchestration\config\logging_config.py
# template=generic version=f35abd82 created=2026-03-22T20:40Z updated=
"""logging_config module.

YAML-driven logging configuration for the copilot_orchestration package.
Follows the SubRoleRequirementsLoader factory pattern exactly.

@layer: Package Config
@dependencies: [yaml, logging, pathlib]
@responsibilities:
    - Load logging config from YAML at construction (Fail-Fast)
    - Provide from_copilot_dir factory: .copilot/logging.yaml > package default
    - Apply config: create log directory and configure root logger via basicConfig
"""

# Standard library
import logging
from pathlib import Path
from typing import Any

# Third-party
import yaml


class LoggingConfig:
    """Loads logging configuration from YAML and applies it.

    Follows SubRoleRequirementsLoader pattern: all path resolution happens at
    construction; apply() is a stateless command with no arguments.
    """

    _DEFAULT_LOG_PATH = ".copilot/logs/orchestration.log"
    _DEFAULT_FORMAT = "%(asctime)s %(name)s %(levelname)s %(message)s"

    def __init__(self, config_path: Path, workspace_root: Path) -> None:
        """Parse YAML at construction. Raises FileNotFoundError / yaml.YAMLError.

        Resolves log_file_path to an absolute path (Fail-Fast: detectable at startup).
        """
        if not config_path.exists():
            raise FileNotFoundError(f"Logging config not found: {config_path}")
        raw: Any = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        self._level: str = raw.get("level", "WARNING")
        self._format: str = raw.get("format", self._DEFAULT_FORMAT)
        relative = raw.get("handlers", {}).get("file", {}).get("path", self._DEFAULT_LOG_PATH)
        self._log_file_path: Path = workspace_root / relative

    @property
    def level(self) -> str:
        """Return the configured log level string."""
        return self._level

    @classmethod
    def from_copilot_dir(cls, workspace_root: Path) -> "LoggingConfig":
        """Factory: .copilot/logging.yaml first, then package _default_logging.yaml."""
        project_yaml = workspace_root / ".copilot" / "logging.yaml"
        if project_yaml.exists():
            return cls(project_yaml, workspace_root)
        package_default = Path(__file__).parent / "_default_logging.yaml"
        return cls(package_default, workspace_root)

    def apply(self) -> None:
        """Configure Python logging: create log directory if absent, then basicConfig.

        Note: mkdir + basicConfig in one method is a justified YAGNI choice — mkdir is
        a 1-line precondition, not a separate reason-to-change.
        """
        self._log_file_path.parent.mkdir(parents=True, exist_ok=True)
        logging.basicConfig(
            level=self._level,
            format=self._format,
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(self._log_file_path, encoding="utf-8"),
            ],
            force=True,
        )
