# ST3 Workflow MCP Server - Tools Specification

**Status:** v1.0 (Foundation)
**Last Updated:** 2025-01-21

> **Note:** These tools are currently in the planning/implementation phase. The foundation infrastructure (`BaseTool`) is implemented, but concrete tools are not yet available in the server.

---

## 1. Discovery & Planning Tools

Tools for understanding context and planning work.

---

### 1.1 `search_documentation`

**Description:** Semantic/fuzzy search across all `docs/` files. Returns ranked results with snippets.

**Category:** `discovery`

```yaml
parameters:
  - name: query
    type: string
    required: true
    description: "Search query (e.g., 'how to implement a worker', 'DTO validation rules')"
  - name: scope
    type: string
    required: false
    default: "all"
    validation: enum [all, architecture, coding_standards, development, reference, implementation]

returns:
  success:
    schema:
      type: array
      items:
        type: object
        properties:
          file_path: { type: string }
          title: { type: string }
          snippet: { type: string, description: "Context around match (150 chars)" }
          relevance_score: { type: number, minimum: 0, maximum: 1 }
          line_number: { type: integer }

implementation:
  steps:
    - "Index all .md files in docs/"
    - "Perform fuzzy/semantic matching against query"
    - "Rank by relevance"
    - "Return top 10 results"

idempotency: true
dry_run_support: false
offline_capable: true
```

---

### 1.2 `get_work_context`

**Description:** Aggregates context from GitHub Issues, Project board, and current branch to understand what to work on next.

**Category:** `planning`

```yaml
parameters:
  - name: include_closed_recent
    type: boolean
    required: false
    default: false
    description: "Include recently closed issues (last 7 days) for context"

returns:
  success:
    schema:
      type: object
      properties:
        active_issue:
          type: object
          description: "Issue linked to current branch (if any)"
          properties:
            number: { type: integer }
            title: { type: string }
            body: { type: string }
            acceptance_criteria:
              type: array
              items: { type: string }
              description: "Extracted from issue body (checkbox items)"
        in_progress_issues:
          type: array
          items:
            type: object
            properties:
              number: { type: integer }
              title: { type: string }
              priority: { type: string }
        next_up_issues:
          type: array
          description: "Issues in 'Todo' column ordered by priority"
          items:
            type: object
            properties:
              number: { type: integer }
              title: { type: string }
              labels: { type: array, items: { type: string } }
        blockers:
          type: array
          items:
            type: object
            properties:
              number: { type: integer }
              title: { type: string }
              blocked_by: { type: string, description: "Reason for blocking" }

implementation:
  steps:
    - "Get current branch name"
    - "Extract issue number from branch (feature/42-component-name → #42)"
    - "Fetch issue details if linked"
    - "Query GitHub Project for 'In Progress' and 'Todo' items"
    - "Identify blockers by label"
    - "Return aggregated context"

idempotency: true
offline_capable: false
```

---

## 2. Documentation Tools

Tools for creating, updating, and maintaining documentation.

---

### 2.1 `scaffold_document`

**Description:** Creates a new documentation file using the appropriate template. Supports all 5 template types.

**Category:** `documentation`

```yaml
parameters:
  - name: template_type
    type: string
    required: true
    validation: enum [architecture, design, reference, tracking, base]
    description: "Template to use (see st3://templates/list for guidance)"
  - name: document_name
    type: string
    required: true
    description: "Name of the document (e.g., 'MCP_SERVER', 'EVENT_ADAPTER')"
  - name: target_directory
    type: string
    required: false
    description: "Override default location (default inferred from template_type)"

returns:
  success:
    schema:
      type: object
      properties:
        created_path: { type: string }
        template_used: { type: string }
        placeholders_remaining:
          type: array
          items: { type: string }
          description: "List of {PLACEHOLDER} strings that need manual replacement"

implementation:
  prerequisites:
    - "Target file does not already exist"
  steps:
    - "Read template from docs/reference/templates/{template_type}_TEMPLATE.md"
    - "Replace automatic placeholders: {YYYY-MM-DD}, {DOCUMENT_NAME}"
    - "Determine target directory based on template_type:"
    - "  architecture → docs/architecture/"
    - "  design → docs/development/"
    - "  reference → docs/reference/"
    - "  tracking → docs/ or docs/implementation/"
    - "Write file to target location"
    - "Return list of remaining placeholders"
  side_effects:
    - "Creates new file in docs/"

idempotency: false
dry_run_support: true
offline_capable: true
```

