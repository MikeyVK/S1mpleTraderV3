# ST3 Workflow MCP Server - Resources Specification

**Status:** DRAFT  
**Version:** 2.0  
**Last Updated:** 2025-12-08

---

## 1. Resources

Resources provide read-only, queryable context to the AI agent. They represent the current state of the project and are refreshed based on source changes.

---

### 1.1 `st3://status/implementation`

**Description:** Live view of project implementation status, test counts, and module completion metrics. Parsed from `docs/implementation/IMPLEMENTATION_STATUS.md`.

**Data Format:** `json`

**Refresh Trigger:** File watcher on `docs/implementation/IMPLEMENTATION_STATUS.md`

```yaml
schema:
  type: object
  properties:
    last_updated:
      type: string
      format: date
      description: "Date the status doc was last updated"
    quick_status:
      type: string
      description: "One-line summary (e.g., '456 tests passing')"
    summary_table:
      type: array
      description: "Layer-by-layer breakdown"
      items:
        type: object
        properties:
          layer: { type: string, examples: ["Strategy DTOs", "Shared DTOs", "Core Services"] }
          tests_passing: { type: integer }
          tests_total: { type: integer }
          quality_gates: { type: string, examples: ["10/10"] }
          status: { type: string, enum: ["✅ Complete", "🔄 In Progress", "🔴 Not Started"] }
    recent_updates:
      type: array
      description: "Last 5 significant changes"
      items:
        type: object
        properties:
          date: { type: string, format: date }
          description: { type: string }
          commit_hash: { type: string }
    technical_debt:
      type: object
      properties:
        open_items: { type: integer }
        resolved_items: { type: integer }

example_output: |
  {
    "last_updated": "2025-12-02",
    "quick_status": "456 tests passing (100% coverage), all quality gates 10/10",
    "summary_table": [
      { "layer": "Strategy DTOs", "tests_passing": 145, "tests_total": 145, "quality_gates": "10/10", "status": "✅ Complete" },
      { "layer": "Execution DTOs", "tests_passing": 50, "tests_total": 50, "quality_gates": "10/10", "status": "✅ Complete" }
    ],
    "recent_updates": [
      { "date": "2025-12-02", "description": "StrategyDirective: Added ExecutionPolicy field", "commit_hash": "cb7c761" }
    ],
    "technical_debt": { "open_items": 5, "resolved_items": 8 }
  }
```

---

### 1.2 `st3://status/phase`

**Description:** Derived state showing current development phase based on Git branch, GitHub Project board, and active issues. Helps agent understand what mode to operate in.

**Data Format:** `json`

**Refresh Trigger:** Git hook (branch change) + GitHub webhook/polling

```yaml
schema:
  type: object
  properties:
    current_phase:
      type: string
      enum: [Discovery, Planning, Design, Implementation, Integration, Documentation, Maintenance]
    phase_description:
      type: string
      description: "Human-readable context for the phase"
    active_branch:
      type: string
      description: "Current Git branch name"
    branch_type:
      type: string
      enum: [main, feature, fix, refactor, docs]
    current_sprint:
      type: object
      description: "Active GitHub Project iteration"
      properties:
        name: { type: string }
        start_date: { type: string, format: date }
        end_date: { type: string, format: date }
    blocking_issues:
      type: array
      items: { type: string }
      description: "Issues with 'blocker' or 'critical' label"
    in_progress_issues:
      type: array
      items:
        type: object
        properties:
          number: { type: integer }
          title: { type: string }
          assignee: { type: string }

example_output: |
  {
    "current_phase": "Implementation",
    "phase_description": "Week 1: Configuration Schemas",
    "active_branch": "feature/config-schemas-week1",
    "branch_type": "feature",
    "current_sprint": {
      "name": "Sprint 3: Config & Bootstrap",
      "start_date": "2025-12-02",
      "end_date": "2025-12-16"
    },
    "blocking_issues": ["#42: Config Schema validation failing"],
    "in_progress_issues": [
      { "number": 45, "title": "Implement WorkerManifest schema", "assignee": "mikey" }
    ]
  }
```

---

### 1.3 `st3://github/issues`

**Description:** Comprehensive view of GitHub issues with filtering by state, labels, milestone, and project.

**Data Format:** `json`

**Refresh Trigger:** Polling (TTL: 60 seconds) or webhook

**Dependencies:** `GITHUB_TOKEN` environment variable

