# mcp_server/config/settings.py
"""
Configuration settings for the MCP server.

Defines runtime settings loaded from environment variables and optional YAML
overrides for server, logging, and GitHub integration.

@layer: Backend (Config)
@dependencies: [importlib.metadata, os, pathlib, pydantic, yaml]
@responsibilities:
    - Define typed settings models for MCP server runtime configuration
    - Load settings from environment variables with YAML overlay support
    - Resolve server version metadata from installed package information
"""

# Standard library
import os
from importlib import metadata
from pathlib import Path
from typing import Any

# Third-party
import yaml
from pydantic import BaseModel, Field


def _default_server_version() -> str:
    """Resolve server version from installed package metadata."""
    for package_name in ("mcp_server", "simpletraderv3"):
        try:
            return metadata.version(package_name)
        except metadata.PackageNotFoundError:
            continue

    raise metadata.PackageNotFoundError(
        "Unable to resolve installed package metadata for 'mcp_server' or 'simpletraderv3'."
    )


class LogSettings(BaseModel):
    """Logging configuration settings."""

    level: str = "INFO"
    audit_log: str = ".logs/mcp_audit.log"


class ServerSettings(BaseModel):
    """Server configuration settings."""

    name: str = "st3-workflow"
    version: str = Field(default_factory=_default_server_version)
    workspace_root: str = Field(default_factory=os.getcwd)
    config_root: str | None = None


class GitHubSettings(BaseModel):
    """GitHub integration settings."""

    owner: str = "MikeyVK"
    repo: str = "S1mpleTraderV3"
    project_number: int = 1
    token: str | None = Field(default=None, validate_default=True)


class Settings(BaseModel):
    """Main settings container."""

    server: ServerSettings = ServerSettings()
    logging: LogSettings = LogSettings()
    github: GitHubSettings = GitHubSettings()

    @classmethod
    def from_env(cls) -> "Settings":
        """Load settings from env vars with optional MCP_CONFIG_PATH overlay."""
        config_data: dict[str, Any] = {}

        path_value = os.environ.get("MCP_CONFIG_PATH")
        if path_value:
            path = Path(path_value)
            if path.exists():
                with path.open(encoding="utf-8") as file_handle:
                    config_data = yaml.safe_load(file_handle) or {}

        server_data = config_data.setdefault("server", {})
        github_data = config_data.setdefault("github", {})
        logging_data = config_data.setdefault("logging", {})

        if env_name := os.environ.get("MCP_SERVER_NAME"):
            server_data["name"] = env_name
        if env_workspace_root := os.environ.get("MCP_WORKSPACE_ROOT"):
            server_data["workspace_root"] = env_workspace_root
        if env_config_root := os.environ.get("MCP_CONFIG_ROOT"):
            server_data["config_root"] = env_config_root

        if env_owner := os.environ.get("GITHUB_OWNER"):
            github_data["owner"] = env_owner
        if env_repo := os.environ.get("GITHUB_REPO"):
            github_data["repo"] = env_repo
        if env_project_number := os.environ.get("GITHUB_PROJECT_NUMBER"):
            github_data["project_number"] = int(env_project_number)
        if env_token := os.environ.get("GITHUB_TOKEN"):
            github_data["token"] = env_token

        if env_log_level := os.environ.get("LOG_LEVEL"):
            logging_data["level"] = env_log_level

        return cls(**config_data)
