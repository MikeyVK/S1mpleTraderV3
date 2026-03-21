<!-- src/copilot_orchestration/README.md -->
<!-- template=generic_doc version=43c84181 created=2026-03-21T00:00:00Z updated= -->
# copilot_orchestration

**Status:** DEFINITIVE  
**Version:** 1.0  
**Last Updated:** 2026-03-21

---

## Purpose

A VS Code Copilot hook package that enforces structured hand-over discipline across implementation and QA sessions using agent-scoped hooks.

## Scope

**In Scope:**
Hook entry points, sub-role detection, stop enforcement, compaction handling, workspace configuration.

**Out of Scope:**
External tooling integrations, coding standards, role-specific instructions.

---

## Summary

`copilot_orchestration` is a lightweight Python package that provides VS Code Copilot hooks for sub-role-based enforcement. It installs three hooks — `UserPromptSubmit`, `Stop`, and `PreCompact` — that together detect the active sub-role for a session and enforce a structured hand-over block at the end of enforced sessions. The package is agent-scoped and has no external dependencies beyond the Python standard library.





---

## What This Package Does

- Hook-based sub-role detection on every user prompt (via `UserPromptSubmit`).
- Stop-time enforcement of structured hand-over blocks for enforced sub-roles.
- Idempotent session state: sub-role is detected once at session start and locked for the remainder of the session.
- Compaction awareness: writes transcript snapshots and injects context warnings before compaction.
- Workspace-local configuration via `.copilot/sub-role-requirements.yaml`.

## What This Package Is Not

- This package has **no dependency on external tooling** or workflow engines.
- It does **not** define agent roles, coding standards, or review policies — those live in `agent.md`, `imp_agent.md`, `qa_agent.md`, and `*.instructions.md` files.
- It does **not** run as a service or daemon. The hooks are invoked by VS Code as subprocess commands.
- It is **not** a replacement for reading or following the project's role-specific instructions.

## Setup

Install the package in development mode from the repository root:

```
pip install -e .
```

Register the hook scripts by configuring your custom agent files (`.github/agents/imp.agent.md`, `.github/agents/qa.agent.md`) to invoke the entry-point scripts in `scripts/copilot_hooks/`.

Customise enforcement per sub-role by editing `.copilot/sub-role-requirements.yaml`.

## Reference Documentation

For a full description of the hook architecture, sub-role table, enforcement matrix, and slash command use cases, see the reference documentation.

## Related Documentation
- **[docs/reference/copilot_orchestration/reference.md][related-1]**
- **[.copilot/sub-role-requirements.yaml][related-2]**

<!-- Link definitions -->

[related-1]: docs/reference/copilot_orchestration/reference.md
[related-2]: .copilot/sub-role-requirements.yaml

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-03-21 | Agent | Initial draft |