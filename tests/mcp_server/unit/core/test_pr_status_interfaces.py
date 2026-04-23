# tests/mcp_server/unit/core/test_pr_status_interfaces.py
"""Unit tests for PRStatus enum, IPRStatusReader, and IPRStatusWriter.

@layer: Tests (Unit)
@dependencies: [pytest, mcp_server.core.interfaces]
"""

from __future__ import annotations

from mcp_server.core.interfaces import IPRStatusReader, IPRStatusWriter, PRStatus


class TestPRStatusEnum:
    """PRStatus is an enum with OPEN and ABSENT members."""

    def test_open_member_exists(self) -> None:
        assert PRStatus.OPEN is not None

    def test_absent_member_exists(self) -> None:
        assert PRStatus.ABSENT is not None

    def test_only_two_members(self) -> None:
        assert set(PRStatus) == {PRStatus.OPEN, PRStatus.ABSENT}


class TestIPRStatusReader:
    """IPRStatusReader protocol has get_pr_status(branch) -> PRStatus."""

    def test_interface_exists(self) -> None:
        assert IPRStatusReader is not None

    def test_has_get_pr_status(self) -> None:
        assert hasattr(IPRStatusReader, "get_pr_status")


class TestIPRStatusWriter:
    """IPRStatusWriter protocol has set_pr_status(branch, status) -> None."""

    def test_interface_exists(self) -> None:
        assert IPRStatusWriter is not None

    def test_has_set_pr_status(self) -> None:
        assert hasattr(IPRStatusWriter, "set_pr_status")
