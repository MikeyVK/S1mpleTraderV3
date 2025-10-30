"""Configuration schemas package.

Pydantic models for configuration validation (NOT runtime DTOs!):
- worker_manifest_schema.py: WorkerManifest, SchemaReference
- wiring_config_schema.py: EventWiring, WiringConfig
- strategy_blueprint_schema.py: Workforce, StrategyBlueprint
- buildspec_schemas.py: WorkerBuildSpec, WiringBuildSpec, StrategyBuildSpec

Naming convention: *_schema.py (not DTO suffix)
Rationale: Config schemas are validation contracts, not runtime data DTOs.
"""
