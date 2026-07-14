import { useEffect, useRef, useState } from 'react'
import {
  Chart as ChartJS, CategoryScale, LinearScale, BarElement, PointElement,
  LineElement, ArcElement, Title, Tooltip, Legend
} from 'chart.js'
import { Bar, Line, Pie } from 'react-chartjs-2'

ChartJS.register(CategoryScale, LinearScale, BarElement, PointElement,
  LineElement, ArcElement, Title, Tooltip, Legend)

const PALETTE = ['#4e79a7','#f28e2b','#e15759','#76b7b2','#59a14f','#edc948','#b07aa1','#ff9da7']

function toChartJs(chartType, data) {
  const datasets = data.datasets.map((ds, i) => ({
    label: ds.label,
    data: ds.data,
    backgroundColor: chartType === 'pie'
      ? data.labels.map((_, j) => PALETTE[j % PALETTE.length])
      : PALETTE[i % PALETTE.length],
    borderColor: PALETTE[i % PALETTE.length],
    fill: chartType === 'line' ? false : undefined,
  }))
  return { labels: data.labels, datasets }
}

// Suggested questions derived from the warehouse shape — helps the user know
// what is answerable without first reading the schema.
const SUGGESTIONS = [
  'जिलेवार FIR पंजीकरण की मासिक प्रवृत्ति (Monthly FIR registration trend by district)',
  'अपराध के प्रकार के अनुसार कुल FIR (Total FIRs by crime head/category)',
  'बरामदगी दर (Detection rate) — अपराध जिनमें चार्जशीट हुई (crimes detected vs undetected)',
  'लंबित मामलों की स्थिति (Case disposal / pendency status)',
  'शीर्ष 10 थाने (police stations) अधिकतम FIR के साथ (Top 10 PS by FIR count)',
  'वर्ष 2024 में सबसे अधिक अपराध वाले जिले (Districts with most crimes in 2024)',
]

export default function App() {
  const [question, setQuestion] = useState('')
  const [busy, setBusy] = useState(false)
  const [plan, setPlan] = useState('')
  const [sql, setSql] = useState('')
  const [steps, setSteps] = useState([])
  const [chartType, setChartType] = useState('bar')
  const [chartData, setChartData] = useState(null)
  const [clarification, setClarification] = useState(null)
  const [error, setError] = useState(null)
  const [collapsed, setCollapsed] = useState(false)
  const [dailyTokens, setDailyTokens] = useState(0)
  const [catalog, setCatalog] = useState(null)
  const stepIndex = useRef(0)

  const today = new Date().toISOString().slice(0, 10)

  async function refreshTokens() {
    try {
      const r = await fetch(`/api/audit?date=${today}`)
      const j = await r.json()
      setDailyTokens(j.totalTokens ?? 0)
    } catch { /* ignore */ }
  }

  async function loadCatalog() {
    try {
      const r = await fetch('/api/schema')
      const j = await r.json()
      setCatalog(j)
    } catch { /* ignore */ }
  }

  useEffect(() => { refreshTokens(); loadCatalog() }, [])

  async function ask(q) {
    const query = (q ?? question).trim()
    if (!query || busy) return
    setQuestion(query)
    setBusy(true); setError(null); setPlan(''); setSql(''); setSteps([])
    setChartData(null); setClarification(null); setCollapsed(false)
    stepIndex.current = 0

    try {
      // Non-streaming call: reliable through the dev proxy (SSE is truncated by
      // http-proxy buffering). The response still carries the full reasoning
      // chain (plan, steps, sql) so the panel renders identically.
      const resp = await fetch('/api/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: query }),
      })
      const j = await resp.json()
      if (!resp.ok) throw new Error(j.error || `HTTP ${resp.status}`)
      setChartType(j.chartType)
      setPlan(j.plan ?? '')
      setSteps(j.reasoningSteps ?? [])
      setSql(j.sql ?? '')
      if (j.clarification) setClarification(j.clarification)
      if (j.data) setChartData(j.data)
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false); setCollapsed(true); refreshTokens()
    }
  }

  const ChartComp = chartType === 'line' ? Line : chartType === 'pie' ? Pie : Bar

  return (
    <div className="app">
      <header>
        <h1>📊 पुलिस अपराध विश्लेषक (Police Crime Analyst) <span className="badge">UP Police · v0.1</span></h1>
        <div className="tokens">आज के टोकन (Daily tokens): <b>{dailyTokens}</b></div>
      </header>

      <div className="ask-row">
        <input value={question} disabled={busy}
          onChange={e => setQuestion(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && ask()}
          placeholder="अपराध डेटा के बारे में पूछें... (Ask about crime data — e.g. FIR trend by district)" />
        <button onClick={() => ask()} disabled={busy || !question.trim()}>
          {busy ? 'विचार कर रहा... (Thinking)' : 'पूछें (Ask)'}
        </button>
      </div>

      <div className="suggestions">
        <span className="sug-label">आज़माएँ (Try):</span>
        {SUGGESTIONS.map((s, i) => (
          <button key={i} className="chip" disabled={busy} onClick={() => ask(s)}>{s}</button>
        ))}
      </div>

      <nav className="stubs">
        <button disabled title="Phase 2 में (Coming in Phase 2)">इतिहास (History)</button>
        <button disabled title="Phase 3 में (Coming in Phase 3)">CSV निर्यात (Export CSV)</button>
      </nav>

      {error && <div className="error">⚠️ {error}</div>}

      {clarification && (
        <div className="clarify">🤔 <b>Clarification needed:</b> {clarification}</div>
      )}

      {(plan || sql || steps.length > 0) && (
        <section className="reasoning">
          <div className="reasoning-head" onClick={() => setCollapsed(c => !c)}>
            <b>Reasoning chain</b>
            <span>{steps.length > 0 ? `Step ${steps.length} of ${steps.length}` : ''} {collapsed ? '▸' : '▾'}</span>
          </div>
          {!collapsed && (
            <div className="reasoning-body">
              {plan && <p><b>Plan:</b> {plan}</p>}
              {steps.map((s, i) => <p key={i} className="step">{s}</p>)}
              {sql && <pre className="sql">{sql}</pre>}
            </div>
          )}
        </section>
      )}

      {chartData && (
        <section className="chart">
          <ChartComp data={toChartJs(chartType, chartData)}
            options={{ responsive: true, plugins: { legend: { position: 'top' } } }} />
        </section>
      )}

      {catalog && (
        <section className="catalog">
          <h2>📚 डेटाबेस कैटलॉग (Database catalog — CCTNS 1.0)</h2>
          <p className="catalog-note">केवल स्कीमा और सारांश (Schema + aggregate profiles only) — कच्ची पंक्तियाँ (raw rows) डेटाबेस से बाहर नहीं जातीं।</p>
          <div className="tables">
            {catalog.tables.map(t => (
              <div key={t.table} className="table-card">
                <div className="table-head">
                  <b>{t.table}</b>
                  <span className="rowcount">{t.rowCount?.toLocaleString()} rows</span>
                </div>
                <table>
                  <thead>
                    <tr><th>Column</th><th>Type</th><th>Distinct</th><th>Nulls</th><th>Min</th><th>Max</th></tr>
                  </thead>
                  <tbody>
                    {t.columns.map(c => (
                      <tr key={c.column}>
                        <td>{c.column}</td>
                        <td>{c.dataType}</td>
                        <td>{c.distinctCount}</td>
                        <td>{c.nullPercent}%</td>
                        <td>{c.min ?? '—'}</td>
                        <td>{c.max ?? '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  )
}
