# MCP Tools Reference

## Overview

The S1mpleTrader V3 MCP Server provides **31 tools** for complete git workflow automation, project management, quality assurance, and documentation scaffolding. All tools are accessed via Model Context Protocol (MCP) and integrated with VS Code.

**Server Location:** `mcp_server/`
**Configuration:** `.vscode/mcp.json` → `st3-workflow`
**Main Entry:** `mcp_server/__main__.py`

## Tool Categories

### 1. Git Workflow Tools (8 tools)

Comprehensive git flow automation with TDD phase tracking.

| Tool | Purpose | Parameters | Example |
|------|---------|------------|---------|
| **CreateBranchTool** | Create feature/fix/refactor/docs branch | `name` (kebab-case), `branch_type` (default: feature) | `create_feature_branch name=add-metrics` |
| **GitStatusTool** | Show working tree status | None | Returns current branch, staged, unstaged files |
| **GitCommitTool** | Commit with TDD phase prefix | `message`, `phase` (red/green/refactor/docs) | `commit message="Implement feature" phase=green` |
| **GitCheckoutTool** | Switch branches | `branch` | `checkout main` |
| **GitPushTool** | Push to origin | `set_upstream` (optional, for new branches) | `push set_upstream=true` |
| **GitMergeTool** | Merge feature → main | `branch` to merge | `merge feature/new-feature` |
| **GitDeleteBranchTool** | Delete branch (safe by default) | `branch`, `force` (optional) | `delete_branch branch=feature/old force=false` |
| **GitStashTool** | Save/restore WIP | `action` (push/pop/list), `message` (optional for push) | `stash action=push message=wip` |

**Workflow Example:**
```
1. create_feature_branch name=my-feature
2. (Make changes)
3. git_commit message="Add feature" phase=green
4. git_push set_upstream=true
5. (Create PR via CreatePRTool)
6. (After merge)
7. git_checkout branch=main
8. git_delete_branch branch=feature/my-feature
```

**Related:** [TDD_WORKFLOW.md](../../coding_standards/TDD_WORKFLOW.md)

### 2. Issue Management Tools (5 tools)

Full CRUD for GitHub issues with filtering and updates.

| Tool | Purpose | Parameters | Returns |
|------|---------|------------|---------|
| **CreateIssueTool** | Create new issue | `title`, `body`, `labels` (optional), `milestone_number` (optional), `assignees` (optional) | Issue number, URL |
| **ListIssuesTool** | List issues with filters | `state` (open/closed/all), `labels` (optional list) | Formatted list with numbers, titles, labels |
| **GetIssueTool** | Get issue details | `issue_number` | Full issue data, acceptance criteria extracted |
| **CloseIssueTool** | Close issue | `issue_number`, `comment` (optional) | Confirmation message |
| **UpdateIssueTool** | Modify issue fields | `issue_number`, then any of: `title`, `body`, `state`, `labels`, `milestone_number`, `assignees` | Updated issue |

**Usage Example:**
```
1. list_issues state=open
2. get_issue issue_number=4
3. update_issue issue_number=4 state=in-progress labels=["bug", "critical"]
4. close_issue issue_number=4 comment="Fixed in PR #123"
```

### 3. Pull Request Tools (3 tools)

Create, list, and merge PRs with merge strategy options.

| Tool | Purpose | Parameters | Returns |
|------|---------|------------|---------|
| **CreatePRTool** | Create new PR | `title`, `body`, `head` (source branch), `base` (default: main), `draft` (optional) | PR number, URL |
| **ListPRsTool** | List PRs with filters | `state` (open/closed/all), `base` (optional), `head` (optional) | Formatted list with numbers, titles, status |
| **MergePRTool** | Merge PR | `pr_number`, `commit_message` (optional), `merge_method` (merge/squash/rebase, default: merge) | Merge result, SHA, message |

**Usage Example:**
```
1. create_pr title="Add feature X" body="..." head=feature/x
2. list_prs state=open base=main
3. merge_pr pr_number=42 merge_method=squash
```

### 4. Label Management Tools (5 tools)

Manage repository labels and apply to issues/PRs.

| Tool | Purpose | Parameters | Returns |
|------|---------|------------|---------|
| **ListLabelsTool** | List all labels | None | Formatted list with colors, descriptions |
| **CreateLabelTool** | Create new label | `name`, `color` (hex), `description` (optional) | Label created |
| **DeleteLabelTool** | Delete label | `name` | Confirmation |
| **AddLabelsTool** | Add labels to issue/PR | `issue_number`, `labels` (list) | Confirmation |
| **RemoveLabelsTool** | Remove labels from issue/PR | `issue_number`, `labels` (list) | Confirmation |

