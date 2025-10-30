"""Configuration management package.

This package handles the complete configuration pipeline:
- ConfigLoader: YAML → Pydantic models (structure validation)
- ConfigValidator: Validates worker params, handler methods, event wiring
- ConfigTranslator: Pydantic models → BuildSpecs (factory instructions)

Config Schemas (validation contracts) live in backend/config/schemas/.
"""
