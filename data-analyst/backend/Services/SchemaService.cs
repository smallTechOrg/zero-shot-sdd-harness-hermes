using Microsoft.Data.SqlClient;
using DataAnalyst.Backend.Models;

namespace DataAnalyst.Backend.Services;

/// <summary>
/// Introspects INFORMATION_SCHEMA + computes sampled aggregate profiles for the
/// warehouse. Cached in memory after first load. Never reads raw rows into any
/// LLM-bound structure — only counts/distincts/min/max/avg/null%.
/// </summary>
public class SchemaService
{
    private readonly string _connString;
    private SchemaCatalog? _cache;
    private readonly SemaphoreSlim _lock = new(1, 1);

    public SchemaService(string connString) => _connString = connString;

    public async Task<SchemaCatalog> GetCatalogAsync(bool refresh = false, CancellationToken ct = default)
    {
        if (_cache is not null && !refresh) return _cache;
        await _lock.WaitAsync(ct);
        try
        {
            if (_cache is not null && !refresh) return _cache;
            _cache = await BuildCatalogAsync(ct);
            return _cache;
        }
        finally { _lock.Release(); }
    }

    private async Task<SchemaCatalog> BuildCatalogAsync(CancellationToken ct)
    {
        var tables = new List<TableProfile>();
        await using var conn = new SqlConnection(_connString);
        await conn.OpenAsync(ct);

        // Discover base tables.
        var tableCols = new Dictionary<string, List<(string col, string type)>>();
        const string colSql = @"SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE
            FROM INFORMATION_SCHEMA.COLUMNS c
            WHERE EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.TABLES t
                          WHERE t.TABLE_NAME = c.TABLE_NAME AND t.TABLE_TYPE = 'BASE TABLE')
            ORDER BY TABLE_NAME, ORDINAL_POSITION";
        await using (var cmd = new SqlCommand(colSql, conn))
        await using (var r = await cmd.ExecuteReaderAsync(ct))
        {
            while (await r.ReadAsync(ct))
            {
                var tbl = r.GetString(0);
                if (!tableCols.TryGetValue(tbl, out var list))
                    tableCols[tbl] = list = new();
                list.Add((r.GetString(1), r.GetString(2)));
            }
        }

        foreach (var (tbl, cols) in tableCols)
        {
            long rowCount = await ScalarLongAsync(conn, $"SELECT COUNT_BIG(*) FROM [{tbl}]", ct);
            var colProfiles = new List<ColumnProfile>();
            foreach (var (col, type) in cols)
            {
                long distinct = await ScalarLongAsync(conn,
                    $"SELECT COUNT_BIG(DISTINCT [{col}]) FROM [{tbl}]", ct);
                long nulls = await ScalarLongAsync(conn,
                    $"SELECT COUNT_BIG(*) FROM [{tbl}] WHERE [{col}] IS NULL", ct);
                double nullPct = rowCount == 0 ? 0 : (double)nulls * 100.0 / rowCount;

                double? min = null, max = null, avg = null;
                if (IsNumericType(type))
                {
                    (min, max, avg) = await NumericStatsAsync(conn, tbl, col, ct);
                }
                colProfiles.Add(new ColumnProfile(col, type, distinct, Math.Round(nullPct, 2), min, max, avg));
            }
            tables.Add(new TableProfile(tbl, rowCount, colProfiles));
        }

        return new SchemaCatalog(tables);
    }

    private static bool IsNumericType(string t) => t is
        "int" or "bigint" or "smallint" or "tinyint" or
        "decimal" or "numeric" or "money" or "smallmoney" or "float" or "real";

    private static async Task<long> ScalarLongAsync(SqlConnection conn, string sql, CancellationToken ct)
    {
        await using var cmd = new SqlCommand(sql, conn) { CommandTimeout = 30 };
        var o = await cmd.ExecuteScalarAsync(ct);
        return o is null or DBNull ? 0 : Convert.ToInt64(o);
    }

    private static async Task<(double?, double?, double?)> NumericStatsAsync(
        SqlConnection conn, string tbl, string col, CancellationToken ct)
    {
        await using var cmd = new SqlCommand(
            $"SELECT MIN(CAST([{col}] AS float)), MAX(CAST([{col}] AS float)), AVG(CAST([{col}] AS float)) FROM [{tbl}]",
            conn) { CommandTimeout = 30 };
        await using var r = await cmd.ExecuteReaderAsync(ct);
        if (await r.ReadAsync(ct))
        {
            double? min = r.IsDBNull(0) ? null : r.GetDouble(0);
            double? max = r.IsDBNull(1) ? null : r.GetDouble(1);
            double? avg = r.IsDBNull(2) ? null : r.GetDouble(2);
            return (min, max, avg);
        }
        return (null, null, null);
    }
}