**Suggested Labels:**
- `bug` - Bug report / fix
- `feature` - New feature request
- `enhancement` - Improvement to existing feature
- `documentation` - Docs only
- `critical` - High priority
- `in-progress` - Currently being worked on
- `blocked` - Blocked by another issue

### 5. Milestone Tools (3 tools)

Organize issues into release milestones.

| Tool | Purpose | Parameters | Returns |
|------|---------|------------|---------|
| **ListMilestonesTool** | List milestones | `state` (open/closed/all) | Formatted list with titles, due dates, progress |
| **CreateMilestoneTool** | Create milestone | `title`, `description` (optional), `due_on` (optional ISO 8601) | Milestone created |
| **CloseMilestoneTool** | Close milestone | `milestone_number` | Confirmation |

**ISO 8601 Format:** `2025-12-31T00:00:00Z` or `2025-12-31T00:00:00+00:00`

### 6. Quality & Testing Tools (6 tools)

Run linters, type checkers, tests, and validate code.

| Tool | Purpose | Parameters | Returns |
|------|---------|------------|---------|
| **RunQualityGatesTool** | Run pylint + mypy | `files` (list of paths) | Score: Linting 0-10, Type checking Pass/Fail |
| **ValidateDocTool** | Check doc structure | `file_path` | Validation results (headings, links, etc.) |
| **ValidationTool** | Generic code validation | `file_path` | Issues found |
| **ValidateDTOTool** | Validate DTO schema | `file_path` | DTO structure validation |
| **RunTestsTool** | Run pytest | `path` (default: tests/), `markers` (optional), `verbose` (optional), `timeout` (default: 300s) | Test results, pass/fail count |
| **HealthCheckTool** | Server health status | None | OK/ERROR |

**Quality Gates Standard:**
- **Linting:** 10.00/10 (pylint + custom rules)
- **Type Checking:** Pass (mypy with strict mode)
- **Tests:** All passing (715 tests currently)

### 7. Discovery & Navigation Tools (2 tools)

Find documentation and understand current work context.

| Tool | Purpose | Parameters | Returns |
|------|---------|------------|---------|
| **SearchDocumentationTool** | Search docs semantically | `query`, `scope` (optional: all/architecture/coding_standards/development/reference/implementation) | Ranked results with file path, line number, snippet |
| **GetWorkContextTool** | Get current work state | `include_closed_recent` (optional, last 7 days) | Current branch, issue number, TDD phase |

**Usage Example:**
```
1. get_work_context → Returns: branch=feature/x, issue=#4, phase=green
2. search_documentation query="how to implement worker" → Returns: Ranked docs with examples
```

### 8. Scaffolding Tools (1 tool)

Generate new artifacts from templates (unified system).

| Tool | Purpose | Parameters | Returns |
|------|---------|------------|---------|
| **ScaffoldArtifactTool** | Generate code/docs from artifacts.yaml | `artifact_type` (dto/worker/design/etc), `name`, context fields (varies by type), `output_path` (optional) | Generated file path |

**Artifact Types (from artifacts.yaml):**
- `dto` - Data Transfer Object with Pydantic
- `worker` - Background job/processor
- `design` - Design document
- `adapter` - External API integration
- `tool` - MCP tool

See `.st3/artifacts.yaml` for complete list and required fields per type.

### 9. Development & File Tools (2 tools)

Manage files and check server health.

| Tool | Purpose | Parameters | Returns |
|------|---------|------------|---------|
| **CreateFileTool** | Create new file | `path`, `content` | File created (deprecated) |
| **HealthCheckTool** | Check MCP server | None | OK if healthy |

## Architecture

### Tool Registration

All tools are registered in `mcp_server/server.py`:

**Always Available (8 tools):**
- Git tools (8)
- Quality tools (4)
- Development tools (2)
- Scaffold tools (2)
- Discovery tools (2)

**GitHub-Dependent (13 tools, requires GITHUB_TOKEN):**
- Issue tools (5)
- PR tools (3)
- Label tools (5)
- Milestone tools (3)

**Total: 31 tools**

### Execution Flow

```
User Request (VS Code)
    ↓
MCP Client (VS Code Extension)
    ↓
MCP Protocol (stdio)
    ↓
MCPServer.execute_tool()
    ↓
Tool.execute(**params)
    ↓
Manager.operation() [business logic]
    ↓
Adapter.method() [external API calls]
    ↓
ToolResult (success/error)
    ↓
MCP Response
    ↓
VS Code Display
```

### Error Handling

All tools use three exception types:

| Exception | When | Recovery |
|-----------|------|----------|
| **ExecutionError** | Tool fails to complete (API error, file not found) | Check parameters, retry |
| **ValidationError** | Invalid input parameters | Review schema, adjust input |
| **MCPSystemError** | Server misconfiguration (missing token, no repo access) | Configure settings, check permissions |

