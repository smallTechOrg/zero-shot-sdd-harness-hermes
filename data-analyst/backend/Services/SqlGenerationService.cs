using System.Text;
using System.Text.Json;
using DataAnalyst.Backend.Models;

namespace DataAnalyst.Backend.Services;

/// <summary>
/// Calls OpenRouter chat completions with the schema + aggregate profile in the
/// system prompt and a strict JSON output contract. RAW ROWS ARE NEVER SENT.
/// If no API key is configured, IsConfigured is false and callers return 503.
/// </summary>
public class SqlGenerationService
{
    private readonly HttpClient _http;
    private readonly string? _apiKey;
    private readonly string _model;

    public SqlGenerationService(HttpClient http, string? apiKey, string model)
    {
        _http = http;
        _apiKey = apiKey;
        _model = string.IsNullOrWhiteSpace(model) ? "google/gemini-flash-1.5" : model;
    }

    public bool IsConfigured => !string.IsNullOrWhiteSpace(_apiKey);

    public sealed record GenResult(LlmPlan Plan, int TokensUsed);

    private const string ContractInstructions = @"You are a careful data analyst. Given a warehouse schema with aggregate
profile stats (NOT raw data), plan the analysis, choose a chart type, and write ONE read-only
Microsoft SQL Server SELECT query. Rules:
- Output STRICT JSON only: {""plan"":string, ""chartType"":""bar""|""line""|""pie"", ""sql"":string, ""reasoning"":[string], ""clarification"":string|null}
- SQL MUST be a single SELECT with an explicit TOP N (N<=1000). Never SELECT *. Never mutate data.
- The first selected column is the category/label; remaining numeric columns are chart series.
- If the question is ambiguous, set ""clarification"" to a question and leave sql empty.
- Flag any obvious data-quality issues (nulls/outliers) you notice in the reasoning.";

    public string BuildSystemPrompt(SchemaCatalog catalog)
    {
        var sb = new StringBuilder();
        sb.AppendLine(ContractInstructions);
        sb.AppendLine();
        sb.AppendLine("WAREHOUSE SCHEMA + AGGREGATE PROFILES (no raw rows):");
        sb.AppendLine(SchemaProfileSerializer.ToPromptContext(catalog));
        return sb.ToString();
    }

    public async Task<GenResult> GenerateAsync(string question, SchemaCatalog catalog, CancellationToken ct = default)
    {
        if (!IsConfigured)
            throw new InvalidOperationException("LLM not configured");

        var payload = new
        {
            model = _model,
            messages = new object[]
            {
                new { role = "system", content = BuildSystemPrompt(catalog) },
                new { role = "user", content = question }
            },
            temperature = 0.1,
            response_format = new { type = "json_object" }
        };

        using var req = new HttpRequestMessage(HttpMethod.Post,
            "https://openrouter.ai/api/v1/chat/completions");
        req.Headers.Add("Authorization", $"Bearer {_apiKey}");
        req.Content = new StringContent(JsonSerializer.Serialize(payload), Encoding.UTF8, "application/json");

        using var resp = await _http.SendAsync(req, ct);
        var body = await resp.Content.ReadAsStringAsync(ct);
        resp.EnsureSuccessStatusCode();

        using var doc = JsonDocument.Parse(body);
        var root = doc.RootElement;
        var content = root.GetProperty("choices")[0].GetProperty("message").GetProperty("content").GetString() ?? "{}";
        int tokens = 0;
        if (root.TryGetProperty("usage", out var usage) &&
            usage.TryGetProperty("total_tokens", out var tt))
            tokens = tt.GetInt32();

        var plan = ParsePlan(content);
        return new GenResult(plan, tokens);
    }

    public static LlmPlan ParsePlan(string content)
    {
        // Strip markdown fences if present.
        var c = content.Trim();
        if (c.StartsWith("```"))
        {
            var first = c.IndexOf('\n');
            if (first >= 0) c = c[(first + 1)..];
            if (c.EndsWith("```")) c = c[..^3];
            c = c.Trim();
        }
        using var doc = JsonDocument.Parse(c);
        var r = doc.RootElement;
        string plan = r.TryGetProperty("plan", out var p) ? p.GetString() ?? "" : "";
        string chart = r.TryGetProperty("chartType", out var ch) ? ch.GetString() ?? "bar" : "bar";
        string sql = r.TryGetProperty("sql", out var s) ? s.GetString() ?? "" : "";
        var reasoning = new List<string>();
        if (r.TryGetProperty("reasoning", out var re) && re.ValueKind == JsonValueKind.Array)
            foreach (var item in re.EnumerateArray())
                reasoning.Add(item.GetString() ?? "");
        string? clar = r.TryGetProperty("clarification", out var cl) && cl.ValueKind == JsonValueKind.String
            ? cl.GetString() : null;
        if (string.IsNullOrWhiteSpace(clar)) clar = null;
        return new LlmPlan(plan, chart, sql, reasoning, clar);
    }
}
