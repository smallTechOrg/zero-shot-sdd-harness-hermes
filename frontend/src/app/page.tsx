"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

type ApiRow = unknown[];

type ApiResponse = {
  data?: {
    answer: string;
    sql: string;
    columns: string[];
    rows: ApiRow[];
    latency_ms: number;
    row_count: number;
    sql_attempts: number;
    status: "completed" | "failed";
  };
  error?: { code: string; message: string } | null;
};

export default function Page() {
  const [question, setQuestion] = useState(
    "How many FIRs are registered in Lucknow district?"
  );
  const [busy, setBusy] = useState(false);
  const [response, setResponse] = useState<ApiResponse["data"] | null>(null);
  const [showSql, setShowSql] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onAsk(e?: React.FormEvent) {
    if (e) e.preventDefault();
    if (!question.trim()) return;
    setBusy(true);
    setError(null);
    setResponse(null);
    try {
      const r = await fetch("/v1/answer", {
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
          CCTNS Analyst
        </h1>
        <span
          className="rounded bg-gray-200 px-2 py-0.5 text-xs font-medium text-gray-700 dark:bg-gray-800 dark:text-gray-300"
          data-mirror-mode="mock"
        >
          mirror: mock
        </span>
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
        <div data-testid="loading" className="rounded-md bg-white p-4 shadow dark:bg-gray-800">
          <p className="text-sm text-gray-500">Step 2 of 4 … running against the mirror.</p>
        </div>
      )}

      {error && (
        <div data-testid="error" className="rounded-md bg-red-50 p-4 text-sm text-red-800 shadow dark:bg-red-900/40 dark:text-red-100">
          <p className="font-medium">{error}</p>
          <p className="mt-1 opacity-75">Try a shorter or more specific question.</p>
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
              {response.sql_attempts > 1 ? ` · ${response.sql_attempts} attempts` : ""}
            </span>
          </div>
          <div
            data-testid="answer"
            className="answer-markdown prose-sm mb-4"
          >
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{response.answer}</ReactMarkdown>
          </div>

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
                  <tr key={i} className="odd:bg-white even:bg-gray-50 dark:odd:bg-gray-800 dark:even:bg-gray-700">
                    {(row as unknown[]).map((cell, j) => (
                      <td
                        key={j}
                        className="border-b border-gray-100 px-3 py-1.5 dark:border-gray-700"
                      >
                        {String(cell)}
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

      {/* Phase 2/3 stubs — clearly labelled, never mistaken for bugs. */}
      <aside
        aria-disabled="true"
        data-stub="history"
        className="mt-8 rounded-md border border-dashed border-gray-300 p-4 text-sm text-gray-500 dark:border-gray-600 dark:text-gray-400"
      >
        <p className="font-medium">Conversation history — coming in Phase 2</p>
        <p className="opacity-75">Sidebar of past questions and answers.</p>
      </aside>

      <aside
        aria-disabled="true"
        data-stub="role"
        className="mt-3 rounded-md border border-dashed border-gray-300 p-4 text-sm text-gray-500 dark:border-gray-600 dark:text-gray-400"
      >
        <p className="font-medium">Multi-user / role filter — coming in Phase 2</p>
      </aside>

      <aside
        aria-disabled="true"
        data-stub="live"
        className="mt-3 rounded-md border border-dashed border-gray-300 p-4 text-sm text-gray-500 dark:border-gray-600 dark:text-gray-400"
      >
        <p className="font-medium">Switch to live CCTNS — coming in Phase 3</p>
      </aside>

      <aside
        aria-disabled="true"
        data-stub="followup"
        className="mt-3 rounded-md border border-dashed border-gray-300 p-4 text-sm text-gray-500 dark:border-gray-600 dark:text-gray-400"
      >
        <p className="font-medium">Follow-up input — coming in Phase 3</p>
      </aside>
    </main>
  );
}