---

### 2.2 `update_implementation_status`

**Description:** Updates `docs/implementation/IMPLEMENTATION_STATUS.md` after completing work. Adds row to appropriate table and updates test counts.

**Category:** `documentation`

```yaml
parameters:
  - name: component_name
    type: string
    required: true
    description: "Name of the component (e.g., 'signal.py', 'strategy_cache.py')"
  - name: layer
    type: string
    required: true
    validation: enum [Strategy DTOs, Execution DTOs, Shared DTOs, State DTOs, Core Services, Utilities]
  - name: tests_passing
    type: integer
    required: true
  - name: tests_total
    type: integer
    required: true
  - name: quality_gates
    type: string
    required: true
    default: "10/10"
  - name: status
    type: string
    required: true
    validation: enum [Complete, In Progress, Not Started]
  - name: update_description
    type: string
    required: true
    description: "Brief description for 'Recent Updates' section"

implementation:
  prerequisites:
    - "IMPLEMENTATION_STATUS.md exists"
    - "Component not already in target table (or update existing row)"
  steps:
    - "Find appropriate layer table"
    - "Add/update row with provided values"
    - "Update Summary table totals"
    - "Add entry to 'Recent Updates' section with today's date"
    - "Update 'Last Updated' header field"
  side_effects:
    - "Modifies IMPLEMENTATION_STATUS.md"

idempotency: false
dry_run_support: true
```

---

### 2.3 `validate_document_structure`

**Description:** Validates that a document follows its template structure. Checks required sections, heading levels, and link definitions.

**Category:** `documentation`

```yaml
parameters:
  - name: file_path
    type: string
    required: true
    description: "Path to document to validate"
  - name: template_type
    type: string
    required: false
    description: "Expected template type (auto-detected from path if not provided)"

returns:
  success:
    schema:
      type: object
      properties:
        valid: { type: boolean }
        template_detected: { type: string }
        issues:
          type: array
          items:
            type: object
            properties:
              severity: { type: string, enum: [error, warning] }
              message: { type: string }
              line_number: { type: integer }
        missing_sections:
          type: array
          items: { type: string }
        line_count: { type: integer }
        exceeds_limit: { type: boolean }
        limit: { type: integer }

implementation:
  steps:
    - "Read document"
    - "Detect template type from path or parameter"
    - "Check required sections per template:"
    - "  BASE: Header, Purpose, Scope, Content, Related Documentation, Version History"
    - "  ARCHITECTURE: + numbered sections, Constraints & Decisions"
    - "  DESIGN: + Context & Requirements, Design Options, Chosen Design, Open Questions"
    - "  REFERENCE: + Source, Tests, API Reference, Usage Examples"
    - "  TRACKING: Header (LIVING DOCUMENT), Current Focus, Quick Links, Summary"
    - "Check line limits: Standard 300, Architecture 1000, Templates 150"
    - "Check link definitions section exists"

idempotency: true
dry_run_support: false
offline_capable: true
```

---

## 3. GitHub Issue Management Tools

Tools for managing work items via GitHub Issues and Projects.

---

### 3.1 `create_issue`

**Description:** Creates a new GitHub issue with proper labels, milestone, and project assignment.

**Category:** `github`

