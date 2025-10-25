"""
Pytest configuration and shared fixtures for S1mpleTrader V3 tests.

This module provides shared test fixtures and pytest configuration
following the TDD principles outlined in the architecture documentation.

@layer: Tests
@dependencies: [pytest]
"""

import pytest

from backend.dtos.shared.disposition_envelope import DispositionEnvelope


@pytest.fixture
def sample_continue_envelope():
    """Fixture providing a sample CONTINUE disposition envelope."""
    return DispositionEnvelope(disposition="CONTINUE")


@pytest.fixture
def sample_stop_envelope():
    """Fixture providing a sample STOP disposition envelope."""
    return DispositionEnvelope(disposition="STOP")
