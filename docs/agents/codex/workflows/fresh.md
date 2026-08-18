---
description: Bootstrap active sub-role instructions and AGENTS.md rules at initial session startup.
---

# /fresh

This command forces the agent to initialize its session, synchronize its internal instruction set, and verify compliance with the active workspace rules.

## Step-by-Step Sequence

1. **Check Active Context**:
   Call `get_work_context()` to retrieve the current active branch, workflow, phase, issue number, and sub-role hint.

2. **Read Project Rules**:
   Read **[AGENTS.md](../../AGENTS.md)** to load and align with all general workspace-level guidelines and tool restrictions.

3. **Read Sub-Role Instructions**:
   Read the specific sub-role rule file corresponding to the argument passed (e.g. `/fresh co`, `/fresh imp`, `/fresh qa`) or the file mentioned in the command:
   - If argument is `co`: read **[co.agent.md](../rules/co.agent.md)**.
   - If argument is `imp`: read **[imp.agent.md](../rules/imp.agent.md)**.
   - If argument is `qa`: read **[qa.agent.md](../rules/qa.agent.md)**.
   - Alternatively, if a file is explicitly mentioned or @-mentioned, read that file.

4. **Verify Tool Priority and Built-In Tool Restrictions**:
   Re-read and verify the **Tool Priority Matrix** and **run_in_terminal Restrictions** from **[AGENTS.md](../../AGENTS.md)**. Confirm that:
   - Git, GitHub, File, Quality, and Test operations MUST use MCP tools.
   - Built-in agent tools (e.g., `write_to_file`, `replace_file_content`, `multi_replace_file_content`) are strictly forbidden for repository operations when a corresponding MCP tool exists.
   - Running terminal commands via `run_in_terminal`/`run_command` is strictly restricted.

5. **Acknowledge and Report**:
   Output a formal startup confirmation block to the user detailing the synchronized state:
   ```markdown
   ### 🚀 Agent Startup Confirmation
   * **Branch**: `<active_branch>`
   * **Active Role / Sub-role**: `<active_role_from_context>`
   * **Workflow Phase**: `<active_phase>`
   * **Understanding of Rules**: Confirmed reading of `AGENTS.md` and the active sub-role instructions.
   * **Tool Priority Compliance**: Verified that Git, GitHub, File, Quality, and Test operations MUST use MCP tools, built-in agent tools (like `write_to_file`) are prohibited for repository actions, and terminal executions are strictly restricted.
   ```