```yaml
parameters:
  - name: title
    type: string
    required: true
    description: "Issue title (concise, actionable)"
  - name: body
    type: string
    required: true
    description: "Issue body in markdown (supports templates)"
  - name: labels
    type: array
    required: false
    description: "Labels to apply (e.g., ['type:feature', 'priority:high', 'phase:implementation'])"
  - name: milestone
    type: string
    required: false
    description: "Milestone title to assign (e.g., 'Week 1: Config Schemas')"
  - name: assignees
    type: array
    required: false
    description: "GitHub usernames to assign"
  - name: project_column
    type: string
    required: false
    default: "Backlog"
    validation: enum [Backlog, Todo, In Progress, In Review, Done]
    description: "Initial column in GitHub Project"

returns:
  success:
    schema:
      type: object
      properties:
        issue_number: { type: integer }
        issue_url: { type: string }
        project_item_id: { type: string }

implementation:
  steps:
    - "Validate labels exist in repository"
    - "Validate milestone exists"
    - "gh issue create --title '{title}' --body '{body}' --label {labels} --milestone '{milestone}' --assignee {assignees}"
    - "Add issue to GitHub Project in specified column"
    - "Return issue details"
  side_effects:
    - "Creates GitHub issue"
    - "Adds to Project board"

idempotency: false
dry_run_support: true
```

---

### 3.2 `update_issue`

**Description:** Updates an existing GitHub issue (title, body, labels, status, assignees).

**Category:** `github`

```yaml
parameters:
  - name: issue_number
    type: integer
    required: true
    description: "Issue number to update"
  - name: title
    type: string
    required: false
    description: "New title (if changing)"
  - name: body
    type: string
    required: false
    description: "New body (if changing)"
  - name: add_labels
    type: array
    required: false
    description: "Labels to add"
  - name: remove_labels
    type: array
    required: false
    description: "Labels to remove"
  - name: assignees
    type: array
    required: false
    description: "New assignees (replaces existing)"
  - name: project_column
    type: string
    required: false
    validation: enum [Backlog, Todo, In Progress, In Review, Done]
    description: "Move to different Project column"

returns:
  success:
    schema:
      type: object
      properties:
        issue_number: { type: integer }
        changes_applied:
          type: array
          items: { type: string }

implementation:
  steps:
    - "gh issue edit {issue_number} [--title] [--body] [--add-label] [--remove-label] [--assignee]"
    - "If project_column: Update Project item status"
  side_effects:
    - "Modifies GitHub issue"
    - "May update Project board"

idempotency: false
```

---

### 3.3 `close_issue`

**Description:** Closes a GitHub issue with optional closing comment and linked PR.

**Category:** `github`

```yaml
parameters:
  - name: issue_number
    type: integer
    required: true
    description: "Issue number to close"
  - name: reason
    type: string
    required: false
    validation: enum [completed, not_planned, duplicate]
    default: "completed"
  - name: comment
    type: string
    required: false
    description: "Closing comment (e.g., 'Completed in PR #123')"
  - name: linked_pr
    type: integer
    required: false
    description: "PR number that resolves this issue"

returns:
  success:
    schema:
      type: object
      properties:
        issue_number: { type: integer }
        closed_at: { type: string, format: datetime }
        project_column: { type: string, description: "Moved to 'Done' automatically" }

implementation:
  steps:
    - "If comment: gh issue comment {issue_number} --body '{comment}'"
    - "gh issue close {issue_number} --reason {reason}"
    - "Move Project item to 'Done' column"
  side_effects:
    - "Closes GitHub issue"
    - "Updates Project board"

idempotency: false
```

---

### 3.4 `link_issue_to_branch`

**Description:** Links a GitHub issue to the current feature branch. Enables automatic tracking.

**Category:** `github`

