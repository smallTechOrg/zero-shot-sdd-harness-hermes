"use client";

import { useEffect, useState } from "react";

type ApiRow = unknown[];

type ApiResponse = {
  data?: {
    sql: string;
    columns: string[];
    rows: ApiRow[];
    latency_ms: number;
    row_count: number;
    sql_attempts: number;
    tokens_used: number;
    status: "completed" | "failed";
  };
  error?: { code: string; message: string } | null;
};

type Usage = {
  total_questions: number;
  total_tokens: number;
  total_rows_returned: number;
  last_questions: Array<{
    id: string;
    question: string;
    sql: string;
    status: string;
    row_count: number;
    tokens_used: number;
    latency_ms: number;
    created_at: string;
  }>;
};

function formatAnswer(payload: NonNullable<ApiResponse["data"]>): string {
  // Phase 1 deterministic UI message — no markdown required.
  if (payload.status !== "completed") return "—";
  const rows = payload.rows.slice(0, 1);
  const cols = payload.columns.slice(0, 2).join(", ");
  const count = rows.length;
  if (count === 0) return "No rows returned.";
  if (count === 1) {
    const cell = rows[0][0];
    if (cell === null || cell === undefined || cell === "") {
      return "Empty result for the question.";
    }
    return `Found: ${cell}${payload.row_count > 1 ? ` (and ${payload.row_count - 1} more rows not shown)` : ""}.`;
  }
  return `${count} rows returned. Columns: ${cols || "(none)"}.`;
}

