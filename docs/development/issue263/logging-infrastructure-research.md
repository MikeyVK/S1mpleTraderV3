<!-- docs\development\issue263\logging-infrastructure-research.md -->
<!-- template=research version=8b7bb3ab created=2026-03-22T20:00Z updated= -->
# Logging Infrastructure for copilot_orchestration Package

**Status:** DRAFT  
**Version:** 1.0  
**Last Updated:** 2026-03-22

---

## Purpose

Design YAML-driven logging for all hooks so that failures are never silent and enforcement decisions are auditable, keeping config contained in the package.

## Scope

**In Scope:**
LoggingConfig YAML loader, _default_logging.yaml (package default), .copilot/logging.yaml (project override), logging calls in all 7 hook/config files, unit tests for LoggingConfig

**Out of Scope:**
Backend/MCP server logging, external log aggregation, log rotation policy, structured JSON logging

## Prerequisites

Read these first:
1. C_V2.8–C_V2.11 + QA cycles complete (commit e2d90b0)
2. Root .md files deleted, .github/agents/ wrappers as SSOT (commit 6c28edb)
3. 71/71 tests green, 5/5 quality gates green
---

## Problem Statement

All hooks in the copilot_orchestration package have silent failure paths. Two modules declare a logger but make zero calls. Crashes in __main__ entrypoints (FileNotFoundError, JSONDecodeError, OSError) propagate uncaught and produce no audit trail. Enforcement decisions (stop/allow) in stop_handover_guard are unobservable.

## Research Goals

- Define LoggingConfig YAML loader following SubRoleRequirementsLoader.from_copilot_dir() pattern
- Identify all silent failure and silent fallback paths per file
- Specify exact logging calls (level + message) per file
- Assess whether full implementation fits in a single TDD cycle
- Define test coverage requirements for LoggingConfig loader

---

## Background

The package has two modules with a declared but unused logger (detect_sub_role.py, requirements_loader.py). Five other files have no logger at all. Per-file analysis done in prior session identified: 4 critical crash paths, 6 silent fallbacks, and 8 observability gaps. Agreed levels: ERROR (crashes), WARNING (unexpected fallbacks/ConfigError caught silently), INFO (key decisions per hook-run), DEBUG (all intermediate steps). Production default: WARNING.

---

## Findings

Full implementation spans: 1 new config class (LoggingConfig), 1 package default YAML, 1 project override YAML, ~50–70 logging calls across 7 files, unit tests for loader. Estimated: 2–3 TDD sub-cycles. Fits in 1 cycle if scope is kept tight (no DI refactor for logger, no ILoggingConfig Protocol unless needed).

## Open Questions

~~❓ Should LoggingConfig be wired via DI (ILoggingConfig Protocol) or via module-level basicConfig call in each __main__?~~
✅ **Resolved:** `ILoggingConfig` Protocol in `contracts/interfaces.py` voor patroon-consistentie. `log_config.apply(workspace_root)` als eerste call in `main()`.

~~❓ Should .copilot/logging.yaml be committed (project default) or gitignored (developer override only)?~~
✅ **Resolved:** Gitignored — developer-local override.

~~❓ Is a file handler required in the default config, or stdout only for now?~~
✅ **Resolved:** File handler in package default → `.copilot/logs/orchestration.log` (gitignored).


---

## Per-File Analysis

### Summary Table

