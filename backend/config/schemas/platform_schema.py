# backend/config/schemas/platform_schema.py
"""
Pydantic schemas for platform-level configuration.

@layer: Backend (Config)
@dependencies: []
@responsibilities:
    - Define PlatformConfig schema (global platform settings)
    - Define LoggingConfig schema (logging profiles and levels)
    - Define CoreConfig schema (language, timezone, paths)
"""

# Standard library
from pathlib import Path
from typing import Dict, List

# Third-party
from pydantic import BaseModel, Field


def _default_project_root() -> Path:
    """Factory function for default project root."""
    return Path.cwd()


class LoggingConfig(BaseModel):
    """Configuration for the logging system."""

    profile: str = Field(
        default="development",
        description="Active logging profile (development, production, backtest, silent)",
    )
    profiles: Dict[str, List[str]] = Field(
        default_factory=lambda: {
            "development": [
                "DEBUG",
                "INFO",
                "SETUP",
                "MATCH",
                "FILTER",
                "POLICY",
                "RESULT",
                "TRADE",
                "WARNING",
                "ERROR",
                "CRITICAL",
            ],
            "production": ["INFO", "TRADE", "WARNING", "ERROR", "CRITICAL"],
            "backtest": ["SETUP", "RESULT", "TRADE", "ERROR", "CRITICAL"],
            "silent": ["ERROR", "CRITICAL"],
        },
        description="Logging profile definitions (profile -> allowed levels)",
    )


class CoreConfig(BaseModel):
    """Core platform settings."""

    language: str = Field(
        default="en", description="Language code for i18n (en, nl, etc.)"
    )
    timezone: str = Field(default="UTC", description="Timezone for timestamps")
    project_root: Path = Field(
        default_factory=_default_project_root,
        description="Absolute path to project root directory",
    )


class PlatformConfig(BaseModel):
    """Root platform configuration."""

    core: CoreConfig = Field(default_factory=CoreConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
