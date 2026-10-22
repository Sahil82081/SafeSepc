"""Pytest configuration and session-wide fixtures."""

import pytest
from backend.app.db.session import init_db


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Ensure all database tables exist before running test suite."""
    init_db()
