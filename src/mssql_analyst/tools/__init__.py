"""Tools — pure functions / classes the graph nodes call.

Phase 1 contains:
- ``validator.assert_select_only`` — read-only enforcement at the SQL layer.
- ``mssql.MssqlConnector`` — ``pyodbc``-backed live MSSQL connector with
  schema caching. One connection per call (the connector does NOT pool
  internally; pooling is the responsibility of an upstream gateway).
"""

from mssql_analyst.tools.anomaly import anomaly_zscore
from mssql_analyst.tools.csv_export import to_csv
from mssql_analyst.tools.mssql import MssqlConnector, get_mssql_connector
from mssql_analyst.tools.row_cap import shrink_row_cap
from mssql_analyst.tools.structural_validator import validate_sql_structure
from mssql_analyst.tools.validator import (
    UnsafeSQLError,
    assert_select_only,
)

__all__ = [
    "MssqlConnector",
    "UnsafeSQLError",
    "anomaly_zscore",
    "assert_select_only",
    "get_mssql_connector",
    "shrink_row_cap",
    "to_csv",
    "validate_sql_structure",
]
