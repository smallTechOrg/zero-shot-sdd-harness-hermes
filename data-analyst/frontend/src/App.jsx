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

export default function App() {
  const [question, setQuestion] = useState('Show me monthly sales amount by channel as a line chart')
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
  const stepIndex = useRef(0)

  const today = new Date().toISOString().slice(0, 10)

  async function refreshTokens() {
    try {
      const r = await fetch(`/api/audit?date=${today}`)
      const j = await r.json()
      setDailyTokens(j.totalTokens ?? 0)
    } catch { /* ignore */ }
  }
  useEffect(() => { refreshTokens() }, [])

  async function ask() {
    setBusy(true); setError(null); setPlan(''); setSql(''); setSteps([])
    setChartData(null); setClarification(null); setCollapsed(false)
    stepIndex.current = 0

    try {
      const resp = await fetch('/api/query/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question }),
      })
      if (!resp.ok || !resp.body) throw new Error(`HTTP ${resp.status}`)

      const reader = resp.body.getReader()
      const decoder = new TextDecoder()
      let buf = ''
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buf += decoder.decode(value, { stream: true })
        const events = buf.split('\n\n')
        buf = events.pop() ?? ''
        for (const block of events) handleEvent(block)
      }
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false); setCollapsed(true); refreshTokens()
    }
  }

  function handleEvent(block) {
    const evLine = block.split('\n').find(l => l.startsWith('event:'))
    const dataLine = block.split('\n').find(l => l.startsWith('data:'))
    if (!evLine || !dataLine) return
    const ev = evLine.slice(6).trim()
    let payload
    try { payload = JSON.parse(dataLine.slice(5).trim()) } catch { return }

    if (ev === 'plan') setPlan(payload.text)
    else if (ev === 'sql') setSql(payload.text)
    else if (ev === 'step') setSteps(s => [...s, payload.text])
    else if (ev === 'data') {
      setChartType(payload.chartType)
      if (payload.clarification) setClarification(payload.clarification)
      if (payload.data) setChartData(payload.data)
    }
    else if (ev === 'error') setError(payload.error)
  }

  const ChartComp = chartType === 'line' ? Line : chartType === 'pie' ? Pie : Bar

  return (
    <div className="app">
      <header>
        <h1>📊 Data Analyst Agent <span className="badge">v0.1</span></h1>
        <div className="tokens">Daily tokens: <b>{dailyTokens}</b></div>
      </header>

      <div className="ask-row">
        <input value={question} disabled={busy}
          onChange={e => setQuestion(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && !busy && ask()}
          placeholder="Ask about the warehouse..." />
        <button onClick={ask} disabled={busy || !question.trim()}>
          {busy ? 'Thinking…' : 'Ask'}
        </button>
      </div>

      <nav className="stubs">
        <button disabled title="Coming in Phase 2">History</button>
        <button disabled title="Coming in Phase 3">Export CSV</button>
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
    </div>
  )
}
