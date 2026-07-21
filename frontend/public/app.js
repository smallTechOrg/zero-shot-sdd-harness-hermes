/* Phase 3 frontend: CSV upload + Q&A, live DB query, run history.
 Single-origin against the FastAPI backend at /app.
*/
"use strict";

const q = (id) => document.getElementById(id);
const $ = q;
const hide = (el) => { if (el) el.hidden = true; };
const show = (el) => { if (el) el.hidden = false; };
const setStatus = (el, text) => { if (!el) return; el.textContent = text; show(el); };
const clearStatus = (el) => { if (el) el.hidden = true; };
const setError = (el, text) => { if (!el) return; el.textContent = text; hide(el); show(el); };
const setOk = (el, text) => { if (!el) return; el.textContent = text; hide(el); show(el); };

async function loadHealth() {
 const badge = q("provider-badge");
 try {
  const res = await fetch("/health");
  const body = await res.json();
  const { provider, model, key_configured: keyed } = body.data;
  if (!keyed) {
   badge.textContent = `no API key — set one in .env`;
   badge.classList.add("stub");
  } else {
   badge.textContent = `${provider} · ${model}`;
  }
 } catch {
  badge.textContent = "backend unreachable";
  badge.classList.add("stub");
 }
}

function switchTab(name) {
 document.querySelectorAll(".tab").forEach((btn) => {
  const active = btn.dataset.tab === name;
  btn.classList.toggle("active", active);
  btn.setAttribute("aria-selected", active ? "true" : "false");
 });
 document.querySelectorAll(".panel").forEach((panel) => {
  panel.classList.toggle("hidden", panel.id !== `panel-${name}`);
 });
}

// CSV upload
async function uploadCSV(file) {
 const statusEl = q("csv-upload-status");
 const errorEl = q("csv-upload-error");
 const form = new FormData();
 form.append("file", file);
 setStatus(statusEl, "Uploading…");
 clearStatus(errorEl);
 try {
  const res = await fetch("/csv/upload", { method: "POST", body: form });
  if (!res.ok) {
   const body = await res.json();
   throw new Error(body?.detail?.message || `Upload failed (${res.status})`);
  }
  const body = await res.json();
  const data = body.data;
  setOk(statusEl, `Uploaded ${data.file_name} · ${data.row_count} rows · ${data.columns.length} columns`);
  return data;
 } catch (err) {
  setError(errorEl, err.message);
  return null;
 }
}

async function runCSVQuery(question, fileId) {
 const statusEl = q("csv-query-status");
 const errorEl = q("csv-query-error");
 clearStatus(statusEl);
 clearStatus(errorEl);
 show(statusEl);
 setStatus(statusEl, "Running…");
 try {
  const res = await fetch("/csv/query", {
   method: "POST",
   headers: { "content-type": "application/json" },
   body: JSON.stringify({ question, data_source: "csv", csv_file_ids: [fileId] }),
  });
  if (!res.ok) {
   const body = await res.json();
   throw new Error(body?.detail?.message || `Query failed (${res.status})`);
  }
  const body = await res.json();
  const data = body.data;
  if (data.status === "failed") {
   throw new Error(data.error || "Agent run failed.");
  }
  setOk(statusEl, "Done");
  q("csv-result").textContent = data.answer_text || "";
  q("csv-result-meta").textContent = `run ${data.run_id} · ${data.provider || "unknown"} · ${data.model || "unknown"}`;
  if (data.result_table && data.result_table.columns) {
   renderTable("csv-table", "csv-table-wrap", data.result_table);
  }
  if (data.run_id) {
   q("csv-download").href = `/csv/runs/${data.run_id}/download`;
  }
  show(q("csv-result-wrap"));
 } catch (err) {
  setError(errorEl, err.message);
 }
}

function renderTable(tableId, wrapId, resultTable) {
 const table = q(tableId);
 const wrap = q(wrapId);
 if (!table || !resultTable) return;
 const thead = table.querySelector("thead");
 const tbody = table.querySelector("tbody");
 thead.innerHTML = "";
 tbody.innerHTML = "";
 const header = document.createElement("tr");
 (resultTable.columns || []).forEach((col) => {
  const th = document.createElement("th");
  th.textContent = col;
  header.appendChild(th);
 });
 thead.appendChild(header);
 (resultTable.rows || []).forEach((row) => {
  const tr = document.createElement("tr");
  (resultTable.columns || []).forEach((col) => {
   const td = document.createElement("td");
   td.textContent = row[col] === null || row[col] === undefined ? "" : row[col];
   tr.appendChild(td);
  });
  tbody.appendChild(tr);
 });
 show(wrap);
}

