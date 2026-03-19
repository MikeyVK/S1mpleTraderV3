from __future__ import annotations

# Thin entry shim — delegates to the package-owned implementation.
# VS Code wiring continues to call this script path unchanged.
from copilot_orchestration.hooks.session_start_imp import main

if __name__ == "__main__":
    main()
