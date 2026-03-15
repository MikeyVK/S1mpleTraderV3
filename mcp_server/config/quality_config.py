"""Legacy compatibility wrapper for QualityConfig during C_LOADER migration."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import ValidationError

from mcp_server.config.loader import ConfigLoader
from mcp_server.config.schemas.quality_config import (
    ArtifactLoggingConfig,
    CapabilitiesMetadata,
    ExecutionConfig,
    GateScope,
    JsonViolationsParsing,
    QualityGate,
    SuccessCriteria,
    TextViolationsParsing,
    ViolationDTO,
)
from mcp_server.config.schemas.quality_config import (
    QualityConfig as _QualityConfigSchema,
)
from mcp_server.core.exceptions import ConfigError

__all__ = [
    "ArtifactLoggingConfig",
    "CapabilitiesMetadata",
    "ExecutionConfig",
    "GateScope",
    "JsonViolationsParsing",
    "QualityConfig",
    "QualityGate",
    "SuccessCriteria",
    "TextViolationsParsing",
    "ViolationDTO",
]


class QualityConfig(_QualityConfigSchema):
    """Compatibility surface for pre-C_LOADER consumers."""

    @classmethod
    def load(cls, path: Path | None = None) -> QualityConfig:
        config_path = Path(".st3/quality.yaml") if path is None else Path(path)
        if not config_path.exists():
            raise FileNotFoundError(
                f"Quality config not found: {config_path}\n"
                "Expected location: .st3/quality.yaml\n"
                "Hint: Add .st3/quality.yaml to define available gate tools"
            )

        loader = ConfigLoader(config_root=config_path.parent)
        try:
            loaded = loader.load_quality_config(config_path=config_path)
        except ConfigError as exc:
            cause = exc.__cause__
            if isinstance(cause, (yaml.YAMLError, ValidationError, ValueError)):
                raise cause from exc
            raise

        return cls.model_validate(loaded.model_dump())
