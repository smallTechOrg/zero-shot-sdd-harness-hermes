"""Helpers — live database query path decoding and safe routing."""
from __future__ import annotations

import re

from src.graph.state import AgentState


LIVE_DB_PATH_PREFIX = "/live-db"


def decode_live_db_path(raw: str) -> str:
 text = (raw or "").strip().lower()
 text = re.sub(r"[^a-z0-9/_-]+", "-", text)
 text = re.sub(r"/{2,}", "/", text).strip("/")
 return f"{LIVE_DB_PATH_PREFIX}/{text}" if text else LIVE_DB_PATH_PREFIX


def classify_live_db_path(path: str) -> str:
 normalized = (path or "").strip().lower()
 if normalized.startswith(f"{LIVE_DB_PATH_PREFIX}/query"):
  return "query"
 if normalized.startswith(f"{LIVE_DB_PATH_PREFIX}/runs/"):
  return "run_detail"
 return "root"
