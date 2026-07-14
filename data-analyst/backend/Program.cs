using System.Text;
using System.Text.Json;
using DataAnalyst.Backend.Models;
using DataAnalyst.Backend.Services;

var builder = WebApplication.CreateBuilder(args);

// ---- Load .env from repo root (two levels up from data-analyst/backend) ----
var repoRoot = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", ".."));
var envPath = Path.Combine(repoRoot, ".env");
if (File.Exists(envPath))
    DotNetEnv.Env.Load(envPath);

string Env(string k, string def = "") =>
    Environment.GetEnvironmentVariable(k) is { Length: > 0 } v ? v : def;

var connString = Env("AGENT_DATABASE_URL",
    "Server=localhost,1433;Database=WarehouseDemo;User Id=sa;Password=Str0ngP@ssw0rd!;TrustServerCertificate=True;Connection Timeout=30;");
var apiKey = Env("AGENT_OPENROUTER_API_KEY");
var model = Env("AGENT_LLM_MODEL", "google/gemini-flash-1.5");
var denyTokens = Env("SQL_DENY_TOKENS");
var port = Env("PORT", "8001");
var auditDb = Path.Combine(AppContext.BaseDirectory, "audit.db");

builder.Services.AddCors(o => o.AddDefaultPolicy(p =>
    p.AllowAnyOrigin().AllowAnyHeader().AllowAnyMethod()));

builder.Services.AddSingleton(new SchemaService(connString));
builder.Services.AddSingleton(new SqlExecutionService(connString, denyTokens));
builder.Services.AddSingleton(new AuditService(auditDb));
builder.Services.AddHttpClient();
builder.Services.AddSingleton(sp =>
    new SqlGenerationService(sp.GetRequiredService<IHttpClientFactory>().CreateClient(), apiKey, model));

builder.WebHost.UseUrls($"http://0.0.0.0:{port}");

var app = builder.Build();
app.UseCors();

var jsonOpts = new JsonSerializerOptions { PropertyNamingPolicy = JsonNamingPolicy.CamelCase };

app.MapGet("/api/health", () => Results.Json(new { status = "ok" }));

app.MapGet("/api/schema", async (SchemaService schema) =>
{
    var cat = await schema.GetCatalogAsync();
    return Results.Content(SchemaProfileSerializer.ToJson(cat), "application/json");
});

app.MapGet("/api/audit", (string? date, AuditService audit) =>
{
    var d = string.IsNullOrWhiteSpace(date) ? DateTime.UtcNow.ToString("yyyy-MM-dd") : date;
    var (runs, total) = audit.GetByDate(d);
    return Results.Json(new { date = d, runs, totalTokens = total }, jsonOpts);
});

// ---- Core: plan + generate + execute + chart + audit ----
async Task<QueryResponse> RunQueryAsync(
    string question, SchemaService schema, SqlGenerationService gen,
    SqlExecutionService exec, AuditService audit,
    Action<string, string>? onStep, CancellationToken ct)
{
    var runId = Guid.NewGuid().ToString();
    var ts = DateTime.UtcNow.ToString("yyyy-MM-dd HH:mm:ss");
    var cat = await schema.GetCatalogAsync(ct: ct);

    var genResult = await gen.GenerateAsync(question, cat, ct);
    var plan = genResult.Plan;
    onStep?.Invoke("plan", plan.Plan);

    // Clarification path — no SQL runs.
    if (plan.Clarification is not null)
    {
        audit.Save(new AuditRecord(runId, question, plan.Plan, "", plan.ChartType, 0,
            genResult.TokensUsed, ts, "clarification"));
        return new QueryResponse(runId, plan.Plan, plan.ChartType, "", plan.Reasoning,
            plan.Clarification, null, true);
    }

    onStep?.Invoke("sql", plan.Sql);
    var execResult = await exec.ExecuteAsync(plan.Sql, ct);
    if (!execResult.Ok)
    {
        audit.Save(new AuditRecord(runId, question, plan.Plan, plan.Sql, plan.ChartType, 0,
            genResult.TokensUsed, ts, "rejected: " + execResult.Error));
        throw new InvalidOperationException(execResult.Error);
    }

    for (int i = 0; i < plan.Reasoning.Count; i++)
        onStep?.Invoke("step", $"Step {i + 1} of {plan.Reasoning.Count}: {plan.Reasoning[i]}");

    var chart = ChartService.FromGrid(execResult.Columns, execResult.Rows);
    audit.Save(new AuditRecord(runId, question, plan.Plan, execResult.SafeSql, plan.ChartType,
        execResult.Rows.Count, genResult.TokensUsed, ts, "ok"));

    return new QueryResponse(runId, plan.Plan, plan.ChartType, execResult.SafeSql,
        plan.Reasoning, null, chart, true);
}

app.MapPost("/api/query", async (QueryRequest req, SchemaService schema, SqlGenerationService gen,
    SqlExecutionService exec, AuditService audit, CancellationToken ct) =>
{
    if (!gen.IsConfigured)
        return Results.Json(new { error = "LLM not configured" }, statusCode: 503);
    try
    {
        var resp = await RunQueryAsync(req.Question, schema, gen, exec, audit, null, ct);
        return Results.Json(resp, jsonOpts);
    }
    catch (InvalidOperationException ex)
    {
        return Results.Json(new { error = ex.Message }, statusCode: 400);
    }
});

app.MapPost("/api/query/stream", async (HttpContext http, QueryRequest req, SchemaService schema,
    SqlGenerationService gen, SqlExecutionService exec, AuditService audit, CancellationToken ct) =>
{
    http.Response.Headers.Append("Content-Type", "text/event-stream");
    http.Response.Headers.Append("Cache-Control", "no-cache");

    async Task Send(string ev, object data)
    {
        var json = JsonSerializer.Serialize(data, jsonOpts);
        await http.Response.WriteAsync($"event: {ev}\ndata: {json}\n\n", ct);
        await http.Response.Body.FlushAsync(ct);
    }

    if (!gen.IsConfigured)
    {
        await Send("error", new { error = "LLM not configured" });
        return;
    }

    try
    {
        void OnStep(string ev, string text) => Send(ev, new { text }).GetAwaiter().GetResult();
        var resp = await RunQueryAsync(req.Question, schema, gen, exec, audit, OnStep, ct);
        await Send("data", resp);
        await Send("done", new { runId = resp.RunId });
    }
    catch (InvalidOperationException ex)
    {
        await Send("error", new { error = ex.Message });
    }
});

app.Run();

public partial class Program { }
