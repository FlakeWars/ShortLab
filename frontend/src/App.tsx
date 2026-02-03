import { useEffect, useMemo, useState } from 'react'
import { Badge } from './components/ui/badge'
import { Button } from './components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from './components/ui/card'
import { cn } from './lib/utils'

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

type AnimationRow = {
  id: string
  animation_code?: string | null
  status?: string | null
  pipeline_stage?: string | null
  idea_id?: string | null
  created_at?: string | null
  updated_at?: string | null
  render?: {
    id?: string | null
    status?: string | null
    seed?: number | null
    dsl_version_id?: string | null
    design_system_version_id?: string | null
    renderer_version?: string | null
    duration_ms?: number | null
    width?: number | null
    height?: number | null
    fps?: number | null
    created_at?: string | null
    started_at?: string | null
    finished_at?: string | null
  } | null
  qc?: {
    id?: string | null
    result?: string | null
    checklist_version_id?: string | null
    decided_at?: string | null
  } | null
}

type Artifact = {
  id: string
  render_id?: string | null
  artifact_type?: string | null
  storage_path?: string | null
  size_bytes?: number | null
  created_at?: string | null
}

type IdeaCandidate = {
  id: string
  idea_batch_id?: string | null
  title?: string | null
  summary?: string | null
  what_to_expect?: string | null
  preview?: string | null
  generator_source?: string | null
  similarity_status?: string | null
  status?: string | null
  selected?: boolean | null
  selected_at?: string | null
  selected_by?: string | null
  decision_at?: string | null
  created_at?: string | null
}

type AuditEvent = {
  id: string
  event_type?: string | null
  source?: string | null
  actor_user_id?: string | null
  payload?: Record<string, unknown> | null
  occurred_at?: string | null
}

type SummaryResponse = {
  summary?: Record<string, number>
  jobs?: Job[]
}

const STATUS_ORDER = ['queued', 'running', 'failed', 'succeeded']
const ANIMATION_STATUSES = [
  'draft',
  'queued',
  'running',
  'review',
  'accepted',
  'rejected',
  'published',
  'archived',
]
const PIPELINE_STAGES = ['idea', 'render', 'qc', 'publish', 'metrics', 'done']

const explicitApiBase = import.meta.env.VITE_API_URL || import.meta.env.VITE_API_TARGET
const fallbackApiBase = (() => {
  if (typeof window === 'undefined') return '/api'
  const host = window.location.hostname
  const port = window.location.port
  if ((host === 'localhost' || host === '127.0.0.1') && port === '5173') {
    return 'http://localhost:8016'
  }
  return '/api'
})()
const API_BASE = (explicitApiBase || fallbackApiBase).replace(/\/$/, '')

type SettingsResponse = {
  database_url?: string
  redis_url?: string
  rq_job_timeout?: string
  rq_render_timeout?: string
  ffmpeg_timeout_s?: string
  idea_gate_enabled?: string
  idea_gate_count?: string
  idea_gate_threshold?: string
  idea_gate_auto?: string
  operator_guard?: boolean
  artifacts_base_dir?: string
  openai_model?: string
  openai_base_url?: string
  openai_temperature?: string
  openai_max_output_tokens?: string
}

function formatDate(value?: string | null) {
  if (!value) return '—'
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return '—'
  return parsed.toLocaleString()
}

function statusLabel(status?: string | null) {
  return status ? status.toUpperCase() : 'UNKNOWN'
}

function statusTone(status?: string | null) {
  switch (status) {
    case 'queued':
      return 'bg-amber-100/70 text-amber-950 border-amber-200'
    case 'running':
      return 'bg-emerald-100/70 text-emerald-950 border-emerald-200'
    case 'failed':
      return 'bg-rose-100/70 text-rose-950 border-rose-200'
    case 'succeeded':
      return 'bg-sky-100/70 text-sky-950 border-sky-200'
    default:
      return 'bg-stone-100/70 text-stone-700 border-stone-200'
  }
}

function chipTone(value?: string | null) {
  if (!value) return 'bg-stone-100 text-stone-600 border-stone-200'
  return 'bg-stone-900 text-white border-stone-900'
}

function similarityTone(value?: string | null) {
  switch (value) {
    case 'ok':
      return 'bg-emerald-100 text-emerald-900 border-emerald-200'
    case 'too_similar':
      return 'bg-amber-100 text-amber-900 border-amber-200'
    case 'unknown':
      return 'bg-stone-100 text-stone-700 border-stone-200'
    default:
      return 'bg-stone-100 text-stone-600 border-stone-200'
  }
}

function SettingRow({ label, value }: { label: string; value?: string | null }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-xs uppercase tracking-[0.18em] text-stone-500">{label}</span>
      <span className="rounded-full border border-stone-200 bg-white px-3 py-1 text-xs font-semibold text-stone-700">
        {value ?? '—'}
      </span>
    </div>
  )
}

