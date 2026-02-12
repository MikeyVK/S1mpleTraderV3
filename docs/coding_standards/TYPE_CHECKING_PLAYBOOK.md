# Type Checking Playbook

## Purpose

This document standardizes how we resolve typing issues so that **all agents** (and humans) apply the **same** fixes in the **same order**.

**Goals:**
- Keep CI/PR gates strict and consistent.
- Avoid “random” workarounds (casts vs disables vs global config changes).
- Prefer durable type fixes over silencing.

---

## Non‑Negotiables

1. **No global disables** to “make the checker shut up”.
   - Do not relax `mypy` strictness globally.
   - Do not mass-disable Pyright diagnostics in `pyrightconfig.json` unless explicitly approved as a project policy.

2. **No blind casting of untrusted data.**
   - Never `cast(...)` external input (events, JSON, dict payloads) without a runtime check or validation first.

3. **If you must ignore, ignore precisely.**
   - Prefer error-code specific ignores.
   - Add a short rationale comment.

---

## Resolution Order (Mandatory)

When a typing issue appears, follow this sequence:

### 1) Fix the types at the source
- Add missing annotations (parameters and return types).
- Tighten `Any` where possible.
- Prefer concrete types (e.g., `Mapping[str, str]`, `Sequence[int]`) over `Any`.

### 2) Narrow types using runtime checks
Use narrowing before using `cast` or ignores.

**Patterns:**
- `assert x is not None`
- `if x is None: ...`
- `isinstance(x, SomeType)`
- `match` on tagged unions / Literals

Example:
```python
value = dto.optional_field
assert value is not None  # narrows Optional[T] -> T
use(value)
```

### 3) Improve the model/type design
Prefer structural fixes that reduce future friction.

**Common tools:**
- `TypedDict` for dict-shaped payloads
- `Protocol` for dependency injection / interfaces
- `Literal` for constrained strings
- `NewType` for typed IDs
- `@overload` for factories/helpers

### 4) Contain dynamic edges (boundaries)
At system boundaries, convert “dynamic” input to typed objects once.

**Preferred boundary patterns:**
- Parse/validate into a Pydantic model (DTO) at the boundary.
- Convert to a typed dataclass/model and pass that through the core.

### 5) Targeted ignore (last resort)
Only after 1–4 are not feasible.

**Mypy:**
```python
something()  # type: ignore[call-arg]  # rationale: third-party stub mismatch
```

**Pyright/Pylance:**
```python
x = something()  # pyright: ignore[reportGeneralTypeIssues]  # rationale: known false positive
```

Rules:
- Ignore **one line** or the smallest possible block.
- Always include a short rationale.
- Never use bare `# type: ignore` unless there is no error code available.

### 6) Casting (very last)
Use `cast(...)` only when:
- you have an invariant the type checker cannot prove, and
- you can defend it with a runtime check, validation, or documented guarantee.

Example:
```python
from typing import cast

assert isinstance(x, str)
value = cast(str, x)
```

---

## Standard Workarounds (Approved)

### A) Pydantic FieldInfo false positives (often in tests)
Some IDE type engines can treat Pydantic fields as `FieldInfo` instead of the runtime value.

**Preferred fix:** use `getattr` to avoid the false-positive member access.
```python
assert getattr(signal, "initiator_id").startswith("TCK_")
```

**Acceptable alternative:** normalize to a concrete type.
```python
initiator_id = str(signal.initiator_id)
assert initiator_id.startswith("TCK_")
```

### B) Optional fields
Prefer narrowing:
```python
value = dto.optional_field
assert value is not None
assert value.startswith("ABC")
```

### C) Generics + `Field(...)` edge cases
If the runtime is correct but mypy/IDE still complains, use a **code-specific** ignore with rationale.
```python
from pydantic import Field

factors: list[ContextFactor] = Field(default_factory=list)  # type: ignore[valid-type]  # pydantic typing edge
```

### D) Third-party missing/incorrect stubs
Prefer:
- installing typed stub packages (e.g., `types-PyYAML`) if available, or
- adding small local stubs in the repo when needed.

Only if unavoidable, use targeted ignore(s) with rationale.

---

## What Agents Should Do (Short Checklist)

- Apply fixes in the **Resolution Order** above.
- Prefer `assert` / `isinstance` narrowing over `cast`.
- If ignoring: use **error-code specific** ignores + a brief reason.
- Avoid global config changes to silence issues.

