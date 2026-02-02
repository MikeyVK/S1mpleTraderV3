# .st3/scaffold_review/ReviewSyncWorker.py
# template=worker version=9cb30b12 created=2026-02-02T08:39Z updated=
"""
ReviewSync - Review worker (sync mode)..

@layer: Backend (Workers)
@dependencies: [backend.core.interfaces, backend.dtos]
@responsibilities:
    - Review IWorkerLifecycle structure
    - Check DI guard clauses + token discipline
    - Verify LogEnricher/Translator usage
"""

# Standard library
from __future__ import annotations
from typing import TYPE_CHECKING, Any
import logging

# Third-party
# (Add third-party imports here if needed)

# Project modules
from backend.core.interfaces.worker import IWorker, IWorkerLifecycle, WorkerInitializationError
from backend.utils.app_logger import LogEnricher
from backend.utils.translator import Translator

if TYPE_CHECKING:
    from backend.core.interfaces.strategy_cache import IStrategyCache
    from backend.core.interfaces.config import BuildSpec

__all__ = ["ReviewSync"]


class ReviewSync(IWorker, IWorkerLifecycle):
    """
    ReviewSync worker implementation.

    Architecture:
    - EventAdapter-compliant: Standard IWorker + IWorkerLifecycle pattern
    - Worker scope: strategy
    - Strategy worker: Requires strategy_cache for runtime state
    - Required capabilities: dto_types
    """

    def __init__(self, build_spec: BuildSpec) -> None:
        """
        Construct ReviewSync with configuration.

        V3 Pattern: Construction phase accepts BuildSpec only (no dependencies).
        Dependencies injected via initialize() during runtime initialization.

        Args:
            build_spec: Worker configuration (from manifest.yaml)
        """
        self._name: str = build_spec.name
        self._config = build_spec.config

        self._cache: "IStrategyCache | None" = None


        self.logger: LogEnricher | None = None
        self._translator: Translator | None = None

    @property
    def name(self) -> str:
        """Get worker name (IWorker requirement)."""
        return self._name

    def initialize(
        self,
        strategy_cache: IStrategyCache | None = None,
        **capabilities: Any,
    ) -> None:
        """
        Initialize with runtime dependencies.

        V3 Pattern: Runtime initialization phase injects dependencies.
        Platform assembles workers in any order, then calls initialize() with DI.

        Args:
            strategy_cache: StrategyCache instance or None
                - Strategy worker: REQUIRED (validates cache not None)
            **capabilities: Optional capabilities injected by platform

        Raises:
            WorkerInitializationError: If requirements not met
        """
        if strategy_cache is None:
            raise WorkerInitializationError(
                f"{self._name}: di.dependency.strategy_cache.required"
            )

        self._cache = strategy_cache

        # Optional: translator can be injected as a capability
        # (fallback behavior is to use keys as display strings)
        if "translator" in capabilities:
            self._translator = capabilities["translator"]

        # Set up structured logger (LogEnricher)
        logger = LogEnricher(logging.getLogger(__name__))
        self.logger = logger
        self.logger.setup("worker.initialize")

        # Use dot-notation keys for i18n (example key: app.start)
        # Pattern: translator.get(key, default=key)  (fallback is key itself)
        # Special-case parameter display names: translator.get_param_name(param_path, default=param_path)

        # Validate required capabilities
        if "dto_types" not in capabilities:
            raise WorkerInitializationError(
                f"{self._name}: di.capability.dto_types.required"
            )

        # Store required capabilities
        self._dto_types = capabilities["dto_types"]

        # Perform additional initialization here

    def shutdown(self) -> None:
        """Graceful shutdown and resource cleanup.

        IWorkerLifecycle requirement: Must be idempotent (safe to call multiple times).
        Must complete within 5 seconds and never raise exceptions.
        """
        try:
            self._cache = None
        except Exception:  # noqa: BLE001
            # GUIDELINE: shutdown must not raise; best-effort cleanup only.
            pass
