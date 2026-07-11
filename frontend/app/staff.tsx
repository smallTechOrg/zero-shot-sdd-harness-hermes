"use client";

interface StaffProps {
  svg: string;
  playing?: boolean;
}

// Renders the server-computed SVG staff. The SVG is generated deterministically
// from the note's pitch on the backend — never guessed by the model.
export default function Staff({ svg, playing }: StaffProps) {
  return (
    <div
      className={`rounded-xl border border-slate-200 bg-white p-4 shadow-sm transition ${
        playing ? "ring-4 ring-emerald-300" : ""
      }`}
      // The SVG is produced by our own backend (trusted).
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  );
}
