# SCAFFOLD: template=dto version=90e38d36 created=2026-01-26T09:07:19.034911Z path=D:\dev\SimpleTraderV3\tmp\.st3\TestDTO.py
"""
 module.
"""

from pydantic import BaseModel, Field

class TestDTO(BaseModel):
    """Test
    
    Data Transfer Object for testdto.
    """
    id: int
