using Microsoft.Data.Sqlite;
using DataAnalyst.Backend.Models;

namespace DataAnalyst.Backend.Services;

/// <summary>Server-side audit trail of every run, stored in SQLite.</summary>
public class AuditService
{
    private readonly string _dbPath;

    public AuditService(string dbPath)
    {
        _dbPath = dbPath;
        Init();
    }

    private string ConnStr => $"Data Source={_dbPath}";

    private void Init()
    {
        using var conn = new SqliteConnection(ConnStr);
        conn.Open();
        using var cmd = conn.CreateCommand();
        cmd.CommandText = @"CREATE TABLE IF NOT EXISTS runs (
            RunId TEXT PRIMARY KEY,
            Question TEXT, Plan TEXT, Sql TEXT, ChartType TEXT,
            RowCount INTEGER, TokensUsed INTEGER,
            Timestamp TEXT, Outcome TEXT);";
        cmd.ExecuteNonQuery();
    }

    public void Save(AuditRecord rec)
    {
        using var conn = new SqliteConnection(ConnStr);
        conn.Open();
        using var cmd = conn.CreateCommand();
        cmd.CommandText = @"INSERT OR REPLACE INTO runs
            (RunId,Question,Plan,Sql,ChartType,RowCount,TokensUsed,Timestamp,Outcome)
            VALUES ($id,$q,$p,$s,$c,$rc,$tk,$ts,$o)";
        cmd.Parameters.AddWithValue("$id", rec.RunId);
        cmd.Parameters.AddWithValue("$q", rec.Question);
        cmd.Parameters.AddWithValue("$p", rec.Plan);
        cmd.Parameters.AddWithValue("$s", rec.Sql);
        cmd.Parameters.AddWithValue("$c", rec.ChartType);
        cmd.Parameters.AddWithValue("$rc", rec.RowCount);
        cmd.Parameters.AddWithValue("$tk", rec.TokensUsed);
        cmd.Parameters.AddWithValue("$ts", rec.Timestamp);
        cmd.Parameters.AddWithValue("$o", rec.Outcome);
        cmd.ExecuteNonQuery();
    }

    public (List<AuditRecord> runs, int totalTokens) GetByDate(string dateYmd)
    {
        var runs = new List<AuditRecord>();
        int total = 0;
        using var conn = new SqliteConnection(ConnStr);
        conn.Open();
        using var cmd = conn.CreateCommand();
        cmd.CommandText = @"SELECT RunId,Question,Plan,Sql,ChartType,RowCount,TokensUsed,Timestamp,Outcome
            FROM runs WHERE substr(Timestamp,1,10)=$d ORDER BY Timestamp DESC";
        cmd.Parameters.AddWithValue("$d", dateYmd);
        using var r = cmd.ExecuteReader();
        while (r.Read())
        {
            var tk = r.GetInt32(6);
            total += tk;
            runs.Add(new AuditRecord(
                r.GetString(0), r.GetString(1), r.GetString(2), r.GetString(3),
                r.GetString(4), r.GetInt32(5), tk, r.GetString(7), r.GetString(8)));
        }
        return (runs, total);
    }
}
