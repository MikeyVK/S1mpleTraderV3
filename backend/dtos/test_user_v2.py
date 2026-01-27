# backend/dtos/test_user_v2.py
# template=dto version=6fefd064 created=2026-01-27T15:18Z updated=
"""TestUserV2 DTO module.

Data Transfer Object for testuserv2.

@layer: Domain > DTOs
@dependencies: pydantic
@responsibilities: Data validation, Type safety
"""

# Standard library

# Third-party
from pydantic import BaseModel, Field

# Project modules

class TestUserV2(BaseModel):
    """User data after template fixes
    
    Data Transfer Object for testuserv2.
    
    Fields:
        id: User ID
        name: User name
        email: User email
    """
    id: int = Field(
        description="User ID"
    )
    name: str = Field(
        description="User name"
    )
    email: str = Field(
        description="User email"
    )

    model_config = {
        "frozen": True,
        "extra": "forbid",
        "json_schema_extra": {
            "examples": [
                {
                    "email": "jane@test.com",
                    "id": 2,
                    "name": "Jane"
                }
            ]
        }
    }