| File | Logger declared | Logger calls | Critical crashes | Silent fallbacks |
|---|---|---|---|---|
| `detect_sub_role.py` | ✅ yes | 0 | 2 (`RuntimeError`, `OSError`) | 2 (`read_sub_role` returns None) |
| `stop_handover_guard.py` | ❌ no | 0 | 1 (`ConfigError` re-raised unlogged) | 1 (`ConfigError` caught → allow, no audit) |
| `notify_compaction.py` | ❌ no | 0 | 2 (`JSONDecodeError`, `OSError`) | 1 (state file absent = WARNING) |
| `pre_compact_agent.py` | ❌ no | 0 | 2 (`OSError` on 2 write_text calls) | 3 (per-tier extraction = black box) |
| `session_start_imp.py` | ❌ no | 0 | 1 (`OSError` snapshot write) | 1 (git stderr discarded) |
| `session_start_qa.py` | ❌ no | 0 | 1 (`OSError` snapshot write) | 1 (git stderr discarded) |
| `requirements_loader.py` | ✅ yes | 0 | 2 (`YAMLError`, `ValidationError`) | 1 (project YAML fallback to package default) |
| `_paths.py` | ❌ no | 0 | 1 (`RuntimeError` propagates bare) | 0 |

**Totals: 4 files missing logger, 12 crash paths unlogged, 9 silent fallbacks**

---

### `detect_sub_role.py` (hooks)
**Priority:** HIGH — runs on every prompt submission.

| Path | Level | Message |
|---|---|---|
| Exploration mode active | WARNING | `"Exploration mode: no state file path → skipping sub_role detection"` |
| Role read from argv | DEBUG | `"role=%s prompt_len=%d"` |
| Step 1 regex match | DEBUG | `"Step1 regex match=%r"` |
| Step 2 difflib match | DEBUG | `"Step2 difflib match=%r score=%.2f"` |
| Sub-role detected | INFO | `"Sub-role detected: %s (role=%s)"` |
| No sub-role matched | WARNING | `"No sub-role matched — prompt does not start with a known sub-role name"` |
| State file written | DEBUG | `"State file written: %s"` |
| `find_workspace_root()` RuntimeError | ERROR | `"Cannot find workspace root: %s"` |
| `write_text()` OSError | ERROR | `"Failed to write sub-role state file %s: %s"` |

---

### `stop_handover_guard.py` (hooks)
**Priority:** CRITICAL — enforcement decisions must be auditable.

| Path | Level | Message |
|---|---|---|
| Entry: stop hook active flag | DEBUG | `"evaluate_stop_hook: stop_hook_active=%s"` |
| Sub-role read | DEBUG | `"read_sub_role result: %r"` |
| Enforcement: allows stop | INFO | `"ALLOW stop: %s"` |
| Enforcement: blocks stop | INFO | `"BLOCK stop: %s — crosschat handover required"` |
| ConfigError caught → allow (silent fallback) | WARNING | `"ConfigError on get_requirement(%r) → defaulting to allow: %s"` |
| ConfigError on requires_crosschat_block re-raised | ERROR | `"ConfigError on requires_crosschat_block(role=%r sub_role=%r): %s"` |

---

### `notify_compaction.py` (hooks)
**Priority:** HIGH — silent crash loses compaction context permanently.

| Path | Level | Message |
|---|---|---|
| Role + path resolved | DEBUG | `"notify_compaction: role=%s state_path=%s exists=%s"` |
| JSON parsed from stdin | DEBUG | `"Parsed compaction event: keys=%s"` |
| Sub-role extracted | DEBUG | `"Sub-role from state=%r"` |
| Output assembled | DEBUG | `"Compaction output written (%d chars)"` |
| State file absent | WARNING | `"Sub-role state file not found: %s — proceeding without sub-role context"` |
| `json.loads()` JSONDecodeError | ERROR | `"Cannot parse compaction event from stdin: %s"` |
| `read_text()` OSError | ERROR | `"Cannot read state file %s: %s"` |

---

### `pre_compact_agent.py` (hooks)
**Priority:** MEDIUM — complex multi-tier extraction, entire logic is currently a black box.