```yaml
parameters:
  - name: issue_number
    type: integer
    required: true
    description: "Issue number to link"
  - name: move_to_in_progress
    type: boolean
    required: false
    default: true
    description: "Move issue to 'In Progress' column"

returns:
  success:
    schema:
      type: object
      properties:
        branch_name: { type: string }
        issue_number: { type: integer }
        project_status: { type: string }

implementation:
  prerequisites:
    - "Current branch is not main"
    - "Issue exists and is open"
  steps:
    - "Add development branch reference to issue"
    - "If move_to_in_progress: Update Project item status to 'In Progress'"
    - "Add 'in-progress' label to issue"
  side_effects:
    - "Links branch to issue"
    - "Updates issue labels"
    - "Updates Project board"

idempotency: true
```

---

### 3.5 `start_work_on_issue`

**Description:** One-command workflow: creates feature branch from issue and links them together.

**Category:** `github`

```yaml
parameters:
  - name: issue_number
    type: integer
    required: true
    description: "Issue number to start work on"
  - name: branch_type
    type: string
    required: false
    default: "feature"
    validation: enum [feature, fix, refactor, docs]

returns:
  success:
    schema:
      type: object
      properties:
        branch_name: { type: string }
        issue:
          type: object
          properties:
            number: { type: integer }
            title: { type: string }
            acceptance_criteria: { type: array, items: { type: string } }

implementation:
  steps:
    - "Fetch issue details"
    - "Generate branch name: {branch_type}/{issue_number}-{slug-from-title}"
    - "Call create_feature_branch"
    - "Call link_issue_to_branch"
    - "Assign issue to current user if unassigned"
    - "Return issue context for agent"
  side_effects:
    - "Creates and switches to new branch"
    - "Updates issue status and labels"
    - "Updates Project board"

idempotency: false
```

---

### 3.6 `add_issue_comment`

**Description:** Adds a comment to a GitHub issue. Useful for progress updates and technical notes.

**Category:** `github`

```yaml
parameters:
  - name: issue_number
    type: integer
    required: true
  - name: body
    type: string
    required: true
    description: "Comment body in markdown"
  - name: comment_type
    type: string
    required: false
    validation: enum [progress, question, blocker, resolution]
    description: "Adds emoji prefix based on type"

implementation:
  steps:
    - "Format comment with type prefix:"
    - "  progress → 📝 Progress Update"
    - "  question → ❓ Question"
    - "  blocker → 🚫 Blocker"
    - "  resolution → ✅ Resolution"
    - "gh issue comment {issue_number} --body '{formatted_body}'"
  side_effects:
    - "Adds comment to issue"

idempotency: false
```

---

### 3.7 `create_milestone`

**Description:** Creates a GitHub milestone for tracking a phase or sprint.

**Category:** `github`

```yaml
parameters:
  - name: title
    type: string
    required: true
    description: "Milestone title (e.g., 'Week 1: Config Schemas')"
  - name: description
    type: string
    required: false
    description: "Milestone description"
  - name: due_date
    type: string
    required: false
    format: date
    description: "Due date in YYYY-MM-DD format"

returns:
  success:
    schema:
      type: object
      properties:
        milestone_number: { type: integer }
        milestone_url: { type: string }

implementation:
  steps:
    - "gh api /repos/{owner}/{repo}/milestones --method POST -f title='{title}' -f description='{description}' -f due_on='{due_date}T00:00:00Z'"
  side_effects:
    - "Creates GitHub milestone"

idempotency: false
```

---

## 4. Implementation Tools

Tools for generating code structure and scaffolding.

---

### 4.1 `scaffold_artifact` (Unified Scaffolding Tool)

**Description:** Unified tool for generating ANY artifact (code or documentation) using templates from `.st3/artifacts.yaml` registry. Replaces legacy `scaffold_component` and `scaffold_design_doc` tools.

**Category:** `implementation`

**Status:** ✅ Active (replaces deprecated scaffold_component/scaffold_design_doc)

