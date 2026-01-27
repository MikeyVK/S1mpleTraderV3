# backend/dtos/product.py
# template=dto version=6fefd064 created=2026-01-27T15:27Z updated=
"""Product DTO module.

Data Transfer Object for product.

@layer: Domain > DTOs
@dependencies: pydantic
@responsibilities: Data validation
"""

# Standard library

# Third-party
from pydantic import BaseModel, Field

# Project modules


class Product(BaseModel):
    """Product data
    
    Data Transfer Object for product.
    
    Fields:
        id: Product ID
        name: Product name
        price: Product price
    """
    id: int = Field(
        description="Product ID"
    )
    name: str = Field(
        description="Product name"
    )
    price: float = Field(
        description="Product price"
    )

    model_config = {
        "frozen": True,
        "extra": "forbid",
        "json_schema_extra": {
            "examples": [
                {
                    "id": 1,
                    "name": "Widget",
                    "price": 9.99
                }
            ]
        }
    }
