"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Staff from "./staff";

// ---- types mirror src/schemas.py (server is source of truth) ----
interface Exercise {
  id: string;
  drill_id?: string;
  type: string; // "note" | "rhythm"
  midi: number | null;
  correct_name: string;
  clef: string | null;
  label: string | null;
  is_rest: boolean | null;
  staff_svg: string;
  options: string[];
}
interface Teaching {
  text: string;
  tokens: { prompt: number; completion: number; total: number };
  model: string;
  used_fallback: boolean;
}
interface DashItem {
  item_id: string;
  weight: number;
  attempts: number;
  correct: number;
  box: number;
  streak: number;
  lapses: number;
}
interface DashTopic {
  id: string;
  label: string;
  type: string;
  items: DashItem[];
}
interface Suggest {
  topic_id: string | null;
  label: string | null;
  type: string | null;
  drill_type: string | null;
  reason: string | null;
  weak_item: string | null;
  avg_box: number | null;
  avg_weight: number | null;
}
interface Dashboard {
  topics: DashTopic[];
  suggest: Suggest;
}

const API = "/api"; // same origin (served by FastAPI at /app)

async function jpost<T>(url: string, body: unknown): Promise<T> {
  const r = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await r.json();
  if (!r.ok) throw new Error(data?.message || "request failed");
  return data.data as T;
}

async function jget<T>(url: string): Promise<T> {
  const r = await fetch(url);
  const data = await r.json();
  if (!r.ok) throw new Error(data?.message || "request failed");
  return data.data as T;
}

// Genuinely-later stubs (Phase 3+). Clearly non-functional, never a bug.
const STUBS = [
  "Chords drill",
  "Progressions / sight-reading",
  "Multi-student studio",
  "PDF / image export",
  "Animated full-piece playback",
];

// A topic mastery is the mean of per-item correctness ratios (0..1).
function topicMastery(t: DashTopic): number {
  if (!t.items.length) return 0;
  const sum = t.items.reduce(
    (a, it) => a + (it.attempts > 0 ? it.correct / it.attempts : 0),
    0
  );
  return sum / t.items.length;
}

