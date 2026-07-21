from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from src.config.settings import get_settings


def _engine():
 settings = get_settings()
 url = settings.live_db_url
 if not url:
  raise RuntimeError("AGENT_LIVE_DB_URL is not configured")
 return create_engine(url, pool_pre_ping=True, pool_size=5, max_overflow=10)


class LiveDBQueryError(Exception):
 pass


def read_only_query(sql: str) -> tuple[list[str], list[dict]]:
 sql = sql.strip()
 lowered = sql.lower()
 if not lowered.startswith("select"):
  raise LiveDBQueryError("Only read-only SELECT queries are allowed.")
 forbidden = ["insert ", "update ", "delete ", "drop ", "alter ", "truncate "]
 if any(token in lowered for token in forbidden):
  raise LiveDBQueryError("Query contains forbidden clauses or statements.")
 engine = _engine()
 try:
  with engine.connect() as conn:
   cursor = conn.execute(text(sql))
   if cursor.returns_rows:
    columns = list(cursor.keys())
    rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
    return columns, rows
   return [], []
 except SQLAlchemyError as exc:
  raise LiveDBQueryError(f"Query failed: {exc}") from exc
