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

    private const string ContractInstructions = @"You are a careful crime-data analyst assisting the SENIOR LEADERSHIP of Uttar
Pradesh Police. Given a CCTNS 1.0 police schema with aggregate profile stats (NOT raw data),
plan the analysis, choose a chart type, and write ONE read-only Microsoft SQL Server (T-SQL)
SELECT query that answers the leadership's question in plain, decision-oriented terms.
Rules:
- The engine is Microsoft SQL Server / Azure SQL Edge. Use only T-SQL.
- Output STRICT JSON only: {""plan"":string, ""chartType"":""bar""|""line""|""pie"", ""sql"":string, ""reasoning"":[string], ""clarification"":string|null}
- SQL MUST be a single SELECT with an explicit TOP clause written exactly as 'TOP 1000 '
  (the word TOP, a space, the integer, a space) — never 'TOP(1000)' or 'TOP1000'.
- Never SELECT *. Never mutate data. The first selected column is the category/label;
  remaining numeric columns are chart series.
- For zero-padded month formatting use T-SQL: RIGHT('0' + CAST(d.Month AS VARCHAR(2)), 2).
  NEVER use LPAD, RPAD, DATE_FORMAT, STR_TO_DATE, IFNULL, NVL, or REGEXP — those are not T-SQL.
- Keep technical police terms in English where they are standard: FIR, IPC, charge sheet
  (चार्जशीट), detection rate (बरामदगी दर), pendency (लंबित), police station (थाना), district (जिला).
  Otherwise frame the plan and reasoning in simple Hindi-friendly English for non-technical leaders.
- If the question is ambiguous (e.g. which year, which district), set ""clarification"" to a
  question and leave sql empty.
- Flag any obvious data-quality issues you notice in the reasoning.";

    public string BuildSystemPrompt(SchemaCatalog catalog)
    {
        var sb = new StringBuilder();
        sb.AppendLine(ContractInstructions);
        sb.AppendLine();
        sb.AppendLine("CCTNS POLICE DATA SCHEMA + AGGREGATE PROFILES (no raw rows):");
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
            max_tokens = 600,
            response_format = new { type = "json_object" }
        };

        string body = "";
        HttpResponseMessage? resp = null;
        const int MaxRetries = 4;
        for (int attempt = 0; attempt < MaxRetries; attempt++)
        {
            using var req = new HttpRequestMessage(HttpMethod.Post,
                "https://openrouter.ai/api/v1/chat/completions");
            req.Headers.Add("Authorization", $"Bearer {_apiKey}");
            req.Content = new StringContent(JsonSerializer.Serialize(payload), Encoding.UTF8, "application/json");

            resp = await _http.SendAsync(req, ct);
            body = await resp.Content.ReadAsStringAsync(ct);
            // Free-tier models are heavily rate-limited (HTTP 429). Retry with
            // backoff; fail fast on auth/credit errors.
            if ((int)resp.StatusCode == 429 && attempt < MaxRetries - 1)
            {
                await Task.Delay(1500 * (attempt + 1), ct);
                continue;
            }
            break;
        }

        if (resp is null || !resp.IsSuccessStatusCode)
        {
            // Surface OpenRouter's own error (e.g. 402 credits, 401 auth) instead of a bare 500.
            string detail = body;
            try
            {
                using var err = JsonDocument.Parse(body);
                if (err.RootElement.TryGetProperty("error", out var e) &&
                    e.TryGetProperty("message", out var m))
                    detail = m.GetString() ?? body;
            }
            catch { /* keep raw body */ }
            throw new InvalidOperationException($"OpenRouter {resp?.StatusCode}: {detail}");
        }

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
