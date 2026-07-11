"use client";

interface StepVerdict {
  name_ok: boolean;
  duration_ok: boolean;
  expected: [string, string];
}

interface PhraseTranscriptionProps {
  steps: number;
  transcription: { name: string; duration: string }[];
  result: {
    correct: boolean;
    first_wrong_step: number | null;
    total_steps: number;
    details: StepVerdict[];
  } | null;
  onChange: (i: number, field: "name" | "duration", value: string) => void;
  onSubmit: () => void;
  correctName: string;
  onReveal: () => void;
}

// Note-name options for the transcription dropdowns (treble + bass naturals,
// plus "rest" for rest steps). Mirrors src.music.theory ranges.
const NATURAL_NOTES = [
  "G2", "A2", "B2", "C3", "D3", "E3", "F3", "G3", "A3", "B3",
  "C4", "D4", "E4", "F4", "G4", "A4", "B4", "C5", "D5", "E5", "F5", "G5",
];

const DURATIONS = ["whole", "half", "quarter", "eighth", "sixteenth"];

const NAMES = [...NATURAL_NOTES, "rest"];

export default function PhraseTranscription({
  steps,
  transcription,
  result,
  onChange,
  onSubmit,
  onReveal,
}: PhraseTranscriptionProps) {
  const n = Math.max(1, steps);
  return (
    <div className="mt-4 space-y-3">
      <p className="text-sm text-slate-500">
        For each step, pick the note name (or “rest”) and its duration.
      </p>
      {Array.from({ length: n }, (_, i) => {
        const verdict = result?.details?.[i];
        const wrong = verdict && !(verdict.name_ok && verdict.duration_ok);
        return (
          <div
            key={i}
            className={`flex flex-wrap items-center gap-2 rounded-lg border p-3 ${
              wrong ? "border-amber-400 bg-amber-50" : "border-slate-200 bg-white"
            }`}
          >
            <span className="w-16 text-sm font-semibold text-slate-600">
              Step {i + 1}
            </span>
            <select
              value={transcription[i]?.name ?? ""}
              onChange={(e) => onChange(i, "name", e.target.value)}
              className="rounded-md border border-slate-300 bg-white px-2 py-2 text-sm text-slate-800"
              aria-label={`step ${i + 1} note name`}
            >
              <option value="">note…</option>
              {NAMES.map((nm) => (
                <option key={nm} value={nm}>
                  {nm}
                </option>
              ))}
            </select>
            <select
              value={transcription[i]?.duration ?? ""}
              onChange={(e) => onChange(i, "duration", e.target.value)}
              className="rounded-md border border-slate-300 bg-white px-2 py-2 text-sm text-slate-800"
              aria-label={`step ${i + 1} duration`}
            >
              <option value="">duration…</option>
              {DURATIONS.map((d) => (
                <option key={d} value={d}>
                  {d}
                </option>
              ))}
            </select>
            {wrong && verdict && (
              <span className="text-xs text-amber-700">
                expected {verdict.expected[0]} · {verdict.expected[1]}
              </span>
            )}
          </div>
        );
      })}
      <div className="flex flex-wrap gap-2">
        <button
          onClick={onSubmit}
          className="rounded-lg bg-emerald-600 px-4 py-2 font-semibold text-white transition hover:bg-emerald-700"
        >
          Submit transcription
        </button>
        <button
          onClick={onReveal}
          className="rounded-md border border-amber-700 px-3 py-1 text-xs font-semibold text-amber-700 hover:bg-amber-50"
        >
          Reveal answer
        </button>
      </div>
    </div>
  );
}
