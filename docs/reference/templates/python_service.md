# Python Service Template

**Layer:** Services
**Inherits:** None (Standalone Class)
**Path:** `services/<name>_service.py`

## Purpose
Encapsulates business logic. We use 3 flavors: **Orchestrator**, **Command**, and **Query**.

## Variants

### 1. Orchestrator Service
High-level coordination of multiple services.

```python
"""
<Docstring>

@layer: Service (Orchestrator)
@dependencies: [DependencyA, DependencyB]
"""
class <Name>Service:
    def __init__(self, dep_a: DepA, dep_b: DepB):
        self._dep_a = dep_a
        self._dep_b = dep_b
```

### 2. Command Service (Write)
Handles data mutation, transactions, and validation.

```python
"""
<Docstring>

@layer: Service (Command)
"""
class <Name>Service:
    def execute_command(self, cmd: CommandDTO) -> None:
        # Validate
        # Transact
        pass
```

### 3. Query Service (Read)
Handles data retrieval and optimization.

```python
"""
<Docstring>

@layer: Service (Query)
"""
class <Name>Service:
    def get_data(self, query: QueryDTO) -> ResultDTO:
        # Fetch
        return result
```
