# Architectural Principles

**Status:** Binding contract for all implementation work
**Read when:** Start of every implementation session — referenced from `.github/.copilot-instructions.md`
**Last updated:** 2026-03-12

---

## 0. Primacy of This Document

These principles are **laws, not suggestions**. A code change that violates these principles is **REJECTED** during code review, even if all tooling gates pass. Tooling gates (ruff, mypy, coverage) validate *form*. This document validates *architecture*.

> **Agents:** read this document at the start of every implementation session. The question "may I write it this way?" is answered by this document, not by whether ruff complains.

---

## 1. SOLID

### 1.1 SRP — Single Responsibility Principle

A class has exactly one reason to change.

**Binding rules:**
- A class with more than one logical responsibility is a God Class. Always split.
- Methods that persist state, read state, and execute business logic do not belong in the same class.
- Test whether you can describe the class in one sentence without "and" — if not, there is an SRP violation.

**Anti-patterns:**
```python
# ❌ WRONG — WorkEngine mixes state persistence + transition validation + hook dispatch + reconstruction
class WorkEngine:
    def _save_state(self): ...    # state persistence
    def transition(self): ...     # validation + hook dispatch
    def on_exit_phase(self): ...  # hook implementation
    def _reconstruct(self): ...   # external-source reconstruction

# ✅ CORRECT — each class has one responsibility
class StateRepository: ...        # state persistence
class WorkEngine: ...             # transition validation + dispatch
class EnforcementRunner: ...      # enforcement orchestration
class StateReconstructor: ...     # external-source reconstruction
```

### 1.2 OCP — Open/Closed Principle

Code is open for extension, closed for modification.

**Binding rules:**
- If-chains on phase names, workflow names, or action types are OCP violations. Use a registry or config-driven dispatch.
- Adding a new phase or action type must **never** require modifying an existing method. It only adds a new registration or config entry.

**Anti-pattern:**
```python
# ❌ WRONG — every new phase requires modifying this method
def transition(self, from_phase):
    if from_phase == "planning":
        self.on_exit_planning()
    elif from_phase == "research":
        self.on_exit_research()
    # new phase requires a code change here
```

**Correct pattern:** Config-driven dispatch — an enforcement config file registers actions per phase; the engine reads the registry instead of an if-chain.

### 1.3 LSP — Liskov Substitution Principle

Subclasses must be fully interchangeable with their base class.

**Binding rules:**
- `FileStateRepository` and `InMemoryStateRepository` are interchangeable in every place that accepts `IStateRepository`.
- A subclass may not tighten preconditions of the base class or weaken postconditions.
- Tests using `InMemoryStateRepository` must validate the same contracts as production tests with `FileStateRepository`.

### 1.4 ISP — Interface Segregation Principle

Clients must not be forced to implement interfaces they do not use.

**Binding rules:**
- A read-only consumer must **never** receive an interface with write methods.
- Split interfaces at the narrowest usable contract:
  ```python
  # core/interfaces.py
  class IStateReader(Protocol):
      def load(self, context: str) -> State: ...

  class IStateRepository(IStateReader, Protocol):
      def save(self, state: State) -> None: ...
  ```
- Read-only consumers → inject `IStateReader`
- Read-write consumers → inject `IStateRepository`

### 1.5 DIP — Dependency Inversion Principle

High-level modules do not depend on low-level modules. Both depend on abstractions.

**Binding rules:**
- Direct instantiation (`SomeManager()`) inside `execute()` of a tool is forbidden. All dependencies via constructor injection.
- Interfaces for external systems (file, git, external API) live in `core/interfaces/` — never in `managers/`.
- The concrete implementation may only be instantiated at the composition root (tool layer or server startup).

**Anti-pattern:**
```python
# ❌ WRONG — tool instantiates directly
async def execute(self, params):
    manager = SomeManager(workspace_root=Path.cwd())
    engine = WorkEngine(workspace_root=Path.cwd(), manager=manager)

# ✅ CORRECT — dependency injected via constructor
class WorkTool(BaseTool):
    def __init__(self, engine: IWorkEngine | None = None) -> None:
        self._engine = engine or WorkEngine.create_default()
```

---

## 2. DRY + SSOT — Don't Repeat Yourself + Single Source of Truth

**Binding rules:**
- Every fact in the system has exactly **one authoritative location**. All other locations reference or read from it.
- Any config file defining a list of valid values (branch types, phase names, action types) is the SSOT. Duplicating that list as a regex alternation or hardcoded set elsewhere is a violation.
- Two classes independently reading the same config file without a shared interface is a DRY violation.

---

## 3. Config-First

Business knowledge needed in multiple places is **always** stored in config, never hardcoded.

**Binding rules:**
- Phase names, workflow names, subphase names, commit-type mappings, branch types, deliverable gates: **always in config** (e.g., YAML), never as string literals in Python.
- An `if phase_name == "implementation"` in production code is a Config-First violation.
- The config loader is responsible for fail-fast validation. Code that reads config must never silently treat missing fields as "normal".
- **SSOT for config**: one reader class per config file. No two classes independently reading the same file.

**Combination validation rule:**
Config loaders raise `ConfigError` for logically inconsistent combinations (e.g., a flag enabled while its required companion field is empty). These are detected at startup, not at runtime.

---

## 4. Fail-Fast

Errors are detected as early as possible, as close to the source as possible.

