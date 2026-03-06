"""Tests for --selftest graceful skip when examples/ is not found."""

import os
import sys
from io import StringIO
from unittest.mock import patch
from pathlib import Path


def test_radia_selftest_skips_without_examples(tmp_path, monkeypatch):
    """Radia selftest should print SKIP when examples/ not found."""
    monkeypatch.setattr(
        'mcp_server_cae_ai.radia.server.PROJECT_ROOT', tmp_path
    )
    from mcp_server_cae_ai.radia.server import _selftest

    captured = StringIO()
    monkeypatch.setattr('sys.stdout', captured)
    _selftest()
    output = captured.getvalue()
    assert 'SKIP' in output


def test_cubit_selftest_skips_without_examples(tmp_path, monkeypatch):
    """Cubit selftest should print SKIP when examples/ not found."""
    monkeypatch.setattr(
        'mcp_server_cae_ai.cubit.server.PROJECT_ROOT', tmp_path
    )
    from mcp_server_cae_ai.cubit.server import _selftest

    captured = StringIO()
    monkeypatch.setattr('sys.stdout', captured)
    _selftest()
    output = captured.getvalue()
    assert 'SKIP' in output
