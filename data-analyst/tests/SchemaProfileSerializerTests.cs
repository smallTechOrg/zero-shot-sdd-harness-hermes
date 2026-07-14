using System.Text.Json;
using DataAnalyst.Backend.Models;
using DataAnalyst.Backend.Services;
using Xunit;

namespace DataAnalyst.Tests;

public class SchemaProfileSerializerTests
{
    private static SchemaCatalog Sample() => new(new List<TableProfile>
    {
        new("FactSales", 100000, new List<ColumnProfile>
        {
            new("Amount", "decimal", 95000, 0.0, 5.0, 1900.0, 512.3),
            new("ChannelKey", "int", 4, 0.0, 1, 4, 2.5),
        })
    });

    [Fact]
    public void JsonIsCamelCaseAndHasProfileStats()
    {
        var json = SchemaProfileSerializer.ToJson(Sample());
        Assert.Contains("\"tables\"", json);
        Assert.Contains("\"rowCount\":100000", json);
        Assert.Contains("\"distinctCount\":95000", json);
        Assert.Contains("\"nullPercent\":0", json);
    }

    [Fact]
    public void JsonRoundTrips()
    {
        var json = SchemaProfileSerializer.ToJson(Sample());
        var opts = new JsonSerializerOptions { PropertyNameCaseInsensitive = true };
        var back = JsonSerializer.Deserialize<SchemaCatalog>(json, opts);
        Assert.NotNull(back);
        Assert.Single(back!.Tables);
        Assert.Equal("FactSales", back.Tables[0].Table);
        Assert.Equal(2, back.Tables[0].Columns.Count);
    }

    [Fact]
    public void PromptContextContainsNoRawRowsJustStats()
    {
        var ctx = SchemaProfileSerializer.ToPromptContext(Sample());
        Assert.Contains("TABLE FactSales", ctx);
        Assert.Contains("distinct=95000", ctx);
        Assert.Contains("avg=", ctx);
        // Sanity: it is schema/stats text, compact.
        Assert.Contains("Amount decimal", ctx);
    }
}