**Binding rules:**
- Configuration errors (missing fields, inconsistent values) are detected at **startup**, not at runtime of a user action.
- An unknown action type in an enforcement config → `ConfigError` on startup. Never a `KeyError` at execution time.
- Missing config files → explicit `FileNotFoundError` with path, never `None` return.
- Combination validations are checked in the Pydantic loader via `model_validator`, not in the consumer.

---

## 5. CQS — Command/Query Separation

Methods that change state (commands) and methods that read state (queries) are strictly separated.

**Binding rules:**
- A method returns **either** a value (query) **or** mutates state (command) — never both.
- Value objects returned as query results are **frozen**: `model_config = ConfigDict(frozen=True)`. The type system enforces that queries cannot mutate.
- `get_state()` and similar read methods are pure queries — they **never** call `save()`.

```python
# ✅ Frozen value object as query result
class WorkState(BaseModel):
    model_config = ConfigDict(frozen=True)
    context: str
    workflow_name: str
    current_phase: str
    # ... all fields immutable
```

---

## 6. ISP in Practice — Narrow Interfaces

See also 1.4. Concrete application:

| Consumer | Interface | Reason |
|---|---|---|
| Read-only consumer (e.g., decoder) | `IStateReader` | read-only |
| Read-only consumer (e.g., resolver) | `IStateReader` | read-only |
| State engine | `IStateRepository` | reads and writes |
| Enforcement runner | `IStateRepository` | writes execution state |

All `IStateReader` and `IStateRepository` interfaces live in `core/interfaces/`. Never in `managers/`.

---

## 7. Law of Demeter

Talk to direct friends, not to their friends.

**Binding rule:**
- `tool.engine.state_repo.load(context)` is a violation. Tool talks to engine, engine talks to StateRepository.
- Tool layer knows: the engine, config. Tool layer does **not** know: `StateRepository`, `AtomicWriter`, internal infrastructure classes.
- Depth of dependency chain is at most 2 layers from the tool.

---

## 8. Explicit over Implicit

No silent fallbacks, no implicit conventions that are not visible in code.

**Binding rules:**
- No `None` as a fallback for a required configuration value → `ConfigError`.
- No silent default that hides an error. Prefer a hard error at the right moment over a silent non-value that causes an `AttributeError` three layers later.
- Code tells the story: class variables, type annotations, and Pydantic constraints are the primary communication tools. Comments supplement; they do not tell the story.

---

## 9. YAGNI — You Aren't Gonna Need It

Do not write code for hypothetical future needs.

**Binding rules:**
- No migration code for scenarios that do not exist now.
- No backward-compat layer for deprecated parameters longer than one release cycle.
- No abstraction layer for a concern that today has only one implementation (unless testability requires it).
- No configurable flag for behavior that should always be the same.

---

## 10. Cohesion — Methods Belong to Their Domain

**Binding rule:**
- A method that exclusively needs domain X knowledge belongs in the class that models domain X.
- Example: `extract_issue_number(branch)` belongs in a git-conventions config class, not in a state engine. The method answers a question about git conventions.
- When in doubt: "Is this a question about X?" If yes, the method belongs with X.

---

## 11. Dependency Injection as Default

**Binding rules:**
- Constructor injection is the default. `execute()` never instantiates a dependency itself.
- All production dependencies are injectable. Tests inject a fake/in-memory variant.
- Composition root: only server startup and the tool layer may instantiate concrete implementations.
- `BaseTool.__init__` accepts optional dependencies with `None` default, resolved via factory method:
  ```python
  def __init__(self, engine: IWorkEngine | None = None) -> None:
      self._engine = engine or WorkEngine.create_default()
  ```

---

## 12. No Import-Time Side Effects

**Binding rule:**
- Module-level code that reads files, makes network requests, or initializes singletons = forbidden.
- A `config = AppConfig.load()` as a module-level statement causes `FileNotFoundError` on import in tests. Use `ClassVar` with lazy init.
- All singletons use the `ClassVar` pattern: the instance is created at the first call to `.load()`, not at import.

---

## 13. Enforcement is Config-First

**Binding rule:**
- Behavior that "triggers at phase X" or "runs after tool Y" is configured in a YAML enforcement file, not hardcoded in Python.
- Every new enforcement action = one registration in the enforcement runner's action registry + one entry in the enforcement config. Never an if-chain in the engine or a tool.
- Tools declare their own enforcement event as a class variable: `enforcement_event: str | None = None`.

---

## Quick Reference — Prohibited Patterns

| Pattern | Violation | Alternative |
|---|---|---|
| `if phase_name == "implementation":` | Config-First, OCP | Config determines; code dispatches on type |
| `SomeManager()` in `execute()` | DIP, SRP | Constructor injection |
| `if sub_phase == "x": commit_type = "y"` | DRY, Config-First | `commit_type_map` in config file |
| Two classes reading the same config file | SSOT, DRY | One reader class, singleton |
| `module_var = Config.load()` at module level | Fail-Fast (import side effect) | ClassVar + lazy init |
| Read-only consumer injected with write interface | ISP | Use narrower read-only interface |
| `get_state()` calls `save()` | CQS | Query returns, command mutates |
| Mutating a frozen value object | CQS | Create new instance via command method |
| `tool.engine.state_repo.load()` | Law of Demeter | `tool.engine.get_state(context)` |
| Hardcoded regex/list with type or phase names | DRY, Config-First | Build from config at startup |
| Inconsistent config combination (flag on + map empty) | Fail-Fast | `ConfigError` on startup |
| Migration code for deprecated parameter | YAGNI | Flag-day: remove directly |
