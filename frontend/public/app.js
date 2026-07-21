// Zero-build frontend for the UP Police Data Analyst.
"use strict";

const $ = (id) => document.getElementById(id);

async function loadHealth() {
  const badge = $("provider-badge");
  try {
    const res = await fetch("/health");
    const body = await res.json();
    const { provider, model, key_configured: keyed } = body.data;
    if (!keyed) {
      badge.textContent = "no API key — set one in .env";
      badge.classList.add("stub");
    } else {
      badge.textContent = `${provider} · ${model}`;
    }
  } catch {
    badge.textContent = "backend unreachable";
    badge.classList.add("stub");
  }
}

async function ingest() {
  const btn = $("ingest-btn");
  const status = $("ingest-status");
  const wrap = $("schema-wrap");
  const text = $("schema-text");
  const input = $("file-input");
  const files = input.files;

  if (!files || !files.length) {
    status.textContent = "Select at least one CSV file first.";
    status.hidden = false;
    return;
  }

  const form = new FormData();
  for (const f of files) form.append("files", f);

  btn.disabled = true;
  status.textContent = "Ingesting...";
  status.hidden = false;

  try {
    const res = await fetch("/api/v1/ingest", { method: "POST", body: form });
    const body = await res.json();
    if (!res.ok) throw new Error(body?.detail?.message || `HTTP ${res.status}`);
    const data = body.data;
    text.textContent = data.schema_markdown || "(no tables)";
    wrap.hidden = false;
    status.textContent = `Ingested ${data.tables.length} table(s). Session: ${data.session_id}`;
  } catch (err) {
    status.textContent = err.message;
  } finally {
    btn.disabled = false;
  }
}

function renderTable(columns, rows) {
  const table = $("result-table");
  if (!columns.length) { table.innerHTML = ""; return; }
  const thead = "<tr>" + columns.map((c) => `<th>${c}</th>`).join("") + "</tr>";
  const tbody = rows
    .map((r) => "<tr>" + r.map((v) => `<td>${v == null ? "" : v}</td>`).join("") + "</tr>")
    .join("");
  table.innerHTML = thead + tbody;
}

async function runQuestion() {
  const btn = $("run-btn");
  const status = $("status");
  const errBox = $("error");
  const wrap = $("result-wrap");
  const question = $("question").value.trim();

  errBox.hidden = true;
  wrap.hidden = true;

  if (!question) {
    errBox.textContent = "Type a question first.";
    errBox.hidden = false;
    return;
  }

  btn.disabled = true;
  status.textContent = "Running… Planning → executing → finalizing";
  status.hidden = false;

  const start = performance.now();
  try {
    const res = await fetch("/api/v1/query", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ session_id: "sess1", question, data_source: "cache" }),
    });
    const body = await res.json();
    if (!res.ok) throw new Error(body?.detail?.message || `HTTP ${res.status}`);
    const queued = body.data;
    const elapsed = Math.max(0, Math.round((performance.now() - start) / 1000));
    status.textContent = `Queued as ${queued.run_id} (${elapsed}s) — polling`;

    const answer = await pollRun(queued.run_id, status);
    let parsed = {};
    if (typeof answer.output_text === "string") {
      try { parsed = JSON.parse(answer.output_text); } catch { parsed = {}; }
    } else {
      parsed = answer.output_text || {};
    }

    $("answer").innerHTML = `<p>${parsed.answer || "(no answer)"}</p>`;
    if (parsed.sql) $("sql").textContent = parsed.sql;

    if (Array.isArray(parsed.suggestions) && parsed.suggestions.length) {
      const chips = $("suggestions");
      chips.innerHTML = parsed.suggestions.map((s) => `<button class="chip">${s}</button>`).join("");
      chips.querySelectorAll(".chip").forEach((btn, i) => {
        btn.addEventListener("click", () => {
          $("question").value = parsed.suggestions[i];
          runQuestion();
        });
      });
    }

    const latencyMs = typeof parsed.latency_ms === "number" ? parsed.latency_ms : null;
    if (latencyMs != null) $("latency-badge").textContent = `${latencyMs} ms`;
    $("source-badge").textContent = parsed.source || "cache";

    const cols = Array.isArray(parsed.table?.columns) ? parsed.table.columns : [];
    const rows = Array.isArray(parsed.table?.rows) ? parsed.table.rows : [];
    if (cols.length) {
      $("table-wrap").hidden = false;
      renderTable(cols, rows);
    } else {
      $("table-wrap").hidden = true;
    }

    if (parsed.chart) {
      $("chart-wrap").hidden = false;
      Plotly.newPlot(
        "chart",
        parsed.chart.data || [],
        parsed.chart.layout || {},
        { displayModeBar: false, responsive: true }
      );
    } else {
      $("chart-wrap").hidden = true;
    }

    wrap.hidden = false;
  } catch (err) {
    errBox.textContent = err.message;
    errBox.hidden = false;
    status.hidden = true;
  } finally {
    btn.disabled = false;
    status.hidden = true;
  }
}

async function pollRun(runId, statusEl) {
  for (let i = 0; i < 40; i++) {
    await new Promise((r) => setTimeout(r, 500));
    const res = await fetch(`/runs/${runId}`);
    const body = await res.json();
    const run = body.data;
    if (run.status === "completed" || run.status === "failed") return run;
    if (statusEl) statusEl.textContent = `Polling... (${(i + 1) * 0.5}s)`;
  }
  throw new Error("Timed out waiting for run.");
}

$("ingest-btn").addEventListener("click", ingest);
$("run-btn").addEventListener("click", runQuestion);
loadHealth();
