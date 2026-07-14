namespace DataAnalyst.Backend.Models;

public record QueryRequest(string Question);

public record ChartDataset(string Label, List<double> Data);

public record ChartData(List<string> Labels, List<ChartDataset> Datasets);

public record LlmPlan(
    string Plan,
    string ChartType,
    string Sql,
    List<string> Reasoning,
    string? Clarification
);

public record QueryResponse(
    string RunId,
    string Plan,
    string ChartType,
    string Sql,
    List<string> ReasoningSteps,
    string? Clarification,
    ChartData? Data,
    bool AuditSaved
);

public record ColumnProfile(
    string Column,
    string DataType,
    long DistinctCount,
    double NullPercent,
    double? Min,
    double? Max,
    double? Avg
);

public record TableProfile(
    string Table,
    long RowCount,
    List<ColumnProfile> Columns
);

public record SchemaCatalog(List<TableProfile> Tables);

public record AuditRecord(
    string RunId,
    string Question,
    string Plan,
    string Sql,
    string ChartType,
    int RowCount,
    int TokensUsed,
    string Timestamp,
    string Outcome
);
