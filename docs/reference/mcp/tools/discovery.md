<!-- docs/reference/mcp/tools/discovery.md -->
<!-- template=reference version=064954ea created=2026-02-08T12:00:00+01:00 updated=2026-02-08 -->
# Discovery & Admin Tools

**Status:** DEFINITIVE  
**Version:** 2.0  
**Last Updated:** 2026-02-08  

**Source:** [mcp_server/tools/discovery_tools.py](../../../../mcp_server/tools/discovery_tools.py), [health_tools.py](../../../../mcp_server/tools/health_tools.py), [admin_tools.py](../../../../mcp_server/tools/admin_tools.py)  
**Tests:** [tests/unit/test_discovery_tools.py](../../../../tests/unit/test_discovery_tools.py)  

---

## Purpose

Complete reference documentation for discovery and administration tools covering documentation search, work context aggregation, server health checks, and hot-reload functionality.

These tools support agent onboarding, project awareness, and server lifecycle management.

---

## Overview

The MCP server provides **4 discovery/admin tools**:

| Tool | Purpose | Key Features |
|------|---------|-------------|
| `search_documentation` | Semantic/fuzzy search across docs/ | Scope filtering, ranked results with snippets |
| `get_work_context` | Aggregate GitHub + branch + phase | Work queue discovery, context-aware suggestions |
| `health_check` | Server health status | Uptime, memory, registered tools count |
| `restart_server` | Hot-reload server via proxy | Zero-downtime restart for code changes |

---

## API Reference

### search_documentation

**MCP Name:** `search_documentation`  
**Class:** `SearchDocumentationTool`  
**File:** [mcp_server/tools/discovery_tools.py](../../../../mcp_server/tools/discovery_tools.py)

Semantic/fuzzy search across all docs/ files. Returns ranked results with snippets for understanding project structure.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `query` | `str` | **Yes** | Search query (e.g., `"how to implement a worker"`, `"DTO validation rules"`) |
| `scope` | `str` | No | Optional scope: `"all"`, `"architecture"`, `"coding_standards"`, `"development"`, `"reference"`, `"implementation"` (default: `"all"`) |

#### Returns

```json
{
  "success": true,
  "results": [
    {
      "file": "docs/architecture/worker-pattern.md",
      "score": 0.92,
      "snippet": "Workers must inherit from BaseWorker and implement the execute() method...",
      "section": "Worker Implementation",
      "context": "architecture"
    },
    {
      "file": "docs/coding_standards/backend-conventions.md",
      "score": 0.85,
      "snippet": "Worker classes follow the pattern: <Name>Worker (e.g., OrderProcessingWorker)...",
      "section": "Naming Conventions",
      "context": "coding_standards"
    }
  ],
  "count": 2,
  "query": "how to implement a worker"
}
```

#### Example Usage

**Search across all docs:**
```json
{
  "query": "how to implement a worker"
}
```

**Search architecture docs only:**
```json
{
  "query": "DTO validation rules",
  "scope": "architecture"
}
```

**Search coding standards:**
```json
{
  "query": "naming conventions",
  "scope": "coding_standards"
}
```

#### Search Scopes

| Scope | Directories | Use Case |
|-------|-------------|----------|
| `all` | `docs/**` | Broad search when you don't know where to look |
| `architecture` | `docs/architecture/` | Design patterns, architectural decisions |
| `coding_standards` | `docs/coding_standards/` | Style guides, conventions |
| `development` | `docs/development/` | Issue tracking, research, planning |
| `reference` | `docs/reference/` | API docs, tool references |
| `implementation` | `docs/implementation/` | Implementation guides |

#### Behavior Notes

- **Semantic Matching:** Uses TF-IDF and fuzzy matching (not just exact string match)
- **Ranking:** Results sorted by relevance score (0.0 to 1.0)
- **Snippets:** Returns relevant text snippet (50-100 words) around match
- **Section Detection:** Identifies which section of document contains match
- **Case-Insensitive:** Search is case-insensitive

---

### get_work_context

