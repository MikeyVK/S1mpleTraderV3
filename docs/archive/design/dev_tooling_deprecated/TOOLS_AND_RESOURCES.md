# docs/dev_tooling/TOOLS_AND_RESOURCES.md
# ST3 Workflow MCP Server - Tools & Resources Specification

**Status:** PRELIMINARY  
**Version:** 1.0  
**Created:** 2025-12-08  
**Last Updated:** 2025-12-08  

---

## Purpose

Complete specification of all MCP Resources (read-only data) and Tools (actions) provided by the ST3 Workflow MCP Server. Each entry includes schemas, examples, and implementation notes.

---

## Section 1: Resources

Resources provide read-only access to project state via the `st3://` URI scheme.

### 1.1 Status Resources

#### `st3://status/implementation`

```yaml
resource_name: implementation_dashboard
uri: "st3://status/implementation"
description: "Current implementation status: test counts, quality gates, module completion"
data_format: json
refresh_trigger: polling
cache_ttl: 30

schema:
  type: object
  properties:
    last_updated:
      type: string
      format: datetime
    total_tests:
      type: integer
    modules:
      type: array
      items:
        type: object
        properties:
          name: { type: string }
          tests_passing: { type: integer }
          tests_total: { type: integer }
          quality_gates:
            type: object
            properties:
              g1_whitespace: { type: number }
              g2_imports: { type: number }
              g3_line_length: { type: number }
              g4_types: { type: number }
              g5_tests: { type: number }
          status: { type: string, enum: [complete, in_progress, not_started] }

example_output: |
  {
    "last_updated": "2025-12-08T14:30:00Z",
    "total_tests": 456,
    "modules": [
      {
        "name": "backend.dtos.strategy.signal",
        "tests_passing": 32,
        "tests_total": 32,
        "quality_gates": { "g1": 10.0, "g2": 10.0, "g3": 10.0, "g4": 10.0, "g5": 10.0 },
        "status": "complete"
      }
    ]
  }
```

#### `st3://status/tests`

```yaml
resource_name: test_metrics
uri: "st3://status/tests"
description: "Real-time test counts per module, coverage percentages"
data_format: json
refresh_trigger: event
cache_ttl: null  # Invalidated on test file change

schema:
  type: object
  properties:
    total_tests: { type: integer }
    total_passing: { type: integer }
    coverage_percent: { type: number }
    by_directory:
      type: object
      additionalProperties:
        type: object
        properties:
          tests: { type: integer }
          passing: { type: integer }

example_output: |
  {
    "total_tests": 456,
    "total_passing": 456,
    "coverage_percent": 92.5,
    "by_directory": {
      "tests/unit/dtos/strategy": { "tests": 145, "passing": 145 },
      "tests/unit/dtos/execution": { "tests": 50, "passing": 50 },
      "tests/unit/core": { "tests": 94, "passing": 94 }
    }
  }
```

#### `st3://status/quality-gates`

```yaml
resource_name: quality_gates_status
uri: "st3://status/quality-gates"
description: "Current quality gate scores for staged/modified files"
data_format: json
refresh_trigger: event
cache_ttl: null

schema:
  type: object
  properties:
    files:
      type: array
      items:
        type: object
        properties:
          path: { type: string }
          gates:
            type: object
            properties:
              g1_whitespace: { type: number }
              g2_imports: { type: number }
              g3_line_length: { type: number }
              g4_types: { type: number, nullable: true }
              g5_tests: { type: string, enum: [passing, failing, no_tests] }
          all_passing: { type: boolean }

example_output: |
  {
    "files": [
      {
        "path": "backend/dtos/strategy/signal.py",
        "gates": { "g1": 10.0, "g2": 10.0, "g3": 10.0, "g4": 10.0, "g5": "passing" },
        "all_passing": true
      }
    ]
  }
```

---

### 1.2 Git Resources

#### `st3://git/status`

