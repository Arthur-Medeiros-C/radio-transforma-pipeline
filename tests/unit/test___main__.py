"""Verify ``python -m radio_transforma`` dispatches to the CLI."""

from __future__ import annotations

import runpy
import sys

import pytest


def test_main_module_help_exits_zero(monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["radio_transforma", "--help"])
    with pytest.raises(SystemExit) as excinfo:
        runpy.run_module("radio_transforma", run_name="__main__")
    assert excinfo.value.code == 0
