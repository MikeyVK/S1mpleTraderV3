"""Configuration settings for the MCP server."""
import os
from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic import BaseModel, Field


class LogSettings(BaseModel):
    """Logging configuration settings."""

    level: str = "INFO"
    audit_log: str = "logs/mcp_audit.log"


class ServerSettings(BaseModel):
    """Server configuration settings."""

    name: str = "st3-workflow"
    version: str = "1.0.0"
    workspace_root: str = Field(default_factory=os.getcwd)


class GitHubSettings(BaseModel):
    """GitHub integration settings."""

    owner: str = "MikeyVK"
    repo: str = "S1mpleTraderV3"
    project_number: int = 1
    token: Optional[str] = Field(default=None, validate_default=True)


class Settings(BaseModel):
    """Main settings container."""

    server: ServerSettings = Field(default_factory=ServerSettings)
    logging: LogSettings = Field(default_factory=LogSettings)
    github: GitHubSettings = Field(default_factory=GitHubSettings)

    @classmethod
    def load(cls, config_path: Optional[str] = None) -> "Settings":
        """Load settings from a YAML file and environment variables."""
        config_data: dict[str, Any] = {}

        # Determine config path
        if config_path:
            path = Path(config_path)
        else:
            path = Path(os.environ.get("MCP_CONFIG_PATH", "mcp_config.yaml"))

        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                config_data = yaml.safe_load(f) or {}

        # Override with environment variables
        if env_token := os.environ.get("GITHUB_TOKEN"):
            if "github" not in config_data:
                config_data["github"] = {}
            config_data["github"]["token"] = env_token

        if env_log_level := os.environ.get("MCP_LOG_LEVEL"):
            if "logging" not in config_data:
                config_data["logging"] = {}
            config_data["logging"]["level"] = env_log_level

        return cls(**config_data)


# Global settings instance
settings = Settings.load()