```yaml
resource_name: git_status
uri: "st3://git/status"
description: "Current branch, uncommitted changes, staged files"
data_format: json
refresh_trigger: polling
cache_ttl: 5

schema:
  type: object
  properties:
    branch: { type: string }
    is_clean: { type: boolean }
    staged_files: { type: array, items: { type: string } }
    modified_files: { type: array, items: { type: string } }
    untracked_files: { type: array, items: { type: string } }
    ahead: { type: integer }
    behind: { type: integer }

example_output: |
  {
    "branch": "feature/signal-dto-refactor",
    "is_clean": false,
    "staged_files": ["backend/dtos/strategy/signal.py"],
    "modified_files": ["tests/unit/dtos/strategy/test_signal.py"],
    "untracked_files": [],
    "ahead": 3,
    "behind": 0
  }
```

#### `st3://git/log`

```yaml
resource_name: git_log
uri: "st3://git/log"
description: "Recent commit history with conventional commit parsing"
data_format: json
refresh_trigger: polling
cache_ttl: 10

schema:
  type: object
  properties:
    commits:
      type: array
      items:
        type: object
        properties:
          hash: { type: string }
          short_hash: { type: string }
          message: { type: string }
          author: { type: string }
          date: { type: string, format: datetime }
          conventional:
            type: object
            nullable: true
            properties:
              type: { type: string }
              scope: { type: string, nullable: true }
              description: { type: string }
              tdd_status: { type: string, nullable: true }

example_output: |
  {
    "commits": [
      {
        "hash": "abc123def456",
        "short_hash": "abc123d",
        "message": "feat: implement Signal DTO\n\nStatus: GREEN",
        "author": "Developer",
        "date": "2025-12-08T14:00:00Z",
        "conventional": {
          "type": "feat",
          "scope": null,
          "description": "implement Signal DTO",
          "tdd_status": "GREEN"
        }
      }
    ]
  }
```

#### `st3://git/tdd-phase`

```yaml
resource_name: current_phase
uri: "st3://git/tdd-phase"
description: "Derived TDD phase (RED/GREEN/REFACTOR) from recent commits"
data_format: json
refresh_trigger: event
cache_ttl: null

schema:
  type: object
  properties:
    current_phase: { type: string, enum: [RED, GREEN, REFACTOR, UNKNOWN] }
    last_commit_type: { type: string, nullable: true }
    phase_commits:
      type: object
      properties:
        red: { type: integer }
        green: { type: integer }
        refactor: { type: integer }
    suggested_next: { type: string }

example_output: |
  {
    "current_phase": "GREEN",
    "last_commit_type": "feat",
    "phase_commits": { "red": 1, "green": 1, "refactor": 0 },
    "suggested_next": "REFACTOR: Run quality gates and improve code quality"
  }
```

#### `st3://git/branch`

```yaml
resource_name: branch_info
uri: "st3://git/branch"
description: "Branch name, type, linked issue"
data_format: json
refresh_trigger: polling
cache_ttl: 5

schema:
  type: object
  properties:
    name: { type: string }
    type: { type: string, enum: [feature, fix, refactor, docs, main, other] }
    linked_issue: { type: integer, nullable: true }
    is_main: { type: boolean }

example_output: |
  {
    "name": "feature/signal-dto-123",
    "type": "feature",
    "linked_issue": 123,
    "is_main": false
  }
```

---

### 1.3 GitHub Resources

#### `st3://github/issues`

```yaml
resource_name: github_issues
uri: "st3://github/issues"
description: "Open issues with labels, assignees, milestones"
data_format: json
refresh_trigger: polling
cache_ttl: 60

schema:
  type: object
  properties:
    issues:
      type: array
      items:
        type: object
        properties:
          number: { type: integer }
          title: { type: string }
          state: { type: string }
          labels: { type: array, items: { type: string } }
          milestone: { type: string, nullable: true }
          assignee: { type: string, nullable: true }
          created_at: { type: string }
          updated_at: { type: string }
          tdd_phase: { type: string, nullable: true }
          issue_type: { type: string, nullable: true }

example_output: |
  {
    "issues": [
      {
        "number": 42,
        "title": "Implement Signal DTO refactor",
        "state": "open",
        "labels": ["type:feature", "phase:green", "priority:high"],
        "milestone": "Week 1: Foundation",
        "assignee": "developer",
        "tdd_phase": "green",
        "issue_type": "feature"
      }
    ]
  }
```