```yaml
schema:
  type: object
  properties:
    open_count: { type: integer }
    closed_count: { type: integer }
    issues:
      type: array
      items:
        type: object
        properties:
          number: { type: integer }
          title: { type: string }
          state: { type: string, enum: [open, closed] }
          labels:
            type: array
            items: { type: string }
          milestone:
            type: object
            properties:
              title: { type: string }
              due_on: { type: string, format: date }
          assignees:
            type: array
            items: { type: string }
          project_status:
            type: string
            enum: [Backlog, Todo, In Progress, In Review, Done]
            description: "Status from GitHub Project board"
          linked_pr:
            type: integer
            description: "PR number if issue is linked to a PR"
          created_at: { type: string, format: datetime }
          updated_at: { type: string, format: datetime }
          closed_at: { type: string, format: datetime }

example_output: |
  {
    "open_count": 12,
    "closed_count": 45,
    "issues": [
      {
        "number": 45,
        "title": "Implement WorkerManifest schema",
        "state": "open",
        "labels": ["type:feature", "phase:implementation", "priority:high"],
        "milestone": { "title": "Week 1: Config Schemas", "due_on": "2025-12-09" },
        "assignees": ["mikey"],
        "project_status": "In Progress",
        "linked_pr": null,
        "created_at": "2025-12-01T10:00:00Z",
        "updated_at": "2025-12-08T14:30:00Z"
      }
    ]
  }
```

---

### 1.4 `st3://github/project`

**Description:** GitHub Project board state including columns, items, and iteration tracking.

**Data Format:** `json`

**Refresh Trigger:** Polling (TTL: 120 seconds)

**Dependencies:** `GITHUB_TOKEN` environment variable with `project` scope

```yaml
schema:
  type: object
  properties:
    project_name: { type: string }
    project_url: { type: string }
    columns:
      type: array
      items:
        type: object
        properties:
          name: { type: string }
          count: { type: integer }
          items:
            type: array
            items:
              type: object
              properties:
                type: { type: string, enum: [Issue, PR, DraftIssue] }
                number: { type: integer }
                title: { type: string }
                assignee: { type: string }
    current_iteration:
      type: object
      properties:
        name: { type: string }
        start_date: { type: string, format: date }
        end_date: { type: string, format: date }
        completed_points: { type: integer }
        total_points: { type: integer }
    metrics:
      type: object
      properties:
        velocity: { type: number, description: "Average points per sprint" }
        burndown:
          type: array
          items:
            type: object
            properties:
              date: { type: string, format: date }
              remaining: { type: integer }

example_output: |
  {
    "project_name": "ST3 Development",
    "project_url": "https://github.com/users/mikey/projects/1",
    "columns": [
      { "name": "Backlog", "count": 8, "items": [...] },
      { "name": "Todo", "count": 3, "items": [...] },
      { "name": "In Progress", "count": 2, "items": [...] },
      { "name": "Done", "count": 15, "items": [...] }
    ],
    "current_iteration": {
      "name": "Sprint 3",
      "start_date": "2025-12-02",
      "end_date": "2025-12-16",
      "completed_points": 8,
      "total_points": 21
    }
  }
```

---

### 1.5 `st3://git/status`

**Description:** Current branch, uncommitted changes, staged files, and TDD phase.

**Data Format:** `json`

**Refresh Trigger:** Polling (5s)

```yaml
schema:
  type: object
  properties:
    branch: { type: string }
    is_clean: { type: boolean }
    staged_files: { type: array, items: { type: string } }
    modified_files: { type: array, items: { type: string } }
    untracked_files: { type: array, items: { type: string } }
    tdd_phase: { type: string, enum: [RED, GREEN, REFACTOR, UNKNOWN] }
```

### 1.6 `st3://docs/inventory`

**Description:** Inventory of all documentation files with compliance status.

**Data Format:** `json`

**Refresh Trigger:** Polling (300s)

```yaml
schema:
  type: object
  properties:
    documents:
      type: array
      items:
        type: object
        properties:
          path: { type: string }
          line_count: { type: integer }
          template_compliance: { type: boolean }
          broken_links: { type: integer }
```

### 1.7 `st3://arch/violations`

**Description:** Detected architecture anti-patterns and violations.

**Data Format:** `json`

**Refresh Trigger:** On save

```yaml
schema:
  type: object
  properties:
    violations:
      type: array
      items:
        type: object
        properties:
          file: { type: string }
          line: { type: integer }
          pattern: { type: string }
          message: { type: string }
          severity: { type: string, enum: [error, warning] }
```

