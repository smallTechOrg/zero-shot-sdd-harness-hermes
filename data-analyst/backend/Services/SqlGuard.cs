using System.Text.RegularExpressions;

namespace DataAnalyst.Backend.Services;

/// <summary>
/// Belt-and-suspenders read-only enforcement. Rejects any generated SQL that
/// contains a mutating token (case-insensitive, word-boundary) and enforces a
/// TOP row limit + rejects SELECT *.
/// </summary>
public static class SqlGuard
{
    public static readonly string[] DefaultDenyTokens =
    {
        "INSERT", "UPDATE", "DELETE", "DROP", "ALTER",
        "TRUNCATE", "GRANT", "EXEC", "EXECUTE", "MERGE"
    };

    public const int MaxRows = 1000;

    public sealed record ValidationResult(bool Ok, string? Error, string Sql);

    public static string[] ResolveDenyTokens(string? envTokens)
    {
        if (string.IsNullOrWhiteSpace(envTokens))
            return DefaultDenyTokens;
        var custom = envTokens
            .Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries)
            .Select(t => t.ToUpperInvariant())
            .ToArray();
        return custom.Length == 0 ? DefaultDenyTokens : custom;
    }

    public static string? FindDeniedToken(string sql, string[]? denyTokens = null)
    {
        var tokens = denyTokens ?? DefaultDenyTokens;
        foreach (var token in tokens)
        {
            var pattern = $@"\b{Regex.Escape(token)}\b";
            if (Regex.IsMatch(sql, pattern, RegexOptions.IgnoreCase))
                return token.ToUpperInvariant();
        }
        return null;
    }

    /// <summary>
    /// Validates SQL and returns a possibly-modified SQL with a TOP clause
    /// injected if the query is a bare SELECT without one.
    /// </summary>
    public static ValidationResult Validate(string sql, string[]? denyTokens = null, int maxRows = MaxRows)
    {
        if (string.IsNullOrWhiteSpace(sql))
            return new ValidationResult(false, "SQL is empty", sql);

        var trimmed = sql.Trim().TrimEnd(';').Trim();

        var denied = FindDeniedToken(trimmed, denyTokens);
        if (denied is not null)
            return new ValidationResult(false, $"SQL rejected: contains {denied}", trimmed);

        // Must start with SELECT (or WITH ... SELECT for CTEs).
        if (!Regex.IsMatch(trimmed, @"^\s*(WITH|SELECT)\b", RegexOptions.IgnoreCase))
            return new ValidationResult(false, "SQL rejected: only SELECT queries are allowed", trimmed);

        // Reject SELECT * (unqualified star).
        if (Regex.IsMatch(trimmed, @"SELECT\s+\*", RegexOptions.IgnoreCase))
            return new ValidationResult(false, "SQL rejected: SELECT * is not allowed", trimmed);

        // Enforce TOP on the leading SELECT if missing.
        var hasTop = Regex.IsMatch(trimmed, @"SELECT\s+TOP\s*\(?\s*\d+", RegexOptions.IgnoreCase);
        var final = trimmed;
        if (!hasTop)
        {
            final = Regex.Replace(
                trimmed,
                @"SELECT\s+",
                $"SELECT TOP {maxRows} ",
                RegexOptions.IgnoreCase);
        }

        return new ValidationResult(true, null, final);
    }
}
