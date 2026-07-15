"use client";

import { useEffect, useState } from "react";

type Stage = { stage: string; count: number };
type Funnel = { entity: string; sample: boolean; stages: Stage[]; insight: string | null };
type Kpis = { signups: number; activated: number; retention_pct: number; revenue: number };
type Point = { created_at: string; sample: boolean; signup: number; activated: number; retained: number; revenue: number };
type Connector = { id: string; name: string; configured: boolean; env_var: string };
type SetupStep = { title: string; detail: string };

const STAGE_LABELS: Record<string, string> = {
  visit_or_install: "Visit / Install",
  signup: "Signup",
  activated: "Activated",
  retained: "Retained",
  revenue: "Revenue",
};

export default function Page() {
  const [funnel, setFunnel] = useState<Funnel | null>(null);
  const [kpis, setKpis] = useState<Kpis | null>(null);
  const [points, setPoints] = useState<Point[]>([]);
  const [connectors, setConnectors] = useState<Connector[]>([]);
  const [loading, setLoading] = useState(true);
  const [toast, setToast] = useState<string | null>(null);
  const [setupFor, setSetupFor] = useState<Connector | null>(null);
  const [setupSteps, setSetupSteps] = useState<SetupStep[]>([]);

  async function load() {
    setLoading(true);
    try {
      const [f, k, s, c] = await Promise.all([
        fetch("/api/funnel").then((r) => r.json()),
        fetch("/api/kpis").then((r) => r.json()),
        fetch("/api/snapshots").then((r) => r.json()),
        fetch("/api/connectors").then((r) => r.json()),
      ]);
      setFunnel(f.data);
      setKpis(k.data);
      setPoints(s.data);
      setConnectors(c.data);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function refresh() {
    setLoading(true);
    await fetch("/api/refresh", { method: "POST" });
    await load();
    setToast("Updated");
    setTimeout(() => setToast(null), 2000);
  }

  async function openSetup(c: Connector) {
    setSetupFor(c);
    const res = await fetch(`/api/setup_guide?source=${c.id}`).then((r) => r.json());
    setSetupSteps(res.data || []);
  }

  const top = funnel ? Math.max(...funnel.stages.map((s) => s.count), 1) : 1;
  const maxRev = points.length ? Math.max(...points.map((p) => p.revenue), 1) : 1;

  return (
    <main className="min-h-screen p-6 max-w-5xl mx-auto">
      <header className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">#local Analytics</h1>
          <span className="inline-block mt-1 px-2 py-0.5 rounded bg-indigo-600/30 text-indigo-200 text-xs">
            entity: #local
          </span>
        </div>
        <button
          onClick={refresh}
          className="px-4 py-2 rounded bg-indigo-600 hover:bg-indigo-500 text-white font-medium"
        >
          Refresh
        </button>
      </header>

      {toast && (
        <div className="mb-4 px-3 py-2 rounded bg-green-600/30 text-green-200 text-sm">{toast}</div>
      )}

      {loading && !funnel ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="h-24 rounded bg-slate-800 animate-pulse" />
          ))}
        </div>
      ) : (
        <>
          <section className="rounded-lg bg-slate-900/60 p-5 mb-6">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-lg font-semibold">Acquisition + Retention Funnel</h2>
              {funnel?.sample && (
                <span className="px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 text-xs font-medium">
                  SAMPLE DATA
                </span>
              )}
            </div>
            <div className="space-y-2">
              {funnel?.stages.map((s) => (
                <div key={s.stage}>
                  <div className="flex justify-between text-sm mb-1">
                    <span>{STAGE_LABELS[s.stage] ?? s.stage}</span>
                    <span className="text-slate-400">
                      {s.count.toLocaleString()} · {((s.count / top) * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="h-6 rounded bg-slate-800 overflow-hidden">
                    <div
                      className="h-full bg-indigo-500"
                      style={{ width: `${(s.count / top) * 100}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
            {funnel?.insight && (
              <p className="mt-3 text-sm text-slate-300 italic">{funnel.insight}</p>
            )}
          </section>

          <section className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <KpiTile label="Signups" value={kpis ? kpis.signups.toLocaleString() : "—"} />
            <KpiTile label="Activated" value={kpis ? kpis.activated.toLocaleString() : "—"} />
            <KpiTile label="Retention" value={kpis ? `${kpis.retention_pct}%` : "—"} />
            <KpiTile label="Revenue" value={kpis ? `$${Math.round(kpis.revenue).toLocaleString()}` : "—"} />
          </section>

          <section className="rounded-lg bg-slate-900/60 p-5 mb-6">
            <h2 className="text-lg font-semibold mb-3">Trend (revenue over time)</h2>
            {points.length === 0 ? (
              <p className="text-sm text-slate-400">No snapshots yet.</p>
            ) : (
              <div className="flex items-end gap-1 h-24">
                {points.map((p, i) => (
                  <div
                    key={i}
                    title={`$${Math.round(p.revenue)}`}
                    className="flex-1 bg-emerald-500/70 rounded-t"
                    style={{ height: `${(p.revenue / maxRev) * 100}%` }}
                  />
                ))}
              </div>
            )}
          </section>

          <section className="rounded-lg bg-slate-900/60 p-5">
            <h2 className="text-lg font-semibold mb-3">Connectors</h2>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              {connectors.map((c) => (
                <div key={c.id} className="rounded border border-slate-700 p-3">
                  <div className="flex items-center justify-between">
                    <span className="font-medium">{c.name}</span>
                    <span
                      className={
                        c.configured
                          ? "text-green-400 text-xs"
                          : "text-amber-400 text-xs"
                      }
                    >
                      {c.configured ? "CONNECTED" : "NOT CONFIGURED"}
                    </span>
                  </div>
                  <button
                    onClick={() => openSetup(c)}
                    className="mt-2 text-xs text-indigo-300 hover:underline"
                  >
                    Set up
                  </button>
                </div>
              ))}
            </div>
            <div className="mt-4 flex flex-wrap gap-2 text-xs text-slate-400">
              <span className="px-2 py-1 rounded bg-slate-800">🔔 Notifications — Phase 2</span>
              <span className="px-2 py-1 rounded bg-slate-800">⏱ Scheduled refresh — Phase 2</span>
            </div>
          </section>
        </>
      )}

      {setupFor && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center p-4" onClick={() => setSetupFor(null)}>
          <div className="bg-slate-900 rounded-lg p-5 max-w-lg w-full" onClick={(e) => e.stopPropagation()}>
            <div className="flex justify-between items-center mb-3">
              <h3 className="text-lg font-semibold">Set up {setupFor.name}</h3>
              <button onClick={() => setSetupFor(null)} className="text-slate-400 hover:text-white">✕</button>
            </div>
            <p className="text-xs text-amber-300 mb-3">
              Connector is live in Phase 2. These are the exact steps + env var to fill in <code>.env</code>.
            </p>
            <ol className="space-y-3">
              {setupSteps.map((step, i) => (
                <li key={i} className="text-sm">
                  <div className="font-medium">{i + 1}. {step.title}</div>
                  <div className="text-slate-400 whitespace-pre-wrap">{step.detail}</div>
                </li>
              ))}
            </ol>
          </div>
        </div>
      )}
    </main>
  );
}

function KpiTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-slate-900/60 p-4" data-testid={`kpi-${label.toLowerCase()}`}>
      <div className="text-xs text-slate-400">{label}</div>
      <div className="text-2xl font-bold mt-1">{value}</div>
    </div>
  );
}
