// CrimAnalyze frontend — multi-file CSV upload + officer question.
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

async function runAnalyze() {
  const btn = $("run-btn");
  const status = $("status");
  const errBox = $("error");
  const wrap = $("result-wrap");

  const files = ($("files").files || []);
  const instruction = $("instruction").value.trim();

  errBox.hidden = true;
  wrap.hidden = true;

  if (!files.length) {
    errBox.textContent = "Upload at least one CSV file.";
    errBox.hidden = false;
    return;
  }
  if (!instruction) {
    errBox.textContent = "Type an investigator question first.";
    errBox.hidden = false;
    return;
  }
  if (files.length > 12) {
    errBox.textContent = "You can upload at most 12 files in one run.";
    errBox.hidden = false;
    return;
  }

  btn.disabled = true;
  status.textContent = `Analyzing ${files.length} file(s)... (one real LLM call)`;
  status.hidden = false;

  try {
    const form = new FormData();
    form.append("instruction", instruction);
    for (const file of files) {
      form.append("files", file, file.name || "data.csv");
    }

    const res = await fetch("/runs", {
      method: "POST",
      body: form,
    });
    const body = await res.json();

    if (!res.ok) {
      const msg = body?.detail?.message || `HTTP ${res.status}`;
      throw new Error(msg);
    }
    const run = body.data;
    if (run.status === "failed") {
      throw new Error(run.error_message || "The agent run failed.");
    }
    $("result").textContent = run.output_text || "";
    $("result-meta").textContent =
      `run ${run.run_id} · ${run.provider} · ${run.model} · ${run.file_count} file(s)`;
    wrap.hidden = false;
  } catch (err) {
    errBox.textContent = err.message;
    errBox.hidden = false;
  } finally {
    btn.disabled = false;
    status.hidden = true;
  }
}

$("run-btn").addEventListener("click", runAnalyze);
loadHealth();
