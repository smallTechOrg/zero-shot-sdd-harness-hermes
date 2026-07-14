using System.Text;
using System.Text.Json;
using DataAnalyst.Backend.Models;

namespace DataAnalyst.Backend.Services;

/// <summary>
/// Serializes the warehouse schema + aggregate profiles into a compact,
/// LLM-safe context string. Contains ONLY schema + aggregate stats — never
/// raw rows. Pure/testable.
/// </summary>
public static class SchemaProfileSerializer
{
    private static readonly JsonSerializerOptions JsonOpts = new()
    {
        WriteIndented = false,
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase
    };

    public static string ToJson(SchemaCatalog catalog) =>
        JsonSerializer.Serialize(catalog, JsonOpts);

    /// <summary>Compact human/LLM-readable prompt context.</summary>
    public static string ToPromptContext(SchemaCatalog catalog)
    {
        var sb = new StringBuilder();
        foreach (var t in catalog.Tables)
        {
            sb.Append($"TABLE {t.Table} (~{t.RowCount} rows)\n");
            foreach (var c in t.Columns)
            {
                sb.Append($"  - {c.Column} {c.DataType} distinct={c.DistinctCount} null%={c.NullPercent:0.##}");
                if (c.Min is not null || c.Max is not null || c.Avg is not null)
                    sb.Append($" min={c.Min} max={c.Max} avg={c.Avg:0.##}");
                sb.Append('\n');
            }
        }
        return sb.ToString();
    }
}