**MCP Name:** `get_work_context`  
**Class:** `GetWorkContextTool`  
**File:** [mcp_server/tools/discovery_tools.py](../../../../mcp_server/tools/discovery_tools.py)

Aggregates context from GitHub Issues, current branch, and TDD phase to understand what to work on next.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `include_closed_recent` | `bool` | No | Include recently closed issues (last 7 days) for context (default: `False`) |

#### Returns

```json
{
  "success": true,
  "context": {
    "current_branch": {
      "name": "feature/123-oauth",
      "issue_number": 123,
      "phase": "green",
      "parent_branch": "main"
    },
    "open_issues": [
      {
        "number": 123,
        "title": "Add OAuth2 authentication",
        "labels": ["type:feature", "priority:high"],
        "state": "open",
        "assignees": ["developer1"]
      },
      {
        "number": 124,
        "title": "Fix login validation",
        "labels": ["type:bug", "priority:medium"],
        "state": "open",
        "assignees": []
      }
    ],
    "recent_closed": [
      {
        "number": 122,
        "title": "Update user DTO",
        "labels": ["type:refactor"],
        "state": "closed",
        "closed_at": "2026-02-07T10:00:00Z"
      }
    ],
    "suggestions": [
      "Continue implementing OAuth2 authentication (feature/123-oauth, phase: green)",
      "Review unassigned bug #124: Fix login validation"
    ]
  }
}
```

#### Example Usage

**Get current work context:**
```json
{}
```

**Include recently closed issues:**
```json
{
  "include_closed_recent": true
}
```

#### Behavior Notes

- **Current Branch:** Includes phase state from `.st3/state.json`
- **Open Issues:** All open issues in repository
- **Recent Closed:** Last 7 days if `include_closed_recent=true`
- **Suggestions:** AI-generated suggestions based on branch, phase, and open issues
- **GitHub Token:** Requires `GITHUB_TOKEN` for issue data

---

### health_check

**MCP Name:** `health_check`  
**Class:** `HealthCheckTool`  
**File:** [mcp_server/tools/health_tools.py](../../../../mcp_server/tools/health_tools.py)

Check server health status.

#### Parameters

None.

#### Returns

```json
{
  "success": true,
  "health": {
    "status": "healthy",
    "uptime": 3600,
    "memory_usage_mb": 245.5,
    "registered_tools": 46,
    "github_token_set": true,
    "workspace_root": "/workspace",
    "python_version": "3.11.7",
    "server_version": "2.0.0"
  }
}
```

#### Example Usage

```json
{}
```

#### Health Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `status` | `str` | Overall status: `"healthy"`, `"degraded"`, `"unhealthy"` |
| `uptime` | `int` | Server uptime in seconds |
| `memory_usage_mb` | `float` | Current memory usage in megabytes |
| `registered_tools` | `int` | Number of registered MCP tools |
| `github_token_set` | `bool` | Whether `GITHUB_TOKEN` is configured |
| `workspace_root` | `str` | Absolute path to workspace root |
| `python_version` | `str` | Python runtime version |
| `server_version` | `str` | MCP server version |

#### Behavior Notes

