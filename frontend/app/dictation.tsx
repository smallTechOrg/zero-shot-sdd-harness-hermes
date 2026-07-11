"use client";

// Dictation (writing notation) UI — melody + rhythm.
// The student REPRODUCES a played phrase: for melody, set pitch + duration per
// step; for rhythm, set duration per step. Correctness is computed server-side.

interface StepMeta {
  duration_label: string;
  is_rest: boolean;
}

interface DictationProps {
  mode: "melody" | "rhythm";
  steps: number;
  stepsMeta: StepMeta[];
  bpm: number;
  // current student input: melody -> {name, duration}; rhythm -> {duration}
  value: DictStep[];
  result:
    | {
        correct: boolean;
        first_wrong_step: number | null;
        total_steps: number;
        details: { name_ok?: boolean; duration_ok: boolean; expected: any }[];
      }
    | null;
  onChange: (i: number, patch: Partial<DictStep>) => void;
  onSubmit: () => void;
  onReveal: () => void;
}

export interface DictStep {
  name?: string;
  duration: string;
}

const DURATIONS = ["whole", "half", "quarter", "eighth", "sixteenth"];
// Note-name options for the treble/bass pitch picker ( naturals only, like the tutor ).
const NOTE_NAMES = [
  "C4", "D4", "E4", "F4", "G4", "A4", "B4",
  "C5", "D5", "E5", "F5", "G5", "A5", "B5",
  "C3", "D3", "E3", "F3", "G3", "A3", "B3",
];

export default function Dictation({
  mode,
  steps,
  bpm,
  value,
  result,
  onChange,
  onSubmit,
  onReveal,
}: DictationProps) {
  return (
    <div className="mt-4 space-y-4">
      <div className="flex items-center justify-between text-xs text-slate-500">
        <span>
          {mode === "melody"
            ? "Write the melody — pick the note + duration for each step."
            : "Write the rhythm — pick the duration for each step."}
        </span>
        <span>♩ = {bpm} BPM</span>
      </div>

      <div className="space-y-2">
        {Array.from({ length: steps }).map((_, i) => {
          const wrong = result && !result.correct && result.first_wrong_step === i;
          const stepOk =
            result && result.correct
              ? true
              : result && result.details[i]?.duration_ok &&
                (mode === "rhythm" || result.details[i]?.name_ok);
          return (
            <div
              key={i}
              className={`flex flex-wrap items-center gap-2 rounded-lg border px-3 py-2 ${
                wrong
                  ? "border-amber-400 bg-amber-50"
                  : stepOk
                  ? "border-emerald-300 bg-emerald-50"
                  : "border-slate-200 bg-white"
              }`}
            >
              <span className="w-12 text-xs font-semibold text-slate-500">
                step {i + 1}
              </span>
              {mode === "melody" && (
                <select
                  value={value[i]?.name ?? ""}
                  onChange={(e) => onChange(i, { name: e.target.value })}
                  className="rounded-md border border-slate-300 px-2 py-1 text-sm"
                >
                  <option value="">note…</option>
                  {NOTE_NAMES.map((n) => (
                    <option key={n} value={n}>
                      {n}
                    </option>
                  ))}
                </select>
              )}
              <select
                value={value[i]?.duration ?? ""}
                onChange={(e) => onChange(i, { duration: e.target.value })}
                className="rounded-md border border-slate-300 px-2 py-1 text-sm"
              >
                <option value="">duration…</option>
                {DURATIONS.map((d) => (
                  <option key={d} value={d}>
                    {d}
                  </option>
                ))}
              </select>
              {result && !result.correct && result.details[i] && (
                <span className="text-xs text-amber-700">
                  expected:{" "}
                  {mode === "melody"
                    ? `${result.details[i].expected?.[0]} (${result.details[i].expected?.[1]})`
                    : `${result.details[i].expected}`}
                </span>
              )}
            </div>
          );
        })}
      </div>

      <div className="flex gap-2">
        <button
          onClick={onSubmit}
          className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-700"
        >
          Submit transcription
        </button>
        <button
          onClick={onReveal}
          className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100"
        >
          Reveal answer
        </button>
      </div>

      {result?.correct && (
        <div className="rounded-lg bg-emerald-100 px-4 py-2 text-sm font-medium text-emerald-800">
          Correct! You notated the whole {mode === "melody" ? "melody" : "rhythm"}.
        </div>
      )}
    </div>
  );
}
