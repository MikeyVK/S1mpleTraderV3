"""Workflow gate orchestration skeleton for phase and cycle boundaries."""

from __future__ import annotations

from mcp_server.core.interfaces import GateReport, GateViolation
from mcp_server.managers.deliverable_checker import (
    DeliverableChecker,
    DeliverableCheckError,
)
from mcp_server.managers.phase_contract_resolver import PhaseContractResolver
from mcp_server.schemas import CheckSpec


class WorkflowGateRunner:
    """Execute resolved gate checks through DeliverableChecker."""

    def __init__(
        self,
        deliverable_checker: DeliverableChecker,
        phase_contract_resolver: PhaseContractResolver | None = None,
    ) -> None:
        self._deliverable_checker = deliverable_checker
        self._phase_contract_resolver = phase_contract_resolver

    def enforce(
        self,
        workflow_name: str,
        phase: str,
        cycle_number: int | None = None,
        checks: list[CheckSpec] | None = None,
    ) -> GateReport:
        """Run blocking gate evaluation and raise on the first blocking check."""
        return self._run_checks(
            workflow_name=workflow_name,
            phase=phase,
            cycle_number=cycle_number,
            checks=checks,
            raise_on_block=True,
        )

    def inspect(
        self,
        workflow_name: str,
        phase: str,
        cycle_number: int | None = None,
        checks: list[CheckSpec] | None = None,
    ) -> GateReport:
        """Run non-blocking gate inspection and return all blocked checks."""
        return self._run_checks(
            workflow_name=workflow_name,
            phase=phase,
            cycle_number=cycle_number,
            checks=checks,
            raise_on_block=False,
        )

    def _resolve_checks(
        self,
        workflow_name: str,
        phase: str,
        cycle_number: int | None,
        checks: list[CheckSpec] | None,
    ) -> list[CheckSpec]:
        if checks is not None:
            return list(checks)
        if self._phase_contract_resolver is None:
            raise ValueError("PhaseContractResolver must be provided when checks are not passed")
        return self._phase_contract_resolver.resolve(workflow_name, phase, cycle_number)

    def _run_checks(
        self,
        workflow_name: str,
        phase: str,
        cycle_number: int | None,
        checks: list[CheckSpec] | None,
        raise_on_block: bool,
    ) -> GateReport:
        resolved_checks = self._resolve_checks(workflow_name, phase, cycle_number, checks)
        passing: list[str] = []
        blocking: list[str] = []
        details: dict[str, str] = {}

        for spec in resolved_checks:
            payload = spec.model_dump(exclude_none=True)
            try:
                self._deliverable_checker.check(spec.id, payload)
            except DeliverableCheckError as exc:
                blocking.append(spec.id)
                details[spec.id] = str(exc)
                report = GateReport(
                    passing=tuple(passing),
                    blocking=tuple(blocking),
                    details=details,
                )
                if raise_on_block:
                    raise GateViolation(str(exc), report) from exc
            else:
                passing.append(spec.id)

        return GateReport(
            passing=tuple(passing),
            blocking=tuple(blocking),
            details=details,
        )