## Configuration

### Environment Variables

```bash
GITHUB_TOKEN=ghp_xxxxx           # Enable GitHub tools
GITHUB_OWNER=MikeyVK             # Repository owner
GITHUB_REPO=S1mpleTraderV3        # Repository name
```

### VS Code Configuration

File: `.vscode/mcp.json`

```json
{
  "servers": {
    "st3-workflow": {
      "type": "stdio",
      "command": "d:\\...\\python.exe",
      "args": ["-m", "mcp_server"],
      "cwd": "d:\\dev\\SimpleTraderV3",
      "env": {
        "GITHUB_TOKEN": "${env:GITHUB_TOKEN}"
      }
    }
  }
}
```

## Usage Examples

### Complete Feature Branch Workflow

```
1. create_feature_branch name=add-caching branch_type=feature
2. (Make code changes in IDE)
3. git_status
4. git_commit message="Implement caching logic" phase=green
5. run_quality_gates files=["mcp_server/tools/cache.py"]
6. run_tests path=tests/unit
7. git_push set_upstream=true
8. create_pr title="Add caching mechanism" body="Implements Redis caching for..." head=feature/add-caching base=main
9. (Request review, get approval)
10. merge_pr pr_number=123 merge_method=squash
11. git_checkout branch=main
12. git_delete_branch branch=feature/add-caching force=false
```

### Issue Lifecycle Management

```
1. create_issue title="Bug: Memory leak" body="..." labels=["bug", "critical"]
   → Returns: issue_number=47
2. update_issue issue_number=47 state=in-progress
3. (Create PR linked to issue)
4. close_issue issue_number=47 comment="Fixed in PR #124"
```

### Release Milestone Workflow

```
1. create_milestone title="v1.0.0" description="First stable release" due_on="2025-12-31T00:00:00Z"
2. create_issue title="Feature A" milestone_number=1
3. create_issue title="Feature B" milestone_number=1
4. (As features complete)
5. update_issue issue_number=X state=closed
6. (When all done)
7. close_milestone milestone_number=1
```

## Best Practices

### TDD Workflow Integration

```
RED Phase:    git_commit "Add failing test" phase=red
GREEN Phase:  git_commit "Implement feature" phase=green
REFACTOR:     git_commit "Clean up code" phase=refactor
DOCS:         git_commit "Update documentation" phase=docs
```

### Quality Gates Before Push

```
1. run_quality_gates files=[modified files]
2. run_tests path=tests/
3. Ensure: Linting 10.00/10 + Type checking Pass
4. git_push
```

### Label Strategy

- Use labels for quick filtering (state, priority, type)
- Assign to milestones for release planning
- Link issues to PRs for traceability
- Keep labels consistent across projects

### Documentation with Tools

```
1. search_documentation query="related topic"
2. scaffold_design_doc title="New Feature Design"
3. write content in created file
4. validate_doc file_path=path/to/doc.md
5. git_commit "docs: Add design document" phase=docs
```

## Related Documentation

- **Git Workflow:** [../../coding_standards/TDD_WORKFLOW.md](../../coding_standards/TDD_WORKFLOW.md)
- **Quality Standards:** [../../coding_standards/QUALITY_GATES.md](../../coding_standards/QUALITY_GATES.md)
- **Architecture:** [../../architecture/README.md](../../architecture/README.md)
- **Implementation Status:** [../../implementation/IMPLEMENTATION_STATUS.md](../../implementation/IMPLEMENTATION_STATUS.md)

## Troubleshooting

### Tool Returns "GitHub token not configured"

**Fix:** Set `GITHUB_TOKEN` environment variable and restart MCP server

### Quality Gates Show "N/A" for Mypy

**Fix:** Server was just started. Mypy needs venv initialization. Retry the command.

### CreatePRTool Fails: "Head branch not found"

**Fix:** Branch must exist on remote. Run `git_push set_upstream=true` first.

### MergePRTool Returns "Merge failed"

**Fix:** Check PR has no merge conflicts, you have merge permissions, and PR is approved.

## Roadmap

**Completed:**
- ✅ Git workflow (8 tools)
- ✅ Issue management (5 tools)
- ✅ PR management (3 tools)
- ✅ Label management (5 tools)
- ✅ Milestone management (3 tools)

**Future:**
- 🚧 Review management (approve/request changes/dismiss)
- 🚧 Project board automation (move cards, auto-assign)
- 🚧 Documentation quality tooling (structure validation, link checking)
- 🚧 Release notes generation
- 🚧 Changelog automation

## Support

**Issues or suggestions?**
- Create issue with `mcp:` label
- Search existing [MCP reference](../mcp/MCP_TOOLS.md)
- Check [TDD Workflow](../../coding_standards/TDD_WORKFLOW.md) for best practices