#### `st3://github/pull-requests`

```yaml
resource_name: github_prs
uri: "st3://github/pull-requests"
description: "Open PRs with review status, checks, conflicts"
data_format: json
refresh_trigger: polling
cache_ttl: 60

schema:
  type: object
  properties:
    pull_requests:
      type: array
      items:
        type: object
        properties:
          number: { type: integer }
          title: { type: string }
          state: { type: string }
          head_branch: { type: string }
          base_branch: { type: string }
          mergeable: { type: boolean }
          checks_passing: { type: boolean }
          review_status: { type: string }
          linked_issues: { type: array, items: { type: integer } }
```

#### `st3://github/project`

```yaml
resource_name: github_project_board
uri: "st3://github/project"
description: "Project board columns, cards, WIP status"
data_format: json
refresh_trigger: polling
cache_ttl: 60

schema:
  type: object
  properties:
    project_name: { type: string }
    columns:
      type: array
      items:
        type: object
        properties:
          name: { type: string }
          cards_count: { type: integer }
          cards:
            type: array
            items:
              type: object
              properties:
                issue_number: { type: integer }
                title: { type: string }
```

#### `st3://github/milestones`

```yaml
resource_name: github_milestones
uri: "st3://github/milestones"
description: "Milestone progress, due dates, linked issues"
data_format: json
refresh_trigger: polling
cache_ttl: 300

schema:
  type: object
  properties:
    milestones:
      type: array
      items:
        type: object
        properties:
          title: { type: string }
          due_date: { type: string, nullable: true }
          open_issues: { type: integer }
          closed_issues: { type: integer }
          progress_percent: { type: number }
```

---

### 1.4 Documentation Resources

#### `st3://docs/inventory`

```yaml
resource_name: doc_inventory
uri: "st3://docs/inventory"
description: "All docs with line counts, template compliance, broken links"
data_format: json
refresh_trigger: polling
cache_ttl: 300

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
          over_limit: { type: boolean }
          template_type: { type: string, nullable: true }
          compliant: { type: boolean }
          broken_links: { type: integer }
          last_modified: { type: string }
```

#### `st3://docs/compliance`

```yaml
resource_name: doc_template_compliance
uri: "st3://docs/compliance"
description: "Per-doc template compliance check results"
data_format: json
refresh_trigger: event
cache_ttl: null

schema:
  type: object
  properties:
    results:
      type: array
      items:
        type: object
        properties:
          path: { type: string }
          template_type: { type: string }
          compliant: { type: boolean }
          missing_sections: { type: array, items: { type: string } }
          issues: { type: array, items: { type: string } }
```

---

### 1.5 Architecture Resources

#### `st3://arch/violations`

```yaml
resource_name: architecture_violations
uri: "st3://arch/violations"
description: "Detected anti-pattern violations"
data_format: json
refresh_trigger: event
cache_ttl: null

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
          remediation: { type: string }

example_output: |
  {
    "violations": [
      {
        "file": "backend/workers/my_worker.py",
        "line": 42,
        "pattern": "direct_eventbus_access",
        "message": "Worker directly calls EventBus.publish()",
        "severity": "error",
        "remediation": "Return DispositionEnvelope(PUBLISH, event_payload=...) instead"
      }
    ]
  }
```

#### `st3://arch/dtos`

