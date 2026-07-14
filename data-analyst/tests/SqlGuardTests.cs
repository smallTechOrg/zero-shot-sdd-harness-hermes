using DataAnalyst.Backend.Services;
using Xunit;

namespace DataAnalyst.Tests;

public class SqlGuardTests
{
    [Theory]
    [InlineData("INSERT INTO T VALUES(1)")]
    [InlineData("update t set x=1")]
    [InlineData("DELETE FROM T")]
    [InlineData("DROP TABLE T")]
    [InlineData("ALTER TABLE T ADD c int")]
    [InlineData("TRUNCATE TABLE T")]
    [InlineData("GRANT SELECT ON T TO u")]
    [InlineData("EXEC sp_who")]
    [InlineData("MERGE INTO T USING S ON 1=1")]
    public void RejectsMutatingSql(string sql)
    {
        var r = SqlGuard.Validate(sql);
        Assert.False(r.Ok);
        Assert.NotNull(r.Error);
    }

    [Fact]
    public void RejectsSelectStar()
    {
        var r = SqlGuard.Validate("SELECT * FROM FactSales");
        Assert.False(r.Ok);
        Assert.Contains("SELECT *", r.Error);
    }

    [Fact]
    public void RejectsNonSelect()
    {
        var r = SqlGuard.Validate("WITHOUT SELECT nonsense");
        Assert.False(r.Ok);
    }

    [Fact]
    public void InjectsTopWhenMissing()
    {
        var r = SqlGuard.Validate("SELECT ChannelKey, SUM(Amount) FROM FactSales GROUP BY ChannelKey");
        Assert.True(r.Ok);
        Assert.Contains("TOP 1000", r.Sql);
    }

    [Fact]
    public void KeepsExistingTop()
    {
        var r = SqlGuard.Validate("SELECT TOP 10 ChannelKey FROM FactSales");
        Assert.True(r.Ok);
        Assert.Contains("TOP 10", r.Sql);
        Assert.DoesNotContain("TOP 1000", r.Sql);
    }

    [Fact]
    public void CaseInsensitiveDenyList()
    {
        Assert.Equal("DROP", SqlGuard.FindDeniedToken("select 1; DrOp table t"));
    }

    [Fact]
    public void CustomDenyTokensFromEnv()
    {
        var tokens = SqlGuard.ResolveDenyTokens("FOO, BAR");
        Assert.Contains("FOO", tokens);
        Assert.Contains("BAR", tokens);
    }
}