export default function Page() {
  const [studentId] = useState("student-1");
  const [clefs, setClefs] = useState<string[]>(["treble"]);
  const [drillType, setDrillType] = useState<"note" | "rhythm">("note");
  const [drillId, setDrillId] = useState<string | null>(null);
  const [exercise, setExercise] = useState<Exercise | null>(null);
  const [teaching, setTeaching] = useState<Teaching | null>(null);
  const [status, setStatus] = useState<"idle" | "loading" | "ready">("idle");
  const [feedback, setFeedback] = useState<
    { kind: "correct" | "wrong"; msg: string } | null
  >(null);
  const [revealed, setRevealed] = useState<string | null>(null);
  const [playing, setPlaying] = useState(false);
  const [showReasoning, setShowReasoning] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dash, setDash] = useState<Dashboard | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const isRhythm = drillType === "rhythm";

  const loadDashboard = useCallback(async () => {
    try {
      const d = await jget<Dashboard>(
        `${API}/dashboard?student_id=${studentId}&clefs=${clefs.join(",")}`
      );
      setDash(d);
    } catch {
      /* dashboard is best-effort; don't block the drill */
    }
  }, [studentId, clefs]);

  useEffect(() => {
    loadDashboard();
  }, [loadDashboard]);

  const playNote = useCallback(async (noteId: string) => {
    if (!noteId) return;
    setPlaying(true);
    try {
      const r = await fetch(`${API}/notes/${noteId}/audio`);
      if (!r.ok) throw new Error("audio failed");
      const blob = await r.blob();
      const url = URL.createObjectURL(blob);
      const a = new Audio(url);
      audioRef.current = a;
      await a.play();
      a.onended = () => {
        setPlaying(false);
        URL.revokeObjectURL(url);
      };
    } catch {
      setPlaying(false);
      setError("Audio unavailable — check your browser sound.");
    }
  }, []);

  const speak = useCallback(async (noteId: string, text: string) => {
    try {
      const r = await fetch(
        `${API}/notes/${noteId}/speak?text=${encodeURIComponent(text)}`
      );
      if (r.status === 503) {
        setError("Speech unavailable (offline) — text shown instead.");
        return;
      }
      if (!r.ok) throw new Error();
      const blob = await r.blob();
      const url = URL.createObjectURL(blob);
      new Audio(url).play();
    } catch {
      setError("Speech unavailable — text shown instead.");
    }
  }, []);

  const startDrill = useCallback(async () => {
    setStatus("loading");
    setError(null);
    setFeedback(null);
    setRevealed(null);
    try {
      const data = await jpost<{
        drill_id: string;
        teaching: Teaching;
        exercise: Exercise;
      }>(`${API}/exercises/start`, {
        student_id: studentId,
        clefs,
        drill_type: drillType,
      });
      setDrillId(data.drill_id);
      setTeaching(data.teaching);
      setExercise(data.exercise);
      setStatus("ready");
      // note drills auto-play the sound; rhythm drills have no pitch audio
      if (data.exercise.type === "note")
        setTimeout(() => playNote(data.exercise.id), 250);
    } catch (e: any) {
      setError(e.message || "Failed to start drill");
      setStatus("idle");
    }
  }, [studentId, clefs, drillType, playNote]);

  const nextNote = useCallback(async () => {
    if (!drillId) return;
    setStatus("loading");
    setFeedback(null);
    setRevealed(null);
    try {
      const ex = await jpost<Exercise>(`${API}/notes/next`, {
        drill_id: drillId,
        student_id: studentId,
        drill_type: drillType,
      });
      setExercise(ex);
      setStatus("ready");
      if (ex.type === "note") setTimeout(() => playNote(ex.id), 200);
    } catch (e: any) {
      setError(e.message || "Failed to load next item");
      setStatus("ready");
    }
  }, [drillId, studentId, drillType, playNote]);

  const submit = useCallback(
    async (answer: string) => {
      if (!exercise) return;
      setFeedback(null);
      try {
        const res = await jpost<{
          correct: boolean;
          computed_name: string;
          hint: string | null;
          revealed: boolean;
        }>(`${API}/notes/${exercise.id}/check`, { student_answer: answer });
        if (res.correct) {
          setFeedback({
            kind: "correct",
            msg: `Correct! That's ${res.computed_name}.`,
          });
          speak(exercise.id, `Correct! That's ${res.computed_name}.`);
          loadDashboard();
          setTimeout(() => nextNote(), 1400);
        } else {
          setFeedback({
            kind: "wrong",
            msg: `Not quite — ${res.hint ?? "try again."}`,
          });
          if (res.hint) speak(exercise.id, res.hint);
          loadDashboard();
        }
      } catch (e: any) {
        setError(e.message || "Check failed");
      }
    },
    [exercise, speak, nextNote, loadDashboard]
  );

  const reveal = useCallback(
    async (name: string) => {
      setRevealed(name);
      speak(exercise!.id, `The answer is ${name}.`);
      setTimeout(() => nextNote(), 1600);
    },
    [exercise, speak, nextNote]
  );

  // When a drill is active, pre-load upcoming items via SSE (streaming).
  useEffect(() => {
    if (!drillId) return;
    const es = new EventSource(
      `${API}/notes/stream?drill_id=${drillId}&student_id=${studentId}`
    );
    es.onmessage = () => {
      /* pre-warmed; the next /next call returns one of these */
    };
    return () => es.close();
  }, [drillId, studentId]);

  const prompt = isRhythm ? "which duration is this?" : "which note is this?";

  return (
    <main className="mx-auto max-w-3xl px-4 py-8">
      <header className="mb-6">
        <h1 className="text-3xl font-bold text-slate-800">🎵 AI Music Tutor</h1>
        <p className="mt-1 text-slate-500">
          Learn to read staff notation — notes, rhythm, and your progress.
        </p>
      </header>

      {/* Suggested next topic (proactive) */}
      {dash?.suggest?.label && (
        <div className="mb-5 flex flex-wrap items-center gap-3 rounded-xl border border-indigo-200 bg-indigo-50 px-4 py-3">
          <span className="text-sm font-semibold text-indigo-800">
            Suggested next: {dash.suggest.label}
          </span>
          <span className="text-xs text-indigo-600">{dash.suggest.reason}</span>
          {dash.suggest.drill_type && (
            <button
              onClick={() => {
                setDrillType(dash.suggest!.drill_type === "rhythm" ? "rhythm" : "note");
              }}
              className="ml-auto rounded-md bg-indigo-600 px-3 py-1 text-xs font-semibold text-white hover:bg-indigo-700"
            >
              Practise this
            </button>
          )}
        </div>
      )}

      {/* Controls */}
      <div className="mb-6 flex flex-wrap items-center gap-3">
        {/* Drill type */}
        <div className="flex gap-2">
          {(["note", "rhythm"] as const).map((t) => (
            <button
              key={t}
              onClick={() => setDrillType(t)}
              className={`rounded-full px-4 py-1.5 text-sm font-medium transition ${
                drillType === t
                  ? "bg-indigo-600 text-white"
                  : "bg-slate-200 text-slate-600"
              }`}
            >
              {t === "note" ? "Note naming" : "Rhythm / duration"}
            </button>
          ))}
        </div>
        {/* Clefs (note drills only) */}
        {!isRhythm && (
          <div className="flex gap-2">
            {(["treble", "bass"] as const).map((c) => (
              <button
                key={c}
                onClick={() =>
                  setClefs((prev) =>
                    prev.includes(c)
                      ? prev.filter((x) => x !== c)
                      : [...prev, c]
                  )
                }
                className={`rounded-full px-4 py-1.5 text-sm font-medium transition ${
                  clefs.includes(c)
                    ? "bg-emerald-600 text-white"
                    : "bg-slate-200 text-slate-600"
                }`}
              >
                {c} clef
              </button>
            ))}
          </div>
        )}
        <button
          onClick={startDrill}
          disabled={status === "loading"}
          className="rounded-lg bg-slate-900 px-5 py-2 font-semibold text-white transition hover:bg-slate-700 disabled:opacity-50"
        >
          {status === "loading" ? "Starting…" : "Start drill"}
        </button>
        {exercise && exercise.type === "note" && (
          <button
            onClick={() => playNote(exercise.id)}
            className="rounded-lg border border-slate-300 px-4 py-2 font-medium text-slate-700 transition hover:bg-slate-100"
          >
            🔊 Play note
          </button>
        )}
      </div>

      {error && (
        <div className="mb-4 rounded-lg bg-amber-50 px-4 py-2 text-sm text-amber-800">
          {error}
        </div>
      )}

      {/* Primary drill surface */}
      {status === "idle" && !exercise && (
        <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-12 text-center text-slate-400">
          Pick a drill type, then click{" "}
          <span className="font-semibold text-slate-600">Start drill</span>.
          {isRhythm
            ? " A rhythm symbol will appear — name its duration."
            : " A note will appear on the staff and play its sound."}
        </div>
      )}

      {exercise && (
        <div className="grid gap-6 md:grid-cols-2">
          <section>
            <Staff svg={exercise.staff_svg} playing={playing} />
            <p className="mt-2 text-center text-sm text-slate-500">
              {isRhythm ? "rhythm" : `${exercise.clef} clef`} · {prompt}
            </p>

            {/* Answer buttons */}
            <div className="mt-4 grid grid-cols-3 gap-2">
              {exercise.options.map((opt) => (
                <button
                  key={opt}
                  onClick={() => submit(opt)}
                  disabled={!!revealed}
                  className="rounded-lg border border-slate-300 bg-white px-3 py-3 text-sm font-semibold text-slate-800 transition hover:border-emerald-500 hover:bg-emerald-50 disabled:opacity-50"
                >
                  {opt}
                </button>
              ))}
            </div>

            {/* Feedback */}
            {feedback && (
              <div
                className={`mt-4 rounded-lg px-4 py-3 text-sm font-medium ${
                  feedback.kind === "correct"
                    ? "bg-emerald-100 text-emerald-800"
                    : "bg-amber-100 text-amber-800"
                }`}
              >
                {feedback.msg}
                {feedback.kind === "wrong" && !revealed && (
                  <div className="mt-2 flex gap-2">
                    <button
                      onClick={() => reveal(exercise.correct_name)}
                      className="rounded-md bg-amber-700 px-3 py-1 text-xs font-semibold text-white hover:bg-amber-800"
                    >
                      Reveal answer
                    </button>
                    <button
                      onClick={() => {
                        setFeedback(null);
                        if (exercise.type === "note") playNote(exercise.id);
                      }}
                      className="rounded-md border border-amber-700 px-3 py-1 text-xs font-semibold text-amber-700 hover:bg-amber-50"
                    >
                      Try again
                    </button>
                  </div>
                )}
              </div>
            )}
          </section>

          {/* Reasoning + tokens panel */}
          <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
            <button
              onClick={() => setShowReasoning((s) => !s)}
              className="mb-2 flex w-full items-center justify-between text-left text-sm font-semibold text-slate-700"
            >
              <span>Reasoning &amp; tokens</span>
              <span className="text-slate-400">{showReasoning ? "▾" : "▸"}</span>
            </button>
            {showReasoning && teaching && (
              <div className="space-y-2 text-sm">
                <p className="text-slate-600">{teaching.text}</p>
                <div className="flex flex-wrap gap-2 text-xs">
                  <span className="rounded bg-slate-100 px-2 py-1 text-slate-600">
                    model: {teaching.model}
                  </span>
                  <span className="rounded bg-slate-100 px-2 py-1 text-slate-600">
                    prompt: {teaching.tokens.prompt}
                  </span>
                  <span className="rounded bg-slate-100 px-2 py-1 text-slate-600">
                    completion: {teaching.tokens.completion}
                  </span>
                  <span className="rounded bg-slate-100 px-2 py-1 text-slate-600">
                    total: {teaching.tokens.total}
                  </span>
                  {teaching.used_fallback && (
                    <span className="rounded bg-amber-100 px-2 py-1 text-amber-700">
                      offline fallback
                    </span>
                  )}
                </div>
                <p className="text-xs text-slate-400">
                  One Gemini call per drill set (teaching only). The correct
                  answer is computed, never guessed by the model.
                </p>
              </div>
            )}
          </section>
        </div>
      )}

      {/* Per-topic progress dashboard (spaced-repetition state) */}
      {dash && dash.topics.length > 0 && (
        <section className="mt-10">
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">
            Your progress
          </h2>
          <div className="space-y-3">
            {dash.topics.map((t) => {
              const pct = Math.round(topicMastery(t) * 100);
              const attempts = t.items.reduce((a, it) => a + it.attempts, 0);
              const avgBox =
                t.items.reduce((a, it) => a + it.box, 0) /
                Math.max(1, t.items.length);
              return (
                <div
                  key={t.id}
                  className="rounded-xl border border-slate-200 bg-white p-3"
                >
                  <div className="mb-1 flex items-center justify-between text-sm">
                    <span className="font-medium text-slate-700">
                      {t.label}
                    </span>
                    <span className="text-xs text-slate-400">
                      {attempts} attempts · box {avgBox.toFixed(1)}
                    </span>
                  </div>
                  <div className="h-2.5 w-full overflow-hidden rounded-full bg-slate-100">
                    <div
                      className={`h-full rounded-full transition-all ${
                        pct >= 80
                          ? "bg-emerald-500"
                          : pct >= 40
                          ? "bg-indigo-500"
                          : "bg-amber-400"
                      }`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                  <div className="mt-1 text-right text-xs text-slate-400">
                    {pct}% mastered
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      )}

      {/* Genuinely-later stubs — clearly non-functional, never a bug */}
      <section className="mt-10">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-400">
          Coming soon (later phases)
        </h2>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          {STUBS.map((s) => (
            <div
              key={s}
              className="rounded-lg border border-dashed border-slate-200 bg-slate-50 px-3 py-4 text-center text-sm text-slate-400"
              title="Planned for a later phase"
            >
              {s}
              <div className="mt-1 text-xs text-slate-300">coming soon</div>
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}
