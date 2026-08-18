---
description: scaffold and submit a new GitHub issue of a specified type.
---

@co

# Create Issue

Guide through scaffolding a GitHub issue body and submitting it as a real GitHub issue.

## Required Input

Extract from the invocation argument:

- `ISSUE_TYPE` — the issue type (e.g. `feature`, `bug`, `refactor`). Valid values are injected at runtime into the `create_issue` tool schema — check the schema if uncertain.
- `DESCRIPTION` — short description (optional; used as a starting point for the title)

If `ISSUE_TYPE` is absent, ask the user before proceeding. Do not guess.

---

## Step 1: Discover available fields

Call `scaffold_schema(artifact_type="issue")`.

Read the description of each optional field in the returned schema. Using `ISSUE_TYPE` as the selection criterion, select the optional fields whose descriptions match the character of this issue type. Skip fields that are not relevant.

Do not ask about fields you did not select unless the user volunteers them.

---

## Step 2: Collect content

Use conversation context or ask the user for:

- `title` — concise issue title (required)
- `problem` — what is wrong or needed (required)
- The optional fields selected in Step 1

---

## Step 3: Collect metadata

Ask the user for:

- `priority` — valid values are injected at runtime from config into the `create_issue` tool schema. Default to `medium` if the user does not specify.
- `scope` — valid values are injected at runtime from config into the `create_issue` tool schema. Ask if unclear.
- `is_epic` — `true` only when `ISSUE_TYPE` is `epic`. Default `false`.
- `parent_issue` — parent issue number (optional, positive integer).
- `milestone` — milestone title (optional).
- `assignees` — list of GitHub logins (optional).

Do not invent values for `priority` or `scope`. If uncertain, ask.

---

## Step 4: Scaffold the issue body

Call `scaffold_artifact` with the collected context. Include only fields with actual values — omit empty optional fields entirely.

```
scaffold_artifact(
  artifact_type="issue",
  name="<slug-from-title>",
  context={
    "title": "<title>",
    "problem": "<problem>",
    # include only fields selected in Step 1 that the user provided
    "labels": []  # leave empty — assembled by create_issue
  }
)
```

Read the scaffolded file path returned by `scaffold_artifact` and show its content to the user. Offer to adjust before submitting.

> **Important:** Pass the exact file content as the `body` in Step 5. Do NOT retype or reconstruct the body — retyping produces literal `\n` escape sequences instead of real newlines, which breaks formatting on GitHub.

---

## Step 5: Create the issue

After user confirmation, submit with:

```
create_issue(
  issue_type="<ISSUE_TYPE>",
  title="<title>",
  priority="<priority>",
  scope="<scope>",
  body="<rendered markdown from Step 4>",
  is_epic=<true|false>,
  parent_issue=<number>,   # omit if not set
  milestone="<milestone>", # omit if not set
  assignees=["<login>"]    # omit if not set
)
```

Report the created issue number and URL to the user.