- **Always Available:** No dependencies (doesn't require GitHub token)
- **Performance:** Minimal overhead (<10ms execution time)
- **Use Case:** Debugging, CI/CD health checks, agent diagnostics

---

### restart_server

**MCP Name:** `restart_server`  
**Class:** `RestartServerTool`  
**File:** [mcp_server/tools/admin_tools.py](../../../../mcp_server/tools/admin_tools.py)

Hot-reload MCP server to reload code changes via proxy mechanism.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `reason` | `str` | No | Description of why restart is needed (for audit logging) (default: `"code changes"`) |

#### Returns

```json
{
  "success": true,
  "message": "Server restart initiated",
  "restart": {
    "reason": "Updated safe_edit_file validation logic",
    "timestamp": "2026-02-08T12:00:00Z",
    "downtime_ms": 0
  }
}
```

#### Example Usage

**Restart after code changes:**
```json
{
  "reason": "Updated safe_edit_file validation logic"
}
```

**Restart without reason:**
```json
{}
```

#### Behavior Notes

- **Zero Downtime:** Proxy mechanism ensures no client disconnections
- **Code Reload:** Reloads all Python modules (tools, managers, services)
- **State Preservation:** Maintains client connections during restart
- **Wait Time:** **⏳ WAIT 3 SECONDS** after restart before calling next tool (server initialization time)
- **Audit Trail:** Records restart reason and timestamp in server logs

#### When to Use

- After modifying MCP tool code
- After updating validation logic
- After changing configuration files
- After updating templates

#### Proxy Architecture

The restart mechanism uses a transparent proxy:

1. **Proxy intercepts `restart_server` call**
2. **Proxy spawns new server process**
3. **Proxy waits for new process to be ready**
4. **Proxy switches traffic to new process**
5. **Proxy terminates old process**
6. **Zero client downtime** (connections maintained)

**See Also:** [docs/reference/mcp/proxy_restart.md](../proxy_restart.md) for detailed architecture.

---

## Common Use Cases

### Agent Onboarding: Discover Project Structure

```
1. search_documentation(query="project structure overview")
2. search_documentation(query="coding standards", scope="coding_standards")
3. search_documentation(query="how to implement a worker", scope="architecture")
4. get_work_context() → understand current work queue
```

### Find Relevant Documentation During Implementation

```
1. scaffold_artifact(artifact_type="worker", name="OrderWorker")
2. search_documentation(query="worker validation rules")
3. search_documentation(query="async patterns")
4. Implement worker based on documentation
```

### Check Work Queue

```
1. get_work_context()
2. Review open_issues and suggestions
3. git_checkout(branch="feature/123-oauth") → switch to issue branch
4. get_project_plan(issue_number=123) → review phase plan
```

### Development Iteration with Hot-Reload

```
1. safe_edit_file(path="mcp_server/tools/safe_edit_tool.py", ...)
2. restart_server(reason="Updated validation logic")
3. Wait 3 seconds
4. health_check() → verify server restarted
5. Test updated tool
```

---

## Configuration

### Documentation Search Paths

Search scopes map to directories:

```yaml
scopes:
  all: "docs/**/*.md"
  architecture: "docs/architecture/**/*.md"
  coding_standards: "docs/coding_standards/**/*.md"
  development: "docs/development/**/*.md"
  reference: "docs/reference/**/*.md"
  implementation: "docs/implementation/**/*.md"
```

### Restart Proxy Configuration

Proxy behavior configured in [mcp_server/proxy.py](../../../../mcp_server/proxy.py):

- **Startup timeout:** 10 seconds
- **Health check interval:** 500ms
- **Graceful shutdown timeout:** 5 seconds
- **Connection buffer:** 100 concurrent connections

---

## Performance Characteristics

### search_documentation

- **Index Size:** ~100 documents (≈1MB total)
- **Search Time:** 50-200ms (depends on query complexity)
- **Memory:** ~20MB for search index
- **Optimization:** Results cached for repeated queries (5 min TTL)

### get_work_context

- **GitHub API Calls:** 1-2 calls (issues + labels)
- **Execution Time:** 500-1500ms (network dependent)
- **Caching:** Issue data cached for 60 seconds

### health_check

- **Execution Time:** <10ms
- **Memory Overhead:** Negligible (<1MB)
- **Always Available:** No external dependencies

### restart_server

- **Downtime:** 0ms (proxy maintains connections)
- **Restart Time:** 2-3 seconds (new process initialization)
- **Memory:** Temporary 2x memory usage during overlap

---

## Related Documentation

- [README.md](README.md) — MCP Tools navigation index
- [docs/reference/mcp/proxy_restart.md](../proxy_restart.md) — Hot-reload proxy architecture (detailed)
- [docs/reference/mcp/mcp_vision_reference.md](../mcp_vision_reference.md) — MCP server architecture and vision
- [docs/development/issue19/research.md](../../../development/issue19/research.md) — Tool inventory research (Section 1.12: Discovery/Admin tools)

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 2.0 | 2026-02-08 | Agent | Complete reference for 4 discovery/admin tools: documentation search, work context, health check, server restart |
