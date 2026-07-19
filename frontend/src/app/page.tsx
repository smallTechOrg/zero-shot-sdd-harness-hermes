"use client";

import { useEffect, useState } from "react";

type ApiRow = unknown[];

type ApiResponse = {
  data?: {
    run_id: string;
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

type HistoryItem = {
  id: string;
  question: string;
  sql: string;
  status: string;
  row_count: number;
  tokens_used: number;
  latency_ms: number;
  created_at: string;
};

type UsageDay = { day: string; tokens: number; questions: number };

function formatAnswer(payload: NonNullable<ApiResponse["data"]>): string {
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

function Sparkline({ days }: { days: UsageDay[] }) {
  if (days.length === 0) {
    return (
      <p
        data-testid="sparkline-empty"
        className="text-xs text-gray-500"
      >
        No activity yet.
      </p>
    );
  }
  const max = Math.max(1, ...days.map((d) => d.tokens));
  return (
    <div
      data-testid="sparkline"
      className="flex h-12 items-end gap-px"
      aria-label="tokens per day"
    >
      {days
        .slice()
        .reverse()
        .map((d) => (
          <div
            key={d.day}
            title={`${d.day} — ${d.tokens} tok (${d.questions} q)`}
            className="flex-1 rounded-sm bg-indigo-400/80 dark:bg-indigo-300/80"
            style={{ height: `${Math.max(2, (d.tokens / max) * 100)}%` }}
          />
        ))}
    </div>
  );
}

export default function Page() {
  const [question, setQuestion] = useState("How many tables are in master?");
  const [busy, setBusy] = useState(false);
  const [response, setResponse] = useState<ApiResponse["data"] | null>(null);
  const [showSql, setShowSql] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [usage, setUsage] = useState<{
    total_questions: number;
    total_tokens: number;
    total_rows_returned: number;
    last_questions: HistoryItem[];
  } | null>(null);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [historyTotal, setHistoryTotal] = useState(0);
  const [byDay, setByDay] = useState<UsageDay[]>([]);
  const [flaggedRows, setFlaggedRows] = useState<number[]>([]);

  async function refreshAll(extra?: { runId?: string }) {
    try {
      // Refresh usage totals + history list + per-day rollup in parallel.
      const [uRes, hRes, bRes] = await Promise.all([
        fetch("/api/usage").then((r) => r.json()),
        fetch("/api/history?limit=50&offset=0").then((r) => r.json()),
        fetch("/api/usage/by-day?days=14").then((r) => r.json()),
      ]);
      if (uRes?.data) setUsage(uRes.data);
      if (hRes?.data) {
        setHistory(hRes.data.rows || []);
        setHistoryTotal(hRes.data.total || 0);
      }
      if (bRes?.data) setByDay(bRes.data.days || []);
    } catch {
      /* Phase 2: convenience endpoints — ignore * */
    }
    if (extra?.runId) {
      try {
        const r = await fetch(
          `/api/ask/${extra.runId}/anomalies?threshold=2.0`,
        );
        const body = await r.json();
        if (body?.data) setFlaggedRows(body.data.flagged_rows || []);
      } catch {
        setFlaggedRows([]);
      }
    } else {
      setFlaggedRows([]);
    }
  }

  useEffect(() => {
    refreshAll();
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
      // After every Ask, check the resulting run for anomalies.
      // ``status === "completed"`` runs are scannable; failed runs return 404
      // from /anomalies which we treat as "no flagged rows".
      const runIdForAnomalies =
        body.data && body.data.status === "completed"
          ? body.data.run_id
          : undefined;
      await refreshAll({ runId: runIdForAnomalies });
    } catch (err) {
      setError(`network_error: ${(err as Error).message}`);
    } finally {
      setBusy(false);
    }
  }

  const flaggedSet = new Set(flaggedRows);

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
                {response.rows.slice(0, 100).map((row, i) => {
                  const isFlagged = flaggedSet.has(i);
                  return (
                    <tr
                      key={i}
                      data-testid={isFlagged ? "row-flagged" : "row"}
                      className={
                        isFlagged
                          ? "bg-red-50 even:bg-red-100 dark:bg-red-900/40 dark:even:bg-red-900/60"
                          : "odd:bg-white even:bg-gray-50 dark:odd:bg-gray-800 dark:even:bg-gray-700"
                      }
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
                  );
                })}
              </tbody>
            </table>
            {response.rows.length > 100 && (
              <p className="px-3 py-1.5 text-xs text-gray-500">
                Showing 100 of {response.rows.length} rows.
              </p>
            )}
          </div>

          {flaggedRows.length > 0 && (
            <p
              data-testid="anomaly-chip"
              className="mt-2 inline-block rounded bg-red-100 px-2 py-0.5 text-xs font-medium text-red-800 dark:bg-red-900/40 dark:text-red-100"
            >
              {flaggedRows.length} anomalous row
              {flaggedRows.length === 1 ? "" : "s"} highlighted
            </p>
          )}

          <button
            type="button"
            data-testid="toggle-sql"
            onClick={() => setShowSql((s) => !s)}
            className="mt-4 rounded-md border border-gray-300 px-3 py-1.5 text-xs font-medium dark:border-gray-600"
          >
            {showSql ? "Hide SQL" : "Show SQL"}
          </button>
          {response.status === "completed" && (
            <a
              data-testid="download-csv"
              href={`/api/ask/${response.run_id}/csv`}
              download={`mssql-${response.run_id}.csv`}
              className="ml-2 mt-4 inline-block rounded-md border border-gray-300 px-3 py-1.5 text-xs font-medium dark:border-gray-600"
            >
              Download CSV
            </a>
          )}
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

      {/* Phase-2: live history + sparkline */}
      <aside
        data-testid="phase2-history"
        aria-label="phase2-history"
        className="mt-8 rounded-md border border-gray-200 bg-white p-4 shadow dark:border-gray-700 dark:bg-gray-800"
      >
        <div className="mb-3 flex items-baseline justify-between">
          <h2 className="text-sm font-medium">History</h2>
          <span className="text-xs text-gray-500">
            {historyTotal} total
          </span>
        </div>
        <div className="mb-3">
          <p className="mb-1 text-xs uppercase tracking-wide text-gray-500">
            tokens / day
          </p>
          <Sparkline days={byDay} />
        </div>
        {history.length === 0 ? (
          <p
            data-testid="history-empty"
            className="text-xs text-gray-500"
          >
            No questions yet — ask one above.
          </p>
        ) : (
          <ul
            data-testid="history-list"
            className="divide-y divide-gray-100 dark:divide-gray-700"
          >
            {history.slice(0, 10).map((h) => (
              <li
                key={h.id}
                data-testid="history-item"
                className="flex items-baseline justify-between gap-2 py-2 text-xs"
              >
                <span className="flex-1 truncate" title={h.question}>
                  {h.question || "(blank)"}
                </span>
                <span className="font-mono text-gray-500">
                  {h.status === "completed" ? `✓ ${h.row_count} rows` : "—"}
                </span>
                <span className="font-mono text-gray-500">
                  {h.tokens_used} tok
                </span>
              </li>
            ))}
          </ul>
        )}
      </aside>

      {/* Phase-3 stubs left clearly labelled so the user knows what's pending. */}
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