```yaml
resource_name: dto_registry
uri: "st3://arch/dtos"
description: "All DTOs with field counts, validation rules, json_schema_extra presence"
data_format: json
refresh_trigger: polling
cache_ttl: 60

schema:
  type: object
  properties:
    dtos:
      type: array
      items:
        type: object
        properties:
          module: { type: string }
          class_name: { type: string }
          field_count: { type: integer }
          has_validators: { type: boolean }
          has_json_schema_extra: { type: boolean }
          frozen: { type: boolean }
          test_file: { type: string, nullable: true }
          test_count: { type: integer }
```

---

## Section 2: Discovery & Planning Tools

### `create_issue`

```yaml
tool_name: create_issue
description: "Create a new GitHub issue with proper template and labels"
category: github

parameters:
  - name: type
    type: string
    required: true
    description: "Issue type determining template"
    validation: enum [feature, bug, design, tech-debt]
  - name: title
    type: string
    required: true
    description: "Issue title"
    validation: "min_length: 10, max_length: 100"
  - name: body
    type: string
    required: true
    description: "Issue body in markdown format"
  - name: labels
    type: array
    required: false
    description: "Additional labels beyond type label"
  - name: milestone
    type: string
    required: false
    description: "Milestone title to assign"
  - name: project_column
    type: string
    required: false
    description: "Project column to add card to"
    validation: enum [backlog, in-progress, review, done]

returns:
  success:
    schema:
      issue_number: integer
      url: string
      labels: array
    example: |
      { "issue_number": 42, "url": "https://github.com/.../42", "labels": ["type:feature"] }
  error:
    codes:
      - code: GITHUB_AUTH_FAILED
        message: "GitHub authentication failed"
        resolution: "Check GITHUB_TOKEN environment variable"
      - code: MILESTONE_NOT_FOUND
        message: "Milestone 'X' not found"
        resolution: "Create milestone first or use existing milestone name"

implementation:
  prerequisites:
    - "GITHUB_TOKEN environment variable set"
    - "Repository exists and is accessible"
  steps:
    - description: "Validate issue type and select template"
    - description: "Create issue via GitHub API"
    - description: "Add to project board if specified"
  side_effects:
    - "Creates new GitHub issue"
    - "Optionally creates project card"

idempotency: false
dry_run_support: true
offline_capable: false
```

### `update_issue`

```yaml
tool_name: update_issue
description: "Update issue title, body, labels, or status"
category: github

parameters:
  - name: issue_number
    type: integer
    required: true
    description: "Issue number to update"
  - name: title
    type: string
    required: false
  - name: body
    type: string
    required: false
  - name: labels
    type: array
    required: false
    description: "Replace all labels (use add_label/remove_label for incremental)"
  - name: state
    type: string
    required: false
    validation: enum [open, closed]
  - name: add_labels
    type: array
    required: false
  - name: remove_labels
    type: array
    required: false

returns:
  success:
    schema:
      issue_number: integer
      updated_fields: array
    example: |
      { "issue_number": 42, "updated_fields": ["title", "labels"] }

idempotency: true
dry_run_support: true
offline_capable: false
```

### `link_issues`

```yaml
tool_name: link_issues
description: "Create parent/child or dependency relationship between issues"
category: github

parameters:
  - name: parent_issue
    type: integer
    required: true
  - name: child_issue
    type: integer
    required: true
  - name: link_type
    type: string
    required: true
    validation: enum [parent, blocks, relates]

implementation:
  steps:
    - description: "Add link reference to parent issue body"
    - description: "Add backlink reference to child issue body"
```

### `move_project_card`

```yaml
tool_name: move_project_card
description: "Move issue card between project board columns"
category: github

parameters:
  - name: issue_number
    type: integer
    required: true
  - name: target_column
    type: string
    required: true
    validation: enum [backlog, in-progress, review, done]

idempotency: true
```

---

## Section 3: Git Integration Tools

### `create_feature_branch`

