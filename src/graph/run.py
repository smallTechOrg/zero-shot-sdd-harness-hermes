"""Domain graph dispatcher — maps an analyst source to the correct graph runner."""
from __future__ import annotations

from src.graph.runner_csv import run_csv_agent
from src.graph.runner import run_agent as run_transform_agent


def run_agent(source: str, **kwargs):
 canonical = (source or "").strip().lower()
 if canonical == "csv":
  return run_csv_agent(**kwargs)
 return run_transform_agent(**kwargs)