---

### 1.8 `st3://rules/coding_standards`

**Description:** Aggregated summary of all coding standards from `docs/coding_standards/`. Enables agent to understand and apply project rules without reading multiple files.

**Data Format:** `json`

**Refresh Trigger:** File watcher on `docs/coding_standards/*.md`

```yaml
schema:
  type: object
  properties:
    tdd_workflow:
      type: object
      properties:
        phases: { type: array, items: { type: string }, description: "RED, GREEN, REFACTOR" }
        commit_conventions:
          type: object
          properties:
            types: { type: array, items: { type: string }, examples: ["test", "feat", "refactor", "docs"] }
            message_template: { type: string }
        branch_naming:
          type: object
          properties:
            patterns: { type: array, items: { type: string }, examples: ["feature/*", "fix/*", "docs/*"] }
    quality_gates:
      type: array
      items:
        type: object
        properties:
          gate_number: { type: integer }
          name: { type: string }
          command: { type: string }
          expected_score: { type: string }
    code_style:
      type: object
      properties:
        max_line_length: { type: integer, default: 100 }
        import_grouping: { type: array, items: { type: string }, examples: ["Standard library", "Third-party", "Project modules"] }
        file_header_required: { type: boolean }
        docstring_style: { type: string, default: "Google Style" }
    anti_patterns:
      type: array
      items:
        type: object
        properties:
          name: { type: string }
          description: { type: string }
          detection: { type: string }
```

---

### 1.9 `st3://templates/list`

**Description:** Provides the complete template hierarchy and guidance on when to use each template. Sourced from `docs/reference/templates/README.md`.

**Data Format:** `json`

**Refresh Trigger:** File watcher on `docs/reference/templates/`

```yaml
schema:
  type: object
  properties:
    hierarchy:
      type: object
      description: "Template inheritance tree"
      properties:
        base_template:
          type: object
          properties:
            path: { type: string }
            inherits_from: { type: null }
            used_for: { type: string }
        architecture_template:
          type: object
          properties:
            path: { type: string }
            inherits_from: { type: string, default: "BASE_TEMPLATE" }
            used_for: { type: string }
            location: { type: string }
            sections_numbered: { type: boolean }
        design_template:
          type: object
          properties:
            path: { type: string }
            inherits_from: { type: string, default: "BASE_TEMPLATE" }
            used_for: { type: string }
            location: { type: string }
            sections_numbered: { type: boolean }
        reference_template:
          type: object
          properties:
            path: { type: string }
            inherits_from: { type: string, default: "BASE_TEMPLATE" }
            used_for: { type: string }
            location: { type: string }
            sections_numbered: { type: boolean }
        tracking_template:
          type: object
          properties:
            path: { type: string }
            inherits_from: { type: null, description: "Does NOT inherit from BASE" }
            used_for: { type: string }
            location: { type: string }
    decision_tree:
      type: string
      description: "Mermaid flowchart or text decision tree for template selection"
    status_lifecycle:
      type: array
      items: { type: string }
      description: "DRAFT → PRELIMINARY → APPROVED → DEFINITIVE"

example_output: |
  {
    "hierarchy": {
      "base_template": { "path": "docs/reference/templates/BASE_TEMPLATE.md", "used_for": "Foundation structure" },
      "architecture_template": { "path": "docs/reference/templates/ARCHITECTURE_TEMPLATE.md", "inherits_from": "BASE_TEMPLATE", "used_for": "System design (docs/architecture/)", "sections_numbered": true },
      "design_template": { "path": "docs/reference/templates/DESIGN_TEMPLATE.md", "inherits_from": "BASE_TEMPLATE", "used_for": "Pre-implementation decisions (docs/development/)", "sections_numbered": true },
      "reference_template": { "path": "docs/reference/templates/REFERENCE_TEMPLATE.md", "inherits_from": "BASE_TEMPLATE", "used_for": "API & implementation docs (docs/reference/)", "sections_numbered": false },
      "tracking_template": { "path": "docs/reference/templates/TRACKING_TEMPLATE.md", "inherits_from": null, "used_for": "Progress tracking, TODOs (docs/, docs/implementation/)" }
    },
    "status_lifecycle": ["DRAFT", "PRELIMINARY", "APPROVED", "DEFINITIVE"]
  }
```
