## MCP JSON Schema Caching Limitation

**Issue**: Custom git.yaml changes (e.g., adding "hotfix" branch_type) work server-side but are rejected by VS Code MCP client.

**Root Cause**: 
- JSON schemas for tool inputs are generated at the MCP `initialize` handshake
- VS Code MCP client caches these schemas for the duration of the connection
- Server restarts (proxy restart OR manual stop/start) do NOT regenerate schemas
- The proxy replays the original initialize handshake, keeping the same schemas

**Test Results**:
1. ✅ Python direct import: Custom config loads correctly
2. ✅ Server-side @field_validator: Works with custom config
3. ❌ MCP tool calls: Rejected by client-side schema validation
4. ❌ After proxy restart: Schemas still cached
5. ❌ After manual stop + proxy auto-restart: Schemas still cached

**Solution**: To test custom git.yaml configurations, users must:
- Option A: Restart the VS Code MCP extension connection (disconnect/reconnect)
- Option B: Use Python direct import tests (bypass MCP client layer)
- Option C: Reload VS Code window

**Integration Testing Strategy**:
For Issue #55, we''ll use Python direct import tests to verify all 11 externalized conventions work correctly with custom configurations. MCP tool-based E2E tests would require VS Code restarts between config changes, which is not practical for rapid iteration testing.

**Date**: 2026-01-15 23:13
**Branch**: refactor/55-git-yaml