```yaml
parameters:
  - name: artifact_type
    type: string
    required: true
    description: "Type ID from artifacts.yaml registry"
    examples: ["dto", "worker", "adapter", "design", "architecture", "tracking"]
  - name: name
    type: string
    required: true
    description: "Artifact name (PascalCase for code, kebab-case for docs)"
    examples: ["ExecutionRequest", "momentum-scanner-design"]
  - name: output_path
    type: string
    required: false
    description: "Optional explicit path (auto-resolved from registry if omitted)"
  - name: context
    type: object
    required: false
    description: "Template-specific variables (varies by artifact_type)"
    examples:
      dto: { category: "strategy", fields: [...] }
      design: { issue_number: "56", title: "...", author: "..." }
      worker: { worker_type: "signal_detector", description: "..." }

returns:
  success:
    schema:
      type: object
      properties:
        artifact_path:
          type: string
          description: "Path where artifact was created"
        artifact_type:
          type: string
          description: "Type from registry"
        validation_passed:
          type: boolean
          description: "Whether artifact passed validation"

implementation:
  - "Load artifacts.yaml registry configuration"
  - "Resolve output_path (explicit or from artifact config path_template)"
  - "Load Jinja2 template from artifact config template_path"
  - "Render template with context variables"
  - "Run validation chain: validate_syntax → validate_structure → validate_content"
  - "Write artifact to disk"
  - "Return ToolResult with success/error message"

side_effects:
  - "Creates new file at output_path"
  - "Validation errors returned in ToolResult (no exception)"

idempotency: false
dry_run_support: false
offline_capable: true
```

**Migration from Legacy Tools:**

```python
# OLD (deprecated - will fail):
scaffold_component(
    component_type="dto",
    name="execution_request",
    category="strategy"
)

# NEW (unified tool):
scaffold_artifact(
    artifact_type="dto",
    name="ExecutionRequest",
    context={"category": "strategy", "fields": [...]}
)
```

```python
# OLD (deprecated - will fail):
scaffold_design_doc(
    component_name="MomentumScanner",
    component_type="worker",
    implementation_phase="Week 1"
)

# NEW (unified tool):
scaffold_artifact(
    artifact_type="design",
    name="momentum-scanner-design",
    context={
        "issue_number": "42",
        "title": "Momentum Scanner Design",
        "author": "Agent"
    }
)
```

**Common Artifact Types:**

| artifact_type | Output Example | Template |
|---------------|----------------|----------|
| `dto` | `mcp_server/dtos/strategy/execution_request.py` | `templates/code/dto.py.jinja2` |
| `worker` | `mcp_server/workers/signal_detector/momentum_scanner.py` | `templates/code/worker.py.jinja2` |
| `adapter` | `mcp_server/adapters/ib_adapter.py` | `templates/code/adapter.py.jinja2` |
| `design` | `docs/development/issue56/design.md` | `templates/docs/DESIGN_TEMPLATE.md.jinja2` |
| `architecture` | `docs/development/issue56/architecture.md` | `templates/docs/ARCHITECTURE_TEMPLATE.md.jinja2` |
| `tracking` | `docs/development/issue56/tracking.md` | `templates/docs/TRACKING_TEMPLATE.md.jinja2` |

**Registry Configuration:** `.st3/artifacts.yaml`

---

## 5. Quality Tools

Tools for enforcing quality gates and fixing common issues.

---

### 5.1 `run_quality_gates`

**Description:** Runs all 5 mandatory quality gates on specified files. Returns pass/fail status and detailed diagnostics.

**Category:** `quality`

