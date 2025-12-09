# Python Schema Template

**Layer:** Config / Schemas
**Inherits:** `pydantic.BaseModel`
**Path:** `backend/config/schemas/<name>.py` (or similar)

## Purpose
Defines data structures, configuration models, and validation logic using Pydantic.

## Structure

```python
"""
<Docstring>

@layer: Config (Schemas)
@dependencies: [pydantic]
"""
from pydantic import BaseModel, Field

class <ModelName>(BaseModel):
    """<Docstring>"""
    
    field_name: str = Field(..., description="<Description>")
    optional_field: int = Field(default=0, description="<Description>")
```
