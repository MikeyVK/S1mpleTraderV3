<!-- docs\development\issue386\pr.md -->
<!-- template=pr version=93bb9b4e created=2026-07-08T20:19Z updated= -->
# refactor: rename env var prefix MCP_* to PGMCP_*

This PR renames all environment variables with the generic prefix MCP_* to PGMCP_* to prevent namespace conflicts on hosts running multiple MCP servers. Follows a Clean Break strategy with no legacy fallbacks.
## Changes
Renamed settings parsing, proxy logs directory derivation, admin tools restart marker, test monkeypatches, launch configuration templates, and repository documentation to use project-specific PGMCP_* env vars.

## Testing
All 2880 unit/integration tests passed successfully. Quality gates checked and passed with overall pass: True (Ruff Format, Ruff Strict Lint, Imports, Line Length, Pyright, Types).
## Checklist

- [ ] No legacy MCP_* prefixes remain in settings.py source code.
- [ ] Settings precedence and dynamic path loading are preserved.
- [ ] Documentation and IDE configurations are synchronized.

## ⚠️ Breaking Changes

This is a breaking change: legacy MCP_* environment variables will no longer be read. Client environments must update variables to PGMCP_* prefix.
## Related Documentation
- **[[validation.md](file:///c:/temp/pgmcp/docs/development/issue386/validation.md)][related-1]**
- **[[research.md](file:///c:/temp/pgmcp/docs/development/issue386/research.md)][related-2]**
- **[[planning.md](file:///c:/temp/pgmcp/docs/development/issue386/planning.md)][related-3]**

---

Closes: #386