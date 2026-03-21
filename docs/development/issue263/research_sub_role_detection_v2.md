<!-- docs\development\issue263\research_sub_role_detection_v2.md -->
<!-- template=research version=8b7bb3ab created=2026-03-21T19:01Z updated= -->
# Sub-Role Detection V2 — Bug Analysis and Redesign

**Status:** DRAFT  
**Version:** 1.0  
**Last Updated:** 2026-03-21

---

## Scope

**In Scope:**
detect_sub_role.py, stop_handover_guard.py, _paths.py, SessionSubRoleState contract, role-scoped state files, slash-command prefix stripping, exploration mode.

**Out of Scope:**
pre_compact_agent.py, session-state.json (v1 transcript), prompt body rewrites, acceptance tests, reference documentation updates.

---

## Problem Statement

Three interconnected defects discovered during documentation phase.

Bug 1 — sessionId is always empty. VS Code does not send a sessionId in the UserPromptSubmit payload for custom agents. Every invocation writes session_id: ''. The idempotency check always matches after the first write — sub-role is permanently frozen.

Bug 2 — imp and qa share a single state file. STATE_RELPATH is a single shared path used by both agents. A qa session writes verifier; when imp runs next it reads verifier — a value that does not exist in imp config. Silent pass-through, no enforcement.

Bug 3 — Sub-role cannot change mid-session. The idempotency check prevents deliberate phase transitions. A researcher wanting to move to implementer must start a new chat and loses prior context. The original design requirement stated that context must survive phase transitions within a single chat.

## Research Goals

- Eliminate dependence on sessionId (unreliable — always empty from VS Code).
- Isolate imp and qa state into separate role-scoped files.
- Allow intentional sub-role changes mid-session via explicit first-word detection.
- Preserve follow-up safety: prompts that do not start with a sub-role keyword must not trigger a sub-role change.
- Handle the slash-command prefix edge case (/start-work implementer: task).
- Support exploration mode: no sub-role file = no enforcement, so the first response is never unexpectedly blocked.

---

## Background

The hooks were implemented in cycles C_V2.1–C_V2.5. The original design assumed VS Code would supply a stable `sessionId`. This assumption failed in practice — `sessionId` is empty for all custom-agent invocations tested. The file-isolation bug was introduced because `STATE_RELPATH` was designed as a single constant. The idempotency bug was a deliberate tradeoff at design time that turned out to conflict with the stated requirement of in-session phase transitions.

---

## Findings

**Finding 1 — sessionId is always empty**
Confirmed by observing `.copilot/session-sub-role.json` after multiple distinct chat sessions. All write `session_id: ""`. The idempotency check `existing.get("session_id") == session_id` evaluates to `"" == ""` — always True after the first write. Sub-role is frozen permanently.

**Finding 2 — Stop hook cross-role silent failure**
When `stop_handover_guard.py imp` reads a file written by a `@qa` session, it calls `loader.requires_crosschat_block("imp", "verifier")`. The `imp` role config has no `verifier` entry. Silent pass-through — no error, no log, no enforcement.

**Finding 3 — Slash command prefix blocks sub-role detection**
When invoked as `/start-work implementer: task`, the payload `prompt` field is `/start-work implementer: task`. The first word is `/start-work`, not `implementer`. Naive first-word detection fails.

**Finding 4 — Exploration mode desideratum**
At session start the user may want to explore before committing to a sub-role. Current behaviour: missing file → fallback to default → default is enforced → first response immediately blocked. Desired model: no file = no enforcement = exploration mode. Enforcement activates only when a sub-role is explicitly declared.

**Agreed solution design:**

_Paths:_ Replace `STATE_RELPATH` singleton with `state_path_for_role(role: str) -> Path`, returning `.copilot/session-sub-role-imp.json` or `.copilot/session-sub-role-qa.json`.

_detect_sub_role.py new algorithm:_
1. Strip leading `/command\s*` prefix from prompt text
2. Extract first word only
3. Match first word against `valid_sub_roles(role)` (exact, case-insensitive)
4. Match found → write role-scoped file (always; removes idempotency lock)
5. No match + no file → write nothing (exploration mode preserved)
6. No match + file exists → write nothing (current sub-role preserved)
7. sessionId kept in written state for audit only, never read for decisions

_stop_handover_guard.py new algorithm:_
1. Read role-scoped file
2. File not found → pass-through (exploration mode — no enforcement)
3. File found → use sub_role; check requires_crosschat_block
4. No sessionId validation

_SessionSubRoleState contract:_ sessionId field kept for audit; `role` field validated on read to guard against stale cross-role remnants.

## Open Questions

- ❓ OQ-1: Correct place for ask-user-for-sub-role logic? Answer: prompt body, not the hook. Hooks are mechanical; agent intelligence belongs in the prompt.
- ❓ OQ-2: Should STATE_RELPATH be removed from the public API of _paths.py? Answer: yes, clean break. Export state_path_for_role(role) instead.
- ❓ OQ-3: What regex strips the slash-command prefix? Answer: ^/\S+\s* applied via re.sub before extracting the first word.
- ❓ OQ-4: What happens if both @imp and @qa sessions are open simultaneously? Answer: fully isolated via role-scoped files. VS Code serialises hook invocations per agent.


## Related Documentation
- **[docs/reference/copilot_orchestration/reference.md][related-1]**
- **[src/copilot_orchestration/hooks/detect_sub_role.py][related-2]**
- **[src/copilot_orchestration/hooks/stop_handover_guard.py][related-3]**
- **[src/copilot_orchestration/utils/_paths.py][related-4]**

<!-- Link definitions -->

[related-1]: docs/reference/copilot_orchestration/reference.md
[related-2]: src/copilot_orchestration/hooks/detect_sub_role.py
[related-3]: src/copilot_orchestration/hooks/stop_handover_guard.py
[related-4]: src/copilot_orchestration/utils/_paths.py

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 |  | Agent | Initial draft |