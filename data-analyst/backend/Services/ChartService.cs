using System.Data;
using DataAnalyst.Backend.Models;

namespace DataAnalyst.Backend.Services;

/// <summary>
/// Transforms a query result grid into Chart.js {labels, datasets}.
/// Convention: first column = category label (x axis / pie slice), remaining
/// numeric columns = one dataset each. Pure/testable — no DB or LLM.
/// </summary>
public static class ChartService
{
    public static ChartData FromGrid(List<string> columns, List<object?[]> rows)
    {
        if (columns.Count == 0)
            return new ChartData(new(), new());

        var labels = new List<string>();
        var numericColIndexes = new List<int>();

        // Determine which non-first columns are numeric by inspecting first row.
        var sample = rows.FirstOrDefault();
        for (int c = 1; c < columns.Count; c++)
        {
            if (sample is null || IsNumeric(sample[c]))
                numericColIndexes.Add(c);
        }
        // Fallback: if none detected numeric but there are >1 cols, treat col 1.
        if (numericColIndexes.Count == 0 && columns.Count > 1)
            numericColIndexes.Add(1);

        var datasets = numericColIndexes
            .ToDictionary(i => i, i => new List<double>());

        foreach (var row in rows)
        {
            labels.Add(row[0]?.ToString() ?? "");
            foreach (var i in numericColIndexes)
                datasets[i].Add(ToDouble(row[i]));
        }

        var dsList = numericColIndexes
            .Select(i => new ChartDataset(columns[i], datasets[i]))
            .ToList();

        return new ChartData(labels, dsList);
    }

    private static bool IsNumeric(object? v) =>
        v is byte or sbyte or short or ushort or int or uint
          or long or ulong or float or double or decimal;

    private static double ToDouble(object? v)
    {
        if (v is null || v is DBNull) return 0d;
        try { return Convert.ToDouble(v); }
        catch { return 0d; }
    }
}