| Path | Level | Message |
|---|---|---|
| Entry: chat_id, transcript count | DEBUG | `"pre_compact: chat_id=%s transcripts=%d"` |
| Tier N extraction attempted | DEBUG | `"Extracting tier %d"` |
| Tier N extraction succeeded | DEBUG | `"Tier %d succeeded: %d chars"` |
| File names extracted | DEBUG | `"Extracted %d filename(s) from transcript"` |
| Snapshot freshness decision | DEBUG | `"Snapshot fresh=%s (age=%ds, overlap=%d%%)"` |
| Transcript parse failure per tier | WARNING | `"Tier %d parse failed: %s"` |
| Empty file list (no filenames found) | WARNING | `"No filenames extracted from transcript — snapshot may be incomplete"` |
| `write_text()` OSError (session file) | ERROR | `"Failed to write session snapshot %s: %s"` |
| `write_text()` OSError (summary file) | ERROR | `"Failed to write summary file %s: %s"` |

---

### `session_start_imp.py` / `session_start_qa.py` (hooks)
**Priority:** MEDIUM — freshness decision and git failures currently invisible.

| Path | Level | Message |
|---|---|---|
| Git returncode | DEBUG | `"git log returncode=%d stdout_len=%d"` |
| Snapshot age + file overlap | DEBUG | `"snapshot_age=%ds file_overlap=%d%%"` |
| Freshness decision + reason | DEBUG | `"Snapshot fresh=%s reason=%s"` |
| Git non-zero returncode | WARNING | `"git log failed (rc=%d) — snapshot freshness check skipped"` |
| `OSError` on snapshot write | ERROR | `"Failed to write session snapshot %s: %s"` |

---

### `requirements_loader.py` (config)
**Priority:** MEDIUM — YAML loader is the foundation of all enforcement; silent failure here breaks everything.

| Path | Level | Message |
|---|---|---|
| YAML path selected (project vs package) | DEBUG | `"Loading sub-role requirements from: %s"` |
| Parse success | DEBUG | `"YAML parsed successfully"` |
| Pydantic validation success | DEBUG | `"SubRoleRequirements validated: %d roles"` |
| Project YAML not found → fallback | WARNING | `"Project YAML not found at %s — falling back to package default"` |
| `yaml.YAMLError` | ERROR | `"YAML parse error in %s: %s"` |
| `pydantic.ValidationError` | ERROR | `"YAML schema validation failed in %s: %s"` |

---

### `_paths.py` (utils)
**Priority:** LOW — only called at startup.

| Path | Level | Message |
|---|---|---|
| Sentinel found at level N | DEBUG | `"find_workspace_root: anchor=%s found at depth=%d"` |
| Filesystem root reached | ERROR | `"find_workspace_root: exhausted filesystem, no sentinel found"` |

---

## Proposed Architecture

### Decisions (confirmed)

| # | Decision | Rationale |
|---|---|---|
| 1 | `.copilot/logging.yaml` → **gitignored** | Developer-local override only; not project config |
| 2 | Log file → `.copilot/logs/orchestration.log` → **gitignored** | Team hygiene; logs stay local |
| 3 | File handler **included in package default** | User requirement: always visible in logfile |
| 4 | `ILoggingConfig` Protocol → **yes, in `contracts/interfaces.py`** | Pattern consistency with `ISubRoleRequirementsLoader` |
| 5 | `from_copilot_dir(workspace_root: Path)` | Identical signature to `SubRoleRequirementsLoader.from_copilot_dir()` |

### Coding Standards Compliance

| Principle | Status | Detail |
|---|---|---|
| **Fail-Fast (P4)** | ✅ | `__init__` raises `FileNotFoundError` / `yaml.YAMLError` at construction; path resolved at construction, not deferred |
| **Config-First (P3)** | ✅ | Log file path lives in YAML; one reader class (`LoggingConfig`) per config file |
| **Explicit over Implicit (P8)** | ✅ | No silent `None` returns; WARNING logged on fallback to package default |
| **No Import-Time Side Effects (P12)** | ✅ | `apply()` called explicitly from `main()`, never at module level |
| **DIP — Protocol leaks infra detail** | ✅ fixed | `workspace_root` resolved at construction; `ILoggingConfig.apply()` takes no args — see below |
| **SRP — `apply()` does mkdir + basicConfig** | ⚠️ documented | Two concerns in one method; justified by YAGNI (mkdir is a 1-line precondition, not a separate reason-to-change) |
| **No Import-Time Side Effects (P12)** | ✅ | `apply()` called explicitly from `main()`, never at module level |
| **YAGNI (P9)** | ✅ | No ILoggingConfig base hierarchy, no log rotation, no structured JSON |
| **Type Checking Playbook** | ✅ | `@runtime_checkable` Protocol; `isinstance` check in tests; no global disables |