function App() {
  const [summaryData, setSummaryData] = useState<SummaryResponse | null>(null)
  const [summaryError, setSummaryError] = useState<string | null>(null)
  const [summaryLoading, setSummaryLoading] = useState(true)
  const [summaryUpdatedAt, setSummaryUpdatedAt] = useState<Date | null>(null)

  const [animationData, setAnimationData] = useState<AnimationRow[]>([])
  const [animationError, setAnimationError] = useState<string | null>(null)
  const [animationLoading, setAnimationLoading] = useState(false)
  const [animationUpdatedAt, setAnimationUpdatedAt] = useState<Date | null>(null)

  const [animationStatus, setAnimationStatus] = useState('')
  const [pipelineStage, setPipelineStage] = useState('')
  const [ideaId, setIdeaId] = useState('')

  const [selectedAnimation, setSelectedAnimation] = useState<AnimationRow | null>(null)
  const [artifacts, setArtifacts] = useState<Artifact[]>([])
  const [artifactsError, setArtifactsError] = useState<string | null>(null)
  const [artifactsLoading, setArtifactsLoading] = useState(false)

  const [ideaCandidates, setIdeaCandidates] = useState<IdeaCandidate[]>([])
  const [ideaError, setIdeaError] = useState<string | null>(null)
  const [ideaLoading, setIdeaLoading] = useState(false)
  const [ideaUpdatedAt, setIdeaUpdatedAt] = useState<Date | null>(null)
  const [selectedIdea, setSelectedIdea] = useState<IdeaCandidate | null>(null)

  const [ideaSampleCount, setIdeaSampleCount] = useState('3')
  const [ideaDecisions, setIdeaDecisions] = useState<Record<string, string>>({})
  const [ideaDecisionError, setIdeaDecisionError] = useState<string | null>(null)
  const [ideaDecisionMessage, setIdeaDecisionMessage] = useState<string | null>(null)
  const [ideaDecisionLoading, setIdeaDecisionLoading] = useState(false)

  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([])
  const [auditError, setAuditError] = useState<string | null>(null)
  const [auditLoading, setAuditLoading] = useState(false)
  const [auditUpdatedAt, setAuditUpdatedAt] = useState<Date | null>(null)

  const [auditType, setAuditType] = useState('')
  const [auditSource, setAuditSource] = useState('')
  const [auditActor, setAuditActor] = useState('')

  const [enqueueDsl, setEnqueueDsl] = useState('.ai/examples/dsl-v1-happy.yaml')
  const [enqueueOutRoot, setEnqueueOutRoot] = useState('out/pipeline')
  const [rerunAnimationId, setRerunAnimationId] = useState('')
  const [rerunOutRoot, setRerunOutRoot] = useState('out/pipeline')
  const [cleanupOlderMin, setCleanupOlderMin] = useState('30')
  const [opsMessage, setOpsMessage] = useState<string | null>(null)
  const [opsError, setOpsError] = useState<string | null>(null)
  const [opsEnqueueLoading, setOpsEnqueueLoading] = useState(false)
  const [opsRerunLoading, setOpsRerunLoading] = useState(false)
  const [opsCleanupLoading, setOpsCleanupLoading] = useState(false)

  const [settings, setSettings] = useState<SettingsResponse | null>(null)
  const [settingsLoading, setSettingsLoading] = useState(false)
  const [settingsError, setSettingsError] = useState<string | null>(null)

  const opsHeaders = () => {
    const token = import.meta.env.VITE_OPERATOR_TOKEN as string | undefined
    if (token) {
      return { 'Content-Type': 'application/json', 'X-Operator-Token': token }
    }
    return { 'Content-Type': 'application/json' }
  }

  const fetchSummary = async () => {
    setSummaryLoading(true)
    setSummaryError(null)
    try {
      const response = await fetch(`${API_BASE}/pipeline/summary?limit=12`)
      if (!response.ok) {
        throw new Error(`API error ${response.status}`)
      }
      const payload = (await response.json()) as SummaryResponse
      setSummaryData(payload)
      setSummaryUpdatedAt(new Date())
    } catch (err) {
      setSummaryError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setSummaryLoading(false)
    }
  }

  const fetchAnimations = async () => {
    setAnimationLoading(true)
    setAnimationError(null)
    try {
      const params = new URLSearchParams()
      params.set('limit', '12')
      if (animationStatus) params.set('status', animationStatus)
      if (pipelineStage) params.set('pipeline_stage', pipelineStage)
      if (ideaId) params.set('idea_id', ideaId)

      const response = await fetch(`${API_BASE}/animations?${params.toString()}`)
      if (!response.ok) {
        throw new Error(`API error ${response.status}`)
      }
      const payload = (await response.json()) as AnimationRow[]
      setAnimationData(payload)
      setAnimationUpdatedAt(new Date())
      if (payload.length && !selectedAnimation) {
        setSelectedAnimation(payload[0])
      }
    } catch (err) {
      setAnimationError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setAnimationLoading(false)
    }
  }

  const fetchArtifacts = async (renderId?: string | null) => {
    if (!renderId) {
      setArtifacts([])
      return
    }
    setArtifactsLoading(true)
    setArtifactsError(null)
    try {
      const response = await fetch(`${API_BASE}/renders/${renderId}/artifacts`)
      if (!response.ok) {
        throw new Error(`API error ${response.status}`)
      }
      const payload = (await response.json()) as Artifact[]
      setArtifacts(payload)
    } catch (err) {
      setArtifactsError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setArtifactsLoading(false)
    }
  }

  const fetchIdeaCandidates = async () => {
    setIdeaLoading(true)
    setIdeaError(null)
    setIdeaDecisionError(null)
    setIdeaDecisionMessage(null)
    try {
      const count = Number(ideaSampleCount || '3')
      const limit = Number.isNaN(count) ? 3 : Math.max(1, Math.min(count, 10))
      const response = await fetch(`${API_BASE}/idea-repo/sample?limit=${limit}`)
      if (!response.ok) {
        throw new Error(`API error ${response.status}`)
      }
      const payload = (await response.json()) as IdeaCandidate[]
      setIdeaCandidates(payload)
      setIdeaDecisions({})
      setIdeaUpdatedAt(new Date())
      setSelectedIdea(payload[0] ?? null)
    } catch (err) {
      setIdeaError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setIdeaLoading(false)
    }
  }

  const submitIdeaDecisions = async () => {
    setIdeaDecisionLoading(true)
    setIdeaDecisionError(null)
    setIdeaDecisionMessage(null)
    try {
      if (ideaCandidates.length === 0) {
        throw new Error('Brak propozycji do klasyfikacji.')
      }
      const decisions = ideaCandidates.map((idea) => ({
        idea_candidate_id: idea.id,
        decision: ideaDecisions[idea.id],
      }))
      if (decisions.some((item) => !item.decision)) {
        throw new Error('Ustaw decyzję dla każdej propozycji.')
      }
      const picked = decisions.filter((item) => item.decision === 'picked')
      if (picked.length !== 1) {
        throw new Error('Wybierz dokładnie jedną propozycję do generowania.')
      }
      const response = await fetch(`${API_BASE}/idea-repo/decide`, {
        method: 'POST',
        headers: opsHeaders(),
        body: JSON.stringify({ decisions }),
      })
      if (!response.ok) {
        throw new Error(`API error ${response.status}`)
      }
      const payload = (await response.json()) as { idea_id?: string }
      if (!payload.idea_id) {
        throw new Error('Brak idea_id po decyzji.')
      }
      const enqueueResponse = await fetch(`${API_BASE}/ops/enqueue`, {
        method: 'POST',
        headers: opsHeaders(),
        body: JSON.stringify({
          dsl_template: enqueueDsl,
          out_root: enqueueOutRoot,
          idea_id: payload.idea_id,
          idea_gate: false,
        }),
      })
      if (!enqueueResponse.ok) {
        throw new Error(`API error ${enqueueResponse.status}`)
      }
      setIdeaDecisionMessage('Wybrana idea przekazana do pipeline.')
      fetchSummary()
    } catch (err) {
      setIdeaDecisionError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setIdeaDecisionLoading(false)
    }
  }

  const fetchAuditEvents = async () => {
    setAuditLoading(true)
    setAuditError(null)
    try {
      const params = new URLSearchParams()
      params.set('limit', '12')
      if (auditType) params.set('event_type', auditType)
      if (auditSource) params.set('source', auditSource)
      if (auditActor) params.set('actor_user_id', auditActor)

      const response = await fetch(`${API_BASE}/audit-events?${params.toString()}`)
      if (!response.ok) {
        throw new Error(`API error ${response.status}`)
      }
      const payload = (await response.json()) as AuditEvent[]
      setAuditEvents(payload)
      setAuditUpdatedAt(new Date())
    } catch (err) {
      setAuditError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setAuditLoading(false)
    }
  }

  const handleEnqueue = async () => {
    setOpsEnqueueLoading(true)
    setOpsError(null)
    setOpsMessage(null)
    try {
      const response = await fetch(`${API_BASE}/ops/enqueue`, {
        method: 'POST',
        headers: opsHeaders(),
        body: JSON.stringify({
          dsl_template: enqueueDsl,
          out_root: enqueueOutRoot,
        }),
      })
      if (!response.ok) {
        throw new Error(`API error ${response.status}`)
      }
      const payload = (await response.json()) as Record<string, unknown>
      setOpsMessage(`Enqueued: ${JSON.stringify(payload)}`)
      fetchSummary()
    } catch (err) {
      setOpsError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setOpsEnqueueLoading(false)
    }
  }

  const handleRerun = async () => {
    setOpsRerunLoading(true)
    setOpsError(null)
    setOpsMessage(null)
    try {
      const response = await fetch(`${API_BASE}/ops/rerun`, {
        method: 'POST',
        headers: opsHeaders(),
        body: JSON.stringify({
          animation_id: rerunAnimationId,
          out_root: rerunOutRoot,
        }),
      })
      if (!response.ok) {
        throw new Error(`API error ${response.status}`)
      }
      const payload = (await response.json()) as Record<string, unknown>
      setOpsMessage(`Rerun queued: ${JSON.stringify(payload)}`)
      fetchSummary()
    } catch (err) {
      setOpsError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setOpsRerunLoading(false)
    }
  }

  const handleCleanup = async () => {
    setOpsCleanupLoading(true)
    setOpsError(null)
    setOpsMessage(null)
    try {
      const response = await fetch(`${API_BASE}/ops/cleanup-jobs`, {
        method: 'POST',
        headers: opsHeaders(),
        body: JSON.stringify({
          older_min: Number(cleanupOlderMin || 30),
        }),
      })
      if (!response.ok) {
        throw new Error(`API error ${response.status}`)
      }
      const payload = (await response.json()) as Record<string, unknown>
      setOpsMessage(`Cleanup done: ${JSON.stringify(payload)}`)
      fetchSummary()
    } catch (err) {
      setOpsError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setOpsCleanupLoading(false)
    }
  }

  const fetchSettings = async () => {
    setSettingsLoading(true)
    setSettingsError(null)
    try {
      const response = await fetch(`${API_BASE}/settings`)
      if (!response.ok) {
        throw new Error(`API error ${response.status}`)
      }
      const payload = (await response.json()) as SettingsResponse
      setSettings(payload)
    } catch (err) {
      setSettingsError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setSettingsLoading(false)
    }
  }

  useEffect(() => {
    fetchSummary()
    const interval = window.setInterval(fetchSummary, 15000)
    return () => window.clearInterval(interval)
  }, [])

  useEffect(() => {
    fetchAnimations()
  }, [])

  useEffect(() => {
    fetchIdeaCandidates()
  }, [])

  useEffect(() => {
    fetchAuditEvents()
  }, [])

  useEffect(() => {
    fetchSettings()
  }, [])

  useEffect(() => {
    fetchArtifacts(selectedAnimation?.render?.id ?? null)
  }, [selectedAnimation?.render?.id])

  const summary = useMemo(() => summaryData?.summary ?? {}, [summaryData])
  const jobs = useMemo(() => summaryData?.jobs ?? [], [summaryData])

  const videoArtifact = useMemo(
    () => artifacts.find((item) => item.artifact_type === 'video'),
    [artifacts],
  )

  const previewUrl = videoArtifact ? `${API_BASE}/artifacts/${videoArtifact.id}/file` : null

  return (
    <div className="mx-auto flex min-h-screen w-full max-w-6xl flex-col gap-8 px-6 pb-16 pt-12">
      <header className="flex flex-col gap-6 rounded-[32px] border border-amber-100/60 bg-gradient-to-br from-amber-50 via-orange-100/70 to-rose-100/70 p-8 shadow-2xl shadow-amber-950/10">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.35em] text-stone-500">
              ShortLab Control Panel
            </p>
            <h1 className="mt-3 font-serif text-4xl font-semibold text-stone-900 md:text-5xl">
              Pipeline Pulse
            </h1>
            <p className="mt-3 max-w-2xl text-base text-stone-600">
              Live view of queue pressure, execution health, and the latest pipeline jobs.
              Track the rhythm, spot bottlenecks, and react fast.
            </p>
          </div>
          <div className="flex flex-col gap-3 lg:items-end">
            <div className="flex items-center gap-2 rounded-full border border-white/60 bg-white/70 px-4 py-2 text-xs font-medium text-stone-600 shadow">
              <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-emerald-500" />
              Auto-refresh every 15s
            </div>
            <Button variant="outline" className="rounded-full" onClick={fetchSummary} disabled={summaryLoading}>
              Refresh now
            </Button>
          </div>
        </div>
      </header>

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {STATUS_ORDER.map((status) => (
          <Card
            key={status}
            className={cn('border bg-white/80 shadow-lg shadow-stone-900/5', statusTone(status))}
          >
            <CardHeader className="pb-2">
              <CardTitle className="text-xs font-semibold uppercase tracking-[0.2em] text-stone-500">
                {statusLabel(status)}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="text-3xl font-semibold text-stone-900">
                {summary[status] ?? 0}
              </div>
              <div className="h-2 w-full overflow-hidden rounded-full bg-white/60">
                <div
                  className="h-full rounded-full bg-stone-900/70"
                  style={{ width: `${Math.min((summary[status] ?? 0) * 8, 100)}%` }}
                />
              </div>
            </CardContent>
          </Card>
        ))}
      </section>

      <section className="rounded-[28px] border border-stone-200/80 bg-white/90 p-6 shadow-2xl shadow-stone-900/10">
        <div className="flex flex-col gap-3 border-b border-stone-200/70 pb-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h2 className="text-2xl font-semibold text-stone-900">Recent jobs</h2>
            <p className="text-sm text-stone-600">
              Latest 12 pipeline executions with status context and timing metadata.
            </p>
          </div>
          <div className="text-xs text-stone-500">
            <div>API: {API_BASE}</div>
            <div>Updated: {summaryUpdatedAt ? summaryUpdatedAt.toLocaleTimeString() : 'waiting for data'}</div>
          </div>
        </div>

        <div className="mt-4 overflow-x-auto">
          {summaryLoading ? (
            <div className="rounded-2xl border border-dashed border-stone-200 bg-stone-50/60 p-6 text-sm text-stone-600">
              Loading pipeline data…
            </div>
          ) : summaryError ? (
            <div className="rounded-2xl border border-rose-200 bg-rose-50/70 p-6 text-sm text-rose-700">
              <div className="font-semibold">Failed to load</div>
              <div>{summaryError}</div>
            </div>
          ) : (
            <table className="min-w-[720px] w-full text-left text-sm">
              <thead className="text-xs uppercase tracking-[0.18em] text-stone-500">
                <tr>
                  <th className="px-2 py-3">Status</th>
                  <th className="px-2 py-3">Job type</th>
                  <th className="px-2 py-3">Animation</th>
                  <th className="px-2 py-3">Created</th>
                  <th className="px-2 py-3">Started</th>
                  <th className="px-2 py-3">Finished</th>
                </tr>
              </thead>
              <tbody>
                {jobs.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-2 py-6 text-center text-stone-500">
                      No jobs yet. Enqueue a pipeline run to populate this list.
                    </td>
                  </tr>
                ) : (
                  jobs.map((job) => (
                    <tr key={job.id} className="border-t border-stone-200/70">
                      <td className="px-2 py-4">
                        <Badge variant="outline" className={cn('border', statusTone(job.status))}>
                          {statusLabel(job.status)}
                        </Badge>
                      </td>
                      <td className="px-2 py-4 text-stone-700">{job.job_type ?? '—'}</td>
                      <td className="px-2 py-4 font-mono text-xs text-stone-600">
                        {job.animation_id ?? '—'}
                      </td>
                      <td className="px-2 py-4 text-stone-600">{formatDate(job.created_at)}</td>
                      <td className="px-2 py-4 text-stone-600">{formatDate(job.started_at)}</td>
                      <td className="px-2 py-4 text-stone-600">{formatDate(job.finished_at)}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          )}
        </div>
      </section>

      <section className="rounded-[28px] border border-stone-200/80 bg-white/90 p-6 shadow-2xl shadow-stone-900/10">
        <div className="flex flex-col gap-4 border-b border-stone-200/70 pb-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h2 className="text-2xl font-semibold text-stone-900">Animations</h2>
            <p className="text-sm text-stone-600">
              Filter by status, stage, or idea ID to drill into the latest renders.
            </p>
          </div>
          <div className="text-xs text-stone-500">
            <div>Updated: {animationUpdatedAt ? animationUpdatedAt.toLocaleTimeString() : 'waiting for data'}</div>
          </div>
        </div>

        <div className="mt-4 flex flex-wrap items-end gap-3">
          <label className="flex min-w-[180px] flex-col gap-1 text-xs font-semibold uppercase tracking-[0.15em] text-stone-500">
            Status
            <select
              className="rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700 focus:border-stone-400 focus:outline-none"
              value={animationStatus}
              onChange={(event) => setAnimationStatus(event.target.value)}
            >
              <option value="">All</option>
              {ANIMATION_STATUSES.map((status) => (
                <option key={status} value={status}>
                  {status}
                </option>
              ))}
            </select>
          </label>
          <label className="flex min-w-[180px] flex-col gap-1 text-xs font-semibold uppercase tracking-[0.15em] text-stone-500">
            Stage
            <select
              className="rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700 focus:border-stone-400 focus:outline-none"
              value={pipelineStage}
              onChange={(event) => setPipelineStage(event.target.value)}
            >
              <option value="">All</option>
              {PIPELINE_STAGES.map((stage) => (
                <option key={stage} value={stage}>
                  {stage}
                </option>
              ))}
            </select>
          </label>
          <label className="flex min-w-[240px] flex-1 flex-col gap-1 text-xs font-semibold uppercase tracking-[0.15em] text-stone-500">
            Idea ID
            <input
              className="rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700 focus:border-stone-400 focus:outline-none"
              placeholder="UUID"
              value={ideaId}
              onChange={(event) => setIdeaId(event.target.value)}
            />
          </label>
          <div className="flex flex-wrap gap-2">
            <Button className="rounded-full" onClick={fetchAnimations} disabled={animationLoading}>
              Apply filters
            </Button>
            <Button
              variant="ghost"
              className="rounded-full"
              onClick={() => {
                setAnimationStatus('')
                setPipelineStage('')
                setIdeaId('')
                window.setTimeout(fetchAnimations, 0)
              }}
              disabled={animationLoading}
            >
              Reset
            </Button>
          </div>
        </div>

        <div className="mt-4 grid gap-6 lg:grid-cols-[1.3fr_0.9fr]">
          <div className="overflow-x-auto">
            {animationLoading ? (
              <div className="rounded-2xl border border-dashed border-stone-200 bg-stone-50/60 p-6 text-sm text-stone-600">
                Loading animations…
              </div>
            ) : animationError ? (
              <div className="rounded-2xl border border-rose-200 bg-rose-50/70 p-6 text-sm text-rose-700">
                <div className="font-semibold">Failed to load</div>
                <div>{animationError}</div>
              </div>
            ) : (
              <table className="min-w-[780px] w-full text-left text-sm">
                <thead className="text-xs uppercase tracking-[0.18em] text-stone-500">
                  <tr>
                    <th className="px-2 py-3">Status</th>
                    <th className="px-2 py-3">Stage</th>
                    <th className="px-2 py-3">Animation</th>
                    <th className="px-2 py-3">Render</th>
                    <th className="px-2 py-3">QC</th>
                    <th className="px-2 py-3">Updated</th>
                  </tr>
                </thead>
                <tbody>
                  {animationData.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="px-2 py-6 text-center text-stone-500">
                        No animations matched. Adjust filters or run the pipeline.
                      </td>
                    </tr>
                  ) : (
                    animationData.map((row) => (
                      <tr
                        key={row.id}
                        className={cn(
                          'border-t border-stone-200/70 transition hover:bg-stone-100/50',
                          selectedAnimation?.id === row.id && 'bg-stone-100/70',
                        )}
                        onClick={() => setSelectedAnimation(row)}
                      >
                        <td className="px-2 py-4">
                          <Badge variant="outline" className={cn('border', chipTone(row.status))}>
                            {statusLabel(row.status)}
                          </Badge>
                        </td>
                        <td className="px-2 py-4">
                          <Badge variant="outline" className={cn('border', chipTone(row.pipeline_stage))}>
                            {row.pipeline_stage ?? '—'}
                          </Badge>
                        </td>
                        <td className="px-2 py-4 font-mono text-xs text-stone-600">{row.id}</td>
                        <td className="px-2 py-4 text-stone-600">{row.render?.status ?? '—'}</td>
                        <td className="px-2 py-4 text-stone-600">{row.qc?.result ?? '—'}</td>
                        <td className="px-2 py-4 text-stone-600">{formatDate(row.updated_at)}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            )}
          </div>

          <div className="rounded-2xl border border-stone-200/70 bg-stone-50/60 p-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold text-stone-900">Render preview</h3>
                <p className="text-xs text-stone-500">Selected animation detail & QC status.</p>
              </div>
              {selectedAnimation?.status && (
                <Badge variant="outline" className={cn('border', chipTone(selectedAnimation.status))}>
                  {statusLabel(selectedAnimation.status)}
                </Badge>
              )}
            </div>

            {!selectedAnimation ? (
              <div className="mt-4 rounded-xl border border-dashed border-stone-200 bg-white/70 p-4 text-sm text-stone-500">
                Select an animation row to preview render details.
              </div>
            ) : (
              <div className="mt-4 space-y-4">
                <div className="aspect-[9/16] w-full overflow-hidden rounded-2xl border border-stone-200 bg-stone-900">
                  {previewUrl ? (
                    <video className="h-full w-full object-cover" controls src={previewUrl} />
                  ) : (
                    <div className="flex h-full w-full items-center justify-center text-sm text-stone-300">
                      No video artifact found.
                    </div>
                  )}
                </div>

                <div className="space-y-2 text-xs text-stone-600">
                  <div className="flex items-center justify-between">
                    <span>Pipeline stage</span>
                    <span className="font-semibold text-stone-800">
                      {selectedAnimation.pipeline_stage ?? '—'}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>QC result</span>
                    <span className="font-semibold text-stone-800">
                      {selectedAnimation.qc?.result ?? '—'}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Render status</span>
                    <span className="font-semibold text-stone-800">
                      {selectedAnimation.render?.status ?? '—'}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Seed</span>
                    <span className="font-semibold text-stone-800">
                      {selectedAnimation.render?.seed ?? '—'}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Canvas</span>
                    <span className="font-semibold text-stone-800">
                      {selectedAnimation.render?.width ?? '—'} x {selectedAnimation.render?.height ?? '—'}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>FPS</span>
                    <span className="font-semibold text-stone-800">
                      {selectedAnimation.render?.fps ?? '—'}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Duration</span>
                    <span className="font-semibold text-stone-800">
                      {selectedAnimation.render?.duration_ms ?? '—'} ms
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Renderer</span>
                    <span className="font-semibold text-stone-800">
                      {selectedAnimation.render?.renderer_version ?? '—'}
                    </span>
                  </div>
                </div>

                <div className="rounded-xl border border-stone-200 bg-white/80 p-3 text-xs text-stone-600">
                  <div className="mb-2 text-[0.65rem] uppercase tracking-[0.2em] text-stone-400">
                    Artifacts
                  </div>
                  {artifactsLoading ? (
                    <div>Loading artifacts…</div>
                  ) : artifactsError ? (
                    <div className="text-rose-600">{artifactsError}</div>
                  ) : artifacts.length === 0 ? (
                    <div>No artifacts available.</div>
                  ) : (
                    <ul className="space-y-1">
                      {artifacts.map((item) => (
                        <li key={item.id} className="flex items-center justify-between">
                          <span className="font-semibold text-stone-700">{item.artifact_type}</span>
                          <span className="truncate text-[0.7rem] text-stone-500">
                            {item.storage_path}
                          </span>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </section>

      <section className="rounded-[28px] border border-stone-200/80 bg-white/90 p-6 shadow-2xl shadow-stone-900/10">
        <div className="flex flex-col gap-4 border-b border-stone-200/70 pb-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h2 className="text-2xl font-semibold text-stone-900">Idea Gate</h2>
            <p className="text-sm text-stone-600">
              Losuj propozycje z repozytorium i sklasifikuj każdą z nich.
            </p>
          </div>
          <div className="text-xs text-stone-500">
            <div>Updated: {ideaUpdatedAt ? ideaUpdatedAt.toLocaleTimeString() : 'waiting for data'}</div>
          </div>
        </div>

        <div className="mt-4 flex flex-wrap items-end gap-3">
          <label className="flex min-w-[180px] flex-col gap-1 text-xs font-semibold uppercase tracking-[0.15em] text-stone-500">
            Liczba propozycji
            <input
              className="rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700 focus:border-stone-400 focus:outline-none"
              value={ideaSampleCount}
              onChange={(event) => setIdeaSampleCount(event.target.value)}
            />
          </label>
          <div className="flex flex-wrap gap-2">
            <Button className="rounded-full" onClick={fetchIdeaCandidates} disabled={ideaLoading}>
              Losuj propozycje
            </Button>
            <Button
              variant="ghost"
              className="rounded-full"
              onClick={() => {
                setIdeaCandidates([])
                setIdeaDecisions({})
                setSelectedIdea(null)
                setIdeaDecisionError(null)
                setIdeaDecisionMessage(null)
              }}
              disabled={ideaLoading}
            >
              Wyczyść
            </Button>
          </div>
        </div>

        {ideaDecisionMessage ? (
          <div className="mt-4 rounded-2xl border border-emerald-200 bg-emerald-50/70 p-4 text-xs text-emerald-800">
            {ideaDecisionMessage}
          </div>
        ) : null}
        {ideaDecisionError ? (
          <div className="mt-4 rounded-2xl border border-rose-200 bg-rose-50/70 p-4 text-xs text-rose-700">
            {ideaDecisionError}
          </div>
        ) : null}

        <div className="mt-4 grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
          <div className="space-y-3">
            {ideaLoading ? (
              <div className="rounded-2xl border border-dashed border-stone-200 bg-stone-50/60 p-6 text-sm text-stone-600">
                Loading ideas…
              </div>
            ) : ideaError ? (
              <div className="rounded-2xl border border-rose-200 bg-rose-50/70 p-6 text-sm text-rose-700">
                <div className="font-semibold">Failed to load</div>
                <div>{ideaError}</div>
              </div>
            ) : ideaCandidates.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-stone-200 bg-stone-50/60 p-6 text-sm text-stone-600">
                No ideas sampled yet. Click “Losuj propozycje”.
              </div>
            ) : (
              ideaCandidates.map((idea) => {
                const decision = ideaDecisions[idea.id] || ''
                return (
                  <div
                    key={idea.id}
                    className={cn(
                      'rounded-2xl border border-stone-200 bg-white/80 p-4 shadow-sm transition hover:bg-stone-50',
                      selectedIdea?.id === idea.id && 'border-stone-400 bg-stone-50',
                    )}
                    onClick={() => setSelectedIdea(idea)}
                  >
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <div className="text-base font-semibold text-stone-900">
                          {idea.title ?? 'Untitled'}
                        </div>
                        <div className="mt-1 text-sm text-stone-600">
                          {idea.summary ?? '—'}
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge variant="outline" className={cn('border', similarityTone(idea.similarity_status))}>
                          {idea.similarity_status ?? '—'}
                        </Badge>
                        <Badge variant="outline" className={cn('border', chipTone(idea.status))}>
                          {idea.status ?? '—'}
                        </Badge>
                      </div>
                    </div>
                    <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-stone-500">
                      <span>Source: {idea.generator_source ?? '—'}</span>
                    </div>
                    <div className="mt-4 flex flex-wrap gap-2">
                      <Button
                        variant={decision === 'picked' ? 'default' : 'outline'}
                        className="rounded-full"
                        onClick={() =>
                          setIdeaDecisions((prev) => ({ ...prev, [idea.id]: 'picked' }))
                        }
                      >
                        Do generowania
                      </Button>
                      <Button
                        variant={decision === 'later' ? 'default' : 'outline'}
                        className="rounded-full"
                        onClick={() =>
                          setIdeaDecisions((prev) => ({ ...prev, [idea.id]: 'later' }))
                        }
                      >
                        Na później
                      </Button>
                      <Button
                        variant={decision === 'rejected' ? 'destructive' : 'outline'}
                        className="rounded-full"
                        onClick={() =>
                          setIdeaDecisions((prev) => ({ ...prev, [idea.id]: 'rejected' }))
                        }
                      >
                        Odrzuć
                      </Button>
                    </div>
                  </div>
                )
              })
            )}
          </div>

          <div className="rounded-2xl border border-stone-200/70 bg-stone-50/60 p-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold text-stone-900">Idea detail</h3>
                <p className="text-xs text-stone-500">Selection signal and narrative preview.</p>
              </div>
              {selectedIdea?.similarity_status && (
                <Badge variant="outline" className={cn('border', similarityTone(selectedIdea.similarity_status))}>
                  {selectedIdea.similarity_status}
                </Badge>
              )}
            </div>

            {!selectedIdea ? (
              <div className="mt-4 rounded-xl border border-dashed border-stone-200 bg-white/70 p-4 text-sm text-stone-500">
                Select an idea candidate to preview details.
              </div>
            ) : (
              <div className="mt-4 space-y-4 text-sm text-stone-700">
                <div>
                  <div className="text-xs uppercase tracking-[0.2em] text-stone-400">Title</div>
                  <div className="mt-1 text-base font-semibold text-stone-900">
                    {selectedIdea.title ?? 'Untitled'}
                  </div>
                </div>
                <div>
                  <div className="text-xs uppercase tracking-[0.2em] text-stone-400">Summary</div>
                  <div className="mt-1 text-sm text-stone-700">
                    {selectedIdea.summary ?? '—'}
                  </div>
                </div>
                <div>
                  <div className="text-xs uppercase tracking-[0.2em] text-stone-400">What to expect</div>
                  <div className="mt-1 text-sm text-stone-700">
                    {selectedIdea.what_to_expect ?? '—'}
                  </div>
                </div>
                <div>
                  <div className="text-xs uppercase tracking-[0.2em] text-stone-400">Preview</div>
                  <div className="mt-1 text-sm text-stone-700">
                    {selectedIdea.preview ?? '—'}
                  </div>
                </div>
                <div className="grid gap-2 text-xs">
                  <div className="flex items-center justify-between">
                    <span>Status</span>
                    <span className="font-semibold text-stone-800">
                      {selectedIdea.status ?? '—'}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Decision at</span>
                    <span className="font-semibold text-stone-800">
                      {formatDate(selectedIdea.decision_at)}
                    </span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="mt-6 flex flex-wrap items-center justify-between gap-3">
          <div className="text-xs text-stone-500">
            Wymagana klasyfikacja wszystkich propozycji. Decyzje:{" "}
            {Object.values(ideaDecisions).filter(Boolean).length}/{ideaCandidates.length}
          </div>
          <Button
            className="rounded-full"
            onClick={submitIdeaDecisions}
            disabled={ideaDecisionLoading || ideaCandidates.length === 0}
          >
            {ideaDecisionLoading ? 'Zapisywanie…' : 'Zatwierdź wybór i uruchom'}
          </Button>
        </div>
      </section>

      <section className="rounded-[28px] border border-stone-200/80 bg-white/90 p-6 shadow-2xl shadow-stone-900/10">
        <div className="flex flex-col gap-4 border-b border-stone-200/70 pb-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h2 className="text-2xl font-semibold text-stone-900">Audit log</h2>
            <p className="text-sm text-stone-600">Chronological stream of system actions with filters.</p>
          </div>
          <div className="text-xs text-stone-500">
            <div>Updated: {auditUpdatedAt ? auditUpdatedAt.toLocaleTimeString() : 'waiting for data'}</div>
          </div>
        </div>

        <div className="mt-4 flex flex-wrap items-end gap-3">
          <label className="flex min-w-[200px] flex-col gap-1 text-xs font-semibold uppercase tracking-[0.15em] text-stone-500">
            Event type
            <input
              className="rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700 focus:border-stone-400 focus:outline-none"
              placeholder="qc_decision / publish_record"
              value={auditType}
              onChange={(event) => setAuditType(event.target.value)}
            />
          </label>
          <label className="flex min-w-[200px] flex-col gap-1 text-xs font-semibold uppercase tracking-[0.15em] text-stone-500">
            Source
            <input
              className="rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700 focus:border-stone-400 focus:outline-none"
              placeholder="pipeline / api"
              value={auditSource}
              onChange={(event) => setAuditSource(event.target.value)}
            />
          </label>
          <label className="flex min-w-[220px] flex-1 flex-col gap-1 text-xs font-semibold uppercase tracking-[0.15em] text-stone-500">
            Actor user ID
            <input
              className="rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700 focus:border-stone-400 focus:outline-none"
              placeholder="UUID"
              value={auditActor}
              onChange={(event) => setAuditActor(event.target.value)}
            />
          </label>
          <div className="flex flex-wrap gap-2">
            <Button className="rounded-full" onClick={fetchAuditEvents} disabled={auditLoading}>
              Apply filters
            </Button>
            <Button
              variant="ghost"
              className="rounded-full"
              onClick={() => {
                setAuditType('')
                setAuditSource('')
                setAuditActor('')
                window.setTimeout(fetchAuditEvents, 0)
              }}
              disabled={auditLoading}
            >
              Reset
            </Button>
          </div>
        </div>

        <div className="mt-4 overflow-x-auto">
          {auditLoading ? (
            <div className="rounded-2xl border border-dashed border-stone-200 bg-stone-50/60 p-6 text-sm text-stone-600">
              Loading audit events…
            </div>
          ) : auditError ? (
            <div className="rounded-2xl border border-rose-200 bg-rose-50/70 p-6 text-sm text-rose-700">
              <div className="font-semibold">Failed to load</div>
              <div>{auditError}</div>
            </div>
          ) : (
            <table className="min-w-[780px] w-full text-left text-sm">
              <thead className="text-xs uppercase tracking-[0.18em] text-stone-500">
                <tr>
                  <th className="px-2 py-3">Type</th>
                  <th className="px-2 py-3">Source</th>
                  <th className="px-2 py-3">Actor</th>
                  <th className="px-2 py-3">Occurred</th>
                  <th className="px-2 py-3">Payload</th>
                </tr>
              </thead>
              <tbody>
                {auditEvents.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-2 py-6 text-center text-stone-500">
                      No audit events matched. Trigger actions to populate the log.
                    </td>
                  </tr>
                ) : (
                  auditEvents.map((event) => (
                    <tr key={event.id} className="border-t border-stone-200/70">
                      <td className="px-2 py-4 text-stone-800">{event.event_type ?? '—'}</td>
                      <td className="px-2 py-4 text-stone-600">{event.source ?? '—'}</td>
                      <td className="px-2 py-4 font-mono text-xs text-stone-600">
                        {event.actor_user_id ?? '—'}
                      </td>
                      <td className="px-2 py-4 text-stone-600">{formatDate(event.occurred_at)}</td>
                      <td className="px-2 py-4 text-xs text-stone-500">
                        {event.payload ? JSON.stringify(event.payload) : '—'}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          )}
        </div>
      </section>

      <section className="rounded-[28px] border border-stone-200/80 bg-white/90 p-6 shadow-2xl shadow-stone-900/10">
        <div className="flex flex-col gap-4 border-b border-stone-200/70 pb-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h2 className="text-2xl font-semibold text-stone-900">Operations</h2>
            <p className="text-sm text-stone-600">
              Trigger pipeline actions (enqueue, rerun, cleanup) directly from the panel.
            </p>
          </div>
          <Badge variant="outline" className="border border-amber-200 text-amber-800">
            operator-only
          </Badge>
        </div>

        {opsMessage ? (
          <div className="mt-4 rounded-2xl border border-emerald-200 bg-emerald-50/70 p-4 text-xs text-emerald-800">
            {opsMessage}
          </div>
        ) : null}
        {opsError ? (
          <div className="mt-4 rounded-2xl border border-rose-200 bg-rose-50/70 p-4 text-xs text-rose-700">
            {opsError}
          </div>
        ) : null}

        <div className="mt-6 grid gap-4 lg:grid-cols-3">
          <div className="rounded-2xl border border-stone-200 bg-stone-50/70 p-4">
            <div className="text-sm font-semibold text-stone-900">Enqueue pipeline</div>
            <div className="text-xs text-stone-500">Start a fresh pipeline run.</div>
            <div className="mt-3 space-y-2 text-sm">
              <label className="flex flex-col gap-1 text-xs uppercase tracking-[0.18em] text-stone-500">
                DSL template
                <input
                  className="rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700"
                  value={enqueueDsl}
                  onChange={(event) => setEnqueueDsl(event.target.value)}
                />
              </label>
              <label className="flex flex-col gap-1 text-xs uppercase tracking-[0.18em] text-stone-500">
                Output root
                <input
                  className="rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700"
                  value={enqueueOutRoot}
                  onChange={(event) => setEnqueueOutRoot(event.target.value)}
                />
              </label>
              <Button className="w-full rounded-full" onClick={handleEnqueue} disabled={opsEnqueueLoading}>
                {opsEnqueueLoading ? 'Enqueuing…' : 'Enqueue'}
              </Button>
            </div>
          </div>

          <div className="rounded-2xl border border-stone-200 bg-stone-50/70 p-4">
            <div className="text-sm font-semibold text-stone-900">Rerun render</div>
            <div className="text-xs text-stone-500">Requeue a render for a chosen animation.</div>
            <div className="mt-3 space-y-2 text-sm">
              <label className="flex flex-col gap-1 text-xs uppercase tracking-[0.18em] text-stone-500">
                Animation ID
                <input
                  className="rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700"
                  placeholder="UUID"
                  value={rerunAnimationId}
                  onChange={(event) => setRerunAnimationId(event.target.value)}
                />
              </label>
              <label className="flex flex-col gap-1 text-xs uppercase tracking-[0.18em] text-stone-500">
                Output root
                <input
                  className="rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700"
                  value={rerunOutRoot}
                  onChange={(event) => setRerunOutRoot(event.target.value)}
                />
              </label>
              <Button className="w-full rounded-full" onClick={handleRerun} disabled={opsRerunLoading}>
                {opsRerunLoading ? 'Requeuing…' : 'Rerun render'}
              </Button>
            </div>
          </div>

          <div className="rounded-2xl border border-stone-200 bg-stone-50/70 p-4">
            <div className="text-sm font-semibold text-stone-900">Cleanup jobs</div>
            <div className="text-xs text-stone-500">Mark stale running jobs as failed.</div>
            <div className="mt-3 space-y-2 text-sm">
              <label className="flex flex-col gap-1 text-xs uppercase tracking-[0.18em] text-stone-500">
                Older than (min)
                <input
                  className="rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700"
                  value={cleanupOlderMin}
                  onChange={(event) => setCleanupOlderMin(event.target.value)}
                />
              </label>
              <Button className="w-full rounded-full" onClick={handleCleanup} disabled={opsCleanupLoading}>
                {opsCleanupLoading ? 'Cleaning…' : 'Cleanup jobs'}
              </Button>
            </div>
          </div>
        </div>
      </section>

      <section className="rounded-[28px] border border-stone-200/80 bg-white/90 p-6 shadow-2xl shadow-stone-900/10">
        <div className="flex flex-col gap-4 border-b border-stone-200/70 pb-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h2 className="text-2xl font-semibold text-stone-900">Settings snapshot</h2>
            <p className="text-sm text-stone-600">
              Read-only view of environment flags and timeouts used by the pipeline.
            </p>
          </div>
          <Badge variant="outline" className="border border-stone-300 text-stone-600">
            read-only
          </Badge>
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-2">
          <Button variant="outline" className="rounded-full" onClick={fetchSettings} disabled={settingsLoading}>
            {settingsLoading ? 'Refreshing…' : 'Refresh settings'}
          </Button>
          {settingsError ? (
            <span className="text-xs text-rose-600">{settingsError}</span>
          ) : null}
        </div>

        {settingsLoading ? (
          <div className="mt-4 rounded-2xl border border-dashed border-stone-200 bg-stone-50/60 p-6 text-sm text-stone-600">
            Loading settings…
          </div>
        ) : settings ? (
          <div className="mt-6 grid gap-4 lg:grid-cols-2">
            <div className="rounded-2xl border border-stone-200 bg-stone-50/70 p-4">
              <div className="text-sm font-semibold text-stone-900">Core services</div>
              <div className="text-xs text-stone-500">Live runtime configuration.</div>
              <div className="mt-3 space-y-2 text-sm">
                <SettingRow label="DATABASE_URL" value={settings.database_url} />
                <SettingRow label="REDIS_URL" value={settings.redis_url} />
                <SettingRow label="ARTIFACTS_BASE_DIR" value={settings.artifacts_base_dir} />
                <SettingRow label="OPERATOR_GUARD" value={settings.operator_guard ? 'enabled' : 'disabled'} />
              </div>
            </div>
            <div className="rounded-2xl border border-stone-200 bg-stone-50/70 p-4">
              <div className="text-sm font-semibold text-stone-900">Pipeline timeouts</div>
              <div className="text-xs text-stone-500">Worker and render thresholds.</div>
              <div className="mt-3 space-y-2 text-sm">
                <SettingRow label="RQ_JOB_TIMEOUT" value={settings.rq_job_timeout} />
                <SettingRow label="RQ_RENDER_TIMEOUT" value={settings.rq_render_timeout} />
                <SettingRow label="FFMPEG_TIMEOUT_S" value={settings.ffmpeg_timeout_s} />
              </div>
            </div>
            <div className="rounded-2xl border border-stone-200 bg-stone-50/70 p-4">
              <div className="text-sm font-semibold text-stone-900">Idea Gate</div>
              <div className="text-xs text-stone-500">Similarity and selection settings.</div>
              <div className="mt-3 space-y-2 text-sm">
                <SettingRow label="IDEA_GATE_ENABLED" value={settings.idea_gate_enabled} />
                <SettingRow label="IDEA_GATE_COUNT" value={settings.idea_gate_count} />
                <SettingRow label="IDEA_GATE_THRESHOLD" value={settings.idea_gate_threshold} />
                <SettingRow label="IDEA_GATE_AUTO" value={settings.idea_gate_auto} />
              </div>
            </div>
            <div className="rounded-2xl border border-stone-200 bg-stone-50/70 p-4">
              <div className="text-sm font-semibold text-stone-900">OpenAI generator</div>
              <div className="text-xs text-stone-500">LLM provider runtime config.</div>
              <div className="mt-3 space-y-2 text-sm">
                <SettingRow label="OPENAI_MODEL" value={settings.openai_model} />
                <SettingRow label="OPENAI_BASE_URL" value={settings.openai_base_url} />
                <SettingRow label="OPENAI_TEMPERATURE" value={settings.openai_temperature} />
                <SettingRow label="OPENAI_MAX_OUTPUT_TOKENS" value={settings.openai_max_output_tokens} />
              </div>
            </div>
          </div>
        ) : (
          <div className="mt-4 rounded-2xl border border-dashed border-stone-200 bg-stone-50/60 p-6 text-sm text-stone-600">
            Settings are not available.
          </div>
        )}

        <p className="mt-4 text-xs text-stone-500">
          Values are fetched from the backend runtime via <code>/settings</code>.
        </p>
      </section>
    </div>
  )
}

export default App
