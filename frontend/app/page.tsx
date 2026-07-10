"use client";

import { useEffect, useRef, useState } from "react";

type Host = { id: string; name: string; persona: string; voice: string };

const API = ""; // same-origin via next rewrites -> /api/...

export default function Home() {
  const [topic, setTopic] = useState("future of remote work");
  const [cast, setCast] = useState<Host[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [status, setStatus] = useState<"idle" | "generating" | "done" | "error">("idle");
  const [error, setError] = useState<string>("");
  const [downloadUrl, setDownloadUrl] = useState<string>("");
  const [chunkCount, setChunkCount] = useState<number>(0); // bumps on each new audio chunk
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const chunksRef = useRef<Uint8Array[]>([]);

  useEffect(() => {
    fetch(`${API}/api/podcast/cast`)
      .then((r) => r.json())
      .then((d) => setCast(d.cast))
      .catch(() => setError("Could not load host cast from backend."));
  }, []);

  function toggleHost(id: string) {
    setSelected((prev) => {
      if (prev.includes(id)) return prev.filter((x) => x !== id);
      if (prev.length >= 3) return prev; // max 3
      return [...prev, id];
    });
  }

  async function generate() {
    setError("");
    setDownloadUrl("");
    chunksRef.current = [];
    setChunkCount(0);
    if (!topic.trim()) return setError("Enter a topic first.");
    if (selected.length < 2) return setError("Select at least 2 hosts.");

    setStatus("generating");
    try {
      const res = await fetch(`${API}/api/podcast/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic, hosts: selected }),
      });
      if (!res.ok) {
        const e = await res.json().catch(() => ({}));
        throw new Error(e.detail || `generate failed (${res.status})`);
      }
      const { session_id } = await res.json();
      await consumeStream(session_id);
    } catch (e: any) {
      setStatus("error");
      setError(e.message || "Generation failed.");
    }
  }

  async function consumeStream(sessionId: string) {
    const res = await fetch(`${API}/api/podcast/stream/${sessionId}`);
    if (!res.ok || !res.body) {
      throw new Error(`stream failed (${res.status})`);
    }
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buf = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      // SSE frames are separated by a blank line.
      const frames = buf.split("\n\n");
      buf = frames.pop() || "";
      for (const frame of frames) {
        const ev = parseFrame(frame);
        if (!ev) continue;
        if (ev.event === "audio") {
          chunksRef.current.push(base64ToBytes(ev.data));
          setChunkCount((c) => c + 1); // trigger live-blob rebuild
        } else if (ev.event === "done") {
          finalize(sessionId);
        } else if (ev.event === "error") {
          setStatus("error");
          setError(ev.data || "Stream error.");
        }
      }
    }
    // If stream ended without explicit done (e.g. connection close after last chunk)
    if (status === "generating") finalize(sessionId);
  }

  function finalize(sessionId: string) {
    setStatus("done");
    setDownloadUrl(`${API}/api/podcast/download/${sessionId}`);
  }

  // Rebuild the live audio blob whenever new chunks arrive, so the <audio>
  // element keeps extending instead of freezing on the first chunk.
  useEffect(() => {
    if (chunksRef.current.length === 0 || !audioRef.current) return;
    const blob = new Blob(chunksRef.current, { type: "audio/mpeg" });
    const url = URL.createObjectURL(blob);
    audioRef.current.src = url;
    audioRef.current.play().catch(() => {}); // autoplay as it grows
    return () => URL.revokeObjectURL(url);
  }, [chunkCount]);

  return (
    <main style={{ maxWidth: 720, margin: "40px auto", padding: "0 16px" }}>
      <h1 style={{ fontSize: 28 }}>🎙️ Auto-Podcaster</h1>
      <p style={{ color: "#9aa" }}>Type a topic, pick 2–3 hosts, and hear a real-time AI podcast.</p>

      <label style={{ display: "block", marginTop: 16, fontWeight: 600 }}>Topic</label>
      <input
        value={topic}
        onChange={(e) => setTopic(e.target.value)}
        placeholder="e.g. future of remote work"
        style={inputStyle}
      />

      <label style={{ display: "block", marginTop: 16, fontWeight: 600 }}>Hosts (pick 2–3)</label>
      <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginTop: 8 }}>
        {cast.map((h) => {
          const on = selected.includes(h.id);
          return (
            <button
              key={h.id}
              onClick={() => toggleHost(h.id)}
              style={{
                ...cardStyle,
                borderColor: on ? "#5b8cff" : "#333",
                background: on ? "#1a2233" : "#16181d",
              }}
            >
              <strong>{h.name}</strong>
              <div style={{ fontSize: 12, color: "#9aa", marginTop: 4 }}>{h.persona}</div>
            </button>
          );
        })}
      </div>

      <div style={{ marginTop: 20 }}>
        <button onClick={generate} disabled={status === "generating"} style={btnStyle}>
          {status === "generating" ? "Generating…" : "Generate"}
        </button>
      </div>

      <div style={{ marginTop: 12, color: status === "error" ? "#ff7676" : "#9aa", minHeight: 20 }}>
        {status === "generating" && "Streaming live audio…"}
        {status === "done" && "Done! Listen above or download."}
        {error}
      </div>

      {(chunkCount > 0) && (
        <audio ref={audioRef} controls autoPlay style={{ width: "100%", marginTop: 16 }} />
      )}

      {status === "done" && downloadUrl && (
        <a href={downloadUrl} download style={{ display: "inline-block", marginTop: 12, color: "#5b8cff" }}>
          ⬇ Download episode (mp3)
        </a>
      )}

      <div style={{ marginTop: 32, padding: 16, border: "1px dashed #444", borderRadius: 8, color: "#777" }}>
        <em>Transcript — coming in Phase 2 (stub).</em>
      </div>
    </main>
  );
}

// ---- helpers ----
function parseFrame(frame: string): { event: string; data: string } | null {
  const lines = frame.split("\n");
  let event = "message";
  const dataLines: string[] = [];
  for (const line of lines) {
    if (line.startsWith("event:")) event = line.slice(6).trim();
    else if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
  }
  if (dataLines.length === 0) return null;
  return { event, data: dataLines.join("\n") };
}

function base64ToBytes(b64: string): Uint8Array {
  const bin = atob(b64);
  const arr = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i);
  return arr;
}

const inputStyle: React.CSSProperties = {
  width: "100%", padding: "10px 12px", marginTop: 6, borderRadius: 8,
  border: "1px solid #333", background: "#16181d", color: "#e8e8e8", fontSize: 15,
};
const cardStyle: React.CSSProperties = {
  flex: "1 1 180px", textAlign: "left", padding: "12px 14px", borderRadius: 10,
  border: "1px solid #333", cursor: "pointer", color: "#e8e8e8",
};
const btnStyle: React.CSSProperties = {
  padding: "10px 22px", borderRadius: 8, border: "none", background: "#5b8cff",
  color: "#fff", fontSize: 15, fontWeight: 600, cursor: "pointer",
};