```yaml
parameters:
  - name: files
    type: array
    required: true
    description: "List of file paths to check (e.g., ['backend/dtos/strategy/signal.py'])"
  - name: include_tests
    type: boolean
    required: false
    default: true
    description: "Also check corresponding test files"
  - name: gates
    type: array
    required: false
    default: [1, 2, 3, 4, 5]
    description: "Which gates to run (1=whitespace, 2=imports, 3=line length, 4=mypy, 5=pytest)"

returns:
  success:
    schema:
      type: object
      properties:
        overall_pass: { type: boolean }
        gates:
          type: array
          items:
            type: object
            properties:
              gate_number: { type: integer }
              name: { type: string }
              passed: { type: boolean }
              score: { type: string }
              issues:
                type: array
                items:
                  type: object
                  properties:
                    file: { type: string }
                    line: { type: integer }
                    message: { type: string }
        test_results:
          type: object
          properties:
            passed: { type: integer }
            failed: { type: integer }
            errors: { type: array, items: { type: string } }

implementation:
  steps:
    - "For each file:"
    - "  Gate 1: python -m pylint {file} --disable=all --enable=trailing-whitespace,superfluous-parens"
    - "  Gate 2: python -m pylint {file} --disable=all --enable=import-outside-toplevel"
    - "  Gate 3: python -m pylint {file} --disable=all --enable=line-too-long --max-line-length=100"
    - "  Gate 4 (DTOs only): python -m mypy {file} --strict --no-error-summary"
    - "  Gate 5: pytest {test_file} -q --tb=line"
    - "Aggregate results"
    - "Return structured output"

idempotency: true
dry_run_support: false
offline_capable: true
```

---

### 5.2 `fix_whitespace`

**Description:** Auto-fixes trailing whitespace in specified files. Safe, non-destructive operation.

**Category:** `quality`

```yaml
parameters:
  - name: files
    type: array
    required: true
    description: "List of file paths to fix"

returns:
  success:
    schema:
      type: object
      properties:
        files_modified: { type: array, items: { type: string } }
        lines_fixed: { type: integer }

implementation:
  command: "(Get-Content {file}) | ForEach-Object { $_.TrimEnd() } | Set-Content {file}"
  side_effects:
    - "Modifies files in place"

idempotency: true
dry_run_support: true
```

---

### 5.3 `count_tests`

**Description:** Counts total tests in the project. Used for tracking progress and updating IMPLEMENTATION_STATUS.md.

**Category:** `quality`

```yaml
parameters:
  - name: scope
    type: string
    required: false
    default: "all"
    validation: enum [all, unit, integration]
    description: "Which test directories to count"

returns:
  success:
    schema:
      type: object
      properties:
        total: { type: integer }
        by_directory:
          type: object
          additionalProperties: { type: integer }

implementation:
  command: "pytest tests/{scope}/ --collect-only -q 2>$null | Select-String '^\\d+ tests'"

idempotency: true
offline_capable: true
```

---

### 5.4 `check_arch_compliance`

**Description:** Validates code against architectural patterns and rules.

**Category:** `quality`

```yaml
parameters:
  - name: scope
    type: string
    required: false
    default: "all"
    validation: enum [all, dtos, workers, platform]

implementation:
  steps:
    - "Scan code for anti-patterns defined in ARCHITECTURE.md"
    - "Check DTOs for Pydantic usage"
    - "Check Workers for EventBus pattern validity"
    - "Return list of violations"
```

---

### 5.5 `validate_dto`

**Description:** Validates a DTO definition against the DTO_TEMPLATE and best practices.

**Category:** `quality`

```yaml
parameters:
  - name: file_path
    type: string
    required: true

implementation:
  steps:
    - "Check for Pydantic BaseModel inheritance"
    - "Check for ConfigDict(frozen=True)"
    - "Check for json_schema_extra examples"
    - "Check for field descriptions"
```

---

## 6. Git Integration Tools

Tools for managing version control workflow.

---

### 6.1 `create_feature_branch`

**Description:** Creates a new Git branch enforcing project naming conventions from GIT_WORKFLOW.md.

**Category:** `git`

