# SCAFFOLD: template=dto version=1.0 created=2026-01-26T07:23:39.258733+00:00 path=TestWhitespaceDTO.py

""" module."""


from pydantic import BaseModel, Field

class TestWhitespaceDTO(BaseModel):
    """Test DTO for whitespace
    
    Data Transfer Object for testwhitespacedto.
    """

    id: int
    name: str