```yaml
tool_name: create_feature_branch
description: "Create feature branch with proper naming from issue"
category: git

parameters:
  - name: issue_number
    type: integer
    required: false
    description: "GitHub issue to link (derives branch name from title)"
  - name: branch_type
    type: string
    required: true
    validation: enum [feature, fix, refactor, docs]
  - name: name
    type: string
    required: false
    description: "Custom branch name (used if no issue_number)"
    validation: "pattern: ^[a-z0-9-]+$"

returns:
  success:
    schema:
      branch_name: string
      switched: boolean
    example: |
      { "branch_name": "feature/signal-dto-42", "switched": true }
  error:
    codes:
      - code: BRANCH_EXISTS
        message: "Branch 'feature/X' already exists"
        resolution: "Use existing branch or choose different name"
      - code: UNCOMMITTED_CHANGES
        message: "Uncommitted changes in working directory"
        resolution: "Commit or stash changes first"

implementation:
  prerequisites:
    - "On main branch or specify source"
    - "Working directory clean (or force=true)"
  steps:
    - description: "Validate branch name format"
    - description: "Create branch from current HEAD"
    - description: "Switch to new branch"
    - description: "Update issue with branch link (if issue_number provided)"
  side_effects:
    - "Creates new git branch"
    - "Switches to new branch"
    - "Updates GitHub issue (if linked)"

idempotency: false
dry_run_support: true
offline_capable: true  # Git operations work offline
```

### `commit_with_convention`

```yaml
tool_name: commit_with_convention
description: "Create commit with validated conventional commit message"
category: git

parameters:
  - name: type
    type: string
    required: true
    validation: enum [test, feat, fix, refactor, docs, chore]
  - name: scope
    type: string
    required: false
    description: "Commit scope (e.g., 'signal', 'dto')"
  - name: description
    type: string
    required: true
    description: "Short description (imperative mood)"
    validation: "max_length: 72"
  - name: body
    type: string
    required: false
    description: "Extended description"
  - name: tdd_status
    type: string
    required: false
    validation: enum [RED, GREEN]
    description: "TDD phase status (omit for REFACTOR)"
  - name: issue_reference
    type: integer
    required: false
    description: "Issue number to reference in commit"

returns:
  success:
    schema:
      commit_hash: string
      message: string
    example: |
      { "commit_hash": "abc123d", "message": "feat(signal): implement Signal DTO\n\nStatus: GREEN" }
  error:
    codes:
      - code: NOTHING_STAGED
        message: "No files staged for commit"
        resolution: "Use stage_files first or specify files parameter"
      - code: INVALID_COMMIT_FORMAT
        message: "Commit message doesn't follow conventional format"
        resolution: "Check type and description format"

idempotency: false
dry_run_support: true
offline_capable: true
```

### `stage_files`

```yaml
tool_name: stage_files
description: "Stage files for commit with optional quality gate pre-check"
category: git

parameters:
  - name: files
    type: array | string
    required: true
    description: "File paths or 'all' for all modified"
  - name: run_quality_gates
    type: boolean
    required: false
    default: true
    description: "Run quality gates before staging"

returns:
  success:
    schema:
      staged: array
      quality_gates:
        all_passing: boolean
        details: object
  error:
    codes:
      - code: QUALITY_GATES_FAILED
        message: "Quality gates failed for X files"
        resolution: "Fix issues or use run_quality_gates=false"

idempotency: true
```

### `merge_to_main`

```yaml
tool_name: merge_to_main
description: "Merge current feature branch to main with quality verification"
category: git

parameters:
  - name: strategy
    type: string
    required: true
    validation: enum [squash, no-ff]
  - name: delete_branch
    type: boolean
    required: false
    default: true
  - name: skip_quality_check
    type: boolean
    required: false
    default: false
  - name: push
    type: boolean
    required: false
    default: true

implementation:
  prerequisites:
    - "On feature branch (not main)"
    - "All quality gates passing (unless skip_quality_check)"
    - "No uncommitted changes"
  steps:
    - description: "Run quality gates on all changed files"
    - description: "Switch to main branch"
    - description: "Merge with specified strategy"
    - description: "Push to origin (if push=true)"
    - description: "Delete feature branch (if delete_branch=true)"
  side_effects:
    - "Modifies main branch"
    - "Optionally deletes feature branch"
    - "Optionally pushes to remote"

idempotency: false
dry_run_support: true
offline_capable: false  # Push requires network
```