```yaml
parameters:
  - name: branch_type
    type: string
    required: true
    validation: enum [feature, fix, refactor, docs]
  - name: name
    type: string
    required: true
    description: "Descriptive name in kebab-case (e.g., 'config-schemas-week1')"
    validation: regex "^[a-z0-9-]+$"

returns:
  success:
    schema:
      type: object
      properties:
        branch_name: { type: string }
        created_from: { type: string }

implementation:
  prerequisites:
    - "No uncommitted changes (git status clean)"
    - "On main branch OR user confirms branching from current"
  steps:
    - "git checkout main"
    - "git pull origin main"
    - "git checkout -b {branch_type}/{name}"
  side_effects:
    - "Creates new local branch"
    - "Switches to new branch"

idempotency: false
```

---

### 6.2 `commit_tdd_phase`

**Description:** Creates a commit with proper Conventional Commits format for each TDD phase.

**Category:** `git`

```yaml
parameters:
  - name: phase
    type: string
    required: true
    validation: enum [red, green, refactor, docs]
    description: "TDD phase determines commit type (red=test, green=feat, refactor=refactor)"
  - name: component
    type: string
    required: true
    description: "Component being worked on (e.g., 'SizePlan DTO')"
  - name: details
    type: array
    required: false
    description: "Bullet points for commit body"
  - name: test_count
    type: string
    required: false
    description: "Test status (e.g., '20/20')"
  - name: quality_gates
    type: string
    required: false
    description: "Gate status (e.g., '10/10')"

returns:
  success:
    schema:
      type: object
      properties:
        commit_hash: { type: string }
        commit_message: { type: string }

implementation:
  steps:
    - "Map phase to commit type:"
    - "  red → test:"
    - "  green → feat:"
    - "  refactor → refactor:"
    - "  docs → docs:"
    - "Construct commit message:"
    - "  {type}: {summary for component}"
    - "  "
    - "  - {detail 1}"
    - "  - {detail 2}"
    - "  "
    - "  Status: {RED|GREEN}"
    - "  Quality gates: {quality_gates}"
    - "git add ."
    - "git commit -m '{message}'"
  side_effects:
    - "Stages all changes"
    - "Creates commit"

idempotency: false
```

---

### 6.3 `merge_to_main`

**Description:** Merges current feature branch to main with quality gate verification.

**Category:** `git`

```yaml
parameters:
  - name: merge_strategy
    type: string
    required: false
    default: "no-ff"
    validation: enum [no-ff, squash]
  - name: delete_branch
    type: boolean
    required: false
    default: true
    description: "Delete feature branch after merge"

returns:
  success:
    schema:
      type: object
      properties:
        merged_branch: { type: string }
        target_branch: { type: string }
        commit_hash: { type: string }

implementation:
  prerequisites:
    - "Current branch is NOT main"
    - "All quality gates pass (run_quality_gates on changed files)"
    - "All tests pass"
  steps:
    - "Run quality gates on all modified files"
    - "If any gate fails, abort with error"
    - "git checkout main"
    - "git merge {--no-ff|--squash} {current_branch}"
    - "If squash: git commit -m '{merge message}'"
    - "If delete_branch: git branch -d {current_branch}"
  side_effects:
    - "Merges branch to main"
    - "May delete local branch"

idempotency: false
```

---

### 6.4 `submit_pr`

**Description:** Pushes current branch and creates a GitHub Pull Request using project template.

**Category:** `git`

```yaml
parameters:
  - name: title
    type: string
    required: true
    description: "PR title (follows Conventional Commits: 'feat: implement X')"
  - name: description
    type: string
    required: false
    description: "Additional context for PR body"
  - name: labels
    type: array
    required: false
    description: "GitHub labels to add"

returns:
  success:
    schema:
      type: object
      properties:
        pr_url: { type: string }
        pr_number: { type: integer }

implementation:
  prerequisites:
    - "Branch is not main"
    - "Changes are committed"
  steps:
    - "git push -u origin HEAD"
    - "gh pr create --title '{title}' --body '{description}' --label {labels}"
  side_effects:
    - "Pushes branch to GitHub"
    - "Creates PR"

idempotency: false
```