### Why `apply(self) → None` instead of `apply(self, workspace_root)` (Fail-Fast + DIP)

The first design passed `workspace_root` to both `from_copilot_dir()` **and** `apply()`. This violates two principles:

- **Fail-Fast (P4):** Path resolution should happen at startup (construction), not deferred to `apply()`. If the log path is invalid, that should be detectable at `from_copilot_dir()` time.
- **DIP (P1.5 + ISP):** `ILoggingConfig.apply(workspace_root)` forces every caller to know about `workspace_root` — leaking an infrastructure detail into the Protocol.

**Fix:** `workspace_root` is passed once to `from_copilot_dir(workspace_root)`. The `__init__` resolves and stores `self._log_file_path: Path` as an absolute path. `apply()` takes no arguments.

This matches exactly how `SubRoleRequirementsLoader` works: all resolution at construction, subsequent calls are pure queries or stateless commands.

### Config files

```
src/copilot_orchestration/config/_default_logging.yaml   # package default (committed)
.copilot/logging.yaml                                     # developer override (gitignored)
.copilot/logs/orchestration.log                          # runtime output (gitignored)
```

### `_default_logging.yaml` schema

```yaml
# src/copilot_orchestration/config/_default_logging.yaml
level: WARNING
format: "%(asctime)s %(name)s %(levelname)s %(message)s"
handlers:
  stderr: {}                                         # always present
  file:
    path: .copilot/logs/orchestration.log            # relative to workspace root; resolved at construction
```

### `.copilot/.gitignore` additions

```
logging.yaml
logs/
```

_(or root `.gitignore` — implementation will check which file is already used for `.copilot/` exclusions)_

### `ILoggingConfig` Protocol

```python
# src/copilot_orchestration/contracts/interfaces.py  (extend existing file)
@runtime_checkable
class ILoggingConfig(Protocol):
    def apply(self) -> None:
        """Configure Python logging (basicConfig) + create log dir if absent."""
        ...
```

No `workspace_root` parameter — it is resolved at construction time, not injected per call.

### `LoggingConfig` class

```python
# src/copilot_orchestration/config/logging_config.py
class LoggingConfig:
    """Loads logging config from YAML and applies it. Follows SubRoleRequirementsLoader pattern."""

    def __init__(self, config_path: Path, workspace_root: Path) -> None:
        """Parse YAML at construction. Raises FileNotFoundError / yaml.YAMLError.
        Resolves log_file_path to absolute path (Fail-Fast: detectable at startup)."""
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        self._level: str = raw["level"]
        self._format: str = raw["format"]
        relative = raw.get("handlers", {}).get("file", {}).get("path", ".copilot/logs/orchestration.log")
        self._log_file_path: Path = workspace_root / relative

    @classmethod
    def from_copilot_dir(cls, workspace_root: Path) -> "LoggingConfig":
        """Factory: .copilot/logging.yaml first, then package _default_logging.yaml."""
        project_yaml = workspace_root / ".copilot" / "logging.yaml"
        if project_yaml.exists():
            return cls(project_yaml, workspace_root)
        package_default = Path(__file__).parent / "_default_logging.yaml"
        return cls(package_default, workspace_root)

    def apply(self) -> None:
        """Configure Python logging: creates log dir if absent, then calls basicConfig.
        Note: mkdir + basicConfig in one method is a justified YAGNI choice — mkdir is
        a 1-line precondition, not a separate reason-to-change (see research doc)."""
        self._log_file_path.parent.mkdir(parents=True, exist_ok=True)
        logging.basicConfig(level=self._level, format=self._format, handlers=[...])
```

