import { useEffect, useMemo, useState } from 'react'
import './App.css'

type Job = {
  id: string
  job_type?: string | null
  status?: string | null
  animation_id?: string | null
  created_at?: string | null
  started_at?: string | null
  finished_at?: string | null
  error?: string | null
}

type SummaryResponse = {
  summary?: Record<string, number>
  jobs?: Job[]
}

const STATUS_ORDER = ['queued', 'running', 'failed', 'succeeded']

const API_BASE = (import.meta.env.VITE_API_URL || '/api').replace(/\/$/, '')

function formatDate(value?: string | null) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleString()
}

function statusLabel(status?: string | null) {
  return status ? status.toUpperCase() : 'UNKNOWN'
}

function statusTone(status?: string | null) {
  switch (status) {
    case 'queued':
      return 'tone-wait'
    case 'running':
      return 'tone-live'
    case 'failed':
      return 'tone-alert'
    case 'succeeded':
      return 'tone-ok'
    default:
      return 'tone-neutral'
  }
}

function App() {
  const [data, setData] = useState<SummaryResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)

  const fetchSummary = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch(`${API_BASE}/pipeline/summary?limit=12`)
      if (!response.ok) {
        throw new Error(`API error ${response.status}`)
      }
      const payload = (await response.json()) as SummaryResponse
      setData(payload)
      setLastUpdated(new Date())
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchSummary()
    const interval = window.setInterval(fetchSummary, 15000)
    return () => window.clearInterval(interval)
  }, [])

  const summary = useMemo(() => data?.summary ?? {}, [data])
  const jobs = useMemo(() => data?.jobs ?? [], [data])

  return (
    <div className="app-shell">
      <header className="hero">
        <div>
          <p className="hero-kicker">ShortLab Control Panel</p>
          <h1>Pipeline Pulse</h1>
          <p className="hero-subtitle">
            Live view of queue pressure, execution health, and recent pipeline jobs.
          </p>
        </div>
        <div className="hero-actions">
          <div className="hero-chip">
            <span className="dot" aria-hidden />
            <span>Auto-refresh 15s</span>
          </div>
          <button className="ghost-button" onClick={fetchSummary} disabled={loading}>
            Refresh now
          </button>
        </div>
      </header>

      <section className="status-grid">
        {STATUS_ORDER.map((status) => (
          <article className={`status-card ${statusTone(status)}`} key={status}>
            <div>
              <p className="status-label">{statusLabel(status)}</p>
              <p className="status-value">{summary[status] ?? 0}</p>
            </div>
            <div className="status-meter">
              <div
                className="status-meter-fill"
                style={{ width: `${Math.min((summary[status] ?? 0) * 8, 100)}%` }}
              />
            </div>
          </article>
        ))}
      </section>

      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>Recent jobs</h2>
            <p>Latest 12 pipeline executions with quick status context.</p>
          </div>
          <div className="panel-meta">
            <span>API: {API_BASE}</span>
            <span>
              Updated:{' '}
              {lastUpdated ? lastUpdated.toLocaleTimeString() : 'waiting for data'}
            </span>
          </div>
        </div>

        {loading ? (
          <div className="state-box">Loading pipeline data…</div>
        ) : error ? (
          <div className="state-box state-error">
            <strong>Failed to load</strong>
            <span>{error}</span>
          </div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Status</th>
                  <th>Job type</th>
                  <th>Animation</th>
                  <th>Created</th>
                  <th>Started</th>
                  <th>Finished</th>
                </tr>
              </thead>
              <tbody>
                {jobs.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="table-empty">
                      No jobs yet. Enqueue a pipeline run to populate this list.
                    </td>
                  </tr>
                ) : (
                  jobs.map((job) => (
                    <tr key={job.id}>
                      <td>
                        <span className={`badge ${statusTone(job.status)}`}>
                          {statusLabel(job.status)}
                        </span>
                      </td>
                      <td>{job.job_type ?? '—'}</td>
                      <td className="mono">{job.animation_id ?? '—'}</td>
                      <td>{formatDate(job.created_at)}</td>
                      <td>{formatDate(job.started_at)}</td>
                      <td>{formatDate(job.finished_at)}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}

export default App
