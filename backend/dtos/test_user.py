# backend/dtos/test_user.py
# template=dto version=6fefd064 created=2026-01-27T15:13Z updated=
"""TestUser DTO module.

Data Transfer Object for testuser.

@layer: Domain
@dependencies: pydantic
@responsibilities: Data validation, Type safety, Immutable data container
"""

from pydantic import BaseModel, Field

class TestUser(BaseModel):
    """User data transfer object for testing scaffold output
    
    Data Transfer Object for testuser.
    
    Fields:
        id: Unique user identifier
        name: User full name
        email: User email address
    """
    id: int = Field(
        description="Unique user identifier"
    )
    name: str = Field(
        description="User full name"
    )
    email: str = Field(
        description="User email address"
    )

    model_config = {
        "frozen": True,
        "extra": "forbid",
        "json_schema_extra": {
            "examples": [
                {
                    "email": "john@example.com",
                    "id": 1,
                    "name": "John"
                }
            ]
        }
    }
