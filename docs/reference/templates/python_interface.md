# Python Interface Template

**Layer:** Core Interfaces
**Inherits:** `typing.Protocol`
**Path:** `backend/core/interfaces/<name>.py`

## Purpose
Defines abstract contracts for dependencies to ensure loose coupling and testability.

## Structure

```python
"""
<Docstring>

@layer: Core Interfaces
@dependencies: [typing]
"""
from typing import Protocol

class <InterfaceName>(Protocol):
    """<Docstring>"""
    
    def method_name(self, arg: str) -> bool:
        """<Method Docstring>"""
        ...
```