export default function Page() {
  const [question, setQuestion] = useState("How many tables are in master?");
  const [busy, setBusy] = useState(false);
  const [response, setResponse] = useState<ApiResponse["data"] | null>(null);
  const [showSql, setShowSql] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [usage, setUsage] = useState<Usage | null>(null);

  async function refreshUsage() {
    try {
      const r = await fetch("/api/usage");
      const body: { data?: Usage; error?: unknown } = await r.json();
      if (body.data) setUsage(body.data);
    } catch {
      /* Phase 1: ignore — usage is convenience */
    }
  }

  useEffect(() => {
    refreshUsage();
  }, []);

  async function onAsk(e?: React.FormEvent) {
    if (e) e.preventDefault();
    if (!question.trim()) return;
    setBusy(true);
    setError(null);
    setResponse(null);
    try {
      const r = await fetch("/api/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: question.trim() }),
      });
      const body: ApiResponse = await r.json();
      if (body.error) {
        setError(`${body.error.code}: ${body.error.message}`);
      } else if (body.data) {
        setResponse(body.data);
      }
      await refreshUsage();
    } catch (err) {
      setError(`network_error: ${(err as Error).message}`);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto max-w-3xl px-4 py-8">
      <header className="mb-6 flex items-baseline justify-between">
        <h1 className="text-2xl font-semibold tracking-tight">
          MSSQL Analyst
        </h1>
        <div className="flex items-center gap-2">
          <span
            data-testid="tokens-badge"
            className="rounded bg-gray-200 px-2 py-0.5 text-xs font-medium text-gray-700 dark:bg-gray-800 dark:text-gray-300"
          >
            tokens used: {usage?.total_tokens ?? 0}
          </span>
          <span
            data-testid="source-badge"
            className="rounded bg-indigo-100 px-2 py-0.5 text-xs font-medium text-indigo-800 dark:bg-indigo-900 dark:text-indigo-100"
          >
            source: live MSSQL
          </span>
        </div>
      </header>

      <form onSubmit={onAsk} className="mb-6 flex flex-col gap-2">
        <label htmlFor="q" className="text-sm font-medium">
          Question
        </label>
        <textarea
          id="q"
          name="question"
          data-testid="question"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          rows={2}
          className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-base shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:border-gray-600 dark:bg-gray-800"
        />
        <button
          type="submit"
          data-testid="ask"
          disabled={busy}
          className="self-start rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-indigo-700 disabled:opacity-50"
        >
          {busy ? "Asking…" : "Ask"}
        </button>
      </form>

      {busy && (
        <div
          data-testid="loading"
          className="rounded-md bg-white p-4 shadow dark:bg-gray-800"
        >
          <p className="text-sm text-gray-500">
            Running against live MSSQL…
          </p>
        </div>
      )}

      {error && (
        <div
          data-testid="error"
          className="rounded-md bg-red-50 p-4 text-sm text-red-800 shadow dark:bg-red-900/40 dark:text-red-100"
        >
          <p className="font-medium">{error}</p>
          <p className="mt-1 opacity-75">
            Try a shorter or more specific question.
          </p>
        </div>
      )}

      {response && !error && (
        <section
          data-testid="results"
          className="rounded-md bg-white p-4 shadow dark:bg-gray-800"
        >
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-lg font-medium">Answer</h2>
            <span
              data-testid="latency"
              className="rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-600 dark:bg-gray-700 dark:text-gray-300"
            >
              {response.latency_ms} ms · {response.row_count} rows
              {response.tokens_used ? ` · ${response.tokens_used} tok` : ""}
            </span>
          </div>
          <p
            data-testid="answer"
            className="mb-4 whitespace-pre-wrap text-sm"
          >
            {formatAnswer(response)}
          </p>

          <div className="overflow-x-auto rounded-md border border-gray-200 dark:border-gray-700">
            <table className="min-w-full text-sm" data-testid="results-table">
              <thead>
                <tr className="bg-gray-50 dark:bg-gray-700">
                  {response.columns.map((c) => (
                    <th
                      key={c}
                      className="border-b border-gray-200 px-3 py-2 text-left font-medium dark:border-gray-600"
                    >
                      {c}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {response.rows.slice(0, 100).map((row, i) => (
                  <tr
                    key={i}
                    className="odd:bg-white even:bg-gray-50 dark:odd:bg-gray-800 dark:even:bg-gray-700"
                  >
                    {(row as unknown[]).map((cell, j) => (
                      <td
                        key={j}
                        className="border-b border-gray-100 px-3 py-1.5 dark:border-gray-700"
                      >
                        {String(cell ?? "")}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
            {response.rows.length > 100 && (
              <p className="px-3 py-1.5 text-xs text-gray-500">
                Showing 100 of {response.rows.length} rows.
              </p>
            )}
          </div>

          <button
            type="button"
            data-testid="toggle-sql"
            onClick={() => setShowSql((s) => !s)}
            className="mt-4 rounded-md border border-gray-300 px-3 py-1.5 text-xs font-medium dark:border-gray-600"
          >
            {showSql ? "Hide SQL" : "Show SQL"}
          </button>
          {showSql && (
            <pre
              data-testid="sql"
              className="mt-2 overflow-x-auto rounded-md bg-gray-900 p-3 text-xs text-gray-100"
            >
              <code>{response.sql}</code>
            </pre>
          )}
        </section>
      )}

      <aside
        data-testid="history-stub"
        aria-disabled="true"
        className="mt-8 rounded-md border border-dashed border-gray-300 p-4 text-sm text-gray-500 dark:border-gray-600 dark:text-gray-400"
      >
        <p className="font-medium">History (last 50) — coming in Phase 2</p>
        <p className="opacity-75">
          Past questions and answers will appear here once we wire the audit
          log into a list.
        </p>
      </aside>

      <aside
        aria-disabled="true"
        data-stub="charts"
        className="mt-3 rounded-md border border-dashed border-gray-300 p-4 text-sm text-gray-500 dark:border-gray-600 dark:text-gray-400"
      >
        <p className="font-medium">Charts — coming in Phase 2</p>
      </aside>
      <aside
        aria-disabled="true"
        data-stub="export"
        className="mt-3 rounded-md border border-dashed border-gray-300 p-4 text-sm text-gray-500 dark:border-gray-600 dark:text-gray-400"
      >
        <p className="font-medium">Export CSV — coming in Phase 2</p>
      </aside>
      <aside
        aria-disabled="true"
        data-stub="multi-db"
        className="mt-3 rounded-md border border-dashed border-gray-300 p-4 text-sm text-gray-500 dark:border-gray-600 dark:text-gray-400"
      >
        <p className="font-medium">Multi-DB switcher — coming in Phase 3</p>
      </aside>
      <aside
        aria-disabled="true"
        data-stub="followup"
        className="mt-3 rounded-md border border-dashed border-gray-300 p-4 text-sm text-gray-500 dark:border-gray-600 dark:text-gray-400"
      >
        <p className="font-medium">Follow-up chat — coming in Phase 3</p>
      </aside>
    </main>
  );
}