function renderHistoryTable(rows) {
 const tbody = q("#history-table tbody");
 if (!tbody) return;
 tbody.innerHTML = "";
 rows.forEach((row) => {
  const tr = document.createElement("tr");
  const dataSource = row.data_source || "transform";
  tr.innerHTML = `
   <td>${row.run_id}</td>
   <td>${row.status}</td>
   <td>${dataSource}</td>
   <td>${row.created_at ? new Date(row.created_at).toLocaleString() : ""}</td>
   <td><a class="secondary" href="/app/#history">detail</a></td>
  `;
  tbody.appendChild(tr);
 });
}

async function loadHistory() {
 const statusEl = q("history-status");
 const errorEl = q("history-error");
 clearStatus(statusEl);
 clearStatus(errorEl);
 show(statusEl);
 setStatus(statusEl, "Loading…");
 try {
  const res = await fetch("/runs");
  if (!res.ok) throw new Error(`History failed (${res.status})`);
  const body = await res.json();
  renderHistoryTable(body.data || []);
  setOk(statusEl, "");
 } catch (err) {
  setError(errorEl, err.message);
 }
}

async function runLiveQuery(question, schemaSummary) {
 const statusEl = q("live-query-status");
 const errorEl = q("live-query-error");
 clearStatus(statusEl);
 clearStatus(errorEl);
 show(statusEl);
 setStatus(statusEl, "Running…");
 try {
  const res = await fetch("/live-db/query", {
   method: "POST",
   headers: { "content-type": "application/json" },
   body: JSON.stringify({ question, schema_summary: schemaSummary }),
  });
  if (!res.ok) {
   const body = await res.json();
   throw new Error(body?.detail?.message || `Live query failed (${res.status})`);
  }
  const body = await res.json();
  const data = body.data;
  if (data.status === "failed") {
   throw new Error(data.error || "Live query failed.");
  }
  setOk(statusEl, `Done in ${data.latency_ms ?? "?"} ms`);
  q("live-result").textContent = data.answer_text || "";
  q("live-result-meta").textContent = `run ${data.run_id} · ${data.provider || "unknown"} · served from cache: ${data.served_from_cache ? "yes" : "no"}`;
  if (data.run_id) {
   q("live-download").href = `/live-db/runs/${data.run_id}/download`;
  }
  if (data.result_table && data.result_table.columns) {
   renderTable("live-table", "live-table-wrap", data.result_table);
  }
  show(q("live-result-wrap"));
  } catch (err) {
  setError(errorEl, err.message);
  }
}

// Event wiring
q("csv-upload-form").addEventListener("submit", async (e) => {
 e.preventDefault();
 const file = q("csv-file").files[0];
 if (!file) return setError(q("csv-upload-error"), "Choose a CSV file first.");
 const data = await uploadCSV(file);
 if (data) q("csv-query-form").dataset.fileId = data.file_id;
});

q("csv-query-form").addEventListener("submit", async (e) => {
 e.preventDefault();
 const fileId = parseInt(q("csv-query-form").dataset.fileId || "0", 10);
 if (!fileId) return setError(q("csv-query-error"), "Upload a CSV first.");
 const question = q("csv-question").value.trim();
 if (!question) return setError(q("csv-query-error"), "Enter a question.");
 await runCSVQuery(question, fileId);
});

q("live-query-form").addEventListener("submit", async (e) => {
 e.preventDefault();
 const question = q("live-question").value.trim();
 const schema = q("live-schema").value.trim();
 if (!question || !schema) return setError(q("live-query-error"), "Question and schema summary are required.");
 await runLiveQuery(question, schema);
});

q("refresh-history").addEventListener("click", loadHistory);

document.querySelectorAll(".tab").forEach((btn) => {
 btn.addEventListener("click", () => switchTab(btn.dataset.tab));
});

loadHealth();
loadHistory();
