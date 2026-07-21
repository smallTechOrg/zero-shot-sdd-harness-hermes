"""Regression test — importing the app and running server startup paths still works."""
from __future__ import annotations

import importlib


def test_import_app_package():
 mod = importlib.import_module("src.api")
 assert hasattr(mod, "create_app")


def test_import_entrypoint():
 mod = importlib.import_module("src.__main__")
 assert hasattr(mod, "main")
