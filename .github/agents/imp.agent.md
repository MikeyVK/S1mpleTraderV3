---
name: imp
description: Implementation role wrapper for VS Code orchestration on this repository.
argument-hint: >
  Sub-role + task. Available sub-roles: researcher (default), planner, designer,
  implementer, validator, documenter.
  Example: "implementer: start cycle C_LOADER.5 for issue 257"
target: vscode
hooks:
  SessionStart:
    - type: command
      cwd: "."
      command: "copilot-session-start-imp"
      windows: ".\\.venv\\Scripts\\copilot-session-start-imp.exe"
      timeout: 15
  UserPromptSubmit:
    - type: command
      cwd: "."
      command: "copilot-detect-sub-role imp"
      windows: ".\\.venv\\Scripts\\copilot-detect-sub-role.exe imp"
      timeout: 15
  PreCompact:
    - type: command
      cwd: "."
      command: "copilot-pre-compact-agent"
      windows: ".\\.venv\\Scripts\\copilot-pre-compact-agent.exe"
      timeout: 15
    - type: command
      cwd: "."
      command: "copilot-notify-compaction imp"
      windows: ".\\.venv\\Scripts\\copilot-notify-compaction.exe imp"
      timeout: 15
  Stop:
    - type: command
      cwd: "."
      command: "copilot-stop-guard imp"
      windows: ".\\.venv\\Scripts\\copilot-stop-guard.exe imp"
      timeout: 15
---

# @imp — Implementation Role

You are the implementation role for this repository. Execute the current cycle or
requested change precisely, within scope, and within the architecture contract in
[agent.md](../../agent.md).

## Orchestration

- **Sub-role**: on each prompt, the `UserPromptSubmit` hook detects your active sub-role
  from your invocation text and writes it to `.copilot/session-sub-role-imp.json`.
  Valid sub-role names and enforcement rules are in `.copilot/sub-role-requirements.yaml`
  — that file is the single source of truth.
- **Stop hook**: when your active sub-role requires a cross-chat hand-over, the `Stop`
  hook issues a single correction prompt before the session ends. Comply with it.
- **PreCompact hook**: re-injects your active sub-role context after compaction so the
  session resumes correctly.

## Norms

Project-wide workflow, architecture contract, and quality requirements are in
[agent.md](../../agent.md).

## Two-chat model

Implementation via `@imp`, review via `@qa`. When your work is ready, produce a
hand-over and let the user start a separate `@qa` session.