---

## Section 4: Quality Tools

### `run_quality_gates`

```yaml
tool_name: run_quality_gates
description: "Run all 5 quality gates on specified files"
category: quality

parameters:
  - name: files
    type: array | string
    required: true
    description: "File paths, 'staged', 'modified', or 'all'"
  - name: gates
    type: array
    required: false
    description: "Specific gates to run [1,2,3,4,5]"
    default: [1, 2, 3, 4, 5]
  - name: auto_fix
    type: boolean
    required: false
    default: false
    description: "Auto-fix whitespace issues (Gate 1 only)"

returns:
  success:
    schema:
      files_checked: integer
      all_passing: boolean
      results:
        type: array
        items:
          file: string
          gates:
            g1: { score: number, issues: array }
            g2: { score: number, issues: array }
            g3: { score: number, issues: array }
            g4: { score: number, issues: array, nullable: true }
            g5: { status: string }
    example: |
      {
        "files_checked": 2,
        "all_passing": true,
        "results": [
          {
            "file": "backend/dtos/strategy/signal.py",
            "gates": {
              "g1": { "score": 10.0, "issues": [] },
              "g2": { "score": 10.0, "issues": [] },
              "g3": { "score": 10.0, "issues": [] },
              "g4": { "score": 10.0, "issues": [] },
              "g5": { "status": "passing", "tests": 32 }
            }
          }
        ]
      }

implementation:
  steps:
    - description: "Gate 1: pylint --enable=trailing-whitespace,superfluous-parens"
      command: "python -m pylint {file} --disable=all --enable=trailing-whitespace,superfluous-parens"
    - description: "Gate 2: pylint --enable=import-outside-toplevel"
      command: "python -m pylint {file} --disable=all --enable=import-outside-toplevel"
    - description: "Gate 3: pylint --enable=line-too-long --max-line-length=100"
      command: "python -m pylint {file} --disable=all --enable=line-too-long --max-line-length=100"
    - description: "Gate 4: mypy --strict (DTOs only)"
      command: "python -m mypy {file} --strict --no-error-summary"
    - description: "Gate 5: pytest for corresponding test file"
      command: "pytest {test_file} -q --tb=line"
```

### `fix_whitespace`

```yaml
tool_name: fix_whitespace
description: "Auto-fix trailing whitespace in files"
category: quality

parameters:
  - name: files
    type: array | string
    required: true
    description: "File paths, 'staged', or 'modified'"

implementation:
  command: "(Get-Content {file}) | ForEach-Object { $_.TrimEnd() } | Set-Content {file}"
  side_effects:
    - "Modifies file content (removes trailing whitespace)"

idempotency: true
```

### `run_tests`

```yaml
tool_name: run_tests
description: "Run pytest on specified scope with optional coverage"
category: quality

parameters:
  - name: scope
    type: string
    required: false
    default: "all"
    description: "Test path or 'all'"
  - name: coverage
    type: boolean
    required: false
    default: false
  - name: verbose
    type: boolean
    required: false
    default: true
  - name: filter
    type: string
    required: false
    description: "Test name filter (-k flag)"

implementation:
  command: "pytest {scope} -v --tb=short [--cov=backend --cov-report=term-missing]"
```

---

## Section 5: Documentation Tools

### `validate_doc_template`

```yaml
tool_name: validate_doc_template
description: "Check document against required template structure"
category: docs

parameters:
  - name: file_path
    type: string
    required: true
  - name: template_type
    type: string
    required: true
    validation: enum [base, architecture, design, reference, tracking]

returns:
  success:
    schema:
      compliant: boolean
      missing_sections: array
      issues: array
      suggestions: array
```