### Wiring (each `__main__` / `main()`)

Identical to existing `SubRoleRequirementsLoader` wiring — no extra argument at call sites:

```python
# detect_sub_role.py __main__ — example
workspace_root = find_workspace_root(Path(__file__))
loader = SubRoleRequirementsLoader.from_copilot_dir(workspace_root)
log_config = LoggingConfig.from_copilot_dir(workspace_root)   # +1 line, same pattern

def main(role: str, loader: ISubRoleRequirementsLoader, log_config: ILoggingConfig) -> ...:
    log_config.apply()   # no workspace_root — resolved at construction
    ...
```

`log_config.apply()` is the first statement in `main()` so the logger is ready before any logic runs.

**Path resolution principle:** `LoggingConfig` introduceert geen eigen padresolutie. De `workspace_root` die meegegeven wordt aan `from_copilot_dir()` is altijd het resultaat van `find_workspace_root(Path(__file__))` uit `_paths.py` — dezelfde aanroep die alle andere orchestratiecode gebruikt. Daarmee is het logbestand (`.copilot/logs/orchestration.log`) geanchoreerd op exact dezelfde root als de state files (`.copilot/session-sub-role-{role}.json`) en de config (`.copilot/sub-role-requirements.yaml`).

---

## Cycle Scope Assessment

### Can this be done in 1 cycle?

**Yes — 2 sub-cycles, tight scope.**

| Sub-cycle | Deliverables | TDD |
|---|---|---|
| **C_LOGGING.1** | `ILoggingConfig` Protocol, `LoggingConfig` class, `_default_logging.yaml`, `.gitignore` additions, unit tests for loader | Full RED/GREEN/REFACTOR |
| **C_LOGGING.2** | All 7 files: `logger = logging.getLogger(__name__)` + ~50–70 calls + `main()` signature extension + `log_config.apply()` wiring + `pytest.caplog` tests | RED/GREEN/REFACTOR |

**Risk:** `pre_compact_agent.py` has zero existing tests. Logging calls are safe to add without touching logic, but `caplog` tests require a test harness where none exists. **Mitigation:** limit caplog tests for `pre_compact_agent.py` to ERROR paths only (simpler, lower risk). Full tier-extraction tests are out of scope for this cycle.

**Scope contract:**
- ✅ `ILoggingConfig` Protocol in `contracts/interfaces.py`
- ✅ `LoggingConfig` + `_default_logging.yaml` + factory + `apply()`
- ✅ `.copilot/logs/orchestration.log` file handler by default
- ✅ `.gitignore` entries for `.copilot/logging.yaml` and `.copilot/logs/`
- ✅ `main()` signature extended with `log_config: ILoggingConfig` in all 3 primary hooks
- ✅ `pytest.caplog` tests for: INFO enforcement, WARNING fallback, ERROR crash
- ❌ No log rotation, no structured JSON
- ❌ No full `pre_compact_agent.py` test harness (ERROR-path caplog only)

**Verdict:** 1 cycle, 2 sub-cycles. Manageable single-session work.

---

## Related Documentation
- **[src/copilot_orchestration/config/requirements_loader.py - factory pattern reference][related-1]**
- **[src/copilot_orchestration/hooks/stop_handover_guard.py - most critical logging gap][related-2]**
- **[src/copilot_orchestration/hooks/detect_sub_role.py - most frequent hook (every prompt)][related-3]**

<!-- Link definitions -->

[related-1]: src/copilot_orchestration/config/requirements_loader.py - factory pattern reference
[related-2]: src/copilot_orchestration/hooks/stop_handover_guard.py - most critical logging gap
[related-3]: src/copilot_orchestration/hooks/detect_sub_role.py - most frequent hook (every prompt)

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 |  | Agent | Initial draft |