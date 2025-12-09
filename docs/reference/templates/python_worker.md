# Python Worker Template

**Layer:** Workers
**Inherits:** `BaseWorker[InputDTO, OutputDTO]`
**Path:** `backend/workers/<type>/<name>.py`

## Purpose
Stateless unit of logic that processes an Input DTO and produces an Output DTO.

## Structure

```python
"""
<Name> - <Description>.

@layer: Workers
@dependencies: [InputDTO, OutputDTO]
"""
from backend.core.interfaces.base_worker import BaseWorker
from backend.core.enums import DispositionType

class <Name>(BaseWorker[InputDTO, OutputDTO]):
    """<Docstring>"""

    def __init__(self, strategy_cache: IStrategyCache):
        super().__init__()
        self._strategy_cache = strategy_cache

    async def process(self, input_data: InputDTO) -> OutputDTO:
        """Process input and return output."""
        # 1. Extract
        # 2. Transform / Calculate
        # 3. Construct Output
        return OutputDTO(...)

    def get_disposition(self, output: OutputDTO) -> DispositionType:
        """Determine next step."""
        return DispositionType.CONTINUE
```