---

## 7. Validation & Enforcement Rules

These rules are embedded in tools as pre-flight checks.

| Rule ID | Description | Enforcement Point | Blocking? |
|---------|-------------|--------------------|-----------|
| TDD-001 | RED commit contains only test files | `commit_tdd_phase(phase=red)` | ✅ Yes |
| TDD-002 | Branch naming follows `{type}/{name}` pattern | `create_feature_branch` | ✅ Yes |
| TDD-003 | Commit message follows Conventional Commits | `commit_tdd_phase` | ✅ Yes |
| QG-001 | Pylint score 10/10 for whitespace | `run_quality_gates`, `merge_to_main` | ✅ Yes |
| QG-002 | No imports inside functions | `run_quality_gates`, `merge_to_main` | ✅ Yes |
| QG-003 | Max line length 100 chars | `run_quality_gates`, `merge_to_main` | ✅ Yes |
| QG-004 | mypy strict passes (DTOs) | `run_quality_gates`, `merge_to_main` | ✅ Yes |
| QG-005 | All tests pass | `run_quality_gates`, `merge_to_main` | ✅ Yes |
| DOC-001 | Document line limits respected | `validate_document_structure` | ⚠️ Warning |
| DOC-002 | Required sections present | `validate_document_structure` | ⚠️ Warning |
| DOC-003 | Link definitions for all references | `validate_document_structure` | ⚠️ Warning |

---

## 8. Error Codes & Recovery

| Code | Tool | Cause | Recovery |
|------|------|-------|----------|
| `ERR_UNCOMMITTED_CHANGES` | `create_feature_branch`, `merge_to_main` | Git status not clean | Commit or stash changes first |
| `ERR_QUALITY_GATE_FAILED` | `merge_to_main` | One or more gates < 10/10 | Run `fix_whitespace`, fix issues manually, re-run gates |
| `ERR_TESTS_FAILING` | `merge_to_main` | pytest failed | Fix failing tests before merge |
| `ERR_BRANCH_EXISTS` | `create_feature_branch` | Branch already exists | Use different name or checkout existing |
| `ERR_FILE_EXISTS` | `scaffold_*` | Target file already exists | Use --overwrite flag or choose different name |
| `ERR_TEMPLATE_NOT_FOUND` | `scaffold_document` | Invalid template_type | Check `st3://templates/list` for valid types |
| `ERR_GITHUB_AUTH` | All GitHub tools | GITHUB_TOKEN missing/invalid | Set GITHUB_TOKEN environment variable |
| `ERR_RATE_LIMIT` | GitHub tools | GitHub API rate limited | Wait and retry, or use cached data |
| `ERR_ISSUE_NOT_FOUND` | `update_issue`, `close_issue` | Issue number doesn't exist | Verify issue number |
| `ERR_MILESTONE_NOT_FOUND` | `create_issue` | Milestone doesn't exist | Create milestone first |
| `ERR_PROJECT_NOT_FOUND` | Project tools | GitHub Project not configured | Set up GitHub Project first |

---

## 9. Implementation Notes

### Dependencies

- **Python 3.11+** (consistent with ST3 project)
- **mcp** package (Python MCP SDK)
- **GitPython** or subprocess for Git operations
- **PyGithub** for GitHub API
- **watchdog** for file system watching

### Cache Strategy

| Source | TTL | Invalidation |
|--------|-----|--------------|
| Filesystem (docs/) | 5s | File watcher triggers immediate refresh |
| Git state | 10s | Git hooks trigger refresh |
| GitHub API | 60s | Rate limit aware, conditional requests |
| Derived state | 0s (computed on-demand) | N/A |

### Extensibility

- New tools: Add Python function with `@mcp.tool()` decorator
- New resources: Add URI route with `@mcp.resource()` decorator
- New templates: Add to `docs/reference/templates/`, update `st3://templates/list`
