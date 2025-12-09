# Python DTO Template

**Layer:** DTOs (Data Transfer Objects)
**Inherits:** `pydantic.BaseModel`
**Path:** `backend/dtos/<domain>/<name>.py`

## Purpose
Defines immutable data structures for passing data between layers (Strategy, Execution, etc.).

## Structure

```python
"""
<Name> DTO - <Description>.

@layer: DTOs
@dependencies: [pydantic]
"""
from datetime import datetime, timezone
from pydantic import BaseModel, Field, field_validator
from backend.utils.id_generators import generate_id

class <Name>(BaseModel):
    """<Docstring>"""
    
    # Primary identifier
    <name_lower>_id: str = Field(
        default_factory=generate_id,
        description="Unique identifier"
    )

    # Core data fields
    field_name: str = Field(..., description="Description")

    # Timestamp
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Creation timestamp in UTC"
    )

    model_config = {
        "frozen": True,
        "json_schema_extra": {
            "examples": [{ ... }]
        }
    }
```
