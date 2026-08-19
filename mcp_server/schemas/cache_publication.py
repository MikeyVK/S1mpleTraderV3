# c:\temp\pgmcp\mcp_server\schemas\cache_publication.py
# template=dto version=0d83ee77 created=2026-06-20T18:39Z updated=
"""CachePublication DTO module.

Data Transfer Object for CachePublication.

@layer: DTOs
@dependencies: pydantic.BaseModel
@responsibilities: Data validation, type safety
"""

from __future__ import annotations

# Third-party
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

HexUUID = Annotated[str, StringConstraints(pattern=r"^[a-f0-9]{32}$")]


class CachePublication(BaseModel):
    """CachePublication DTO."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    run_id: HexUUID | None = None
    success: bool = True
    error_code: str | None = None