### `check_doc_links`

```yaml
tool_name: check_doc_links
description: "Verify all markdown links in document are valid"
category: docs

parameters:
  - name: file_path
    type: string
    required: true
    description: "File path or 'all' for all docs"

returns:
  success:
    schema:
      files_checked: integer
      broken_links:
        type: array
        items:
          file: string
          line: integer
          link: string
          reason: string
```

### `generate_doc_from_template`

```yaml
tool_name: generate_doc_from_template
description: "Generate new document skeleton from template"
category: docs

parameters:
  - name: template_type
    type: string
    required: true
    validation: enum [architecture, design, reference, tracking]
  - name: output_path
    type: string
    required: true
  - name: title
    type: string
    required: true
  - name: placeholders
    type: object
    required: false
    description: "Key-value pairs to fill in template"

implementation:
  side_effects:
    - "Creates new file at output_path"
```

---

## Section 6: Workflow Orchestration Tools

### `start_feature`

```yaml
tool_name: start_feature
description: "Complete feature start workflow: create issue → create branch → update project"
category: workflow

parameters:
  - name: title
    type: string
    required: true
  - name: type
    type: string
    required: true
    validation: enum [feature, fix, refactor]
  - name: description
    type: string
    required: true
  - name: milestone
    type: string
    required: false

implementation:
  steps:
    - description: "Create GitHub issue with template"
      tool: create_issue
    - description: "Create feature branch linked to issue"
      tool: create_feature_branch
    - description: "Move issue to 'In Progress' column"
      tool: move_project_card
    - description: "Add 'phase:red' label (TDD starting)"
      tool: update_issue
  side_effects:
    - "Creates GitHub issue"
    - "Creates git branch"
    - "Updates project board"

idempotency: false
dry_run_support: true
```

### `complete_tdd_phase`

```yaml
tool_name: complete_tdd_phase
description: "Complete TDD phase: run tests → commit with status → update issue labels"
category: workflow

parameters:
  - name: phase
    type: string
    required: true
    validation: enum [red, green, refactor]
  - name: files
    type: array | string
    required: false
    default: "staged"
  - name: message
    type: string
    required: true
    description: "Commit description"

implementation:
  steps:
    - phase: red
      actions:
        - "Verify tests fail (expected)"
        - "Commit with type 'test', status 'RED'"
        - "Update issue label to 'phase:red'"
    - phase: green
      actions:
        - "Run tests, verify passing"
        - "Commit with type 'feat', status 'GREEN'"
        - "Update issue label to 'phase:green'"
    - phase: refactor
      actions:
        - "Run all quality gates"
        - "Verify tests still pass"
        - "Commit with type 'refactor'"
        - "Update issue label to 'phase:refactor'"
```

### `prepare_merge`

```yaml
tool_name: prepare_merge
description: "Pre-merge checklist: quality gates → update status → create PR or merge"
category: workflow

parameters:
  - name: create_pr
    type: boolean
    required: false
    default: false
  - name: pr_title
    type: string
    required: false
  - name: reviewers
    type: array
    required: false

implementation:
  steps:
    - description: "Run all quality gates on changed files"
    - description: "Update test count in resources"
    - description: "Create PR or merge directly based on create_pr flag"
    - description: "Update linked issue status"
```

### `sync_status_dashboard`

```yaml
tool_name: sync_status_dashboard
description: "Update IMPLEMENTATION_STATUS.md with current metrics from GitHub + tests"
category: workflow

parameters:
  - name: commit_changes
    type: boolean
    required: false
    default: true

implementation:
  steps:
    - description: "Gather test counts from pytest"
    - description: "Gather issue/milestone status from GitHub"
    - description: "Update IMPLEMENTATION_STATUS.md tables"
    - description: "Commit changes if commit_changes=true"
  side_effects:
    - "Modifies IMPLEMENTATION_STATUS.md"
    - "Optionally creates commit"
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-08 | Initial specification |
