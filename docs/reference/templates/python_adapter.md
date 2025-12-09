# Python Adapter Template

**Layer:** Adapters (Infrastructure)
**Inherits:** `Protocol` (Interface definition) + Implementation
**Path:** `backend/adapters/<name>.py`

## Purpose
Abstracts external dependencies (APIs, Databases, Systems) behind a clean interface.

## Structure

```python
"""
<Name> - <Description>.

@layer: Adapters
"""
from typing import Protocol, Any

# 1. The Interface
class I<Name>(Protocol):
    def operation(self, param: str) -> Any: ...

# 2. The Implementation
class <Name>:
    """Implementation of I<Name>."""
    
    def __init__(self, config: Any):
        self._config = config

    def operation(self, param: str) -> Any:
        # Implementation logic
        pass
```
