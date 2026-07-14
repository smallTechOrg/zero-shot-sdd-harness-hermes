using Microsoft.Data.SqlClient;
using DataAnalyst.Backend.Models;

namespace DataAnalyst.Backend.Services;

/// <summary>
/// Executes validated read-only SQL against the warehouse and returns a grid.
/// Enforces the deny-list + TOP via SqlGuard BEFORE any execution.
/// Query results NEVER go back to the LLM.
/// </summary>
public class SqlExecutionService
{
    private readonly string _connString;
    private readonly string[] _denyTokens;

    public SqlExecutionService(string connString, string? envDenyTokens)
    {
        _connString = connString;
        _denyTokens = SqlGuard.ResolveDenyTokens(envDenyTokens);
    }

    public sealed record ExecResult(
        bool Ok, string? Error, string SafeSql,
        List<string> Columns, List<object?[]> Rows);

    public async Task<ExecResult> ExecuteAsync(string sql, CancellationToken ct = default)
    {
        var v = SqlGuard.Validate(sql, _denyTokens);
        if (!v.Ok)
            return new ExecResult(false, v.Error, v.Sql, new(), new());

        var columns = new List<string>();
        var rows = new List<object?[]>();

        await using var conn = new SqlConnection(_connString);
        await conn.OpenAsync(ct);
        await using var cmd = new SqlCommand(v.Sql, conn) { CommandTimeout = 60 };
        await using var r = await cmd.ExecuteReaderAsync(ct);

        for (int i = 0; i < r.FieldCount; i++)
            columns.Add(r.GetName(i));

        while (await r.ReadAsync(ct))
        {
            var row = new object?[r.FieldCount];
            for (int i = 0; i < r.FieldCount; i++)
                row[i] = r.IsDBNull(i) ? null : r.GetValue(i);
            rows.Add(row);
        }

        return new ExecResult(true, null, v.Sql, columns, rows);
    }
}
