using DataAnalyst.Backend.Services;
using Xunit;

namespace DataAnalyst.Tests;

public class ChartServiceTests
{
    [Fact]
    public void ShapesLabelPlusOneNumericSeries()
    {
        var cols = new List<string> { "Channel", "TotalAmount" };
        var rows = new List<object?[]>
        {
            new object?[] { "Online", 100.5 },
            new object?[] { "Retail", 200.0 },
            new object?[] { "Partner", 50.0 },
        };
        var chart = ChartService.FromGrid(cols, rows);

        Assert.Equal(new[] { "Online", "Retail", "Partner" }, chart.Labels);
        Assert.Single(chart.Datasets);
        Assert.Equal("TotalAmount", chart.Datasets[0].Label);
        Assert.Equal(new List<double> { 100.5, 200.0, 50.0 }, chart.Datasets[0].Data);
    }

    [Fact]
    public void ShapesMultipleNumericSeries()
    {
        var cols = new List<string> { "Month", "Amount", "Quantity" };
        var rows = new List<object?[]>
        {
            new object?[] { "Jan", 10.0, 3 },
            new object?[] { "Feb", 20.0, 5 },
        };
        var chart = ChartService.FromGrid(cols, rows);
        Assert.Equal(2, chart.Datasets.Count);
        Assert.Equal(new List<double> { 3, 5 }, chart.Datasets[1].Data);
    }

    [Fact]
    public void HandlesNullNumericAsZero()
    {
        var cols = new List<string> { "K", "V" };
        var rows = new List<object?[]> { new object?[] { "a", null } };
        var chart = ChartService.FromGrid(cols, rows);
        Assert.Equal(0d, chart.Datasets[0].Data[0]);
    }

    [Fact]
    public void EmptyColumnsYieldsEmptyChart()
    {
        var chart = ChartService.FromGrid(new(), new());
        Assert.Empty(chart.Labels);
        Assert.Empty(chart.Datasets);
    }
}
