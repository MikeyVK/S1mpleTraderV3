# Issue #54 Design: Config Foundation Components

**Status:** DRAFT  
**Author:** GitHub Copilot (Claude Sonnet 4.5)  
**Date:** 2026-01-10  
**Issue:** #54 - Config: Scaffold Rules Configuration  
**Phase:** Design  
**Parent:** Epic #49 - MCP Platform Configurability

---

## Executive Summary

**Purpose:** Detailed component designs for config foundation implementation. Each design maps to implementation phases from planning.md with concrete schemas, interfaces, and behavioral specifications.

**Approach:** Four design phases matching planning.md build order:
1. **Phase 1:** Foundation configs + models (no dependencies)
2. **Phase 2:** Structure layer + DirectoryPolicyResolver (depends on Phase 1)
3. **Phase 3:** PolicyEngine refactor (depends on Phases 1+2)
4. **Phase 4:** Tool integration - ScaffoldComponentTool (depends on Phases 1+2)

**Design Philosophy:**
- Contracts first: Define interfaces before implementation
- Type safety: Pydantic models for all configs
- Fail-fast: Validation at config load time
- SSOT: Cross-config validation enforces referential integrity
- SRP: Each component owns ONE responsibility

---

## Related Documents

- [research.md](./research.md) - Research findings and scope decisions
- [planning.md](./planning.md) - Implementation strategy and build order
- [CORE_PRINCIPLES.md](../../architecture/CORE_PRINCIPLES.md) - Architectural principles
- workflows.yaml (Issue #50) - Phase definitions
- validation.yaml (Issue #52) - Template validation rules

---

## Phase 1 Design: Foundation Configs and Models

**Goal:** Create foundation configs and models with NO dependencies on other Issue #54 components.

**Components:** 
- `.st3/components.yaml` + `ComponentRegistryConfig` (WAT domain)
- `.st3/policies.yaml` + `OperationPoliciesConfig` (WANNEER domain)

**Build Order:** Both can be built in parallel (no interdependencies)

### 1.1 components.yaml Schema Design

**File Location:** `.st3/components.yaml`

**Purpose:** Component type registry (WAT domain) - defines what can be scaffolded

**Design Rationale:**
- Replaces hardcoded dict in `scaffold_tools.py` lines 105-115
- Single source of truth for component metadata
- Enables future dynamic loading (Issue #105)
- Self-documenting with descriptions

**Complete YAML Schema:**

```yaml
# Component Type Registry
# Purpose: Define scaffoldable component types and their metadata
# Used by: ScaffoldComponentTool for validation and dynamic scaffolder loading
# Cross-references: None (leaf config)
# NOTE: Issue #107 will add dynamic loading using scaffolder_class + scaffolder_module

component_types:
  dto:
    type_id: "dto"
    description: "Data Transfer Object - immutable data container (Pydantic BaseModel)"
    scaffolder_class: "DTOScaffolder"  # NEW (Issue #107): Explicit class name for dynamic loading
    scaffolder_module: "mcp_server.scaffolders.dto_scaffolder"  # NEW (Issue #107): Module path
    template_path: "mcp_server/scaffolding/templates/dto.py.j2"
    fallback_template: "mcp_server/scaffolding/templates/generic.py.j2"  # NEW (Issue #107): DRY fallback
    name_suffix: null  # NEW (Issue #107): No suffix for DTOs
    base_path: "backend/dtos"
    test_base_path: "tests/backend/dtos"
    generate_test: true
    required_fields:
      - name
      - description
    optional_fields:
      - fields
      - validation_rules
      - docstring
      - generate_test
  
  worker:
    type_id: "worker"
    description: "Worker - executes single domain operation (async task processor)"
    scaffolder_class: "WorkerScaffolder"  # NEW (Issue #107)
    scaffolder_module: "mcp_server.scaffolders.worker_scaffolder"  # NEW (Issue #107)
    template_path: "mcp_server/scaffolding/templates/worker.py.j2"
    fallback_template: "mcp_server/scaffolding/templates/generic.py.j2"  # NEW (Issue #107)
    name_suffix: "Worker"  # NEW (Issue #107): Auto-append if missing
    base_path: "backend/workers"
    test_base_path: "tests/backend/workers"
    generate_test: true
    required_fields:
      - name
      - input_dto
      - output_dto
    optional_fields:
      - dependencies
      - docstring
  
  adapter:
    type_id: "adapter"
    description: "Adapter - integrates external systems (implements Interface)"
    scaffolder_class: "AdapterScaffolder"  # NEW (Issue #107)
    scaffolder_module: "mcp_server.scaffolders.adapter_scaffolder"  # NEW (Issue #107)
    template_path: "mcp_server/scaffolding/templates/adapter.py.j2"
    fallback_template: "mcp_server/scaffolding/templates/generic.py.j2"  # NEW (Issue #107)
    name_suffix: "Adapter"  # NEW (Issue #107): Auto-append if missing
    base_path: "backend/adapters"
    test_base_path: "tests/backend/adapters"
    generate_test: true
    required_fields:
      - name
      - interface
    optional_fields:
      - dependencies
      - methods
      - docstring
  
  tool:
    type_id: "tool"
    description: "MCP Tool - exposes functionality via MCP protocol"
    scaffolder_class: "ToolScaffolder"  # NEW (Issue #107)
    scaffolder_module: "mcp_server.scaffolders.tool_scaffolder"  # NEW (Issue #107)
    template_path: "mcp_server/scaffolding/templates/tool.py.j2"
    fallback_template: "mcp_server/scaffolding/templates/generic.py.j2"  # NEW (Issue #107)
    name_suffix: "Tool"  # NEW (Issue #107): Auto-append if missing
    base_path: "mcp_server/tools"
    test_base_path: "tests/mcp_server/tools"
    generate_test: true
    required_fields:
      - name
      - input_schema
    optional_fields:
      - dependencies
      - docstring
  
  resource:
    type_id: "resource"
    description: "MCP Resource - provides dynamic content"
    scaffolder_class: "ResourceScaffolder"  # NEW (Issue #107)
    scaffolder_module: "mcp_server.scaffolders.resource_scaffolder"  # NEW (Issue #107)
    template_path: "mcp_server/scaffolding/templates/resource.py.j2"
    fallback_template: "mcp_server/scaffolding/templates/generic.py.j2"  # NEW (Issue #107)
    name_suffix: null  # NEW (Issue #107): No suffix for resources
    base_path: "mcp_server/resources"
    test_base_path: "tests/mcp_server/resources"
    generate_test: true
    required_fields:
      - name
      - uri_pattern
    optional_fields:
      - mime_type
      - docstring
  
  schema:
    type_id: "schema"
    description: "Pydantic Schema - validation models"
    scaffolder_class: "SchemaScaffolder"  # NEW (Issue #107)
    scaffolder_module: "mcp_server.scaffolders.schema_scaffolder"  # NEW (Issue #107)
    template_path: "mcp_server/scaffolding/templates/schema.py.j2"
    fallback_template: "mcp_server/scaffolding/templates/generic.py.j2"  # NEW (Issue #107)
    name_suffix: null  # NEW (Issue #107): No suffix for schemas
    base_path: "mcp_server/schemas"
    test_base_path: "tests/mcp_server/schemas"
    generate_test: true
    required_fields:
      - name
    optional_fields:
      - models
      - docstring
  
  interface:
    type_id: "interface"
    description: "Interface - abstract protocol definition"
    scaffolder_class: "InterfaceScaffolder"  # NEW (Issue #107)
    scaffolder_module: "mcp_server.scaffolders.interface_scaffolder"  # NEW (Issue #107)
    template_path: "mcp_server/scaffolding/templates/interface.py.j2"
    fallback_template: "mcp_server/scaffolding/templates/generic.py.j2"  # NEW (Issue #107)
    name_suffix: null  # NEW (Issue #107): No suffix for interfaces
    base_path: "backend/interfaces"
    test_base_path: "tests/backend/interfaces"
    generate_test: true
    required_fields:
      - name
    optional_fields:
      - methods
      - docstring
  
  service:
    type_id: "service"
    description: "Service - orchestration or business logic"
    scaffolder_class: "ServiceScaffolder"  # NEW (Issue #107)
    scaffolder_module: "mcp_server.scaffolders.service_scaffolder"  # NEW (Issue #107)
    template_path: "mcp_server/scaffolding/templates/service.py.j2"
    fallback_template: "mcp_server/scaffolding/templates/generic.py.j2"  # NEW (Issue #107)
    name_suffix: "Service"  # NEW (Issue #107): Auto-append if missing
    base_path: "backend/services"
    test_base_path: "tests/backend/services"
    generate_test: true
    required_fields:
      - name
    optional_fields:
      - service_type
      - dependencies
      - docstring
  
  generic:
    type_id: "generic"
    description: "Generic component from custom template"
    scaffolder_class: "GenericScaffolder"  # NEW (Issue #107)
    scaffolder_module: "mcp_server.scaffolders.generic_scaffolder"  # NEW (Issue #107)
    template_path: null  # Dynamic, specified at scaffold time
    fallback_template: null  # No fallback for generic
    name_suffix: null  # No suffix for generic
    base_path: null  # Dynamic, specified at scaffold time
    test_base_path: null  # Dynamic
    generate_test: false
    required_fields:
      - name
      - template_name
      - output_path
    optional_fields:
      - context
      - docstring
```

**Schema Constraints:**
- `type_id`: Unique component type identifier (dto, worker, adapter, etc.)
- `scaffolder_class`: Class name for dynamic loading (e.g., "DTOScaffolder") - **Issue #107**
- `scaffolder_module`: Module path for scaffolder class (e.g., "mcp_server.scaffolders.dto_scaffolder") - **Issue #107**
- `template_path`: Path relative to workspace root, must exist (validated at load time)
- `fallback_template`: Optional fallback template if primary not found - **Issue #107 DRY**
- `name_suffix`: Optional auto-append suffix (e.g., "Worker") - **Issue #107 DRY**
- `base_path`: Default directory for component type (can be overridden at scaffold time)
- `test_base_path`: Default test directory (follows backend/tests mirror structure)
- `generate_test`: Boolean flag (true = create test file, false = skip)
- `required_fields`: List of mandatory scaffold parameters (enforced at scaffold time)
- `optional_fields`: List of optional scaffold parameters (documented for tooling)
- `generic` type: Special case with null defaults, all fields specified at runtime

**Issue #107 Benefits:**
- Add new component type = edit config only (no code change)
- Scaffolder class loading is dynamic via `importlib.import_module(scaffolder_module)`
- Fallback template eliminates 8 DRY violations across scaffolders
- Name suffix logic eliminates 4 DRY violations (Worker, Adapter, Tool, Service)

---

### 1.2 ComponentRegistryConfig Model Design

**File Location:** `mcp_server/config/component_registry.py` (NEW)

**Purpose:** Type-safe config model with validation and singleton pattern

**Design Rationale:**
- Pydantic for validation and type safety
- Singleton to ensure single config instance
- Template existence validated at load time (fail-fast)
- Clear error messages with file/field context

**Complete Python Model:**

```python
"""Component registry configuration model.

Purpose: Load and validate components.yaml
Domain: WAT (what can be scaffolded)
Cross-references: None (leaf config)
"""

from pathlib import Path
from typing import Dict, List, Optional
import yaml
from pydantic import BaseModel, Field, field_validator

from mcp_server.core.errors import ConfigError


class ComponentDefinition(BaseModel):
    """Single component type definition."""
    
    type_id: str = Field(
        ..., 
        description="Component type identifier (dto, worker, etc.)"
    )
    description: str = Field(
        ..., 
        description="Human-readable description of component purpose"
    )
    scaffolder_class: str = Field(
        ..., 
        description="Scaffolder class name for dynamic loading (e.g., 'DTOScaffolder')"
    )
    scaffolder_module: str = Field(
        ..., 
        description="Module path for scaffolder class (e.g., 'mcp_server.scaffolders.dto_scaffolder')"
    )
    template_path: Optional[str] = Field(
        None, 
        description="Path to Jinja2 template (relative to workspace root)"
    )
    fallback_template: Optional[str] = Field(
        None, 
        description="Fallback template if primary template not found (DRY for Issue #107)"
    )
    name_suffix: Optional[str] = Field(
        None, 
        description="Auto-append suffix if missing (e.g., 'Worker' for workers) - Issue #107"
    )
    base_path: Optional[str] = Field(
        None, 
        description="Default output directory for this component type"
    )
    test_base_path: Optional[str] = Field(
        None, 
        description="Default test directory for this component type"
    )
    generate_test: bool = Field(
        True, 
        description="Whether to generate test file by default"
    )
    required_fields: List[str] = Field(
        default_factory=list, 
        description="Mandatory scaffold parameters"
    )
    optional_fields: List[str] = Field(
        default_factory=list, 
        description="Optional scaffold parameters"
    )
    
    @field_validator("template_path")
    @classmethod
    def validate_template_exists(cls, v: Optional[str]) -> Optional[str]:
        """Validate template file exists (if specified)."""
        if v is None:
            return v  # Allow null for generic type
        
        template_file = Path(v)
        if not template_file.exists():
            raise ValueError(
                f"Template file not found: {v}. "
                f"Expected template at workspace root."
            )
        return v
    
    @field_validator("fallback_template")
    @classmethod
    def validate_fallback_exists(cls, v: Optional[str]) -> Optional[str]:
        """Validate fallback template exists (if specified)."""
        if v is None:
            return v
        
        fallback_file = Path(v)
        if not fallback_file.exists():
            raise ValueError(
                f"Fallback template not found: {v}. "
                f"Expected template at workspace root."
            )
        return v
    
    def has_required_field(self, field_name: str) -> bool:
        """Check if field is required for this component type."""
        return field_name in self.required_fields
    
    def has_optional_field(self, field_name: str) -> bool:
        """Check if field is optional for this component type."""
        return field_name in self.optional_fields
    
    def all_fields(self) -> List[str]:
        """Get all fields (required + optional)."""
        return self.required_fields + self.optional_fields
    
    def validate_scaffold_fields(self, provided: Dict[str, any]) -> None:
        """Validate provided fields meet requirements.
        
        Args:
            provided: Dict of field names to values provided for scaffolding
            
        Raises:
            ValueError: If required fields are missing
        """
        missing = set(self.required_fields) - set(provided.keys())
        if missing:
            raise ValueError(
                f"Missing required fields for {self.type_id}: {sorted(missing)}"
            )


class ComponentRegistryConfig(BaseModel):
    """Component registry configuration (WAT domain).
    
    Purpose: Single source of truth for component type definitions
    Loaded from: .st3/components.yaml
    Used by: ScaffoldComponentTool, DirectoryPolicyResolver (indirect)
    """
    
    components: Dict[str, ComponentDefinition] = Field(
        ...,
        description="Component type definitions keyed by type_id"
    )
    
    # Singleton pattern
    _instance: Optional["ComponentRegistryConfig"] = None
    
    @classmethod
    def from_file(
        cls, 
        config_path: str = ".st3/components.yaml"
    ) -> "ComponentRegistryConfig":
        """Load config from YAML file (singleton pattern).
        
        Args:
            config_path: Path to components.yaml file
            
        Returns:
            Singleton instance of ComponentRegistryConfig
            
        Raises:
            ConfigError: If file not found or YAML invalid
        """
        # Return cached instance if exists
        if cls._instance is not None:
            return cls._instance
        
        # Load and parse YAML
        path = Path(config_path)
        if not path.exists():
            raise ConfigError(
                f"Config file not found: {config_path}",
                file_path=config_path
            )
        
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ConfigError(
                f"Invalid YAML in {config_path}: {e}",
                file_path=config_path
            )
        
        # Validate structure
        if "components" not in data:
            raise ConfigError(
                f"Missing 'components' key in {config_path}",
                file_path=config_path
            )
        
        # Transform to ComponentDefinition instances
        components = {}
        for type_id, comp_data in data["components"].items():
            try:
                components[type_id] = ComponentDefinition(
                    type_id=type_id,
                    **comp_data
                )
            except Exception as e:
                raise ConfigError(
                    f"Invalid component definition for '{type_id}': {e}",
                    file_path=config_path
                )
        
        # Create and cache instance
        cls._instance = cls(components=components)
        return cls._instance
    
    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton instance (for testing only)."""
        cls._instance = None
    
    def get_component(self, type_id: str) -> ComponentDefinition:
        """Get component definition by type ID.
        
        Args:
            type_id: Component type identifier (dto, worker, etc.)
            
        Returns:
            ComponentDefinition for requested type
            
        Raises:
            ValueError: If type_id not found in registry
        """
        if type_id not in self.components:
            available = sorted(self.components.keys())
            raise ValueError(
                f"Unknown component type: '{type_id}'. "
                f"Available types: {available}"
            )
        return self.components[type_id]
    
    def get_available_types(self) -> List[str]:
        """Get list of all registered component type IDs.
        
        Returns:
            Sorted list of component type identifiers
        """
        return sorted(self.components.keys())
    
    def has_component_type(self, type_id: str) -> bool:
        """Check if component type exists in registry.
        
        Args:
            type_id: Component type identifier to check
            
        Returns:
            True if type exists, False otherwise
        """
        return type_id in self.components
```

**Key Design Decisions:**
1. **Singleton Pattern:** Ensures single config load per process (performance + consistency)
2. **Eager Validation:** Template existence checked at load time (fail-fast)
3. **Clear Errors:** ConfigError includes file path, ValueError includes available options
4. **Type Safety:** Pydantic models provide IDE autocomplete and runtime validation
5. **Testability:** reset_instance() method enables test isolation

---

### 1.3 policies.yaml Schema Design

**File Location:** `.st3/policies.yaml`

**Purpose:** Operation phase policies (WANNEER domain) - defines when operations allowed

**Design Rationale:**
- Replaces hardcoded allowed_phases in `policy_engine.py`
- Operation-level policies only (directory-specific policies deferred to Epic #18)
- Empty allowed_phases = all phases (default permissive)
- Glob patterns for path matching (Q1 decision)

**Complete YAML Schema:**

```yaml
# Operation Phase Policies
# Purpose: Define when scaffold/create_file/commit operations are allowed
# Used by: PolicyEngine for operation decisions
# Cross-references: workflows.yaml (validates allowed_phases exist)

operations:
  scaffold:
    description: "Create new component from template"
    allowed_phases:
      - design
      - tdd
    # Phases where scaffolding is permitted
    # Empty list means: all phases allowed
    
  create_file:
    description: "Create arbitrary file (non-scaffolded)"
    allowed_phases: []  # All phases allowed
    blocked_patterns:
      # Glob patterns for paths where create_file is NOT allowed
      # These paths MUST use scaffold operation instead
      - "backend/**/*.py"
      - "mcp_server/tools/**/*.py"
      - "mcp_server/resources/**/*.py"
      - "mcp_server/adapters/**/*.py"
      - "mcp_server/workers/**/*.py"
    allowed_extensions:
      # File extensions allowed for create_file operation
      # Empty list means: all extensions allowed
      - ".md"
      - ".txt"
      - ".json"
      - ".yaml"
      - ".yml"
      - ".sh"
      - ".ps1"
      - ".rst"
      - ".toml"
      - ".ini"
      - ".cfg"
    
  commit:
    description: "Git commit with message"
    allowed_phases: []  # All phases allowed
    require_tdd_prefix: true  # Commit messages must start with TDD phase
    allowed_prefixes:
      # Valid TDD prefixes for commit messages
      - "red:"
      - "green:"
      - "refactor:"
      - "docs:"
```

**Schema Constraints:**
- `allowed_phases`: List of phase names (empty = all phases allowed)
- `blocked_patterns`: Glob patterns (Q1 decision - glob over regex)
- `allowed_extensions`: File extensions WITH leading dot (e.g., ".py" not "py")
- `require_tdd_prefix`: Boolean flag for commit message validation
- `allowed_prefixes`: List of valid TDD prefixes (lowercase, colon suffix)

**Scope Limitation:** 
Directory-specific phase policies (e.g., "backend allows scaffold only in design phase") are **DEFERRED to Epic #18**. This config only supports operation-level policies.

---

### 1.4 OperationPoliciesConfig Model Design

**File Location:** `mcp_server/config/operation_policies.py` (NEW)

**Purpose:** Type-safe model with cross-validation against workflows.yaml

**Design Rationale:**
- Cross-validates allowed_phases against WorkflowConfig (SSOT enforcement)
- Glob pattern matching using fnmatch (Python stdlib, simple)
- Empty allowed_phases interpreted as "all phases" (default permissive)
- Fail-fast on invalid phase references

**Complete Python Model:**

```python
"""Operation policies configuration model.

Purpose: Load and validate policies.yaml
Domain: WANNEER (when operations are allowed)
Cross-references: workflows.yaml (validates allowed_phases exist)
"""

from pathlib import Path
from typing import Dict, List, Optional
import fnmatch
import yaml
from pydantic import BaseModel, Field, field_validator

from mcp_server.core.errors import ConfigError
from mcp_server.config.workflow_config import WorkflowConfig


class OperationPolicy(BaseModel):
    """Single operation policy definition."""
    
    operation_id: str = Field(
        ...,
        description="Operation identifier (scaffold, create_file, commit)"
    )
    description: str = Field(
        ...,
        description="Human-readable description of operation"
    )
    allowed_phases: List[str] = Field(
        default_factory=list,
        description="Phases where operation allowed (empty = all phases)"
    )
    blocked_patterns: List[str] = Field(
        default_factory=list,
        description="Glob patterns for blocked file paths"
    )
    allowed_extensions: List[str] = Field(
        default_factory=list,
        description="File extensions allowed (empty = all extensions)"
    )
    require_tdd_prefix: bool = Field(
        False,
        description="Require TDD prefix in commit messages"
    )
    allowed_prefixes: List[str] = Field(
        default_factory=list,
        description="Valid TDD prefixes for commit messages"
    )
    
    @field_validator("allowed_extensions")
    @classmethod
    def validate_extension_format(cls, v: List[str]) -> List[str]:
        """Validate extensions have leading dot."""
        for ext in v:
            if not ext.startswith("."):
                raise ValueError(
                    f"File extension must start with dot: '{ext}' "
                    f"should be '.{ext}'"
                )
        return v
    
    def is_allowed_in_phase(self, phase: str) -> bool:
        """Check if operation allowed in given phase.
        
        Args:
            phase: Phase name to check
            
        Returns:
            True if operation allowed in phase, False otherwise
        """
        if not self.allowed_phases:  # Empty = all phases allowed
            return True
        return phase in self.allowed_phases
    
    def is_path_blocked(self, path: str) -> bool:
        """Check if path matches any blocked pattern.
        
        Args:
            path: File path to check (workspace-relative)
            
        Returns:
            True if path is blocked, False otherwise
        """
        for pattern in self.blocked_patterns:
            if fnmatch.fnmatch(path, pattern):
                return True
        return False
    
    def is_extension_allowed(self, path: str) -> bool:
        """Check if file extension is allowed.
        
        Args:
            path: File path to check
            
        Returns:
            True if extension allowed, False otherwise
        """
        if not self.allowed_extensions:  # Empty = all allowed
            return True
        
        ext = Path(path).suffix
        return ext in self.allowed_extensions
    
    def validate_commit_message(self, message: str) -> bool:
        """Check if commit message has valid TDD prefix.
        
        Args:
            message: Commit message to validate
            
        Returns:
            True if message valid or prefix not required, False otherwise
        """
        if not self.require_tdd_prefix:
            return True
        
        return any(
            message.startswith(prefix) 
            for prefix in self.allowed_prefixes
        )


class OperationPoliciesConfig(BaseModel):
    """Operation policies configuration (WANNEER domain).
    
    Purpose: Define when operations are allowed (phase-based policies)
    Loaded from: .st3/policies.yaml
    Used by: PolicyEngine for operation decisions
    Cross-validates: allowed_phases against workflows.yaml
    """
    
    operations: Dict[str, OperationPolicy] = Field(
        ...,
        description="Operation policy definitions keyed by operation_id"
    )
    
    # Singleton pattern
    _instance: Optional["OperationPoliciesConfig"] = None
    
    @classmethod
    def from_file(
        cls,
        config_path: str = ".st3/policies.yaml"
    ) -> "OperationPoliciesConfig":
        """Load config from YAML file with cross-validation.
        
        Args:
            config_path: Path to policies.yaml file
            
        Returns:
            Singleton instance of OperationPoliciesConfig
            
        Raises:
            ConfigError: If file not found, YAML invalid, or cross-validation fails
        """
        # Return cached instance if exists
        if cls._instance is not None:
            return cls._instance
        
        # Load and parse YAML
        path = Path(config_path)
        if not path.exists():
            raise ConfigError(
                f"Config file not found: {config_path}",
                file_path=config_path
            )
        
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ConfigError(
                f"Invalid YAML in {config_path}: {e}",
                file_path=config_path
            )
        
        # Validate structure
        if "operations" not in data:
            raise ConfigError(
                f"Missing 'operations' key in {config_path}",
                file_path=config_path
            )
        
        # Transform to OperationPolicy instances
        operations = {}
        for op_id, op_data in data["operations"].items():
            try:
                operations[op_id] = OperationPolicy(
                    operation_id=op_id,
                    **op_data
                )
            except Exception as e:
                raise ConfigError(
                    f"Invalid operation policy for '{op_id}': {e}",
                    file_path=config_path
                )
        
        # Create instance
        instance = cls(operations=operations)
        
        # Cross-validation: Check allowed_phases exist in workflows.yaml
        instance._validate_phases()
        
        # Cache and return
        cls._instance = instance
        return cls._instance
    
    def _validate_phases(self) -> None:
        """Cross-validate allowed_phases against workflows.yaml.
        
        Raises:
            ConfigError: If any operation references unknown phase
        """
        try:
            workflow_config = WorkflowConfig.from_file()
            valid_phases = workflow_config.get_all_phases()
        except Exception as e:
            raise ConfigError(
                f"Failed to load workflows.yaml for cross-validation: {e}",
                file_path=".st3/workflows.yaml"
            )
        
        for op_id, policy in self.operations.items():
            invalid_phases = set(policy.allowed_phases) - valid_phases
            if invalid_phases:
                raise ConfigError(
                    f"Operation '{op_id}' references unknown phases: {sorted(invalid_phases)}. "
                    f"Valid phases from workflows.yaml: {sorted(valid_phases)}",
                    file_path=".st3/policies.yaml"
                )
    
    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton instance (for testing only)."""
        cls._instance = None
    
    def get_operation_policy(self, operation_id: str) -> OperationPolicy:
        """Get policy for specific operation.
        
        Args:
            operation_id: Operation identifier (scaffold, create_file, commit)
            
        Returns:
            OperationPolicy for requested operation
            
        Raises:
            ValueError: If operation_id not found in config
        """
        if operation_id not in self.operations:
            available = sorted(self.operations.keys())
            raise ValueError(
                f"Unknown operation: '{operation_id}'. "
                f"Available operations: {available}"
            )
        return self.operations[operation_id]
    
    def get_available_operations(self) -> List[str]:
        """Get list of all configured operation IDs.
        
        Returns:
            Sorted list of operation identifiers
        """
        return sorted(self.operations.keys())
```

**Key Design Decisions:**
1. **Cross-Validation:** _validate_phases() enforces SSOT with workflows.yaml
2. **Helper Methods:** is_allowed_in_phase(), is_path_blocked(), etc. simplify PolicyEngine
3. **Glob Matching:** fnmatch.fnmatch() for pattern matching (Python stdlib, Q1 decision)
4. **Default Permissive:** Empty lists interpreted as "allow all"
5. **Clear Errors:** ConfigError with file path, ValueError with available options

---

### 1.5 Phase 1 Test Strategy

**Goal:** 100% coverage on foundation components

**ComponentRegistryConfig Unit Tests:**

```python
def test_load_valid_config():
    """Test loading valid components.yaml"""
    config = ComponentRegistryConfig.from_file(".st3/components.yaml")
    assert len(config.components) == 9
    assert "dto" in config.components
    assert config.components["dto"].template == "mcp_server/scaffolding/templates/dto.py.j2"

def test_singleton_pattern():
    """Test singleton returns same instance"""
    config1 = ComponentRegistryConfig.from_file()
    config2 = ComponentRegistryConfig.from_file()
    assert config1 is config2

def test_missing_file():
    """Test ConfigError when file not found"""
    with pytest.raises(ConfigError, match="Config file not found"):
        ComponentRegistryConfig.from_file(".st3/nonexistent.yaml")

def test_invalid_yaml():
    """Test ConfigError on YAML syntax error"""
    # Create invalid YAML file in temp location
    with pytest.raises(ConfigError, match="Invalid YAML"):
        ...

def test_missing_template():
    """Test ValueError when template doesn't exist"""
    # Create config with invalid template path
    with pytest.raises(ValueError, match="Template file not found"):
        ...

def test_get_component_valid():
    """Test get_component with valid type"""
    config = ComponentRegistryConfig.from_file()
    dto = config.get_component("dto")
    assert dto.type_id == "dto"

def test_get_component_invalid():
    """Test get_component with unknown type"""
    config = ComponentRegistryConfig.from_file()
    with pytest.raises(ValueError, match="Unknown component type"):
        config.get_component("invalid_type")

def test_validate_required_fields_complete():
    """Test field validation with all required fields"""
    config = ComponentRegistryConfig.from_file()
    dto = config.get_component("dto")
    dto.validate_scaffold_fields({"name": "User", "description": "User DTO"})
    # Should not raise

def test_validate_required_fields_missing():
    """Test field validation with missing fields"""
    config = ComponentRegistryConfig.from_file()
    dto = config.get_component("dto")
    with pytest.raises(ValueError, match="Missing required fields"):
        dto.validate_scaffold_fields({"name": "User"})  # Missing description
```

**OperationPoliciesConfig Unit Tests:**

```python
def test_load_valid_config():
    """Test loading valid policies.yaml"""
    config = OperationPoliciesConfig.from_file(".st3/policies.yaml")
    assert len(config.operations) == 3
    assert "scaffold" in config.operations

def test_cross_validation_success():
    """Test cross-validation with valid phases"""
    # All phases in policies.yaml exist in workflows.yaml
    config = OperationPoliciesConfig.from_file()
    assert "scaffold" in config.operations

def test_cross_validation_failure():
    """Test cross-validation with unknown phase"""
    # Create config with invalid phase reference
    with pytest.raises(ConfigError, match="references unknown phases"):
        ...

def test_is_allowed_in_phase_explicit():
    """Test phase check with explicit allowed_phases"""
    config = OperationPoliciesConfig.from_file()
    scaffold = config.get_operation_policy("scaffold")
    assert scaffold.is_allowed_in_phase("design") is True
    assert scaffold.is_allowed_in_phase("refactor") is False

def test_is_allowed_in_phase_empty():
    """Test phase check with empty allowed_phases (all allowed)"""
    config = OperationPoliciesConfig.from_file()
    create = config.get_operation_policy("create_file")
    assert create.is_allowed_in_phase("design") is True
    assert create.is_allowed_in_phase("refactor") is True

def test_is_path_blocked():
    """Test glob pattern matching for blocked paths"""
    config = OperationPoliciesConfig.from_file()
    create = config.get_operation_policy("create_file")
    assert create.is_path_blocked("backend/foo.py") is True
    assert create.is_path_blocked("scripts/bar.sh") is False

def test_is_extension_allowed():
    """Test extension validation"""
    config = OperationPoliciesConfig.from_file()
    create = config.get_operation_policy("create_file")
    assert create.is_extension_allowed("docs/foo.md") is True
    assert create.is_extension_allowed("backend/foo.py") is False

def test_validate_commit_message():
    """Test TDD prefix validation"""
    config = OperationPoliciesConfig.from_file()
    commit = config.get_operation_policy("commit")
    assert commit.validate_commit_message("red: add failing test") is True
    assert commit.validate_commit_message("invalid: bad prefix") is False
```

**Phase 1 Integration Test:**

```python
def test_both_configs_load_successfully():
    """Test both Phase 1 configs load without errors"""
    component_config = ComponentRegistryConfig.from_file()
    operation_config = OperationPoliciesConfig.from_file()
    
    assert len(component_config.components) == 9
    assert len(operation_config.operations) == 3
```

**Coverage Target:** 100% line coverage, 100% branch coverage

---

## Phase 2 Design: Structure Layer (DirectoryPolicyResolver)

**Goal:** Create project structure config and directory policy resolution utility.

**Components:**
- `.st3/project_structure.yaml` + `ProjectStructureConfig` (WAAR domain)
- `DirectoryPolicyResolver` utility (path matching, inheritance)

**Dependencies:** ComponentRegistryConfig (for cross-validation)

### 2.1 project_structure.yaml Schema Design

**File Location:** `.st3/project_structure.yaml`

**Purpose:** Directory structure and file policies (WAAR domain) - defines where components can be created

**Design Rationale:**
- Flat list with parent field (Q4 decision - implicit inheritance)
- Replaces hardcoded directory rules in `policy_engine.py`
- Glob patterns for require_scaffold_for (Q1 decision)
- Cross-references components.yaml for allowed_component_types validation

**Complete YAML Schema:**

```yaml
# Project Structure Configuration
# Purpose: Define directory structure and file policies
# Used by: DirectoryPolicyResolver for path validation
# Cross-references: components.yaml (validates allowed_component_types exist)

directories:
  backend:
    parent: null  # Top-level directory
    description: "Backend application code"
    allowed_component_types:
      - dto
      - worker
      - adapter
      - interface
      - service
    allowed_extensions:
      - ".py"
    require_scaffold_for:
      - "**/*.py"  # All Python files in backend must be scaffolded
  
  backend/dtos:
    parent: backend
    description: "Data Transfer Objects"
    allowed_component_types:
      - dto  # Override: Only DTOs allowed in this subdirectory
    # Inherits allowed_extensions from parent (implicit)
    # Inherits require_scaffold_for from parent (cumulative)
  
  backend/workers:
    parent: backend
    description: "Domain operation workers"
    allowed_component_types:
      - worker
  
  backend/adapters:
    parent: backend
    description: "External system adapters"
    allowed_component_types:
      - adapter
  
  backend/interfaces:
    parent: backend
    description: "Abstract protocol definitions"
    allowed_component_types:
      - interface
  
  backend/services:
    parent: backend
    description: "Orchestration and business logic"
    allowed_component_types:
      - service
  
  mcp_server:
    parent: null
    description: "MCP platform code"
    allowed_component_types:
      - tool
      - resource
      - schema
    allowed_extensions:
      - ".py"
    require_scaffold_for:
      - "tools/**/*.py"
      - "resources/**/*.py"
  
  mcp_server/tools:
    parent: mcp_server
    description: "MCP tool implementations"
    allowed_component_types:
      - tool
  
  mcp_server/resources:
    parent: mcp_server
    description: "MCP resource providers"
    allowed_component_types:
      - resource
  
  mcp_server/schemas:
    parent: mcp_server
    description: "Pydantic validation schemas"
    allowed_component_types:
      - schema
  
  tests:
    parent: null
    description: "Test suite"
    allowed_component_types: []  # No component types (manual test files)
    allowed_extensions:
      - ".py"
    require_scaffold_for: []  # Tests not required to be scaffolded
  
  docs:
    parent: null
    description: "Documentation"
    allowed_component_types: []
    allowed_extensions:
      - ".md"
      - ".rst"
    require_scaffold_for: []
  
  .st3:
    parent: null
    description: "Platform configuration"
    allowed_component_types: []
    allowed_extensions:
      - ".yaml"
      - ".yml"
    require_scaffold_for: []
  
  scripts:
    parent: null
    description: "Utility scripts (no restrictions)"
    allowed_component_types: []
    allowed_extensions: []  # All extensions allowed
    require_scaffold_for: []
  
  proof_of_concepts:
    parent: null
    description: "Experimental code (no restrictions)"
    allowed_component_types: []
    allowed_extensions: []
    require_scaffold_for: []
```

**Inheritance Rules (Q4 decision - implicit):**
- `allowed_extensions`: Child inherits from parent unless explicitly overridden
- `allowed_component_types`: Child overrides parent (no merge)
- `require_scaffold_for`: Child ADDS to parent patterns (cumulative)

**Schema Constraints:**
- `parent`: Directory path or null (top-level)
- `allowed_component_types`: Must exist in components.yaml (cross-validated)
- `allowed_extensions`: List of extensions WITH leading dot
- `require_scaffold_for`: List of glob patterns (relative to directory)

---

### 2.2 ProjectStructureConfig Model Design

**File Location:** `mcp_server/config/project_structure.py` (NEW)

**Purpose:** Load and validate project_structure.yaml with cross-validation

**Complete Python Model:**

```python
"""Project structure configuration model.

Purpose: Load and validate project_structure.yaml
Domain: WAAR (where components can be created)
Cross-references: components.yaml (validates allowed_component_types)
"""

from pathlib import Path
from typing import Dict, List, Optional
import yaml
from pydantic import BaseModel, Field

from mcp_server.core.errors import ConfigError
from mcp_server.config.component_registry import ComponentRegistryConfig


class DirectoryPolicy(BaseModel):
    """Directory-specific file and component policies."""
    
    path: str = Field(..., description="Directory path (workspace-relative)")
    parent: Optional[str] = Field(None, description="Parent directory path")
    description: str = Field(..., description="Human-readable description")
    allowed_component_types: List[str] = Field(
        default_factory=list,
        description="Component types allowed in this directory"
    )
    allowed_extensions: List[str] = Field(
        default_factory=list,
        description="File extensions allowed (empty = all allowed)"
    )
    require_scaffold_for: List[str] = Field(
        default_factory=list,
        description="Glob patterns requiring scaffolding"
    )


class ProjectStructureConfig(BaseModel):
    """Project structure configuration (WAAR domain).
    
    Purpose: Define directory structure and file policies
    Loaded from: .st3/project_structure.yaml
    Used by: DirectoryPolicyResolver for path validation
    Cross-validates: allowed_component_types against components.yaml
    """
    
    directories: Dict[str, DirectoryPolicy] = Field(
        ...,
        description="Directory policies keyed by directory path"
    )
    
    # Singleton pattern
    _instance: Optional["ProjectStructureConfig"] = None
    
    @classmethod
    def from_file(
        cls,
        config_path: str = ".st3/project_structure.yaml"
    ) -> "ProjectStructureConfig":
        """Load config from YAML file with cross-validation."""
        if cls._instance is not None:
            return cls._instance
        
        # Load YAML
        path = Path(config_path)
        if not path.exists():
            raise ConfigError(
                f"Config file not found: {config_path}",
                file_path=config_path
            )
        
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ConfigError(
                f"Invalid YAML in {config_path}: {e}",
                file_path=config_path
            )
        
        # Transform to DirectoryPolicy instances
        directories = {}
        for dir_path, dir_data in data["directories"].items():
            try:
                directories[dir_path] = DirectoryPolicy(
                    path=dir_path,
                    **dir_data
                )
            except Exception as e:
                raise ConfigError(
                    f"Invalid directory policy for '{dir_path}': {e}",
                    file_path=config_path
                )
        
        instance = cls(directories=directories)
        
        # Cross-validation
        instance._validate_component_types()
        instance._validate_parent_references()
        
        cls._instance = instance
        return cls._instance
    
    def _validate_component_types(self) -> None:
        """Cross-validate allowed_component_types against components.yaml."""
        component_config = ComponentRegistryConfig.from_file()
        valid_types = set(component_config.get_available_types())
        
        for dir_path, policy in self.directories.items():
            invalid_types = set(policy.allowed_component_types) - valid_types
            if invalid_types:
                raise ConfigError(
                    f"Directory '{dir_path}' references unknown component types: {sorted(invalid_types)}. "
                    f"Valid types from components.yaml: {sorted(valid_types)}",
                    file_path=".st3/project_structure.yaml"
                )
    
    def _validate_parent_references(self) -> None:
        """Validate parent directories exist in config."""
        for dir_path, policy in self.directories.items():
            if policy.parent is not None and policy.parent not in self.directories:
                raise ConfigError(
                    f"Directory '{dir_path}' references unknown parent: '{policy.parent}'",
                    file_path=".st3/project_structure.yaml"
                )
    
    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton instance (for testing only)."""
        cls._instance = None
    
    def get_directory(self, path: str) -> Optional[DirectoryPolicy]:
        """Get policy for exact directory path."""
        return self.directories.get(path)
    
    def get_all_directories(self) -> List[str]:
        """Get sorted list of all directory paths."""
        return sorted(self.directories.keys())
```

**Key Features:**
- Cross-validation against components.yaml
- Parent reference validation (no dangling references)
- Singleton pattern for consistency

---

### 2.3 DirectoryPolicyResolver Interface Design

**File Location:** `mcp_server/core/directory_policy_resolver.py` (NEW)

**Purpose:** WAAR knowledge - resolve directory policies with inheritance

**Complete Python Implementation:**

```python
"""Directory policy resolution utility.

Purpose: Resolve directory policies with parent inheritance
Responsibility: Single source of WAAR (where) knowledge
Used by: PolicyEngine, ScaffoldComponentTool
"""

from pathlib import Path
from typing import Optional
import fnmatch

from mcp_server.config.project_structure import (
    ProjectStructureConfig,
    DirectoryPolicy
)


class ResolvedDirectoryPolicy:
    """Directory policy with inheritance resolved."""
    
    def __init__(
        self,
        path: str,
        description: str,
        allowed_component_types: List[str],
        allowed_extensions: List[str],
        require_scaffold_for: List[str]
    ):
        self.path = path
        self.description = description
        self.allowed_component_types = allowed_component_types
        self.allowed_extensions = allowed_extensions
        self.require_scaffold_for = require_scaffold_for
    
    def allows_component_type(self, component_type: str) -> bool:
        """Check if component type allowed in this directory."""
        if not self.allowed_component_types:  # Empty = all allowed
            return True
        return component_type in self.allowed_component_types
    
    def allows_extension(self, file_path: str) -> bool:
        """Check if file extension allowed."""
        if not self.allowed_extensions:  # Empty = all allowed
            return True
        ext = Path(file_path).suffix
        return ext in self.allowed_extensions
    
    def requires_scaffold(self, file_path: str) -> bool:
        """Check if file path matches scaffold requirement patterns."""
        relative_path = Path(file_path).relative_to(self.path) if self.path else Path(file_path)
        for pattern in self.require_scaffold_for:
            if fnmatch.fnmatch(str(relative_path), pattern):
                return True
        return False


class DirectoryPolicyResolver:
    """Resolve directory policies with inheritance.
    
    Responsibilities:
    - Path matching (exact, parent walk)
    - Inheritance resolution (Q4 decision - implicit)
    - Policy lookup optimization
    
    NOT Responsible:
    - Policy enforcement (PolicyEngine does this)
    - Config validation (Pydantic does this)
    """
    
    def __init__(self, config: Optional[ProjectStructureConfig] = None):
        """Initialize resolver.
        
        Args:
            config: ProjectStructureConfig instance (loads default if None)
        """
        self._config = config or ProjectStructureConfig.from_file()
        self._cache: Dict[str, ResolvedDirectoryPolicy] = {}  # Q3: No caching for MVP
    
    def resolve(self, path: str) -> ResolvedDirectoryPolicy:
        """Resolve directory policy for given path with inheritance.
        
        Algorithm:
        1. Try exact match
        2. Walk up parent chain
        3. Fallback to workspace root policy (permissive)
        
        Args:
            path: Directory or file path (workspace-relative)
            
        Returns:
            ResolvedDirectoryPolicy with inheritance applied
        """
        # Normalize path
        path = Path(path).as_posix()
        if Path(path).is_file():
            path = str(Path(path).parent)
        
        # Try exact match first
        policy = self._config.get_directory(path)
        if policy:
            return self._resolve_with_inheritance(policy)
        
        # Walk up parent chain
        current = Path(path)
        while current != Path("."):
            parent_path = str(current.parent)
            policy = self._config.get_directory(parent_path)
            if policy:
                return self._resolve_with_inheritance(policy)
            current = current.parent
        
        # Fallback: Permissive default (no restrictions)
        return ResolvedDirectoryPolicy(
            path=path,
            description="Workspace root (no restrictions)",
            allowed_component_types=[],  # Empty = all allowed
            allowed_extensions=[],  # Empty = all allowed
            require_scaffold_for=[]  # Empty = no requirements
        )
    
    def _resolve_with_inheritance(
        self,
        policy: DirectoryPolicy
    ) -> ResolvedDirectoryPolicy:
        """Apply inheritance rules to policy.
        
        Inheritance Rules (Q4 decision - implicit):
        - allowed_extensions: Inherit from parent unless overridden
        - allowed_component_types: Override (no merge)
        - require_scaffold_for: Cumulative (child adds to parent)
        """
        # Start with current policy values
        allowed_extensions = policy.allowed_extensions
        allowed_component_types = policy.allowed_component_types
        require_scaffold_for = list(policy.require_scaffold_for)
        
        # Walk up parent chain
        current_policy = policy
        while current_policy.parent:
            parent_policy = self._config.get_directory(current_policy.parent)
            if not parent_policy:
                break
            
            # Inherit allowed_extensions if not overridden
            if not allowed_extensions and parent_policy.allowed_extensions:
                allowed_extensions = parent_policy.allowed_extensions
            
            # Cumulative require_scaffold_for
            require_scaffold_for.extend(parent_policy.require_scaffold_for)
            
            current_policy = parent_policy
        
        return ResolvedDirectoryPolicy(
            path=policy.path,
            description=policy.description,
            allowed_component_types=allowed_component_types,
            allowed_extensions=allowed_extensions,
            require_scaffold_for=require_scaffold_for
        )
```

**Key Design Decisions:**
- No caching for MVP (Q3 decision - measure first)
- Implicit inheritance (Q4 decision)
- Fallback to permissive default (no error on unknown paths)
- SRP: Only resolves policies, doesn't enforce

---

### 2.4 Inheritance Resolution Algorithm

**Algorithm Visualization:**

```
Given path: backend/dtos/user_dto.py

Step 1: Exact match
  Check: backend/dtos/user_dto.py → No match (file, not directory)
  
Step 2: Parent directory
  Check: backend/dtos → MATCH!
  Policy: { allowed_component_types: [dto], parent: backend }
  
Step 3: Walk parent chain
  Check parent: backend
  Policy: { allowed_extensions: [.py], require_scaffold_for: ["**/*.py"] }
  
Step 4: Apply inheritance
  - allowed_extensions: backend/dtos has none → inherit backend's [.py]
  - allowed_component_types: backend/dtos has [dto] → use [dto] (override)
  - require_scaffold_for: cumulative → ["**/*.py"] from backend
  
Result: ResolvedDirectoryPolicy(
  path="backend/dtos",
  allowed_component_types=[dto],
  allowed_extensions=[.py],
  require_scaffold_for=["**/*.py"]
)
```

---

### 2.5 Phase 2 Test Strategy

**DirectoryPolicyResolver Unit Tests:**

```python
def test_exact_path_match():
    """Test exact directory match"""
    resolver = DirectoryPolicyResolver()
    policy = resolver.resolve("backend")
    assert policy.path == "backend"
    assert "dto" in policy.allowed_component_types

def test_parent_directory_match():
    """Test walking up parent chain"""
    resolver = DirectoryPolicyResolver()
    policy = resolver.resolve("backend/foo")  # Not in config
    # Should resolve to backend policy
    assert "dto" in policy.allowed_component_types

def test_inheritance_extensions():
    """Test allowed_extensions inheritance"""
    resolver = DirectoryPolicyResolver()
    policy = resolver.resolve("backend/dtos")
    # backend/dtos doesn't specify extensions, should inherit from backend
    assert ".py" in policy.allowed_extensions

def test_inheritance_component_types_override():
    """Test allowed_component_types override (no merge)"""
    resolver = DirectoryPolicyResolver()
    policy = resolver.resolve("backend/dtos")
    # backend/dtos overrides with [dto], should NOT include worker/adapter from backend
    assert policy.allowed_component_types == ["dto"]

def test_inheritance_scaffold_cumulative():
    """Test require_scaffold_for cumulative inheritance"""
    resolver = DirectoryPolicyResolver()
    policy = resolver.resolve("backend/dtos")
    # Should include patterns from both backend/dtos and backend (cumulative)
    assert "**/*.py" in policy.require_scaffold_for

def test_fallback_permissive():
    """Test fallback to permissive default for unknown paths"""
    resolver = DirectoryPolicyResolver()
    policy = resolver.resolve("unknown/path")
    # Should return permissive default (all allowed)
    assert policy.allowed_component_types == []  # Empty = all allowed
    assert policy.allowed_extensions == []

def test_allows_component_type():
    """Test component type validation"""
    resolver = DirectoryPolicyResolver()
    policy = resolver.resolve("backend/dtos")
    assert policy.allows_component_type("dto") is True
    assert policy.allows_component_type("worker") is False

def test_allows_extension():
    """Test extension validation"""
    resolver = DirectoryPolicyResolver()
    policy = resolver.resolve("backend")
    assert policy.allows_extension("backend/foo.py") is True
    assert policy.allows_extension("backend/foo.js") is False

def test_requires_scaffold():
    """Test scaffold requirement pattern matching"""
    resolver = DirectoryPolicyResolver()
    policy = resolver.resolve("backend")
    assert policy.requires_scaffold("backend/foo.py") is True
    assert policy.requires_scaffold("backend/README.md") is False
```

**ProjectStructureConfig Unit Tests:**

```python
def test_load_valid_config():
    """Test loading valid project_structure.yaml"""
    config = ProjectStructureConfig.from_file()
    assert len(config.directories) == 15  # 7 top-level + 8 subdirectories

def test_cross_validation_success():
    """Test cross-validation with components.yaml"""
    config = ProjectStructureConfig.from_file()
    # All allowed_component_types should exist in components.yaml

def test_cross_validation_failure():
    """Test cross-validation with unknown component type"""
    # Create config with invalid component type reference
    with pytest.raises(ConfigError, match="references unknown component types"):
        ...

def test_parent_reference_validation():
    """Test parent directory references are valid"""
    config = ProjectStructureConfig.from_file()
    # All parent references should exist in config

def test_dangling_parent_reference():
    """Test error on dangling parent reference"""
    # Create config with invalid parent reference
    with pytest.raises(ConfigError, match="references unknown parent"):
        ...
```

**Phase 2 Integration Test:**

```python
def test_all_phase2_configs_load():
    """Test all Phase 1+2 configs load successfully"""
    component_config = ComponentRegistryConfig.from_file()
    structure_config = ProjectStructureConfig.from_file()
    resolver = DirectoryPolicyResolver(structure_config)
    
    # Verify cross-references work
    backend_policy = resolver.resolve("backend/dtos")
    assert backend_policy.allows_component_type("dto") is True
```

---

## Phase 3 Design: Integration (PolicyEngine Refactor)

**Goal:** Refactor PolicyEngine to use configs instead of hardcoded rules.

**Components:**
- `PolicyEngine` refactor (decision service)
- `PolicyDecision` dataclass (decision result)

**Dependencies:** OperationPoliciesConfig, DirectoryPolicyResolver

### 3.1 PolicyEngine Interface Design

**File Location:** `mcp_server/core/policy_engine.py` (REFACTOR existing)

**Purpose:** Policy Decision Service - answers "is operation X allowed?"

**Design Rationale:**
- Config-driven (no hardcoded rules)
- Delegates WAAR lookups to DirectoryPolicyResolver (SRP)
- Maintains audit trail for all decisions
- Does NOT enforce (Epic #18 responsibility)

**Complete Interface:**

```python
"""Policy decision engine.

Purpose: Answer "is operation X allowed?" based on configs
Responsibilities:
- Load operation policies (WANNEER)
- Delegate directory lookups (WAAR) to DirectoryPolicyResolver
- Make policy decisions (allowed/blocked + reason)
- Maintain audit trail

NOT Responsible:
- Enforcement (Epic #18 adds this)
- Directory knowledge (DirectoryPolicyResolver owns this)
- Config validation (Pydantic handles this)
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Any

from mcp_server.config.operation_policies import OperationPoliciesConfig
from mcp_server.core.directory_policy_resolver import DirectoryPolicyResolver


@dataclass
class PolicyDecision:
    """Result of policy decision."""
    
    allowed: bool
    reason: str
    operation: str
    path: Optional[str] = None
    phase: Optional[str] = None
    directory_policy: Optional[Any] = None  # ResolvedDirectoryPolicy
    context: Dict[str, Any] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
        if self.context is None:
            self.context = {}


class PolicyEngine:
    """Policy decision engine (config-driven).
    
    This is the REFACTORED PolicyEngine - completely config-driven.
    Old hardcoded rules removed, replaced with config lookups.
    """
    
    def __init__(self, config_dir: str = ".st3"):
        """Initialize PolicyEngine with configs.
        
        Args:
            config_dir: Directory containing config files
        """
        self._config_dir = config_dir
        
        # Load configs (singleton pattern ensures single load)
        self._operation_config = OperationPoliciesConfig.from_file(
            f"{config_dir}/policies.yaml"
        )
        self._directory_resolver = DirectoryPolicyResolver()
        
        # Audit trail
        self._audit_trail: List[Dict[str, Any]] = []
    
    def decide(
        self,
        operation: str,
        path: Optional[str] = None,
        phase: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> PolicyDecision:
        """Make policy decision for operation.
        
        Decision Algorithm:
        1. Check operation-level phase policy (WANNEER)
        2. If path provided, check directory policy (WAAR)
        3. Combine results + provide reason
        4. Log to audit trail
        
        Args:
            operation: Operation identifier (scaffold, create_file, commit)
            path: File path (optional, for path-based policies)
            phase: Current phase (optional, for phase-based policies)
            context: Additional context (component_type, branch, etc.)
            
        Returns:
            PolicyDecision with allowed/blocked + reason
        """
        context = context or {}
        
        try:
            # Get operation policy
            op_policy = self._operation_config.get_operation_policy(operation)
            
            # Check phase policy
            if phase and not op_policy.is_allowed_in_phase(phase):
                decision = PolicyDecision(
                    allowed=False,
                    reason=f"Operation '{operation}' not allowed in phase '{phase}'. "
                           f"Allowed phases: {op_policy.allowed_phases or 'all'}",
                    operation=operation,
                    path=path,
                    phase=phase,
                    context=context
                )
                self._log_decision(decision)
                return decision
            
            # Check path-based policies (if path provided)
            if path:
                # Delegate to DirectoryPolicyResolver (SRP)
                dir_policy = self._directory_resolver.resolve(path)
                
                # Check component type (if provided in context)
                component_type = context.get("component_type")
                if component_type and not dir_policy.allows_component_type(component_type):
                    decision = PolicyDecision(
                        allowed=False,
                        reason=f"Component type '{component_type}' not allowed in '{dir_policy.path}'. "
                               f"Allowed types: {dir_policy.allowed_component_types or 'all'}",
                        operation=operation,
                        path=path,
                        phase=phase,
                        directory_policy=dir_policy,
                        context=context
                    )
                    self._log_decision(decision)
                    return decision
                
                # Check blocked patterns (create_file operation)
                if operation == "create_file" and op_policy.is_path_blocked(path):
                    decision = PolicyDecision(
                        allowed=False,
                        reason=f"Path '{path}' matches blocked pattern. Must use scaffold operation instead.",
                        operation=operation,
                        path=path,
                        phase=phase,
                        directory_policy=dir_policy,
                        context=context
                    )
                    self._log_decision(decision)
                    return decision
                
                # Check allowed extensions (create_file operation)
                if operation == "create_file" and not op_policy.is_extension_allowed(path):
                    decision = PolicyDecision(
                        allowed=False,
                        reason=f"File extension not allowed. Allowed extensions: {op_policy.allowed_extensions or 'all'}",
                        operation=operation,
                        path=path,
                        phase=phase,
                        directory_policy=dir_policy,
                        context=context
                    )
                    self._log_decision(decision)
                    return decision
            
            # Check commit message (commit operation)
            if operation == "commit":
                message = context.get("message", "")
                if not op_policy.validate_commit_message(message):
                    decision = PolicyDecision(
                        allowed=False,
                        reason=f"Commit message must start with TDD prefix. "
                               f"Valid prefixes: {op_policy.allowed_prefixes}",
                        operation=operation,
                        phase=phase,
                        context=context
                    )
                    self._log_decision(decision)
                    return decision
            
            # All checks passed - operation allowed
            decision = PolicyDecision(
                allowed=True,
                reason=f"Operation '{operation}' allowed in phase '{phase or 'any'}'" + 
                       (f" for path '{path}'" if path else ""),
                operation=operation,
                path=path,
                phase=phase,
                directory_policy=self._directory_resolver.resolve(path) if path else None,
                context=context
            )
            self._log_decision(decision)
            return decision
            
        except Exception as e:
            # Error in policy evaluation - log and deny by default (fail-safe)
            decision = PolicyDecision(
                allowed=False,
                reason=f"Policy evaluation error: {e}",
                operation=operation,
                path=path,
                phase=phase,
                context=context
            )
            self._log_decision(decision)
            return decision
    
    def _log_decision(self, decision: PolicyDecision) -> None:
        """Log decision to audit trail."""
        self._audit_trail.append({
            "timestamp": decision.timestamp.isoformat(),
            "operation": decision.operation,
            "path": decision.path,
            "phase": decision.phase,
            "allowed": decision.allowed,
            "reason": decision.reason,
            "context": decision.context
        })
    
    def get_audit_trail(self) -> List[Dict[str, Any]]:
        """Get complete audit trail.
        
        Returns:
            List of all policy decisions with metadata
        """
        return list(self._audit_trail)
    
    def reload_configs(self) -> None:
        """Reload configs from disk (without restart).
        
        Useful for testing and dynamic config updates.
        """
        # Reset singleton instances
        OperationPoliciesConfig.reset_instance()
        # Reload
        self._operation_config = OperationPoliciesConfig.from_file(
            f"{self._config_dir}/policies.yaml"
        )
        # DirectoryResolver loads ProjectStructureConfig internally
```

**Key Design Decisions:**
1. **No Hardcoded Rules:** All logic driven by configs
2. **SRP Delegation:** Directory lookups delegated to DirectoryPolicyResolver
3. **Fail-Safe:** Errors result in "denied" decision (secure by default)
4. **Audit Trail:** Every decision logged with reason and context
5. **Reload Support:** Configs can be reloaded without restart

---

### 3.2 PolicyDecision Dataclass Design

**Purpose:** Immutable decision result with all context

**Fields:**
- `allowed: bool` - Decision result (True = allowed, False = blocked)
- `reason: str` - Human-readable explanation (for logging/debugging)
- `operation: str` - Operation that was evaluated
- `path: Optional[str]` - File path (if applicable)
- `phase: Optional[str]` - Phase (if applicable)
- `directory_policy: Optional[ResolvedDirectoryPolicy]` - Resolved directory policy (if path-based)
- `context: Dict[str, Any]` - Additional context (component_type, branch, message, etc.)
- `timestamp: datetime` - When decision was made (UTC)

**Usage Example:**

```python
engine = PolicyEngine()
decision = engine.decide(
    operation="scaffold",
    path="backend/dtos/user_dto.py",
    phase="design",
    context={"component_type": "dto", "branch": "feature/123"}
)

if decision.allowed:
    # Proceed with operation
    scaffold_component(...)
else:
    # Log reason and block
    logger.warning(f"Operation blocked: {decision.reason}")
```

---

### 3.3 Decision Algorithm Design

**Algorithm Flow:**

```
┌─────────────────────────────────────┐
│ decide(operation, path, phase, ctx) │
└─────────────────┬───────────────────┘
                  │
                  ▼
       ┌──────────────────────┐
       │ Get Operation Policy │
       │ (policies.yaml)      │
       └──────────┬───────────┘
                  │
                  ▼
       ┌──────────────────────┐
       │ Check Phase Policy   │
       │ is_allowed_in_phase? │
       └──────────┬───────────┘
                  │
         ┌────────┴────────┐
         │ No              │ Yes
         ▼                 ▼
    ┌────────┐      ┌─────────────────┐
    │ DENIED │      │ Path provided?  │
    └────────┘      └────────┬────────┘
                             │
                    ┌────────┴────────┐
                    │ No              │ Yes
                    ▼                 ▼
              ┌──────────┐    ┌───────────────────────┐
              │ ALLOWED  │    │ Resolve Directory     │
              └──────────┘    │ (DirectoryResolver)   │
                              └──────────┬────────────┘
                                         │
                                         ▼
                              ┌──────────────────────┐
                              │ Check component_type │
                              │ allows_component?    │
                              └──────────┬───────────┘
                                         │
                                ┌────────┴────────┐
                                │ No              │ Yes
                                ▼                 ▼
                           ┌────────┐    ┌────────────────┐
                           │ DENIED │    │ Check blocked  │
                           └────────┘    │ patterns, etc. │
                                         └────────┬───────┘
                                                  │
                                         ┌────────┴────────┐
                                         │ Blocked?        │
                                         └────────┬────────┘
                                                  │
                                         ┌────────┴────────┐
                                         │ No              │ Yes
                                         ▼                 ▼
                                    ┌──────────┐      ┌────────┐
                                    │ ALLOWED  │      │ DENIED │
                                    └──────────┘      └────────┘
                                         │                 │
                                         └────────┬────────┘
                                                  ▼
                                         ┌─────────────────┐
                                         │ Log to Audit    │
                                         │ Return Decision │
                                         └─────────────────┘
```

---

### 3.4 Audit Trail Design

**Format:**

```python
{
    "timestamp": "2026-01-10T14:32:15.123456",
    "operation": "scaffold",
    "path": "backend/dtos/user_dto.py",
    "phase": "design",
    "allowed": True,
    "reason": "Operation 'scaffold' allowed in phase 'design' for path 'backend/dtos/user_dto.py'",
    "context": {
        "component_type": "dto",
        "branch": "feature/123-user-management",
        "user": "agent"
    }
}
```

**Storage:** In-memory list (for Issue #54), can be extended to file/database in Epic #18

**Query Methods:**
- `get_audit_trail()` - Get full trail
- Future: Filter by operation, phase, allowed/denied, time range

---

### 3.5 Phase 3 Test Strategy

**PolicyEngine Tests (NO behavior parity needed - UNUSED):**

```python
def test_scaffold_allowed_in_design_phase():
    """Test scaffold allowed in design phase"""
    engine = PolicyEngine()
    decision = engine.decide(
        operation="scaffold",
        path="backend/dtos/user_dto.py",
        phase="design",
        context={"component_type": "dto"}
    )
    assert decision.allowed is True
    assert "allowed in phase 'design'" in decision.reason

def test_scaffold_blocked_in_refactor_phase():
    """Test scaffold blocked outside allowed phases"""
    engine = PolicyEngine()
    decision = engine.decide(
        operation="scaffold",
        phase="refactor"
    )
    assert decision.allowed is False
    assert "not allowed in phase 'refactor'" in decision.reason

def test_component_type_violation():
    """Test wrong component type in directory"""
    engine = PolicyEngine()
    decision = engine.decide(
        operation="scaffold",
        path="backend/dtos/worker.py",
        phase="design",
        context={"component_type": "worker"}  # Worker not allowed in dtos/
    )
    assert decision.allowed is False
    assert "not allowed in 'backend/dtos'" in decision.reason

def test_blocked_pattern():
    """Test create_file blocked by pattern"""
    engine = PolicyEngine()
    decision = engine.decide(
        operation="create_file",
        path="backend/foo.py",
        phase="design"
    )
    assert decision.allowed is False
    assert "matches blocked pattern" in decision.reason

def test_commit_message_validation():
    """Test commit message TDD prefix"""
    engine = PolicyEngine()
    
    # Valid prefix
    decision = engine.decide(
        operation="commit",
        context={"message": "red: add failing test"}
    )
    assert decision.allowed is True
    
    # Invalid prefix
    decision = engine.decide(
        operation="commit",
        context={"message": "invalid prefix"}
    )
    assert decision.allowed is False

def test_audit_trail():
    """Test decisions logged to audit trail"""
    engine = PolicyEngine()
    engine.decide("scaffold", phase="design")
    engine.decide("create_file", path="docs/foo.md")
    
    trail = engine.get_audit_trail()
    assert len(trail) == 2
    assert trail[0]["operation"] == "scaffold"
    assert trail[1]["operation"] == "create_file"

def test_config_reload():
    """Test config reload without restart"""
    engine = PolicyEngine()
    engine.reload_configs()
    # Should not raise, configs reloaded
```

---

## Phase 4 Design: Tool Integration (ScaffoldComponentTool)

**Goal:** Refactor ScaffoldComponentTool to use ComponentRegistryConfig

**Components:**
- `ScaffoldComponentTool` refactor (validation changes)

**Dependencies:** ComponentRegistryConfig, DirectoryPolicyResolver

### 4.1 ScaffoldComponentTool Changes

**File Location:** `mcp_server/tools/scaffold_tools.py` (REFACTOR existing)

**Changes Summary:**
- Replace hardcoded component_types dict with ComponentRegistryConfig
- Add component_type validation against config
- Add path validation via DirectoryPolicyResolver
- Keep scaffolder dict (NO dynamic loading in Issue #54)

**Modified Methods:**

```python
class ScaffoldComponentTool:
    """MCP Tool for scaffolding components from templates."""
    
    def __init__(self, config_dir: str = ".st3"):
        """Initialize tool with config.
        
        OLD: Hardcoded component_types dict
        NEW: Load from ComponentRegistryConfig
        """
        self._config = ComponentRegistryConfig.from_file(
            f"{config_dir}/components.yaml"
        )
        self._directory_resolver = DirectoryPolicyResolver()
        
        # Keep hardcoded scaffolder dict (NO dynamic loading yet)
        self._scaffolders = {
            "dto": DTOScaffolder(),
            "worker": WorkerScaffolder(),
            "adapter": AdapterScaffolder(),
            "tool": ToolScaffolder(),
            "resource": ResourceScaffolder(),
            "schema": SchemaScaffolder(),
            "interface": InterfaceScaffolder(),
            "service": ServiceScaffolder(),
            "generic": GenericScaffolder()
        }
    
    def _validate_component_type(self, component_type: str) -> None:
        """Validate component type against config.
        
        OLD: Check hardcoded dict
        NEW: Check ComponentRegistryConfig
        """
        if not self._config.has_component_type(component_type):
            available = self._config.get_available_types()
            raise ValueError(
                f"Unknown component type: '{component_type}'. "
                f"Available types: {available}"
            )
    
    def _validate_path(
        self,
        component_type: str,
        output_path: str
    ) -> None:
        """Validate path allows component type.
        
        NEW: Use DirectoryPolicyResolver
        """
        dir_policy = self._directory_resolver.resolve(output_path)
        
        if not dir_policy.allows_component_type(component_type):
            raise ValueError(
                f"Component type '{component_type}' not allowed in '{dir_policy.path}'. "
                f"Allowed types: {dir_policy.allowed_component_types or 'all'}"
            )
    
    def _execute(self, arguments: Dict[str, Any]) -> str:
        """Execute scaffold operation.
        
        Changes:
        1. Validate component_type against config
        2. Validate path against directory policy
        3. Rest unchanged
        """
        component_type = arguments["component_type"]
        output_path = arguments.get("output_path")
        
        # NEW: Config-based validation
        self._validate_component_type(component_type)
        
        if output_path:
            self._validate_path(component_type, output_path)
        
        # Existing scaffolding logic unchanged
        scaffolder = self._scaffolders[component_type]
        result = scaffolder.scaffold(**arguments)
        return result
```

**Preserved:**
- Hardcoded scaffolder dict (dynamic loading deferred to Issue #105)
- Existing scaffold logic (no behavior changes)
- Template rendering (JinjaRenderer unchanged)

---

### 4.2 Component Type Validation

**Before (hardcoded):**

```python
COMPONENT_TYPES = {
    "dto": {...},
    "worker": {...},
    # ... hardcoded
}

if component_type not in COMPONENT_TYPES:
    raise ValueError("Unknown type")
```

**After (config-driven):**

```python
config = ComponentRegistryConfig.from_file()
if not config.has_component_type(component_type):
    available = config.get_available_types()
    raise ValueError(f"Unknown type. Available: {available}")
```

**Benefits:**
- Adding new component type = edit config only (no code change)
- Clear error messages with available types
- Config serves as SSOT

---

### 4.3 Path Validation

**NEW Functionality:**

```python
def _validate_path(self, component_type: str, output_path: str) -> None:
    """Validate path allows component type."""
    dir_policy = self._directory_resolver.resolve(output_path)
    
    if not dir_policy.allows_component_type(component_type):
        raise ValueError(
            f"Component type '{component_type}' not allowed in '{dir_policy.path}'. "
            f"Allowed types: {dir_policy.allowed_component_types or 'all'}"
        )
```

**Examples:**

```python
# ALLOWED: DTO in backend/dtos/
_validate_path("dto", "backend/dtos/user_dto.py")  # ✓

# DENIED: Worker in backend/dtos/
_validate_path("worker", "backend/dtos/worker.py")  # ✗ Raises ValueError

# ALLOWED: Tool in mcp_server/tools/
_validate_path("tool", "mcp_server/tools/github_tool.py")  # ✓
```

---

### 4.4 Phase 4 Test Strategy

**ScaffoldComponentTool Integration Tests:**

```python
def test_scaffold_dto_with_config():
    """Test scaffolding DTO uses ComponentRegistryConfig"""
    tool = ScaffoldComponentTool()
    result = tool._execute({
        "component_type": "dto",
        "name": "UserDTO",
        "description": "User data transfer object",
        "output_path": "backend/dtos/user_dto.py"
    })
    # Should succeed, dto allowed in backend/dtos

def test_invalid_component_type():
    """Test invalid component type rejected"""
    tool = ScaffoldComponentTool()
    with pytest.raises(ValueError, match="Unknown component type"):
        tool._execute({
            "component_type": "invalid_type",
            "name": "Test"
        })

def test_component_type_in_wrong_directory():
    """Test component type validation with DirectoryPolicyResolver"""
    tool = ScaffoldComponentTool()
    with pytest.raises(ValueError, match="not allowed in"):
        tool._execute({
            "component_type": "worker",  # Worker not allowed in dtos/
            "name": "TestWorker",
            "output_path": "backend/dtos/worker.py"
        })

def test_scaffolder_dict_unchanged():
    """Test hardcoded scaffolder dict still works"""
    tool = ScaffoldComponentTool()
    assert "dto" in tool._scaffolders
    assert isinstance(tool._scaffolders["dto"], DTOScaffolder)

def test_existing_scaffold_operations_work():
    """Regression: All existing scaffold operations still work"""
    tool = ScaffoldComponentTool()
    
    # Test each component type can be scaffolded
    for component_type in ["dto", "worker", "adapter", "tool", "resource", "schema", "interface", "service"]:
        component_def = tool._config.get_component(component_type)
        assert component_def.type_id == component_type
```

---

## Cross-Cutting Concerns

### Error Handling Strategy

**ConfigError Design:**

```python
class ConfigError(Exception):
    """Configuration loading or validation error."""
    
    def __init__(self, message: str, file_path: Optional[str] = None):
        self.message = message
        self.file_path = file_path
        super().__init__(self._format_message())
    
    def _format_message(self) -> str:
        """Format error message with file context."""
        if self.file_path:
            return f"{self.message}\nFile: {self.file_path}"
        return self.message
```

**Error Message Examples:**

```
ConfigError: Config file not found: .st3/components.yaml
File: .st3/components.yaml

ConfigError: Operation 'scaffold' references unknown phases: ['invalid_phase']. 
Valid phases from workflows.yaml: ['design', 'tdd', 'refactor', 'integration', 'documentation']
File: .st3/policies.yaml

ConfigError: Directory 'backend/dtos' references unknown component types: ['invalid_type']. 
Valid types from components.yaml: ['dto', 'worker', 'adapter', ...]
File: .st3/project_structure.yaml
```

**Error Handling Principles:**
1. **Fail-Fast:** Config errors block startup (Q5 decision)
2. **Actionable Messages:** Include file path, line context, fix suggestions
3. **Cross-Reference Errors:** Show both sides (what's missing + where it should exist)

---

### Performance Considerations

**Targets (from planning.md):**
- Config loading: <100ms at startup
- DirectoryPolicyResolver.resolve(): <10ms per lookup
- PolicyEngine.decide(): <10ms per decision

**Optimization Strategy:**
1. **Singleton Pattern:** Configs loaded once per process
2. **No Caching (Q3):** Measure first, optimize only if needed
3. **Lazy Loading:** Not needed (configs are small, ~500 lines total)

**Benchmark Tests:**

```python
def test_config_loading_performance():
    """Test all configs load within 100ms"""
    start = time.time()
    ComponentRegistryConfig.from_file()
    ProjectStructureConfig.from_file()
    OperationPoliciesConfig.from_file()
    elapsed = time.time() - start
    assert elapsed < 0.1  # <100ms

def test_directory_resolver_performance():
    """Test directory resolution within 10ms"""
    resolver = DirectoryPolicyResolver()
    start = time.time()
    for _ in range(100):
        resolver.resolve("backend/dtos/user_dto.py")
    elapsed = time.time() - start
    avg = elapsed / 100
    assert avg < 0.01  # <10ms average

def test_policy_decision_performance():
    """Test policy decision within 10ms"""
    engine = PolicyEngine()
    start = time.time()
    for _ in range(100):
        engine.decide("scaffold", "backend/dtos/test.py", "design", {"component_type": "dto"})
    elapsed = time.time() - start
    avg = elapsed / 100
    assert avg < 0.01  # <10ms average
```

---

### Logging and Observability

**What to Log:**

```python
# Config loading
logger.info(f"Loaded ComponentRegistryConfig: 9 component types")
logger.info(f"Loaded ProjectStructureConfig: 15 directories")
logger.info(f"Loaded OperationPoliciesConfig: 3 operations")

# Policy decisions (via audit trail)
logger.debug(f"PolicyDecision: {decision.operation} {'allowed' if decision.allowed else 'denied'} - {decision.reason}")

# Validation failures
logger.warning(f"Component type validation failed: {component_type} not in registry")
logger.warning(f"Path validation failed: {component_type} not allowed in {dir_policy.path}")
```

**Audit Trail Query (future):**

```python
# Filter by operation
scaffold_decisions = [d for d in engine.get_audit_trail() if d["operation"] == "scaffold"]

# Filter by allowed/denied
denied_decisions = [d for d in engine.get_audit_trail() if not d["allowed"]]

# Filter by time range
recent_decisions = [d for d in engine.get_audit_trail() if parse_time(d["timestamp"]) > yesterday]
```

---

## Implementation Notes

**Priority:** Follow build order strictly:
1. Phase 1: ComponentRegistryConfig + OperationPoliciesConfig (parallel)
2. Phase 2: ProjectStructureConfig + DirectoryPolicyResolver (depends on Phase 1)
3. Phase 3: PolicyEngine refactor (depends on Phases 1+2)
4. Phase 4: ScaffoldComponentTool refactor (depends on Phases 1+2)

**Testing:** TDD approach (red → green → refactor) for each phase

**Documentation:** Update AGENT_PROMPT.md after each phase with:
- New configs location and purpose
- Config cross-references
- Usage examples

**Migration:** No breaking changes:
- PolicyEngine loads configs but doesn't enforce (Epic #18 adds enforcement)
- ScaffoldComponentTool behavior unchanged (only validation added)

---

## Open Questions

**None** - All questions from research.md resolved in planning.md Q1-Q6 section:
- Q1: Glob patterns ✅
- Q2: No exclusions ✅
- Q3: No caching ✅
- Q4: Implicit inheritance ✅
- Q5: Fail-fast ✅
- Q6: Strict validation ✅

---

**Design Complete - Ready for TDD Phase**

---

## Phase 4 Design: Tool Integration (ScaffoldComponentTool)

**Goal:** Refactor ScaffoldComponentTool to use ComponentRegistryConfig.

**Components:**
- `ScaffoldComponentTool` refactor (validation changes only)

**Dependencies:** ComponentRegistryConfig, DirectoryPolicyResolver

### 4.1 ScaffoldComponentTool Changes

[Modified methods and validation logic - will be added in next edit]

### 4.2 Component Type Validation

[How tool validates component_type against config - will be added in next edit]

### 4.3 Path Validation

[How tool uses DirectoryPolicyResolver - will be added in next edit]

### 4.4 Phase 4 Test Strategy

[Integration tests (scaffolding still works) - will be added in next edit]

---

## Cross-Cutting Concerns

### Error Handling Strategy

[ConfigError design, error messages - will be added in next edit]

### Performance Considerations

[Config loading time, lookup performance - will be added in next edit]

### Logging and Observability

[What to log, audit trail format - will be added in next edit]

---

## Implementation Notes

**Priority:** Follow build order strictly (dependencies first)

**Testing:** TDD approach (red → green → refactor)

**Documentation:** Update AGENT_PROMPT.md after each phase

**Migration:** No breaking changes (PolicyEngine loads but doesn't enforce)

---

## Open Questions

[Questions that arose during design phase - to be filled during design work]

---

**Next:** Begin detailed design for Phase 1 components