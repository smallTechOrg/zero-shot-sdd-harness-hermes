// Zero-build baseline frontend. Single-origin: the page is served by the
// backend at /app, so API calls are same-origin relative paths.

"use strict";

const $ = (id) => document.getElementById(id);

let sessionId = null;

// Load health badge
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

// Create a session and return its ID
async function createSession() {
  const res = await fetch("/sessions", { method: "POST" });
  if (!res.ok) throw new Error(`Failed to create session: ${res.status}`);
  const data = await res.json();
  return data.data.id;
}

// Upload CSV files to the session
async function uploadCsvs(sessionId, files) {
  const form = new FormData();
  for (const file of files) {
    form.append("files", file); // Note: changed from "file" to "files" to match backend
  }
  const res = await fetch(`/sessions/${sessionId}/csv`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) throw new Error(`Failed to upload CSV: ${res.status}`);
  return await res.json();
}

// Run the agent with a question and session ID
async function runAnalysis(sessionId, question) {
  const res = await fetch("/runs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, question }),
  });
  if (!res.ok) throw new Error(`Failed to run analysis: ${res.status}`);
  return await res.json();
}

// Display the plan in the UI
function displayPlan(planText) {
  $("plan").textContent = planText || "(no plan)";
}

// Display the generated SQL/code
function displayGeneratedCode(codeText) {
  $("generated-code").textContent = codeText || "(no code)";
}

// Display the results in a table
function displayResults(rows) {
  const table = $("result-table");
  const thead = table.tHead || table.createTHead();
  const tbody = table.tBody || table.createTBody();

  // Clear existing content
  thead.innerHTML = "";
  tbody.innerHTML = "";

  if (!rows || rows.length === 0) {
    tbody.innerHTML = "<tr><td colspan='1'>No data</td></tr>";
    return;
  }

  // Create header from the keys of the first row
  const headers = Object.keys(rows[0]);
  const headerRow = thead.insertRow();
  headers.forEach((header) => {
    const th = document.createElement("th");
    th.textContent = header;
    headerRow.appendChild(th);
  });

  // Create rows
  rows.forEach((row) => {
    const tr = tbody.insertRow();
    headers.forEach((key) => {
      const td = tr.insertCell();
      td.textContent = row[key] !== null && row[key] !== undefined ? row[key] : "";
    });
  });
}

// Update KPIs (placeholder implementation)
function updateKpis(rows) {
  // For simplicity, we'll show row count and placeholder for other KPIs
  $("kpi-rows").textContent = rows ? rows.length : 0;
  // In a real app, we would compute date range and distinct columns from the schema
  $("kpi-date-range").textContent = "N/A";
  $("kpi-categories").textContent = "N/A";
}

// Update chart placeholders (placeholder implementation)
function updateCharts() {
  $("chart-bar").textContent = "[chart]";
  $("chart-line").textContent = "[chart]";
  $("chart-pie").textContent = "[chart]";
}

// Main function to handle the Analyze button click
async function runAnalysisClicked() {
  const btn = $("run-btn");
  const status = $("status");
  const errorBox = $("error");
  const wrap = $("result-wrap");

  // Get files and question
  const fileInput = $("csv-files");
  const questionInput = $("question");
  const files = fileInput.files;
  const question = questionInput.value.trim();

  // Basic validation
  if (files.length === 0) {
    errorBox.textContent = "Please select at least one CSV file.";
    errorBox.hidden = false;
    return;
  }
  if (!question) {
    errorBox.textContent = "Please enter a question.";
    errorBox.hidden = false;
    return;
  }

  // Disable UI and clear previous results
  btn.disabled = true;
  status.textContent = "Analyzing...";
  status.hidden = false;
  errorBox.hidden = true;
  wrap.hidden = true;

  try {
    // Step 1: Create or reuse session
    if (!sessionId) {
      sessionId = await createSession();
    }

    // Step 2: Upload CSV files
    await uploadCsvs(sessionId, files);

    // Step 3: Run analysis
    const response = await runAnalysis(sessionId, question);
    const data = response.data;

    if (data.status === "failed") {
      throw new Error(data.error_message || "Analysis failed");
    }

    // Step 4: Update UI with results
    displayPlan(data.plan_text || "");
    displayGeneratedCode(data.generated_code || "");

    // For simplicity, we assume the result is in the output_text as a string.
    // In a real implementation, we would parse the structured result from the agent.
    // Here, we'll just show the output_text as a placeholder for the results.
    // We'll also try to parse a JSON array from the output_text for the table.
    let rows = [];
    try {
      // Try to parse the output_text as JSON (if it's a JSON array)
      const parsed = JSON.parse(data.output_text);
      if (Array.isArray(parsed)) {
        rows = parsed;
      }
    } catch (e) {
      // If not JSON, we'll just show the output_text in a single cell table
      rows = [{ output: data.output_text }];
    }

    displayResults(rows);
    updateKpis(rows);
    updateCharts();

    // Show the results wrapper
    wrap.hidden = false;
  } catch (err) {
    errorBox.textContent = err.message;
    errorBox.hidden = false;
  } finally {
    btn.disabled = false;
    status.hidden = true;
  }
}

// Event listeners
document.addEventListener("DOMContentLoaded", () => {
  loadHealth();
  $("run-btn").addEventListener("click", runAnalysisClicked);
});