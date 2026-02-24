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

type PublishRecordRow = {
  id: string
  render_id?: string | null
  platform_type?: 'youtube' | 'tiktok' | string | null
  status?: 'queued' | 'uploading' | 'published' | 'failed' | 'manual_confirmed' | string | null
  content_id?: string | null
  url?: string | null
  scheduled_for?: string | null
  published_at?: string | null
  error_payload?: Record<string, unknown> | null
  created_at?: string | null
  updated_at?: string | null
}

type MetricsDailyRow = {
  id: string
  platform_type?: 'youtube' | 'tiktok' | string | null
  content_id?: string | null
  publish_record_id?: string | null
  render_id?: string | null
  date?: string | null
  views?: number | null
  likes?: number | null
  comments?: number | null
  shares?: number | null
  watch_time_seconds?: number | null
  avg_view_percentage?: number | null
  avg_view_duration_seconds?: number | null
  extra_metrics?: Record<string, unknown> | null
  created_at?: string | null
}

type PlannerSettings = {
  timezone?: string
  daily_publish_hour?: number
  daily_publish_minute?: number
  publish_window_minutes?: number
  target_per_day?: number
}

type GodotManualStepResult = {
  ok?: boolean
  mode?: 'validate' | 'preview' | 'render'
  script_path?: string
  out_path?: string
  out_exists?: boolean
  log_file?: string | null
  stdout?: string
  stderr?: string
  exit_code?: number
  script_hash?: string
  script_exists?: boolean
  compiler_meta?: Record<string, unknown>
  validation_report?: Record<string, unknown>
}

type GodotManualHistoryRow = {
  id: string
  recorded_at?: string | null
  step?: 'compile' | 'validate' | 'preview' | 'render' | string | null
  ok?: boolean | null
  actor_user_id?: string | null
  idea_id?: string | null
  script_path?: string | null
  out_path?: string | null
  out_exists?: boolean | null
  log_file?: string | null
  exit_code?: number | null
  script_hash?: string | null
  error?: string | null
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
  capability_status?: string | null
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
  worker?: {
    redis_ok?: boolean
    online?: boolean
    worker_count?: number
    queue_depth?: number | null
  }
}

type DslGap = {
  id: string
  gap_key?: string | null
  dsl_version?: string | null
  implemented_in_version?: string | null
  resolved_at?: string | null
  feature?: string | null
  reason?: string | null
  impact?: string | null
  status?: 'new' | 'accepted' | 'in_progress' | 'implemented' | 'rejected' | null
  created_at?: string | null
  updated_at?: string | null
}

type DslVersionRow = {
  id: string
  version: string
  is_active?: boolean
  notes?: string | null
  created_at?: string | null
  introduced_gaps?: number
  implemented_gaps?: number
}

type BlockedIdeaCandidate = {
  id: string
  title?: string | null
  status?: string | null
  gaps?: Array<{ feature?: string | null; status?: string | null }>
}

const STATUS_ORDER = ['queued', 'running', 'failed', 'succeeded']
const LANGUAGE_OPTIONS = [
  { value: 'pl', label: 'PL' },
  { value: 'en', label: 'EN' },
] as const
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
const APP_VIEWS = ['home', 'plan', 'flow', 'repositories', 'settings'] as const
type AppView = (typeof APP_VIEWS)[number]
const CANDIDATE_CAPABILITY_ORDER = ['unverified', 'feasible', 'blocked_by_gaps'] as const
const CANDIDATE_STATUS_ORDER = ['new', 'later', 'picked', 'rejected'] as const
const REPO_CARD_ORDER = [
  'idea_candidates',
  'ideas',
  'dsl_gaps',
  'animations',
  'renders',
  'artifacts',
  'jobs',
  'sfx',
  'music',
] as const

const REPO_LABELS: Record<(typeof REPO_CARD_ORDER)[number], string> = {
  idea_candidates: 'Idea Candidates',
  ideas: 'Ideas',
  dsl_gaps: 'DSL Gaps',
  animations: 'Animations',
  renders: 'Renders',
  artifacts: 'Artifacts',
  jobs: 'Jobs',
  sfx: 'SFX',
  music: 'Music',
}

const REPO_HINTS: Record<(typeof REPO_CARD_ORDER)[number], string> = {
  idea_candidates: 'Surowe propozycje przed decyzją operatora (new/later/picked/rejected).',
  ideas: 'Idee w procesie pipeline (unverified/ready/blocked/feasible/compiled).',
  dsl_gaps: 'Braki DSL blokujące ideę.',
  animations: 'Animacje powiązane z ideami.',
  renders: 'Renderowania i ich statusy.',
  artifacts: 'Pliki wynikowe (wideo/metadata).',
  jobs: 'Joby pipeline (queued/running/failed).',
  sfx: 'Repozytorium efektów dźwiękowych (planowane).',
  music: 'Repozytorium podkładów muzycznych (planowane).',
}

function getViewFromUrl(): AppView {
  if (typeof window === 'undefined') return 'home'
  const params = new URLSearchParams(window.location.search)
  const value = params.get('view')
  if (value && APP_VIEWS.includes(value as AppView)) {
    return value as AppView
  }
  return 'home'
}

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
const TOKEN_BUDGET_ALERT_THRESHOLD = 0.8

type TokenBudgetGroup = {
  limit?: number
  members?: string[]
}

type TokenBudgetConfig = {
  models?: Record<string, number>
  groups?: Record<string, TokenBudgetGroup | number>
}

function parseTokenBudgets(raw?: string | null): TokenBudgetConfig | null {
  if (!raw) return null
  try {
    const parsed = JSON.parse(raw)
    if (!parsed || typeof parsed !== 'object') return null
    return parsed as TokenBudgetConfig
  } catch {
    return null
  }
}

function manualGodotFileUrl(path?: string | null): string | null {
  if (!path) return null
  return `${API_BASE}/godot/manual-file?path=${encodeURIComponent(path)}`
}

function dateKeyInTimezone(value: string | Date, timeZone: string): string {
  const date = value instanceof Date ? value : new Date(value)
  const formatter = new Intl.DateTimeFormat('en-CA', {
    timeZone,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  })
  return formatter.format(date)
}

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
  dev_manual_flow?: string
  operator_guard?: boolean
  artifacts_base_dir?: string
  openai_model?: string
  openai_base_url?: string
  openai_temperature?: string
  openai_max_output_tokens?: string
  llm_token_budgets?: string
}

type LLMRouteMetrics = {
  calls?: number
  success?: number
  errors?: number
  retries?: number
  latency_ms_total?: number
  prompt_tokens_total?: number
  completion_tokens_total?: number
  estimated_cost_usd_total?: number
}

type LLMMetricsResponse = {
  routes?: Record<string, LLMRouteMetrics>
  budget?: {
    spent_usd_total?: number
    daily_budget_usd?: number
    budget_day?: string
  }
  state_backend?: string
}

type SystemStatusResponse = {
  service_status?: Array<{ service?: string; status?: string; details?: string | null }>
  repo_counts?: Record<
    string,
    {
      total?: number | null
      by_status?: Record<string, number>
      by_capability?: Record<string, number>
      placeholder?: boolean
    }
  >
  worker?: {
    redis_ok?: boolean
    online?: boolean
    worker_count?: number
    queue_depth?: number | null
  }
  dsl_version_current?: string | null
  updated_at?: string
  partial_failures?: string[]
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
  const [activeView, setActiveView] = useState<AppView>(getViewFromUrl)
  const [uiLanguage, setUiLanguage] = useState<'pl' | 'en'>(() => {
    if (typeof window === 'undefined') return 'pl'
    return (window.localStorage.getItem('shortlab.ui.language') as 'pl' | 'en') || 'pl'
  })
  const [uiTheme, setUiTheme] = useState<'light' | 'dark'>(() => {
    if (typeof window === 'undefined') return 'light'
    return (window.localStorage.getItem('shortlab.ui.theme') as 'light' | 'dark') || 'light'
  })
  const [systemStatus, setSystemStatus] = useState<SystemStatusResponse | null>(null)
  const [systemStatusLoading, setSystemStatusLoading] = useState(false)
  const [systemStatusError, setSystemStatusError] = useState<string | null>(null)
  const [summaryData, setSummaryData] = useState<SummaryResponse | null>(null)
  const [summaryLoading, setSummaryLoading] = useState(true)

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
  const [publishRecords, setPublishRecords] = useState<PublishRecordRow[]>([])
  const [publishRecordsError, setPublishRecordsError] = useState<string | null>(null)
  const [publishRecordsLoading, setPublishRecordsLoading] = useState(false)
  const [planPublishRecords, setPlanPublishRecords] = useState<PublishRecordRow[]>([])
  const [planPublishRecordsError, setPlanPublishRecordsError] = useState<string | null>(null)
  const [planPublishRecordsLoading, setPlanPublishRecordsLoading] = useState(false)
  const [planMetricsRows, setPlanMetricsRows] = useState<MetricsDailyRow[]>([])
  const [planMetricsError, setPlanMetricsError] = useState<string | null>(null)
  const [planMetricsLoading, setPlanMetricsLoading] = useState(false)
  const [plannerSettings, setPlannerSettings] = useState<PlannerSettings | null>(null)
  const [plannerSettingsLoading, setPlannerSettingsLoading] = useState(false)
  const [plannerSettingsError, setPlannerSettingsError] = useState<string | null>(null)
  const [plannerSettingsMessage, setPlannerSettingsMessage] = useState<string | null>(null)
  const [plannerTimezoneInput, setPlannerTimezoneInput] = useState('UTC')
  const [plannerHourInput, setPlannerHourInput] = useState('18')
  const [plannerMinuteInput, setPlannerMinuteInput] = useState('00')
  const [plannerWindowInput, setPlannerWindowInput] = useState('120')
  const [plannerTargetInput, setPlannerTargetInput] = useState('1')
  const [reviewActionMessage, setReviewActionMessage] = useState<string | null>(null)
  const [reviewActionError, setReviewActionError] = useState<string | null>(null)
  const [qcActionLoading, setQcActionLoading] = useState(false)
  const [publishActionLoading, setPublishActionLoading] = useState(false)
  const [qcResultInput, setQcResultInput] = useState<'accepted' | 'rejected' | 'regenerate'>('accepted')
  const [qcNotesInput, setQcNotesInput] = useState('')
  const [publishPlatformInput, setPublishPlatformInput] = useState<'youtube' | 'tiktok'>('youtube')
  const [publishStatusInput, setPublishStatusInput] = useState<
    'queued' | 'uploading' | 'published' | 'failed' | 'manual_confirmed'
  >('manual_confirmed')
  const [publishContentIdInput, setPublishContentIdInput] = useState('')
  const [publishUrlInput, setPublishUrlInput] = useState('')
  const [publishErrorInput, setPublishErrorInput] = useState('')

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
  const [manualPickCandidates, setManualPickCandidates] = useState<IdeaCandidate[]>([])
  const [manualPickCandidateId, setManualPickCandidateId] = useState('')
  const [manualPickLoading, setManualPickLoading] = useState(false)
  const [manualPickError, setManualPickError] = useState<string | null>(null)
  const [generatorMode, setGeneratorMode] = useState<'llm' | 'text' | 'file'>('llm')
  const [generatorLimit, setGeneratorLimit] = useState('5')
  const [generatorPrompt, setGeneratorPrompt] = useState('')
  const [generatorText, setGeneratorText] = useState('')
  const [generatorFileName, setGeneratorFileName] = useState('')
  const [generatorFileContent, setGeneratorFileContent] = useState('')
  const [generatorMessage, setGeneratorMessage] = useState<string | null>(null)
  const [generatorError, setGeneratorError] = useState<string | null>(null)
  const [generatorLoading, setGeneratorLoading] = useState(false)

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
  const [manualIdeaId, setManualIdeaId] = useState('')
  const [manualCompileLoading, setManualCompileLoading] = useState(false)
  const [manualCompileMessage, setManualCompileMessage] = useState<string | null>(null)
  const [manualCompileError, setManualCompileError] = useState<string | null>(null)
  const [manualPipelineLoading, setManualPipelineLoading] = useState(false)
  const [manualPipelineMessage, setManualPipelineMessage] = useState<string | null>(null)
  const [manualPipelineError, setManualPipelineError] = useState<string | null>(null)
  const [godotScriptPath, setGodotScriptPath] = useState('')
  const [godotSeconds, setGodotSeconds] = useState('2')
  const [godotFps, setGodotFps] = useState('12')
  const [godotMaxNodes, setGodotMaxNodes] = useState('200')
  const [godotPreviewScale, setGodotPreviewScale] = useState('0.5')
  const [godotStepLoading, setGodotStepLoading] = useState<Record<string, boolean>>({})
  const [godotStepStatus, setGodotStepStatus] = useState<Record<string, 'idle' | 'success' | 'fail'>>({})
  const [godotStepError, setGodotStepError] = useState<Record<string, string | null>>({})
  const [godotStepResult, setGodotStepResult] = useState<Record<string, GodotManualStepResult | null>>({})
  const [godotHistoryRows, setGodotHistoryRows] = useState<GodotManualHistoryRow[]>([])
  const [godotHistoryLoading, setGodotHistoryLoading] = useState(false)
  const [godotHistoryError, setGodotHistoryError] = useState<string | null>(null)

  const [settings, setSettings] = useState<SettingsResponse | null>(null)
  const [settingsLoading, setSettingsLoading] = useState(false)
  const [settingsError, setSettingsError] = useState<string | null>(null)
  const [llmMetrics, setLlmMetrics] = useState<LLMMetricsResponse | null>(null)
  const [llmMetricsLoading, setLlmMetricsLoading] = useState(false)
  const [llmMetricsError, setLlmMetricsError] = useState<string | null>(null)
  const [llmMetricsUpdatedAt, setLlmMetricsUpdatedAt] = useState<Date | null>(null)
  const [dslGaps, setDslGaps] = useState<DslGap[]>([])
  const [dslGapsLoading, setDslGapsLoading] = useState(false)
  const [dslGapsError, setDslGapsError] = useState<string | null>(null)
  const [dslGapsUpdatedAt, setDslGapsUpdatedAt] = useState<Date | null>(null)
  const [dslGapPromptId, setDslGapPromptId] = useState<string | null>(null)
  const [dslVersions, setDslVersions] = useState<DslVersionRow[]>([])
  const [dslVersionsLoading, setDslVersionsLoading] = useState(false)
  const [dslVersionsError, setDslVersionsError] = useState<string | null>(null)
  const [dslVersionsUpdatedAt, setDslVersionsUpdatedAt] = useState<Date | null>(null)
  const [verifyLimit, setVerifyLimit] = useState('20')
  const [verifyLoading, setVerifyLoading] = useState(false)
  const [gapActionLoading, setGapActionLoading] = useState<Record<string, boolean>>({})
  const [blockedCandidates, setBlockedCandidates] = useState<BlockedIdeaCandidate[]>([])
  const [verifierInfo, setVerifierInfo] = useState<{
    provider?: string | null
    model?: string | null
    fallbackUsed?: boolean | null
    verified?: number | null
  } | null>(null)
  const [candidateList, setCandidateList] = useState<IdeaCandidate[]>([])
  const [candidateListLoading, setCandidateListLoading] = useState(false)
  const [candidateListError, setCandidateListError] = useState<string | null>(null)
  const [candidateActionLoading, setCandidateActionLoading] = useState<Record<string, boolean>>({})
  const [candidateFilterStatus, setCandidateFilterStatus] = useState('')
  const [candidateFilterCapability, setCandidateFilterCapability] = useState('')
  const [candidateFilterSimilarity, setCandidateFilterSimilarity] = useState('')
  const [candidateListLimit, setCandidateListLimit] = useState('25')
  const manualFlowEnabled = settings?.dev_manual_flow === '1'

  const opsHeaders = (): Record<string, string> => {
    const token = import.meta.env.VITE_OPERATOR_TOKEN as string | undefined
    const headers: Record<string, string> = { 'Content-Type': 'application/json' }
    if (token) {
      headers['X-Operator-Token'] = token
    }
    return headers
  }

  const readApiError = async (response: Response) => {
    let detail = ''
    try {
      const payload = await response.json()
      if (payload && typeof payload === 'object') {
        const detailValue = (payload as { detail?: unknown; message?: unknown }).detail
        const messageValue = (payload as { detail?: unknown; message?: unknown }).message
        if (typeof detailValue === 'string') {
          detail = detailValue
        } else if (detailValue && typeof detailValue === 'object') {
          const d = detailValue as Record<string, unknown>
          const parts = [
            typeof d.exit_code === 'number' ? `exit=${d.exit_code}` : null,
            typeof d.log_file === 'string' ? `log=${d.log_file}` : null,
            typeof d.stderr === 'string' && d.stderr ? `stderr=${d.stderr}` : null,
            typeof d.stdout === 'string' && d.stdout ? `stdout=${d.stdout}` : null,
          ].filter(Boolean)
          detail = parts.join(' | ') || JSON.stringify(detailValue)
        } else if (typeof messageValue === 'string') {
          detail = messageValue
        } else {
          detail = JSON.stringify(payload)
        }
      }
    } catch {
      try {
        detail = await response.text()
      } catch {
        detail = ''
      }
    }
    return `API error ${response.status}${detail ? `: ${detail}` : ''}`
  }

  const fetchSummary = async () => {
    setSummaryLoading(true)
    try {
      const response = await fetch(`${API_BASE}/pipeline/summary?limit=12`)
      if (!response.ok) {
        throw new Error(`API error ${response.status}`)
      }
      const payload = (await response.json()) as SummaryResponse
      setSummaryData(payload)
    } catch {
      setSummaryData(null)
    } finally {
      setSummaryLoading(false)
    }
  }

  const fetchSystemStatus = async () => {
    setSystemStatusLoading(true)
    setSystemStatusError(null)
    try {
      const response = await fetch(`${API_BASE}/system/status`)
      if (!response.ok) {
        throw new Error(`API error ${response.status}`)
      }
      const payload = (await response.json()) as SystemStatusResponse
      setSystemStatus(payload)
    } catch (err) {
      setSystemStatusError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setSystemStatusLoading(false)
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
      setSelectedAnimation((prev) => {
        if (payload.length === 0) return null
        if (!prev) return payload[0]
        return payload.find((row) => row.id === prev.id) ?? payload[0]
      })
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

  const fetchPublishRecords = async (renderId?: string | null, animationId?: string | null) => {
    if (!renderId && !animationId) {
      setPublishRecords([])
      return
    }
    setPublishRecordsLoading(true)
    setPublishRecordsError(null)
    try {
      const params = new URLSearchParams()
      params.set('limit', '20')
      if (renderId) params.set('render_id', renderId)
      if (animationId) params.set('animation_id', animationId)
      const response = await fetch(`${API_BASE}/publish-records?${params.toString()}`)
      if (!response.ok) {
        throw new Error(await readApiError(response))
      }
      const payload = (await response.json()) as PublishRecordRow[]
      setPublishRecords(payload)
    } catch (err) {
      setPublishRecordsError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setPublishRecordsLoading(false)
    }
  }

  const fetchPlanPublishRecords = async () => {
    setPlanPublishRecordsLoading(true)
    setPlanPublishRecordsError(null)
    try {
      const params = new URLSearchParams()
      params.set('limit', '50')
      const response = await fetch(`${API_BASE}/publish-records?${params.toString()}`)
      if (!response.ok) {
        throw new Error(await readApiError(response))
      }
      const payload = (await response.json()) as PublishRecordRow[]
      setPlanPublishRecords(payload)
    } catch (err) {
      setPlanPublishRecordsError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setPlanPublishRecordsLoading(false)
    }
  }

  const fetchPlanMetrics = async () => {
    setPlanMetricsLoading(true)
    setPlanMetricsError(null)
    try {
      const params = new URLSearchParams()
      params.set('limit', '100')
      const response = await fetch(`${API_BASE}/metrics-daily?${params.toString()}`)
      if (!response.ok) {
        throw new Error(await readApiError(response))
      }
      const payload = (await response.json()) as MetricsDailyRow[]
      setPlanMetricsRows(payload)
    } catch (err) {
      setPlanMetricsError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setPlanMetricsLoading(false)
    }
  }

  const applyPlannerSettingsToInputs = (payload: PlannerSettings) => {
    setPlannerTimezoneInput(payload.timezone ?? 'UTC')
    setPlannerHourInput(String(payload.daily_publish_hour ?? 18))
    setPlannerMinuteInput(String(payload.daily_publish_minute ?? 0).padStart(2, '0'))
    setPlannerWindowInput(String(payload.publish_window_minutes ?? 120))
    setPlannerTargetInput(String(payload.target_per_day ?? 1))
  }

  const fetchPlannerSettings = async () => {
    setPlannerSettingsLoading(true)
    setPlannerSettingsError(null)
    try {
      const response = await fetch(`${API_BASE}/planner/settings`)
      if (!response.ok) {
        throw new Error(await readApiError(response))
      }
      const payload = (await response.json()) as PlannerSettings
      setPlannerSettings(payload)
      applyPlannerSettingsToInputs(payload)
    } catch (err) {
      setPlannerSettingsError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setPlannerSettingsLoading(false)
    }
  }

  const savePlannerSettings = async () => {
    setPlannerSettingsLoading(true)
    setPlannerSettingsError(null)
    setPlannerSettingsMessage(null)
    try {
      const body = {
        timezone: plannerTimezoneInput.trim() || 'UTC',
        daily_publish_hour: Math.max(0, Math.min(23, Math.floor(parseNumberInput(plannerHourInput, 18)))),
        daily_publish_minute: Math.max(0, Math.min(59, Math.floor(parseNumberInput(plannerMinuteInput, 0)))),
        publish_window_minutes: Math.max(15, Math.min(1440, Math.floor(parseNumberInput(plannerWindowInput, 120)))),
        target_per_day: Math.max(1, Math.min(20, Math.floor(parseNumberInput(plannerTargetInput, 1)))),
      }
      const response = await fetch(`${API_BASE}/ops/planner/settings`, {
        method: 'POST',
        headers: opsHeaders(),
        body: JSON.stringify(body),
      })
      if (!response.ok) {
        throw new Error(await readApiError(response))
      }
      const payload = (await response.json()) as PlannerSettings
      setPlannerSettings(payload)
      applyPlannerSettingsToInputs(payload)
      setPlannerSettingsMessage('Zapisano ustawienia planera.')
    } catch (err) {
      setPlannerSettingsError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setPlannerSettingsLoading(false)
    }
  }

  const fetchGodotManualRuns = async () => {
    if (!manualFlowEnabled) return
    setGodotHistoryLoading(true)
    setGodotHistoryError(null)
    try {
      const params = new URLSearchParams()
      params.set('limit', '12')
      if (godotScriptPath.trim()) {
        params.set('script_path', godotScriptPath.trim())
      }
      const response = await fetch(`${API_BASE}/ops/godot/manual-runs?${params.toString()}`, {
        headers: opsHeaders(),
      })
      if (!response.ok) {
        throw new Error(await readApiError(response))
      }
      const payload = (await response.json()) as GodotManualHistoryRow[]
      setGodotHistoryRows(payload)
    } catch (err) {
      setGodotHistoryError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setGodotHistoryLoading(false)
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
      if (payload.length === 0) {
        setIdeaError('Brak kandydatów do wylosowania. Sprawdź, czy są feasible propozycje.')
      }
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

  const fetchManualPickCandidates = async () => {
    setManualPickLoading(true)
    setManualPickError(null)
    try {
      const params = new URLSearchParams()
      params.set('capability_status', 'feasible')
      params.set('limit', '50')
      const response = await fetch(`${API_BASE}/idea-candidates?${params.toString()}`)
      if (!response.ok) {
        throw new Error(`API error ${response.status}`)
      }
      const payload = (await response.json()) as IdeaCandidate[]
      const filtered = payload.filter((row) => row.status === 'new' || row.status === 'later')
      setManualPickCandidates(filtered)
      if (!filtered.find((row) => row.id === manualPickCandidateId)) {
        setManualPickCandidateId(filtered[0]?.id ?? '')
      }
    } catch (err) {
      setManualPickError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setManualPickLoading(false)
    }
  }

  const handleGenerateCandidates = async () => {
    setGeneratorLoading(true)
    setGeneratorError(null)
    setGeneratorMessage(null)
    try {
      const payload: Record<string, unknown> = { mode: generatorMode }
      if (generatorMode === 'llm') {
        const limit = Number(generatorLimit || '5')
        payload.limit = Number.isNaN(limit) ? 5 : Math.max(1, Math.min(limit, 50))
        if (generatorPrompt.trim()) {
          payload.prompt = generatorPrompt.trim()
        }
      } else if (generatorMode === 'text') {
        payload.text = generatorText.trim()
      } else if (generatorMode === 'file') {
        payload.file_name = generatorFileName || undefined
        payload.file_content = generatorFileContent.trim()
      }
      payload.language = uiLanguage
      const response = await fetch(`${API_BASE}/idea-candidates/generate`, {
        method: 'POST',
        headers: opsHeaders(),
        body: JSON.stringify(payload),
      })
      if (!response.ok) {
        throw new Error(`API error ${response.status}`)
      }
      const result = (await response.json()) as { created?: number; skipped?: number }
      setGeneratorMessage(`Utworzono ${result.created ?? 0} kandydatow, pominieto ${result.skipped ?? 0}.`)
      fetchSystemStatus()
      fetchIdeaCandidates()
      fetchCandidateList()
      if (manualFlowEnabled) {
        fetchManualPickCandidates()
      }
    } catch (err) {
      setGeneratorError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setGeneratorLoading(false)
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
      if (manualFlowEnabled) {
        setIdeaDecisionMessage('Wybrana idea zapisana. Uruchom kompilację ręcznie w sekcji Manual.')
      } else {
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
      }
      fetchAuditEvents()
    } catch (err) {
      setIdeaDecisionError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setIdeaDecisionLoading(false)
    }
  }

  const handleManualPick = async () => {
    setIdeaDecisionLoading(true)
    setIdeaDecisionError(null)
    setIdeaDecisionMessage(null)
    try {
      if (!manualPickCandidateId) {
        throw new Error('Wybierz kandydata do ręcznego wyboru.')
      }
      const response = await fetch(`${API_BASE}/idea-repo/decide`, {
        method: 'POST',
        headers: opsHeaders(),
        body: JSON.stringify({
          decisions: [
            {
              idea_candidate_id: manualPickCandidateId,
              decision: 'picked',
            },
          ],
        }),
      })
      if (!response.ok) {
        throw new Error(`API error ${response.status}`)
      }
      const payload = (await response.json()) as { idea_id?: string }
      if (!payload.idea_id) {
        throw new Error('Brak idea_id po decyzji.')
      }
      setIdeaDecisionMessage('Kandydat ręcznie wybrany.')
      fetchSystemStatus()
      fetchCandidateList()
      fetchSummary()
      fetchAuditEvents()
    } catch (err) {
      setIdeaDecisionError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setIdeaDecisionLoading(false)
    }
  }

  const setCandidateAction = (id: string, loading: boolean) => {
    setCandidateActionLoading((prev) => ({ ...prev, [id]: loading }))
  }

  const handleResetCandidateCapability = async (candidateId: string) => {
    setCandidateAction(candidateId, true)
    try {
      const response = await fetch(`${API_BASE}/idea-candidates/${candidateId}/reset-capability`, {
        method: 'POST',
        headers: opsHeaders(),
      })
      if (!response.ok) {
        throw new Error(`API error ${response.status}`)
      }
      fetchCandidateList()
      fetchSystemStatus()
      fetchBlockedCandidates()
      fetchAuditEvents()
    } finally {
      setCandidateAction(candidateId, false)
    }
  }

  const handleOverrideCandidateCapability = async (
    candidateId: string,
    status: 'unverified' | 'feasible' | 'blocked_by_gaps',
    reason?: string,
  ) => {
    setCandidateAction(candidateId, true)
    try {
      const response = await fetch(`${API_BASE}/idea-candidates/${candidateId}/capability`, {
        method: 'POST',
        headers: opsHeaders(),
        body: JSON.stringify({ status, reason }),
      })
      if (!response.ok) {
        throw new Error(`API error ${response.status}`)
      }
      fetchCandidateList()
      fetchSystemStatus()
      fetchBlockedCandidates()
      fetchAuditEvents()
    } finally {
      setCandidateAction(candidateId, false)
    }
  }

  const handleDeleteCandidate = async (candidateId: string) => {
    setCandidateAction(candidateId, true)
    try {
      const response = await fetch(`${API_BASE}/idea-candidates/${candidateId}/delete`, {
        method: 'POST',
        headers: opsHeaders(),
      })
      if (!response.ok) {
        throw new Error(`API error ${response.status}`)
      }
      fetchCandidateList()
      fetchSystemStatus()
      fetchAuditEvents()
    } finally {
      setCandidateAction(candidateId, false)
    }
  }

  const handleUndoCandidateDecision = async (candidateId: string) => {
    setCandidateAction(candidateId, true)
    try {
      const response = await fetch(`${API_BASE}/idea-candidates/${candidateId}/undo-decision`, {
        method: 'POST',
        headers: opsHeaders(),
      })
      if (!response.ok) {
        throw new Error(`API error ${response.status}`)
      }
      fetchCandidateList()
      fetchSystemStatus()
      fetchAuditEvents()
    } finally {
      setCandidateAction(candidateId, false)
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
        throw new Error(await readApiError(response))
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

  const handleManualCompile = async () => {
    setManualCompileLoading(true)
    setManualCompileError(null)
    setManualCompileMessage(null)
    try {
      if (!manualIdeaId.trim()) {
        throw new Error('Podaj idea_id do kompilacji.')
      }
      const response = await fetch(`${API_BASE}/ideas/${manualIdeaId.trim()}/compile-dsl`, {
        method: 'POST',
        headers: opsHeaders(),
        body: JSON.stringify({
          dsl_template: enqueueDsl,
          out_root: 'out/manual-compile',
          max_attempts: 3,
          max_repairs: 2,
        }),
      })
      if (!response.ok) {
        throw new Error(await readApiError(response))
      }
      const payload = (await response.json()) as Record<string, unknown>
      setManualCompileMessage(`Compiled: ${JSON.stringify(payload)}`)
      fetchSystemStatus()
      fetchAuditEvents()
    } catch (err) {
      setManualCompileError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setManualCompileLoading(false)
    }
  }

  const handleManualPipeline = async () => {
    setManualPipelineLoading(true)
    setManualPipelineError(null)
    setManualPipelineMessage(null)
    try {
      if (!manualIdeaId.trim()) {
        throw new Error('Podaj idea_id do uruchomienia pipeline.')
      }
      const response = await fetch(`${API_BASE}/ops/enqueue`, {
        method: 'POST',
        headers: opsHeaders(),
        body: JSON.stringify({
          dsl_template: enqueueDsl,
          out_root: enqueueOutRoot,
          idea_id: manualIdeaId.trim(),
          idea_gate: false,
        }),
      })
      if (!response.ok) {
        throw new Error(await readApiError(response))
      }
      const payload = (await response.json()) as Record<string, unknown>
      setManualPipelineMessage(`Pipeline started: ${JSON.stringify(payload)}`)
      fetchSummary()
      fetchAuditEvents()
    } catch (err) {
      setManualPipelineError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setManualPipelineLoading(false)
    }
  }

  const setGodotStepLoadingState = (step: string, loading: boolean) => {
    setGodotStepLoading((prev) => ({ ...prev, [step]: loading }))
  }

  const setGodotStepOutcome = (
    step: string,
    status: 'idle' | 'success' | 'fail',
    error: string | null,
    result?: GodotManualStepResult | null,
  ) => {
    setGodotStepStatus((prev) => ({ ...prev, [step]: status }))
    setGodotStepError((prev) => ({ ...prev, [step]: error }))
    if (result !== undefined) {
      setGodotStepResult((prev) => ({ ...prev, [step]: result }))
    }
  }

  const parseNumberInput = (raw: string, fallback: number) => {
    const value = Number(raw)
    return Number.isFinite(value) ? value : fallback
  }

  const handleGodotCompile = async () => {
    const step = 'compile'
    setGodotStepLoadingState(step, true)
    setGodotStepOutcome(step, 'idle', null)
    try {
      if (!manualIdeaId.trim()) {
        throw new Error('Podaj idea_id do kompilacji GDScript.')
      }
      const response = await fetch(`${API_BASE}/ops/godot/compile-gdscript`, {
        method: 'POST',
        headers: opsHeaders(),
        body: JSON.stringify({
          idea_id: manualIdeaId.trim(),
          validate: false,
          max_attempts: 3,
          max_repairs: 2,
          max_nodes: Math.max(10, Math.floor(parseNumberInput(godotMaxNodes, 200))),
        }),
      })
      if (!response.ok) {
        throw new Error(await readApiError(response))
      }
      const payload = (await response.json()) as GodotManualStepResult
      if (payload.script_path) {
        setGodotScriptPath(payload.script_path)
      }
      setGodotStepOutcome(step, 'success', null, payload)
      fetchAuditEvents()
    } catch (err) {
      setGodotStepOutcome(step, 'fail', err instanceof Error ? err.message : 'Unknown error', null)
    } finally {
      setGodotStepLoadingState(step, false)
      fetchGodotManualRuns()
    }
  }

  const handleGodotRunStep = async (step: 'validate' | 'preview' | 'render') => {
    setGodotStepLoadingState(step, true)
    setGodotStepOutcome(step, 'idle', null)
    try {
      if (!godotScriptPath.trim()) {
        throw new Error('Najpierw skompiluj GDScript albo podaj ścieżkę skryptu.')
      }
      const body: Record<string, unknown> = {
        script_path: godotScriptPath.trim(),
        seconds: Math.max(0.1, parseNumberInput(godotSeconds, 2)),
        fps: Math.max(1, Math.floor(parseNumberInput(godotFps, 12))),
        max_nodes: Math.max(10, Math.floor(parseNumberInput(godotMaxNodes, 200))),
      }
      if (step === 'preview') {
        body.scale = Math.max(0.1, parseNumberInput(godotPreviewScale, 0.5))
      }
      const response = await fetch(`${API_BASE}/ops/godot/${step}`, {
        method: 'POST',
        headers: opsHeaders(),
        body: JSON.stringify(body),
      })
      if (!response.ok) {
        throw new Error(await readApiError(response))
      }
      const payload = (await response.json()) as GodotManualStepResult
      setGodotStepOutcome(step, 'success', null, payload)
      fetchAuditEvents()
    } catch (err) {
      setGodotStepOutcome(step, 'fail', err instanceof Error ? err.message : 'Unknown error', null)
    } finally {
      setGodotStepLoadingState(step, false)
      fetchGodotManualRuns()
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

  const handleQcDecision = async () => {
    setQcActionLoading(true)
    setReviewActionError(null)
    setReviewActionMessage(null)
    try {
      if (!selectedAnimation?.id) {
        throw new Error('Wybierz animację do decyzji QC.')
      }
      const response = await fetch(`${API_BASE}/ops/qc-decide`, {
        method: 'POST',
        headers: opsHeaders(),
        body: JSON.stringify({
          animation_id: selectedAnimation.id,
          result: qcResultInput,
          notes: qcNotesInput.trim() || undefined,
        }),
      })
      if (!response.ok) {
        throw new Error(await readApiError(response))
      }
      const payload = (await response.json()) as Record<string, unknown>
      setReviewActionMessage(`QC zapisane: ${JSON.stringify(payload)}`)
      await fetchAnimations()
      fetchSystemStatus()
      fetchAuditEvents()
    } catch (err) {
      setReviewActionError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setQcActionLoading(false)
    }
  }

  const handlePublishRecord = async () => {
    setPublishActionLoading(true)
    setReviewActionError(null)
    setReviewActionMessage(null)
    try {
      const renderId = selectedAnimation?.render?.id
      if (!renderId) {
        throw new Error('Wybrana animacja nie ma renderu do publikacji.')
      }
      const contentId = publishContentIdInput.trim()
      const url = publishUrlInput.trim()
      const errorText = publishErrorInput.trim()
      if ((publishStatusInput === 'published' || publishStatusInput === 'manual_confirmed') && !contentId && !url) {
        throw new Error('Dla statusu published/manual_confirmed podaj Content ID lub URL.')
      }
      if (publishStatusInput === 'failed' && !errorText) {
        throw new Error('Dla statusu failed podaj opis błędu.')
      }
      const response = await fetch(`${API_BASE}/ops/publish-record`, {
        method: 'POST',
        headers: opsHeaders(),
        body: JSON.stringify({
          render_id: renderId,
          platform: publishPlatformInput,
          status: publishStatusInput,
          content_id: contentId || undefined,
          url: url || undefined,
          error: errorText || undefined,
        }),
      })
      if (!response.ok) {
        throw new Error(await readApiError(response))
      }
      const payload = (await response.json()) as Record<string, unknown>
      setReviewActionMessage(`Publish zapisany: ${JSON.stringify(payload)}`)
      await fetchAnimations()
      fetchPublishRecords(renderId, selectedAnimation?.id ?? null)
      fetchSystemStatus()
      fetchAuditEvents()
    } catch (err) {
      setReviewActionError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setPublishActionLoading(false)
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

  const fetchLLMMetrics = async () => {
    setLlmMetricsLoading(true)
    setLlmMetricsError(null)
    try {
      const response = await fetch(`${API_BASE}/llm/metrics`, {
        headers: opsHeaders(),
      })
      if (!response.ok) {
        throw new Error(`API error ${response.status}`)
      }
      const payload = (await response.json()) as LLMMetricsResponse
      setLlmMetrics(payload)
      setLlmMetricsUpdatedAt(new Date())
    } catch (err) {
      setLlmMetricsError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLlmMetricsLoading(false)
    }
  }

  const fetchDslGaps = async () => {
    setDslGapsLoading(true)
    setDslGapsError(null)
    try {
      const response = await fetch(`${API_BASE}/dsl-gaps?limit=20`)
      if (!response.ok) {
        throw new Error(`API error ${response.status}`)
      }
      const payload = (await response.json()) as DslGap[]
      setDslGaps(payload)
      setDslGapsUpdatedAt(new Date())
    } catch (err) {
      setDslGapsError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setDslGapsLoading(false)
    }
  }

  const buildGapPrompt = (gap: DslGap) => {
    const currentDslVersion = systemStatus?.dsl_version_current ?? 'v1'
    return [
      'Jesteś asystentem programistycznym. Twoim zadaniem jest wdrożyć GAP w DSL.',
      '',
      'KONTEKST PROJEKTU:',
      `- Repo: ${window.location.origin}`,
      '- Przeczytaj i przestrzegaj zasad: AGENTS.md',
      '- Dokumentacja: .ai/prd.md, .ai/tech-stack.md, .ai/flow.md',
      '- Specyfikacja DSL: .ai/dsl-v1.md (zaktualizuj i bump wersji)',
      '- TODO: TODO.md',
      '',
      'GAP DO WDROZENIA:',
      `- feature: ${gap.feature ?? 'unknown'}`,
      `- reason: ${gap.reason ?? '—'}`,
      `- impact: ${gap.impact ?? '—'}`,
      `- introduced in DSL: ${gap.dsl_version ?? '—'}`,
      `- current DSL version: ${currentDslVersion}`,
      '',
      'WYMAGANIA:',
      '- Wprowadz zmiany w DSL (spec + walidator + renderer, gdzie potrzebne).',
      '- Przygotuj migracje, jesli zmienia sie schema danych.',
      '- Upewnij sie, ze GAP jest pokryty i da sie go zweryfikowac.',
      '- Po wdrozeniu bumpnij wersje DSL (np. 1.1) i oznacz GAP jako implemented.',
      '',
      'PROCES (KROKI):',
      '1) Zaproponuj plan implementacji GAP (krótko).',
      '2) Zidentyfikuj pliki do zmiany (specyfikacja, walidacja, renderer, modele).',
      '3) Wprowadz zmiany w kodzie.',
      '4) Dodaj/aktualizuj testy, jeśli są.',
      '5) Uruchom formatery i lintery przez Makefile.',
      '6) Opisz jak przetestowac recznie.',
      '',
      'KOMENDY (przykladowe):',
      '- make format',
      '- make lint',
      '- make run-dev',
      '- make db-migrate',
      '',
      'UWAGI:',
      '- Trzymaj sie zasad z AGENTS.md (gałęzie, commit, merge).',
      '- Zwracaj uwage na kompatybilnosc z aktualna wersja DSL.',
    ].join('\n')
  }

  const fetchDslVersions = async () => {
    setDslVersionsLoading(true)
    setDslVersionsError(null)
    try {
      const response = await fetch(`${API_BASE}/dsl/versions?limit=20`)
      if (!response.ok) {
        throw new Error(`API error ${response.status}`)
      }
      const payload = (await response.json()) as DslVersionRow[]
      setDslVersions(payload)
      setDslVersionsUpdatedAt(new Date())
    } catch (err) {
      setDslVersionsError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setDslVersionsLoading(false)
    }
  }

  const fetchBlockedCandidates = async () => {
    try {
      const response = await fetch(`${API_BASE}/idea-candidates/blocked?limit=6`)
      if (!response.ok) return
      const payload = (await response.json()) as BlockedIdeaCandidate[]
      setBlockedCandidates(payload)
    } catch {
      // Non-critical panel, ignore transient fetch issues.
    }
  }

  const fetchCandidateList = async () => {
    setCandidateListLoading(true)
    setCandidateListError(null)
    try {
      const params = new URLSearchParams()
      const limit = Number(candidateListLimit || '25')
      params.set('limit', String(Number.isNaN(limit) ? 25 : Math.max(1, Math.min(limit, 200))))
      if (candidateFilterStatus) params.set('status', candidateFilterStatus)
      if (candidateFilterCapability) params.set('capability_status', candidateFilterCapability)
      if (candidateFilterSimilarity) params.set('similarity_status', candidateFilterSimilarity)
      const response = await fetch(`${API_BASE}/idea-candidates?${params.toString()}`)
      if (!response.ok) {
        throw new Error(`API error ${response.status}`)
      }
      const payload = (await response.json()) as IdeaCandidate[]
      const filtered = candidateFilterStatus ? payload : payload.filter((row) => row.status !== 'rejected')
      setCandidateList(filtered)
    } catch (err) {
      setCandidateListError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setCandidateListLoading(false)
    }
  }

  const handleVerifyCandidates = async () => {
    setVerifyLoading(true)
    setOpsError(null)
    setOpsMessage(null)
    try {
      const limit = Number(verifyLimit || '20')
      const response = await fetch(`${API_BASE}/idea-candidates/verify-capability/batch`, {
        method: 'POST',
        headers: opsHeaders(),
        body: JSON.stringify({
          limit: Number.isNaN(limit) ? 20 : Math.max(1, Math.min(limit, 200)),
          language: uiLanguage,
        }),
      })
      if (!response.ok) {
        throw new Error(`API error ${response.status}`)
      }
      const payload = (await response.json()) as Record<string, unknown>
      setOpsMessage(`Verification done: ${JSON.stringify(payload)}`)
      const reports = Array.isArray((payload as { reports?: unknown }).reports)
        ? ((payload as { reports: unknown[] }).reports as Array<Record<string, unknown>>)
        : []
      const verifierErrors = reports
        .map((report) => report.verifier_errors as string[] | undefined)
        .filter(Boolean)
        .flat()
      if (verifierErrors.length > 0) {
        setOpsError(verifierErrors[0] ?? null)
      }
      const metas = reports
        .map((report) => report.verifier_meta as Record<string, unknown> | undefined)
        .filter(Boolean) as Array<Record<string, unknown>>
      const fallbackUsed = metas.some((meta) => Boolean(meta.fallback_used))
      const meta = metas.find((item) => item.provider || item.model) ?? metas[0]
      setVerifierInfo({
        provider: (meta?.provider as string | undefined) ?? null,
        model: (meta?.model as string | undefined) ?? null,
        fallbackUsed: metas.length ? fallbackUsed : null,
        verified: typeof (payload as { verified?: number }).verified === 'number'
          ? (payload as { verified?: number }).verified ?? null
          : null,
      })
      fetchDslGaps()
      fetchIdeaCandidates()
      fetchSystemStatus()
      fetchBlockedCandidates()
      fetchCandidateList()
      fetchAuditEvents()
    } catch (err) {
      setOpsError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setVerifyLoading(false)
    }
  }

  const handleGapStatus = async (gapId: string, status: DslGap['status']) => {
    if (!status) return
    setGapActionLoading((prev) => ({ ...prev, [gapId]: true }))
    setOpsError(null)
    setOpsMessage(null)
    try {
      let implementedInVersion: string | null = null
      let notes: string | null = null
      if (status === 'implemented') {
        implementedInVersion = window.prompt('Wersja DSL dla implementacji (np. 1.1)?')
        if (!implementedInVersion) {
          throw new Error('implemented_in_dsl_version_required')
        }
        notes = window.prompt('Opcjonalne notatki do wersji DSL (opcjonalnie)') ?? null
      }
      const response = await fetch(`${API_BASE}/dsl-gaps/${gapId}/status`, {
        method: 'POST',
        headers: opsHeaders(),
        body: JSON.stringify({
          status,
          implemented_in_dsl_version: implementedInVersion,
          notes,
        }),
      })
      if (!response.ok) {
        throw new Error(`API error ${response.status}`)
      }
      const payload = (await response.json()) as Record<string, unknown>
      setOpsMessage(`Gap updated: ${JSON.stringify(payload)}`)
      fetchDslGaps()
      fetchDslVersions()
      fetchIdeaCandidates()
      fetchSystemStatus()
      fetchBlockedCandidates()
    } catch (err) {
      setOpsError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setGapActionLoading((prev) => ({ ...prev, [gapId]: false }))
    }
  }

  useEffect(() => {
    fetchSystemStatus()
    const interval = window.setInterval(fetchSystemStatus, 15000)
    return () => window.clearInterval(interval)
  }, [])

  useEffect(() => {
    if (typeof window === 'undefined') return
    window.localStorage.setItem('shortlab.ui.language', uiLanguage)
  }, [uiLanguage])

  useEffect(() => {
    if (typeof window === 'undefined') return
    window.localStorage.setItem('shortlab.ui.theme', uiTheme)
    window.document.documentElement.classList.toggle('dark', uiTheme === 'dark')
  }, [uiTheme])

  useEffect(() => {
    if (typeof window === 'undefined') return
    const params = new URLSearchParams(window.location.search)
    params.set('view', activeView)
    const nextUrl = `${window.location.pathname}?${params.toString()}`
    window.history.replaceState(null, '', nextUrl)
  }, [activeView])

  useEffect(() => {
    if (typeof window === 'undefined') return
    const onPopState = () => setActiveView(getViewFromUrl())
    window.addEventListener('popstate', onPopState)
    return () => window.removeEventListener('popstate', onPopState)
  }, [])

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
    if (!manualFlowEnabled) return
    if (activeView !== 'flow') return
    fetchManualPickCandidates()
  }, [activeView, manualFlowEnabled])

  useEffect(() => {
    if (activeView !== 'plan') return
    fetchPlanPublishRecords()
    fetchPlanMetrics()
    fetchPlannerSettings()
  }, [activeView])

  useEffect(() => {
    if (!manualFlowEnabled) return
    if (activeView !== 'flow') return
    fetchGodotManualRuns()
  }, [activeView, manualFlowEnabled, godotScriptPath])

  useEffect(() => {
    fetchAuditEvents()
  }, [])

  useEffect(() => {
    fetchSettings()
  }, [])

  useEffect(() => {
    fetchLLMMetrics()
    const interval = window.setInterval(fetchLLMMetrics, 30000)
    return () => window.clearInterval(interval)
  }, [])

  useEffect(() => {
    fetchDslGaps()
  }, [])

  useEffect(() => {
    fetchDslVersions()
  }, [])

  useEffect(() => {
    fetchBlockedCandidates()
  }, [])

  useEffect(() => {
    fetchArtifacts(selectedAnimation?.render?.id ?? null)
  }, [selectedAnimation?.render?.id])

  useEffect(() => {
    fetchPublishRecords(selectedAnimation?.render?.id ?? null, selectedAnimation?.id ?? null)
  }, [selectedAnimation?.render?.id, selectedAnimation?.id])

  useEffect(() => {
    setReviewActionError(null)
    setReviewActionMessage(null)
  }, [selectedAnimation?.id])

  const summary = useMemo(() => summaryData?.summary ?? {}, [summaryData])
  const services = useMemo(() => systemStatus?.service_status ?? [], [systemStatus])
  const repoCards = useMemo(() => systemStatus?.repo_counts ?? {}, [systemStatus])
  type RepoKey = (typeof REPO_CARD_ORDER)[number]
  const orderedRepoCards = useMemo(() => {
    const entries = Object.entries(repoCards) as Array<[RepoKey, typeof repoCards[RepoKey]]>
    const priority = new Map(REPO_CARD_ORDER.map((name, index) => [name, index]))
    return entries.sort(([a], [b]) => (priority.get(a) ?? 99) - (priority.get(b) ?? 99))
  }, [repoCards])
  const worker = useMemo(() => summaryData?.worker, [summaryData])
  const planPublishStatusCounts = useMemo(() => {
    return planPublishRecords.reduce<Record<string, number>>((acc, row) => {
      const key = row.status || 'unknown'
      acc[key] = (acc[key] ?? 0) + 1
      return acc
    }, {})
  }, [planPublishRecords])
  const planLatestMetricsByContent = useMemo(() => {
    const map = new Map<string, MetricsDailyRow>()
    for (const row of planMetricsRows) {
      const platform = row.platform_type || 'unknown'
      const content = row.content_id || 'unknown'
      const key = `${platform}::${content}`
      const current = map.get(key)
      const currentDate = current?.date ? new Date(current.date).getTime() : 0
      const nextDate = row.date ? new Date(row.date).getTime() : 0
      if (!current || nextDate >= currentDate) {
        map.set(key, row)
      }
    }
    return Array.from(map.values()).sort((a, b) => {
      const aTime = a.date ? new Date(a.date).getTime() : 0
      const bTime = b.date ? new Date(b.date).getTime() : 0
      return bTime - aTime
    })
  }, [planMetricsRows])
  const planMetricsTotals = useMemo(() => {
    return planLatestMetricsByContent.reduce(
      (acc, row) => {
        acc.views += Number(row.views ?? 0)
        acc.likes += Number(row.likes ?? 0)
        return acc
      },
      { views: 0, likes: 0 },
    )
  }, [planLatestMetricsByContent])
  const plannerTimezone = plannerSettings?.timezone || plannerTimezoneInput || 'UTC'
  const todayPlanKey = useMemo(() => dateKeyInTimezone(new Date(), plannerTimezone), [plannerTimezone])
  const planPublishedTodayCount = useMemo(() => {
    return planPublishRecords.filter((row) => {
      if (!(row.status === 'published' || row.status === 'manual_confirmed')) return false
      const sourceTs = row.published_at || row.created_at
      if (!sourceTs) return false
      try {
        return dateKeyInTimezone(sourceTs, plannerTimezone) === todayPlanKey
      } catch {
        return false
      }
    }).length
  }, [planPublishRecords, plannerTimezone, todayPlanKey])
  const llmRouteRows = useMemo(() => {
    const routes = llmMetrics?.routes ?? {}
    return Object.entries(routes)
      .map(([routeKey, metric]) => {
        const [taskType = 'unknown', provider = 'unknown', model = 'unknown'] = routeKey.split('|')
        const calls = Number(metric.calls ?? 0)
        const success = Number(metric.success ?? 0)
        const errors = Number(metric.errors ?? 0)
        const retries = Number(metric.retries ?? 0)
        const promptTokens = Number(metric.prompt_tokens_total ?? 0)
        const completionTokens = Number(metric.completion_tokens_total ?? 0)
        const latencyTotal = Number(metric.latency_ms_total ?? 0)
        const costTotal = Number(metric.estimated_cost_usd_total ?? 0)
        return {
          routeKey,
          taskType,
          provider,
          model,
          calls,
          success,
          errors,
          retries,
          promptTokens,
          completionTokens,
          tokensTotal: promptTokens + completionTokens,
          avgLatencyMs: success > 0 ? latencyTotal / success : 0,
          costTotal,
        }
      })
      .sort((a, b) => b.calls - a.calls)
  }, [llmMetrics])
  const llmTotals = useMemo(() => {
    return llmRouteRows.reduce(
      (acc, row) => {
        acc.calls += row.calls
        acc.success += row.success
        acc.errors += row.errors
        acc.retries += row.retries
        acc.promptTokens += row.promptTokens
        acc.completionTokens += row.completionTokens
        acc.tokensTotal += row.tokensTotal
        acc.costTotal += row.costTotal
        return acc
      },
      {
        calls: 0,
        success: 0,
        errors: 0,
        retries: 0,
        promptTokens: 0,
        completionTokens: 0,
        tokensTotal: 0,
        costTotal: 0,
      },
    )
  }, [llmRouteRows])
  const tokenBudgetAlerts = useMemo(() => {
    const config = parseTokenBudgets(settings?.llm_token_budgets)
    if (!config) return []
    const usageByModel = new Map<string, number>()
    llmRouteRows.forEach((row) => {
      const key = `${row.provider}:${row.model}`
      usageByModel.set(key, (usageByModel.get(key) ?? 0) + row.tokensTotal)
    })
    const alerts: Array<{ label: string; used: number; limit: number }> = []
    if (config.models) {
      Object.entries(config.models).forEach(([modelKey, limit]) => {
        const used = usageByModel.get(modelKey) ?? 0
        if (limit > 0 && used / limit >= TOKEN_BUDGET_ALERT_THRESHOLD) {
          alerts.push({ label: modelKey, used, limit })
        }
      })
    }
    if (config.groups) {
      Object.entries(config.groups).forEach(([groupName, payload]) => {
        const group =
          typeof payload === 'number' ? { limit: payload, members: [] } : payload || {}
        const limit = Number(group.limit ?? 0)
        const members = Array.isArray(group.members) ? group.members : []
        if (!limit || members.length === 0) return
        const used = members.reduce((acc, key) => acc + (usageByModel.get(key) ?? 0), 0)
        if (used / limit >= TOKEN_BUDGET_ALERT_THRESHOLD) {
          alerts.push({ label: `group:${groupName}`, used, limit })
        }
      })
    }
    return alerts
  }, [llmRouteRows, settings?.llm_token_budgets])
  const ideaStatusSummary = useMemo(() => {
    return systemStatus?.repo_counts?.ideas?.by_status ?? {}
  }, [systemStatus])
  const candidateStatusSummary = useMemo(() => {
    return systemStatus?.repo_counts?.idea_candidates?.by_status ?? {}
  }, [systemStatus])
  const candidateCapabilitySummary = useMemo(() => {
    return systemStatus?.repo_counts?.idea_candidates?.by_capability ?? {}
  }, [systemStatus])

  const videoArtifact = useMemo(
    () => artifacts.find((item) => item.artifact_type === 'video'),
    [artifacts],
  )
  const readyCandidates = candidateCapabilitySummary.feasible ?? 0
  const blockedCandidatesCount = candidateCapabilitySummary.blocked_by_gaps ?? 0
  const queuedJobs = (summary.queued ?? 0) + (summary.running ?? 0)
  const compiledIdeas = ideaStatusSummary.compiled ?? 0
  const renderQueue = animationData.filter((row) =>
    row.pipeline_stage === 'render' || row.status === 'queued' || row.status === 'running',
  ).length
  const qcQueue = animationData.filter((row) => row.pipeline_stage === 'qc').length
  const publishReady = animationData.filter((row) => row.status === 'accepted').length
  const selectedGap = dslGapPromptId
    ? dslGaps.find((gap) => gap.id === dslGapPromptId) ?? null
    : null

  const scrollToSection = (sectionId: string) => {
    if (typeof window === 'undefined') return
    const target = window.document.getElementById(sectionId)
    if (target) {
      target.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }

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
            <div className="flex flex-wrap items-center justify-end gap-2">
              <div className="flex items-center gap-2 rounded-full border border-white/60 bg-white/70 px-3 py-1.5 text-xs font-medium text-stone-600 shadow">
                <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-emerald-500" />
                Auto-refresh every 15s
              </div>
              <div className="flex items-center gap-2 rounded-full border border-white/60 bg-white/70 px-3 py-1.5 text-xs text-stone-600 shadow">
                <span className="text-[10px] uppercase tracking-[0.2em] text-stone-500">Lang</span>
                <select
                  className="rounded-full border border-stone-200 bg-white px-2 py-1 text-xs text-stone-700"
                  value={uiLanguage}
                  onChange={(event) => setUiLanguage(event.target.value as 'pl' | 'en')}
                >
                  {LANGUAGE_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex items-center gap-2 rounded-full border border-white/60 bg-white/70 px-3 py-1.5 text-xs text-stone-600 shadow">
                <span className="text-[10px] uppercase tracking-[0.2em] text-stone-500">Theme</span>
                <div className="flex overflow-hidden rounded-full border border-stone-200 bg-white">
                  <button
                    type="button"
                    className={cn(
                      'px-2 py-1 text-[10px] uppercase tracking-[0.18em]',
                      uiTheme === 'light' ? 'bg-stone-900 text-white' : 'text-stone-600',
                    )}
                    onClick={() => setUiTheme('light')}
                  >
                    Light
                  </button>
                  <button
                    type="button"
                    className={cn(
                      'px-2 py-1 text-[10px] uppercase tracking-[0.18em]',
                      uiTheme === 'dark' ? 'bg-stone-900 text-white' : 'text-stone-600',
                    )}
                    onClick={() => setUiTheme('dark')}
                  >
                    Dark
                  </button>
                </div>
              </div>
            </div>
            <Button variant="outline" className="rounded-full" onClick={fetchSummary} disabled={summaryLoading}>
              Refresh now
            </Button>
          </div>
        </div>
      </header>

      <nav className="flex flex-wrap gap-2">
        {APP_VIEWS.map((view) => (
          <Button
            key={view}
            variant={activeView === view ? 'default' : 'outline'}
            className="rounded-full capitalize"
            onClick={() => setActiveView(view)}
          >
            {view}
          </Button>
        ))}
      </nav>

      {activeView === 'home' ? (
        <>
      <section className="rounded-[28px] border border-stone-200/80 bg-white/90 p-6 shadow-2xl shadow-stone-900/10">
        <div className="flex flex-col gap-4 border-b border-stone-200/70 pb-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h2 className="text-2xl font-semibold text-stone-900">System status</h2>
            <p className="text-sm text-stone-600">
              Stan usług i liczników repozytoriów. Pierwszy punkt kontrolny przed pracą z pipeline.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" className="rounded-full" onClick={fetchSystemStatus} disabled={systemStatusLoading}>
              {systemStatusLoading ? 'Refreshing…' : 'Refresh status'}
            </Button>
          </div>
        </div>
        {systemStatusError ? (
          <div className="mt-4 rounded-2xl border border-rose-200 bg-rose-50/70 p-4 text-xs text-rose-700">
            {systemStatusError}
          </div>
        ) : null}
        {systemStatus?.partial_failures && systemStatus.partial_failures.length > 0 ? (
          <div className="mt-4 rounded-2xl border border-amber-200 bg-amber-50/70 p-4 text-xs text-amber-900">
            Partial failures: {systemStatus.partial_failures.join(', ')}
          </div>
        ) : null}

        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          {services.length === 0 ? (
            <div className="col-span-full rounded-xl border border-dashed border-stone-200 bg-stone-50/60 p-4 text-sm text-stone-500">
              Brak danych usług.
            </div>
          ) : (
            services.map((item) => (
              <Card key={item.service} className="border border-stone-200 bg-stone-50/60 shadow-none">
                <CardContent className="pt-4">
                  <div className="flex items-center justify-between">
                    <span className="text-xs uppercase tracking-[0.18em] text-stone-500">{item.service}</span>
                    <span
                      className={cn(
                        'h-2.5 w-2.5 rounded-full',
                        item.status === 'ok' ? 'bg-emerald-500' : 'bg-rose-500',
                      )}
                    />
                  </div>
                  <div className="mt-2 text-sm font-semibold text-stone-900">
                    {item.status === 'ok' ? 'OK' : 'DOWN'}
                  </div>
                  <div className="mt-1 text-xs text-stone-500">{item.details ?? '—'}</div>
                </CardContent>
              </Card>
            ))
          )}
        </div>

        <div className="mt-4 rounded-2xl border border-stone-200 bg-stone-50/70 p-4 text-sm text-stone-700">
          <div className="text-xs uppercase tracking-[0.18em] text-stone-500">DSL Version</div>
          <div className="mt-1 text-lg font-semibold text-stone-900">
            {systemStatus?.dsl_version_current ?? '—'}
          </div>
        </div>

        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {orderedRepoCards.map(([name, value]) => (
            <Card key={name} className="border border-stone-200 bg-stone-50/60 shadow-none">
              <CardContent className="pt-4">
                <div className="flex items-center justify-between">
                  <div className="text-xs uppercase tracking-[0.18em] text-stone-500">
                    {REPO_LABELS[name] ?? name}
                  </div>
                  {value.placeholder ? (
                    <Badge variant="outline" className="border border-stone-300 text-stone-600">
                      planned
                    </Badge>
                  ) : null}
                </div>
                <div className="mt-1 text-xs text-stone-500">
                  {REPO_HINTS[name] ?? ''}
                </div>
                <div className="mt-2 text-2xl font-semibold text-stone-900">{value.total ?? '—'}</div>
                <div className="mt-2 flex flex-wrap gap-1">
                  {name === 'idea_candidates'
                    ? [
                        ...CANDIDATE_CAPABILITY_ORDER.map((key) => [key, value.by_capability?.[key] ?? 0] as const),
                        ...CANDIDATE_STATUS_ORDER.map((key) => [key, value.by_status?.[key] ?? 0] as const),
                      ]
                        .map(([status, count]) => (
                          <Badge key={`${name}-${status}`} variant="outline" className="border border-stone-300 text-stone-700">
                            {status}: {count}
                          </Badge>
                        ))
                    : Object.entries(value.by_status ?? {})
                        .slice(0, 4)
                        .map(([status, count]) => (
                          <Badge key={`${name}-${status}`} variant="outline" className="border border-stone-300 text-stone-700">
                            {status}: {count}
                          </Badge>
                        ))}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
        <p className="mt-3 text-xs text-stone-500">
          Updated: {formatDate(systemStatus?.updated_at)}
        </p>
      </section>

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

      <section className="grid gap-4 lg:grid-cols-3">
        <Card className="border border-stone-200 bg-white/90 shadow-lg shadow-stone-900/5">
          <CardHeader>
            <CardTitle className="text-lg text-stone-900">Co teraz: Idea Gate</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-stone-600">
            <p>Gotowe propozycje do wyboru: <span className="font-semibold text-stone-900">{readyCandidates}</span></p>
            <p>Zablokowane przez gapy: <span className="font-semibold text-stone-900">{blockedCandidatesCount}</span></p>
            <Button className="rounded-full" onClick={() => setActiveView('flow')}>
              Przejdź do Flow
            </Button>
          </CardContent>
        </Card>
        <Card className="border border-stone-200 bg-white/90 shadow-lg shadow-stone-900/5">
          <CardHeader>
            <CardTitle className="text-lg text-stone-900">Co teraz: Produkcja</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-stone-600">
            <p>Joby w toku: <span className="font-semibold text-stone-900">{queuedJobs}</span></p>
            <p>Worker: <span className="font-semibold text-stone-900">{worker?.online ? 'online' : 'offline'}</span></p>
            <Button className="rounded-full" onClick={() => setActiveView('plan')}>
              Otwórz Plan
            </Button>
          </CardContent>
        </Card>
        <Card className="border border-stone-200 bg-white/90 shadow-lg shadow-stone-900/5">
          <CardHeader>
            <CardTitle className="text-lg text-stone-900">Co teraz: Diagnostyka</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-stone-600">
            <p>Przeglądaj artefakty, audit i metryki LLM.</p>
            <div className="flex gap-2">
              <Button variant="outline" className="rounded-full" onClick={() => setActiveView('repositories')}>
                Repositories
              </Button>
              <Button variant="outline" className="rounded-full" onClick={() => setActiveView('settings')}>
                Settings
              </Button>
            </div>
          </CardContent>
        </Card>
      </section>
      
      </>
      ) : null}

      {activeView === 'plan' ? (
      <section className="rounded-[28px] border border-stone-200/80 bg-white/90 p-6 shadow-2xl shadow-stone-900/10">
        <div className="flex flex-col gap-4 border-b border-stone-200/70 pb-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h2 className="text-2xl font-semibold text-stone-900">Plan / Calendar</h2>
            <p className="text-sm text-stone-600">
              Widok operacyjny: co gotowe, co zablokowane i co czeka na decyzję.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
          <Button variant="outline" className="rounded-full" onClick={fetchAnimations}>
            Odśwież plan
          </Button>
          <Button variant="outline" className="rounded-full" onClick={() => {
            fetchPlanPublishRecords()
            fetchPlanMetrics()
          }}>
            Odśwież publikacje/metryki
          </Button>
          </div>
        </div>
        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Card className="border border-stone-200 bg-stone-50/60 shadow-none">
            <CardContent className="pt-4">
              <div className="text-xs uppercase tracking-[0.18em] text-stone-500">Ready to publish</div>
              <div className="mt-2 text-2xl font-semibold text-stone-900">{animationData.filter((a) => a.status === 'accepted').length}</div>
            </CardContent>
          </Card>
          <Card className="border border-stone-200 bg-stone-50/60 shadow-none">
            <CardContent className="pt-4">
              <div className="text-xs uppercase tracking-[0.18em] text-stone-500">Published/manual confirmed</div>
              <div className="mt-2 text-2xl font-semibold text-stone-900">{(planPublishStatusCounts.published ?? 0) + (planPublishStatusCounts.manual_confirmed ?? 0)}</div>
            </CardContent>
          </Card>
          <Card className="border border-stone-200 bg-stone-50/60 shadow-none">
            <CardContent className="pt-4">
              <div className="text-xs uppercase tracking-[0.18em] text-stone-500">Queued/uploading</div>
              <div className="mt-2 text-2xl font-semibold text-stone-900">{(planPublishStatusCounts.queued ?? 0) + (planPublishStatusCounts.uploading ?? 0)}</div>
            </CardContent>
          </Card>
          <Card className="border border-stone-200 bg-stone-50/60 shadow-none">
            <CardContent className="pt-4">
              <div className="text-xs uppercase tracking-[0.18em] text-stone-500">Latest metrics views (snapshot)</div>
              <div className="mt-2 text-2xl font-semibold text-stone-900">{planMetricsTotals.views}</div>
              <div className="text-xs text-stone-500">likes: {planMetricsTotals.likes}</div>
            </CardContent>
          </Card>
        </div>
        <div className="mt-4 rounded-2xl border border-stone-200 bg-white/80 p-4">
          <div className="flex flex-col gap-2 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <div className="text-sm font-semibold text-stone-900">Daily publish schedule (MVP)</div>
              <div className="text-xs text-stone-500">
                Konfiguracja okna publikacji i celu dziennego w widoku Plan. Automatyczny scheduler jobów jeszcze nie jest włączony.
              </div>
            </div>
            <Badge
              variant="outline"
              className={cn(
                'border',
                planPublishedTodayCount >= Number(plannerTargetInput || 1)
                  ? 'border-emerald-200 bg-emerald-100 text-emerald-900'
                  : 'border-amber-200 bg-amber-100 text-amber-900',
              )}
            >
              Today {planPublishedTodayCount}/{Number(plannerTargetInput || 1)} ({plannerTimezone})
            </Badge>
          </div>
          <div className="mt-3 grid gap-3 lg:grid-cols-[1.2fr_repeat(4,minmax(0,1fr))]">
            <label className="text-xs font-semibold uppercase tracking-[0.15em] text-stone-500">
              Timezone
              <input
                className="mt-1 w-full rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700"
                value={plannerTimezoneInput}
                onChange={(event) => setPlannerTimezoneInput(event.target.value)}
                placeholder="Europe/Warsaw / UTC"
              />
            </label>
            <label className="text-xs font-semibold uppercase tracking-[0.15em] text-stone-500">
              Hour
              <input
                className="mt-1 w-full rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700"
                value={plannerHourInput}
                onChange={(event) => setPlannerHourInput(event.target.value)}
                inputMode="numeric"
              />
            </label>
            <label className="text-xs font-semibold uppercase tracking-[0.15em] text-stone-500">
              Minute
              <input
                className="mt-1 w-full rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700"
                value={plannerMinuteInput}
                onChange={(event) => setPlannerMinuteInput(event.target.value)}
                inputMode="numeric"
              />
            </label>
            <label className="text-xs font-semibold uppercase tracking-[0.15em] text-stone-500">
              Window (min)
              <input
                className="mt-1 w-full rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700"
                value={plannerWindowInput}
                onChange={(event) => setPlannerWindowInput(event.target.value)}
                inputMode="numeric"
              />
            </label>
            <label className="text-xs font-semibold uppercase tracking-[0.15em] text-stone-500">
              Target / day
              <input
                className="mt-1 w-full rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700"
                value={plannerTargetInput}
                onChange={(event) => setPlannerTargetInput(event.target.value)}
                inputMode="numeric"
              />
            </label>
          </div>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <Button className="rounded-full" onClick={savePlannerSettings} disabled={plannerSettingsLoading}>
              {plannerSettingsLoading ? 'Zapisywanie…' : 'Zapisz harmonogram'}
            </Button>
            <Button variant="outline" className="rounded-full" onClick={fetchPlannerSettings} disabled={plannerSettingsLoading}>
              Odśwież ustawienia
            </Button>
            {plannerSettingsMessage ? <span className="text-xs text-emerald-700">{plannerSettingsMessage}</span> : null}
            {plannerSettingsError ? <span className="text-xs text-rose-700">{plannerSettingsError}</span> : null}
          </div>
          {plannerSettings ? (
            <div className="mt-2 text-xs text-stone-500">
              Saved: {String(plannerSettings.daily_publish_hour ?? 18).padStart(2, '0')}:
              {String(plannerSettings.daily_publish_minute ?? 0).padStart(2, '0')}
              {' '}({plannerSettings.publish_window_minutes ?? 120} min window), target {plannerSettings.target_per_day ?? 1}/day
            </div>
          ) : null}
        </div>
        <div className="mt-4 grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
          <div className="rounded-2xl border border-stone-200 bg-white/80 p-4">
            <div className="flex items-center justify-between gap-2">
              <div>
                <div className="text-sm font-semibold text-stone-900">Recent publish records</div>
                <div className="text-xs text-stone-500">Status publikacji i ręczne potwierdzenia (YouTube/TikTok)</div>
              </div>
              <div className="text-xs text-stone-500">{planPublishRecords.length} rows</div>
            </div>
            {planPublishRecordsLoading ? (
              <div className="mt-3 text-sm text-stone-600">Loading publish records…</div>
            ) : planPublishRecordsError ? (
              <div className="mt-3 rounded-xl border border-rose-200 bg-rose-50/70 p-3 text-xs text-rose-700">{planPublishRecordsError}</div>
            ) : planPublishRecords.length === 0 ? (
              <div className="mt-3 rounded-xl border border-dashed border-stone-200 bg-stone-50/60 p-4 text-sm text-stone-600">
                Brak publikacji w historii. Użyj `Publish Record (manual)` w widoku Flow.
              </div>
            ) : (
              <div className="mt-3 space-y-2">
                {planPublishRecords.slice(0, 12).map((row) => (
                  <div key={row.id} className="rounded-xl border border-stone-200 bg-stone-50/60 p-3 text-xs">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-semibold text-stone-800">{row.platform_type ?? 'unknown'}</span>
                      <Badge
                        variant="outline"
                        className={cn(
                          'border',
                          row.status === 'published' || row.status === 'manual_confirmed'
                            ? 'border-emerald-200 bg-emerald-100 text-emerald-900'
                            : row.status === 'failed'
                              ? 'border-rose-200 bg-rose-100 text-rose-900'
                              : 'border-stone-200 bg-stone-100 text-stone-700',
                        )}
                      >
                        {row.status ?? 'unknown'}
                      </Badge>
                      <span className="text-stone-500">
                        {row.created_at ? new Date(row.created_at).toLocaleString() : '—'}
                      </span>
                    </div>
                    <div className="mt-1 grid gap-1 text-stone-600">
                      {row.content_id ? <div><span className="font-semibold text-stone-800">content:</span> {row.content_id}</div> : null}
                      {row.url ? <div className="truncate"><span className="font-semibold text-stone-800">url:</span> {row.url}</div> : null}
                      {row.scheduled_for ? <div><span className="font-semibold text-stone-800">scheduled:</span> {new Date(row.scheduled_for).toLocaleString()}</div> : null}
                      {row.published_at ? <div><span className="font-semibold text-stone-800">published_at:</span> {new Date(row.published_at).toLocaleString()}</div> : null}
                      {row.error_payload && typeof row.error_payload === 'object' && 'message' in row.error_payload ? (
                        <div className="text-rose-700">
                          <span className="font-semibold">error:</span> {String((row.error_payload as { message?: unknown }).message ?? '')}
                        </div>
                      ) : null}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
          <div className="rounded-2xl border border-stone-200 bg-white/80 p-4">
            <div className="flex items-center justify-between gap-2">
              <div>
                <div className="text-sm font-semibold text-stone-900">Latest metrics snapshot</div>
                <div className="text-xs text-stone-500">Najnowszy wpis `metrics_daily` per platform/content</div>
              </div>
              <div className="text-xs text-stone-500">{planLatestMetricsByContent.length} items</div>
            </div>
            {planMetricsLoading ? (
              <div className="mt-3 text-sm text-stone-600">Loading metrics…</div>
            ) : planMetricsError ? (
              <div className="mt-3 rounded-xl border border-rose-200 bg-rose-50/70 p-3 text-xs text-rose-700">{planMetricsError}</div>
            ) : planLatestMetricsByContent.length === 0 ? (
              <div className="mt-3 rounded-xl border border-dashed border-stone-200 bg-stone-50/60 p-4 text-sm text-stone-600">
                Brak danych `metrics_daily`. To OK na etapie manualnym, dopóki nie działa pull metryk.
              </div>
            ) : (
              <div className="mt-3 space-y-2">
                {planLatestMetricsByContent.slice(0, 12).map((row) => (
                  <div key={row.id} className="rounded-xl border border-stone-200 bg-stone-50/60 p-3 text-xs">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-semibold text-stone-800">{row.platform_type ?? 'unknown'}</span>
                      <span className="text-stone-500">{row.content_id ?? 'unknown-content'}</span>
                      <span className="text-stone-500">{row.date ?? '—'}</span>
                    </div>
                    <div className="mt-1 grid grid-cols-2 gap-1 text-stone-600">
                      <div>views: <span className="font-semibold text-stone-800">{row.views ?? 0}</span></div>
                      <div>likes: <span className="font-semibold text-stone-800">{row.likes ?? 0}</span></div>
                      <div>comments: <span className="font-semibold text-stone-800">{row.comments ?? 0}</span></div>
                      <div>shares: <span className="font-semibold text-stone-800">{row.shares ?? 0}</span></div>
                      <div>avg %: <span className="font-semibold text-stone-800">{row.avg_view_percentage ?? '—'}</span></div>
                      <div>avg dur: <span className="font-semibold text-stone-800">{row.avg_view_duration_seconds ?? '—'}</span>s</div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          <Button className="rounded-full" onClick={() => setActiveView('flow')}>Przejdź do Flow</Button>
          <Button variant="outline" className="rounded-full" onClick={() => setActiveView('repositories')}>Otwórz Repositories</Button>
        </div>
      </section>
      ) : null}

      {activeView === 'flow' ? (
      <>
      <section className="rounded-[28px] border border-stone-200/80 bg-white/90 p-6 shadow-2xl shadow-stone-900/10">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h2 className="text-2xl font-semibold text-stone-900">Flow</h2>
            <p className="text-sm text-stone-600">Sekwencja operatora: Idea Generator &rarr; Idea Gate &rarr; Compile &rarr; Render &rarr; QC &rarr; Publish.</p>
            {manualFlowEnabled ? (
              <div className="mt-2 inline-flex items-center gap-2 rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-xs text-amber-700">
                Manual flow włączony (brak automatycznych akcji).
              </div>
            ) : null}
          </div>
          <div className="flex flex-wrap gap-2">
            {['Idea Generator', 'Idea Gate', 'Compile', 'Render', 'QC', 'Publish'].map((step) => (
              <Badge key={step} variant="outline" className="border border-stone-300 text-stone-700">
                {step}
              </Badge>
            ))}
          </div>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          <Button variant="outline" className="rounded-full" onClick={() => {
            fetchSummary()
            fetchAnimations()
            fetchSystemStatus()
            fetchDslGaps()
            fetchBlockedCandidates()
          }}>
            Odśwież Flow
          </Button>
          <Button variant="ghost" className="rounded-full" onClick={() => setActiveView('home')}>
            Wróć do Home
          </Button>
        </div>
        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-6">
          <Card className="border border-stone-200 bg-stone-50/60 shadow-none">
            <CardContent className="pt-4 space-y-2">
              <div className="text-xs uppercase tracking-[0.18em] text-stone-500">Idea Generator</div>
              <div className="text-2xl font-semibold text-stone-900">{candidateCapabilitySummary.unverified ?? 0}</div>
              <div className="text-xs text-stone-500">unverified candidates</div>
              <Button variant="outline" className="w-full rounded-full" onClick={() => scrollToSection('idea-generator-panel')}>
                Zobacz
              </Button>
            </CardContent>
          </Card>
          <Card className="border border-stone-200 bg-stone-50/60 shadow-none">
            <CardContent className="pt-4 space-y-2">
              <div className="text-xs uppercase tracking-[0.18em] text-stone-500">Idea Gate</div>
              <div className="text-2xl font-semibold text-stone-900">{readyCandidates}</div>
              <div className="text-xs text-stone-500">gotowe do wyboru</div>
              <Button className="w-full rounded-full" onClick={() => scrollToSection('idea-gate-panel')}>
                Otwórz
              </Button>
            </CardContent>
          </Card>
          <Card className="border border-stone-200 bg-stone-50/60 shadow-none">
            <CardContent className="pt-4 space-y-2">
              <div className="text-xs uppercase tracking-[0.18em] text-stone-500">Compile</div>
              <div className="text-2xl font-semibold text-stone-900">{compiledIdeas}</div>
              <div className="text-xs text-stone-500">idei skompilowanych</div>
              <Button variant="outline" className="w-full rounded-full" onClick={() => scrollToSection('dsl-capability-panel')}>
                DSL Gaps
              </Button>
            </CardContent>
          </Card>
          <Card className="border border-stone-200 bg-stone-50/60 shadow-none">
            <CardContent className="pt-4 space-y-2">
              <div className="text-xs uppercase tracking-[0.18em] text-stone-500">Render</div>
              <div className="text-2xl font-semibold text-stone-900">{renderQueue}</div>
              <div className="text-xs text-stone-500">w toku / w kolejce</div>
              <Button variant="outline" className="w-full rounded-full" onClick={() => scrollToSection('flow-animations-panel')}>
                Animations
              </Button>
            </CardContent>
          </Card>
          <Card className="border border-stone-200 bg-stone-50/60 shadow-none">
            <CardContent className="pt-4 space-y-2">
              <div className="text-xs uppercase tracking-[0.18em] text-stone-500">QC</div>
              <div className="text-2xl font-semibold text-stone-900">{qcQueue}</div>
              <div className="text-xs text-stone-500">do decyzji QC</div>
              <Button variant="outline" className="w-full rounded-full" onClick={() => scrollToSection('flow-animations-panel')}>
                Sprawdź
              </Button>
            </CardContent>
          </Card>
          <Card className="border border-stone-200 bg-stone-50/60 shadow-none">
            <CardContent className="pt-4 space-y-2">
              <div className="text-xs uppercase tracking-[0.18em] text-stone-500">Publish</div>
              <div className="text-2xl font-semibold text-stone-900">{publishReady}</div>
              <div className="text-xs text-stone-500">gotowe do publikacji</div>
              <Button variant="outline" className="w-full rounded-full" onClick={() => setActiveView('plan')}>
                Zaplanuj
              </Button>
            </CardContent>
          </Card>
        </div>
      </section>

{manualFlowEnabled ? (
      <section id="flow-manual-panel" className="rounded-[28px] border border-amber-200/80 bg-amber-50/40 p-6 shadow-2xl shadow-amber-900/10">
        <div className="flex flex-col gap-2 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h3 className="text-xl font-semibold text-stone-900">Manual Flow</h3>
            <p className="text-sm text-stone-600">Kroki uruchamiane ręcznie przez operatora.</p>
          </div>
        </div>
        <div className="mt-4 grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
          <div className="rounded-2xl border border-amber-200/70 bg-white/80 p-4">
            <label className="flex flex-col gap-1 text-xs font-semibold uppercase tracking-[0.15em] text-stone-500">
              Idea ID
              <input
                className="rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700 focus:border-stone-400 focus:outline-none"
                placeholder="UUID"
                value={manualIdeaId}
                onChange={(event) => setManualIdeaId(event.target.value)}
              />
            </label>
            <div className="mt-3 flex flex-wrap gap-2">
              <Button className="rounded-full" onClick={handleManualCompile} disabled={manualCompileLoading}>
                {manualCompileLoading ? 'Compiling…' : 'Compile DSL'}
              </Button>
              <Button variant="outline" className="rounded-full" onClick={handleManualPipeline} disabled={manualPipelineLoading}>
                {manualPipelineLoading ? 'Starting…' : 'Start pipeline (compile+render)'}
              </Button>
            </div>
            {manualCompileMessage ? (
              <div className="mt-3 rounded-2xl border border-emerald-200 bg-emerald-50/70 p-3 text-xs text-emerald-800">
                {manualCompileMessage}
              </div>
            ) : null}
            {manualCompileError ? (
              <div className="mt-3 rounded-2xl border border-rose-200 bg-rose-50/70 p-3 text-xs text-rose-700">
                {manualCompileError}
              </div>
            ) : null}
            {manualPipelineMessage ? (
              <div className="mt-3 rounded-2xl border border-emerald-200 bg-emerald-50/70 p-3 text-xs text-emerald-800">
                {manualPipelineMessage}
              </div>
            ) : null}
            {manualPipelineError ? (
              <div className="mt-3 rounded-2xl border border-rose-200 bg-rose-50/70 p-3 text-xs text-rose-700">
                {manualPipelineError}
              </div>
            ) : null}

            <div className="mt-5 rounded-2xl border border-sky-200/80 bg-sky-50/40 p-4">
              <div className="flex flex-col gap-2 lg:flex-row lg:items-center lg:justify-between">
                <div>
                  <div className="text-sm font-semibold text-stone-900">Godot Manual Run (Etap B)</div>
                  <div className="text-xs text-stone-600">
                    Krok po kroku: compile_gdscript → validate → preview → final_render.
                  </div>
                </div>
              </div>

              <div className="mt-3 grid gap-3 lg:grid-cols-2">
                <label className="flex flex-col gap-1 text-xs font-semibold uppercase tracking-[0.15em] text-stone-500">
                  GDScript path
                  <input
                    className="rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700"
                    placeholder="out/manual-godot/idea-.../script.gd"
                    value={godotScriptPath}
                    onChange={(event) => setGodotScriptPath(event.target.value)}
                  />
                </label>
                <div className="grid gap-3 sm:grid-cols-4">
                  <label className="flex flex-col gap-1 text-xs font-semibold uppercase tracking-[0.15em] text-stone-500">
                    Seconds
                    <input
                      className="rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700"
                      value={godotSeconds}
                      onChange={(event) => setGodotSeconds(event.target.value)}
                    />
                  </label>
                  <label className="flex flex-col gap-1 text-xs font-semibold uppercase tracking-[0.15em] text-stone-500">
                    FPS
                    <input
                      className="rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700"
                      value={godotFps}
                      onChange={(event) => setGodotFps(event.target.value)}
                    />
                  </label>
                  <label className="flex flex-col gap-1 text-xs font-semibold uppercase tracking-[0.15em] text-stone-500">
                    Max nodes
                    <input
                      className="rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700"
                      value={godotMaxNodes}
                      onChange={(event) => setGodotMaxNodes(event.target.value)}
                    />
                  </label>
                  <label className="flex flex-col gap-1 text-xs font-semibold uppercase tracking-[0.15em] text-stone-500">
                    Preview scale
                    <input
                      className="rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700"
                      value={godotPreviewScale}
                      onChange={(event) => setGodotPreviewScale(event.target.value)}
                    />
                  </label>
                </div>
              </div>

              <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                <Button className="rounded-full" onClick={handleGodotCompile} disabled={!!godotStepLoading.compile}>
                  {godotStepLoading.compile ? 'Compiling…' : '1. Compile GDScript'}
                </Button>
                <Button
                  variant="outline"
                  className="rounded-full"
                  onClick={() => handleGodotRunStep('validate')}
                  disabled={!!godotStepLoading.validate}
                >
                  {godotStepLoading.validate ? 'Validating…' : '2. Validate'}
                </Button>
                <Button
                  variant="outline"
                  className="rounded-full"
                  onClick={() => handleGodotRunStep('preview')}
                  disabled={!!godotStepLoading.preview}
                >
                  {godotStepLoading.preview ? 'Rendering preview…' : '3. Preview'}
                </Button>
                <Button
                  variant="outline"
                  className="rounded-full"
                  onClick={() => handleGodotRunStep('render')}
                  disabled={!!godotStepLoading.render}
                >
                  {godotStepLoading.render ? 'Rendering final…' : '4. Final render'}
                </Button>
              </div>

              <div className="mt-4 grid gap-3 lg:grid-cols-2">
                {(['compile', 'validate', 'preview', 'render'] as const).map((step) => {
                  const result = godotStepResult[step]
                  const error = godotStepError[step]
                  const status = godotStepStatus[step] ?? 'idle'
                  return (
                    <div key={step} className="rounded-xl border border-stone-200 bg-white/80 p-3 text-xs">
                      <div className="flex items-center justify-between">
                        <div className="font-semibold text-stone-900 uppercase tracking-[0.15em]">{step}</div>
                        <Badge
                          variant="outline"
                          className={cn(
                            'border',
                            status === 'success'
                              ? 'border-emerald-200 bg-emerald-100 text-emerald-900'
                              : status === 'fail'
                                ? 'border-rose-200 bg-rose-100 text-rose-900'
                                : 'border-stone-200 bg-stone-100 text-stone-700',
                          )}
                        >
                          {status}
                        </Badge>
                      </div>
                      {error ? <div className="mt-2 text-rose-700">{error}</div> : null}
                      {result ? (
                        <div className="mt-2 space-y-1 text-stone-600">
                          {'script_path' in result && result.script_path ? (
                            <div><span className="font-semibold text-stone-800">script:</span> {result.script_path}</div>
                          ) : null}
                          {'out_path' in result && result.out_path ? (
                            <div><span className="font-semibold text-stone-800">out:</span> {result.out_path}</div>
                          ) : null}
                          {result.log_file ? (
                            <div><span className="font-semibold text-stone-800">log:</span> {result.log_file}</div>
                          ) : null}
                          {typeof result.exit_code === 'number' ? (
                            <div><span className="font-semibold text-stone-800">exit:</span> {result.exit_code}</div>
                          ) : null}
                          {(step === 'preview' || step === 'render') &&
                          result.out_exists &&
                          result.out_path &&
                          result.out_path.includes('/out/manual-godot/') ? (
                            <div className="mt-2 overflow-hidden rounded-lg border border-stone-200 bg-stone-900">
                              <video
                                className="max-h-56 w-full object-contain"
                                controls
                                src={manualGodotFileUrl(result.out_path) ?? undefined}
                              />
                            </div>
                          ) : null}
                          {result.stdout ? (
                            <details className="mt-2">
                              <summary className="cursor-pointer text-stone-500">stdout</summary>
                              <pre className="mt-1 max-h-32 overflow-auto rounded-lg bg-stone-100 p-2 whitespace-pre-wrap">{result.stdout}</pre>
                            </details>
                          ) : null}
                          {result.stderr ? (
                            <details className="mt-2">
                              <summary className="cursor-pointer text-stone-500">stderr</summary>
                              <pre className="mt-1 max-h-32 overflow-auto rounded-lg bg-rose-50 p-2 whitespace-pre-wrap text-rose-800">{result.stderr}</pre>
                            </details>
                          ) : null}
                        </div>
                      ) : null}
                    </div>
                  )
                })}
              </div>

              <div className="mt-4 rounded-xl border border-stone-200 bg-white/80 p-3 text-xs">
                <div className="flex items-center justify-between gap-2">
                  <div className="font-semibold uppercase tracking-[0.15em] text-stone-900">recent manual runs</div>
                  <Button
                    variant="outline"
                    className="h-7 rounded-full px-3 text-[11px]"
                    onClick={fetchGodotManualRuns}
                    disabled={godotHistoryLoading}
                  >
                    {godotHistoryLoading ? 'Loading…' : 'Refresh'}
                  </Button>
                </div>
                {godotHistoryError ? <div className="mt-2 text-rose-700">{godotHistoryError}</div> : null}
                {godotHistoryRows.length === 0 && !godotHistoryLoading && !godotHistoryError ? (
                  <div className="mt-2 text-stone-500">No persisted runs yet.</div>
                ) : null}
                <div className="mt-2 space-y-2">
                  {godotHistoryRows.map((row) => (
                    <div key={row.id} className="rounded-lg border border-stone-200 bg-stone-50/60 p-2">
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge
                          variant="outline"
                          className={cn(
                            'border',
                            row.ok ? 'border-emerald-200 bg-emerald-100 text-emerald-900' : 'border-rose-200 bg-rose-100 text-rose-900',
                          )}
                        >
                          {row.ok ? 'success' : 'fail'}
                        </Badge>
                        <span className="font-semibold uppercase tracking-[0.15em] text-stone-700">{row.step ?? 'unknown'}</span>
                        <span className="text-stone-500">{row.recorded_at ? new Date(row.recorded_at).toLocaleString() : '—'}</span>
                        {typeof row.exit_code === 'number' ? <span className="text-stone-500">exit={row.exit_code}</span> : null}
                      </div>
                      <div className="mt-1 space-y-1 text-stone-600">
                        {row.script_path ? <div><span className="font-semibold text-stone-800">script:</span> {row.script_path}</div> : null}
                        {row.out_path ? <div><span className="font-semibold text-stone-800">out:</span> {row.out_path}</div> : null}
                        {row.log_file ? <div><span className="font-semibold text-stone-800">log:</span> {row.log_file}</div> : null}
                        {row.error ? <div className="text-rose-700"><span className="font-semibold">error:</span> {row.error}</div> : null}
                        {(row.step === 'preview' || row.step === 'render') &&
                        row.out_exists &&
                        row.out_path &&
                        row.out_path.includes('/out/manual-godot/') ? (
                          <div className="mt-2 overflow-hidden rounded-lg border border-stone-200 bg-stone-900">
                            <video className="max-h-40 w-full object-contain" controls src={manualGodotFileUrl(row.out_path) ?? undefined} />
                          </div>
                        ) : null}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
          <div className="rounded-2xl border border-amber-200/70 bg-white/70 p-4 text-xs text-stone-600">
            <div className="font-semibold text-stone-900">Tryb manualny</div>
            <ul className="mt-2 list-disc space-y-2 pl-4">
              <li>Brak automatycznego enqueue po Idea Gate.</li>
              <li>Weryfikacja i kompilacja uruchamiane ręcznie.</li>
              <li>Etap B: Godot Manual Run pozwala uruchamiać compile/validate/preview/render z GUI.</li>
            </ul>
          </div>
        </div>
      </section>
) : null}

<section id="flow-logs-panel" className="rounded-[28px] border border-stone-200/80 bg-white/90 p-6 shadow-2xl shadow-stone-900/10">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h3 className="text-xl font-semibold text-stone-900">Logi operacyjne</h3>
            <p className="text-sm text-stone-600">Ostatnie zdarzenia z audit logu + błędy z operacji.</p>
          </div>
          <div className="flex flex-wrap items-center gap-2 text-xs text-stone-500">
            <span>Updated: {auditUpdatedAt ? auditUpdatedAt.toLocaleTimeString() : '—'}</span>
            <Button variant="outline" className="rounded-full" onClick={fetchAuditEvents} disabled={auditLoading}>
              {auditLoading ? 'Ładowanie…' : 'Odśwież'}
            </Button>
          </div>
        </div>
        {opsError ? (
          <div className="mt-4 rounded-2xl border border-rose-200 bg-rose-50/70 p-4 text-xs text-rose-700">
            {opsError}
          </div>
        ) : null}
        {opsMessage ? (
          <div className="mt-4 rounded-2xl border border-emerald-200 bg-emerald-50/70 p-4 text-xs text-emerald-800">
            {opsMessage}
          </div>
        ) : null}
        <div className="mt-4 overflow-x-auto">
          {auditLoading ? (
            <div className="rounded-2xl border border-dashed border-stone-200 bg-stone-50/60 p-6 text-sm text-stone-600">
              Loading events…
            </div>
          ) : auditError ? (
            <div className="rounded-2xl border border-rose-200 bg-rose-50/70 p-6 text-sm text-rose-700">
              <div className="font-semibold">Failed to load</div>
              <div>{auditError}</div>
            </div>
          ) : (
            <table className="min-w-[900px] w-full text-left text-sm">
              <thead className="text-xs uppercase tracking-[0.18em] text-stone-500">
                <tr>
                  <th className="px-2 py-3">Time</th>
                  <th className="px-2 py-3">Type</th>
                  <th className="px-2 py-3">Source</th>
                  <th className="px-2 py-3">Payload</th>
                </tr>
              </thead>
              <tbody>
                {auditEvents.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="px-2 py-6 text-center text-stone-500">
                      Brak zdarzeń.
                    </td>
                  </tr>
                ) : (
                  auditEvents.map((event) => (
                    <tr key={event.id} className="border-t border-stone-200/70">
                      <td className="px-2 py-4 text-xs text-stone-600">{formatDate(event.occurred_at)}</td>
                      <td className="px-2 py-4 text-stone-800">{event.event_type ?? '—'}</td>
                      <td className="px-2 py-4 text-stone-600">{event.source ?? '—'}</td>
                      <td className="px-2 py-4 text-xs text-stone-600">
                        <pre className="max-w-[420px] whitespace-pre-wrap break-words rounded-xl bg-stone-50 p-2">
                          {event.payload ? JSON.stringify(event.payload) : '—'}
                        </pre>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          )}
        </div>
      </section>

<section id="idea-generator-panel" className="rounded-[28px] border border-stone-200/80 bg-white/90 p-6 shadow-2xl shadow-stone-900/10">
        <div className="flex flex-col gap-4 border-b border-stone-200/70 pb-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h2 className="text-2xl font-semibold text-stone-900">Idea Generator</h2>
            <p className="text-sm text-stone-600">
              Punkt startu flow: nowe kandydaty, weryfikacja DSL i odsiew gapów.
            </p>
          </div>
        </div>

        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Card className="border border-stone-200 bg-stone-50/60 shadow-none">
            <CardContent className="pt-4">
              <div className="text-xs uppercase tracking-[0.18em] text-stone-500">Unverified</div>
              <div className="mt-2 text-2xl font-semibold text-stone-900">
                {candidateCapabilitySummary.unverified ?? 0}
              </div>
            </CardContent>
          </Card>
          <Card className="border border-stone-200 bg-stone-50/60 shadow-none">
            <CardContent className="pt-4">
              <div className="text-xs uppercase tracking-[0.18em] text-stone-500">Feasible</div>
              <div className="mt-2 text-2xl font-semibold text-stone-900">
                {candidateCapabilitySummary.feasible ?? 0}
              </div>
            </CardContent>
          </Card>
          <Card className="border border-stone-200 bg-stone-50/60 shadow-none">
            <CardContent className="pt-4">
              <div className="text-xs uppercase tracking-[0.18em] text-stone-500">Blocked by gaps</div>
              <div className="mt-2 text-2xl font-semibold text-stone-900">
                {candidateCapabilitySummary.blocked_by_gaps ?? 0}
              </div>
            </CardContent>
          </Card>
          <Card className="border border-stone-200 bg-stone-50/60 shadow-none">
            <CardContent className="pt-4">
              <div className="text-xs uppercase tracking-[0.18em] text-stone-500">New/Later/Picked</div>
              <div className="mt-2 text-sm text-stone-700">
                new: {candidateStatusSummary.new ?? 0} · later: {candidateStatusSummary.later ?? 0} · picked:{' '}
                {candidateStatusSummary.picked ?? 0} · rejected: {candidateStatusSummary.rejected ?? 0}
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="mt-6 grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
          <div className="rounded-2xl border border-stone-200/70 bg-stone-50/70 p-4">
            <div className="text-sm font-semibold text-stone-900">Tryb generowania</div>
            <div className="mt-3 flex flex-wrap gap-2">
              {(['llm', 'text', 'file'] as const).map((mode) => (
                <Button
                  key={mode}
                  variant={generatorMode === mode ? 'default' : 'outline'}
                  className="rounded-full"
                  onClick={() => setGeneratorMode(mode)}
                >
                  {mode.toUpperCase()}
                </Button>
              ))}
            </div>

            {generatorMode === 'llm' ? (
              <div className="mt-4 space-y-3 text-sm">
                <label className="flex flex-col gap-1 text-xs uppercase tracking-[0.18em] text-stone-500">
                  Limit
                  <input
                    className="rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700"
                    value={generatorLimit}
                    onChange={(event) => setGeneratorLimit(event.target.value)}
                  />
                </label>
                <label className="flex flex-col gap-1 text-xs uppercase tracking-[0.18em] text-stone-500">
                  Prompt (opcjonalny)
                  <textarea
                    className="min-h-[90px] rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700"
                    value={generatorPrompt}
                    onChange={(event) => setGeneratorPrompt(event.target.value)}
                  />
                </label>
              </div>
            ) : null}

            {generatorMode === 'text' ? (
              <div className="mt-4 space-y-3 text-sm">
                <label className="flex flex-col gap-1 text-xs uppercase tracking-[0.18em] text-stone-500">
                  Tekst pomyslu
                  <textarea
                    className="min-h-[140px] rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700"
                    value={generatorText}
                    onChange={(event) => setGeneratorText(event.target.value)}
                  />
                </label>
              </div>
            ) : null}

            {generatorMode === 'file' ? (
              <div className="mt-4 space-y-3 text-sm">
                <label className="flex flex-col gap-1 text-xs uppercase tracking-[0.18em] text-stone-500">
                  Plik z pomyslami (tekst/markdown)
                  <input
                    type="file"
                    accept=".txt,.md"
                    className="rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700"
                    onChange={(event) => {
                      const file = event.target.files?.[0]
                      if (!file) {
                        setGeneratorFileName('')
                        setGeneratorFileContent('')
                        return
                      }
                      setGeneratorFileName(file.name)
                      const reader = new FileReader()
                      reader.onload = () => setGeneratorFileContent(String(reader.result || ''))
                      reader.readAsText(file)
                    }}
                  />
                </label>
                <textarea
                  className="min-h-[120px] rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700"
                  value={generatorFileContent}
                  onChange={(event) => setGeneratorFileContent(event.target.value)}
                />
              </div>
            ) : null}

            <div className="mt-4 flex flex-wrap gap-2">
              <Button className="rounded-full" onClick={handleGenerateCandidates} disabled={generatorLoading}>
                {generatorLoading ? 'Generuje…' : 'Generuj'}
              </Button>
              <Button
                variant="ghost"
                className="rounded-full"
                onClick={() => {
                  setGeneratorPrompt('')
                  setGeneratorText('')
                  setGeneratorFileName('')
                  setGeneratorFileContent('')
                }}
                disabled={generatorLoading}
              >
                Wyczyść
              </Button>
            </div>
            {generatorMessage ? (
              <div className="mt-3 rounded-2xl border border-emerald-200 bg-emerald-50/70 p-3 text-xs text-emerald-800">
                {generatorMessage}
              </div>
            ) : null}
            {generatorError ? (
              <div className="mt-3 rounded-2xl border border-rose-200 bg-rose-50/70 p-3 text-xs text-rose-700">
                {generatorError}
              </div>
            ) : null}
          </div>

          <div className="rounded-2xl border border-stone-200/70 bg-white/70 p-4 text-sm text-stone-600">
            <div className="text-sm font-semibold text-stone-900">Jak to dziala</div>
            <ul className="mt-2 list-disc space-y-2 pl-4 text-xs text-stone-600">
              <li>LLM: generuje wiele propozycji na podstawie promptu.</li>
              <li>Text: jedna propozycja na bazie wlasnego opisu.</li>
              <li>File: wczytanie wielu pomyslow z pliku.</li>
            </ul>
          </div>
        </div>

        <div className="mt-4 flex flex-wrap gap-2 text-xs text-stone-500">
          <span>Generator dostepny z UI oraz CLI: `make idea-generate`.</span>
          <span>Weryfikacja DSL: `make idea-verify-capability`.</span>
          <span>Similarity: porównanie kandydata do historii idei (embedding + cosine similarity).</span>
        </div>
      </section>

      
      <section id="dsl-capability-panel" className="rounded-[28px] border border-stone-200/80 bg-white/90 p-6 shadow-2xl shadow-stone-900/10">
        <div className="flex flex-col gap-4 border-b border-stone-200/70 pb-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h2 className="text-2xl font-semibold text-stone-900">DSL Capability</h2>
            <p className="text-sm text-stone-600">
              Weryfikacja kandydatów i zarządzanie listą `dsl_gap`.
            </p>
          </div>
          <div className="text-xs text-stone-500">
            <div>Updated: {dslGapsUpdatedAt ? dslGapsUpdatedAt.toLocaleTimeString() : 'waiting for data'}</div>
            {verifierInfo ? (
              <div>
                Verifier: {verifierInfo.fallbackUsed ? 'fallback' : 'LLM'}
                {verifierInfo.provider ? ` / ${verifierInfo.provider}` : ''}
                {verifierInfo.model ? ` / ${verifierInfo.model}` : ''}
                {verifierInfo.verified ? ` (verified: ${verifierInfo.verified})` : ''}
              </div>
            ) : null}
          </div>
        </div>

        <div className="mt-4 flex flex-wrap items-end gap-3">
          <label className="flex min-w-[200px] flex-col gap-1 text-xs font-semibold uppercase tracking-[0.15em] text-stone-500">
            Verify limit
            <input
              className="rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700 focus:border-stone-400 focus:outline-none"
              value={verifyLimit}
              onChange={(event) => setVerifyLimit(event.target.value)}
            />
          </label>
          <div className="flex flex-wrap gap-2">
            <Button className="rounded-full" onClick={handleVerifyCandidates} disabled={verifyLoading}>
              {verifyLoading ? 'Verifying…' : 'Verify candidates'}
            </Button>
            <Button variant="outline" className="rounded-full" onClick={fetchDslGaps} disabled={dslGapsLoading}>
              Refresh gaps
            </Button>
          </div>
        </div>

        {blockedCandidates.length > 0 ? (
          <div className="mt-4 rounded-2xl border border-amber-200 bg-amber-50/70 p-4 text-xs text-amber-900">
            <div className="font-semibold">
              {blockedCandidates.length} candidate(s) blocked by DSL gaps and excluded from sampling.
            </div>
            <div className="mt-2 space-y-1">
              {blockedCandidates.map((candidate) => (
                <div key={candidate.id}>
                  {candidate.title}:{' '}
                  {(candidate.gaps ?? []).map((gap) => gap.feature).filter(Boolean).join(', ') || 'gap'}
                </div>
              ))}
            </div>
          </div>
        ) : null}

        <div className="mt-4 flex flex-wrap gap-2 text-xs">
          {['unverified', 'feasible', 'blocked_by_gaps'].map((status) => (
            <Badge key={status} variant="outline" className={cn('border', chipTone(status))}>
              {status}: {candidateCapabilitySummary[status] ?? 0}
            </Badge>
          ))}
        </div>

        <div className="mt-4 overflow-x-auto">
          {dslGapsLoading ? (
            <div className="rounded-2xl border border-dashed border-stone-200 bg-stone-50/60 p-6 text-sm text-stone-600">
              Loading DSL gaps…
            </div>
          ) : dslGapsError ? (
            <div className="rounded-2xl border border-rose-200 bg-rose-50/70 p-6 text-sm text-rose-700">
              <div className="font-semibold">Failed to load</div>
              <div>{dslGapsError}</div>
            </div>
          ) : (
            <table className="min-w-[900px] w-full text-left text-sm">
              <thead className="text-xs uppercase tracking-[0.18em] text-stone-500">
                <tr>
                  <th className="px-2 py-3">Feature</th>
                  <th className="px-2 py-3">Status</th>
                  <th className="px-2 py-3">Introduced</th>
                  <th className="px-2 py-3">Implemented</th>
                  <th className="px-2 py-3">Reason</th>
                  <th className="px-2 py-3">Actions</th>
                </tr>
              </thead>
              <tbody>
                {dslGaps.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-2 py-6 text-center text-stone-500">
                      No DSL gaps yet.
                    </td>
                  </tr>
                ) : (
                  dslGaps.map((gap) => (
                    <tr key={gap.id} className="border-t border-stone-200/70">
                      <td className="px-2 py-4 text-stone-800">{gap.feature ?? '—'}</td>
                      <td className="px-2 py-4">
                        <Badge variant="outline" className={cn('border', chipTone(gap.status ?? undefined))}>
                          {gap.status ?? '—'}
                        </Badge>
                      </td>
                      <td className="px-2 py-4 text-stone-600">{gap.dsl_version ?? '—'}</td>
                      <td className="px-2 py-4 text-stone-600">{gap.implemented_in_version ?? '—'}</td>
                      <td className="px-2 py-4 text-stone-600">{gap.reason ?? '—'}</td>
                      <td className="px-2 py-4">
                        <div className="flex flex-wrap gap-2">
                          <Button
                            variant="outline"
                            className="rounded-full"
                            onClick={() => handleGapStatus(gap.id, 'accepted')}
                            disabled={gapActionLoading[gap.id]}
                          >
                            Accept
                          </Button>
                          <Button
                            variant="outline"
                            className="rounded-full"
                            onClick={() => handleGapStatus(gap.id, 'in_progress')}
                            disabled={gapActionLoading[gap.id]}
                          >
                            In progress
                          </Button>
                          <Button
                            className="rounded-full"
                            onClick={() => handleGapStatus(gap.id, 'implemented')}
                            disabled={gapActionLoading[gap.id]}
                          >
                            Implemented
                          </Button>
                          <Button
                            variant="outline"
                            className="rounded-full"
                            onClick={() =>
                              setDslGapPromptId((prev) => (prev === gap.id ? null : gap.id))
                            }
                          >
                            AI prompt
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          )}
        </div>
        {selectedGap ? (
          <div className="mt-4 rounded-2xl border border-stone-200 bg-stone-50/70 p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="text-sm font-semibold text-stone-800">
                Prompt do wdrozenia GAP: {selectedGap.feature ?? 'gap'}
              </div>
              <div className="flex flex-wrap gap-2">
                <Button
                  variant="outline"
                  className="rounded-full"
                  onClick={async () => {
                    const text = buildGapPrompt(selectedGap)
                    if (navigator.clipboard?.writeText) {
                      await navigator.clipboard.writeText(text)
                    }
                  }}
                >
                  Copy prompt
                </Button>
                <Button
                  variant="ghost"
                  className="rounded-full"
                  onClick={() => setDslGapPromptId(null)}
                >
                  Close
                </Button>
              </div>
            </div>
            <textarea
              className="mt-3 w-full rounded-2xl border border-stone-200 bg-white/90 p-3 text-xs text-stone-700"
              rows={14}
              readOnly
              value={buildGapPrompt(selectedGap)}
            />
          </div>
        ) : null}
      </section>

      <section className="mt-6 rounded-[28px] border border-stone-200/80 bg-white/90 p-6 shadow-2xl shadow-stone-900/10">
        <div className="flex flex-col gap-4 border-b border-stone-200/70 pb-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h2 className="text-2xl font-semibold text-stone-900">DSL Versions</h2>
            <p className="text-sm text-stone-600">Historia wersji DSL oraz gapy wprowadzone w wersjach.</p>
          </div>
          <div className="text-xs text-stone-500">
            <div>Updated: {dslVersionsUpdatedAt ? dslVersionsUpdatedAt.toLocaleTimeString() : 'waiting for data'}</div>
          </div>
        </div>

        <div className="mt-4 flex flex-wrap gap-2">
          <Button variant="outline" className="rounded-full" onClick={fetchDslVersions} disabled={dslVersionsLoading}>
            {dslVersionsLoading ? 'Refreshing…' : 'Refresh versions'}
          </Button>
          {dslVersionsError ? <span className="text-xs text-rose-600">{dslVersionsError}</span> : null}
        </div>

        <div className="mt-4 overflow-x-auto">
          {dslVersionsLoading ? (
            <div className="rounded-2xl border border-dashed border-stone-200 bg-stone-50/60 p-6 text-sm text-stone-600">
              Loading DSL versions…
            </div>
          ) : (
            <table className="min-w-[820px] w-full text-left text-sm">
              <thead className="text-xs uppercase tracking-[0.18em] text-stone-500">
                <tr>
                  <th className="px-2 py-3">Version</th>
                  <th className="px-2 py-3">Active</th>
                  <th className="px-2 py-3">Introduced gaps</th>
                  <th className="px-2 py-3">Implemented gaps</th>
                  <th className="px-2 py-3">Notes</th>
                  <th className="px-2 py-3">Created</th>
                </tr>
              </thead>
              <tbody>
                {dslVersions.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-2 py-6 text-center text-stone-500">
                      No DSL versions yet.
                    </td>
                  </tr>
                ) : (
                  dslVersions.map((row) => (
                    <tr key={row.id} className="border-t border-stone-200/70">
                      <td className="px-2 py-4 text-stone-800">{row.version}</td>
                      <td className="px-2 py-4 text-stone-600">
                        {row.is_active ? 'yes' : 'no'}
                      </td>
                      <td className="px-2 py-4 text-stone-600">{row.introduced_gaps ?? 0}</td>
                      <td className="px-2 py-4 text-stone-600">{row.implemented_gaps ?? 0}</td>
                      <td className="px-2 py-4 text-stone-600">{row.notes ?? '—'}</td>
                      <td className="px-2 py-4 text-stone-600">{formatDate(row.created_at)}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          )}
        </div>
      </section>

      <section id="idea-gate-panel" className="rounded-[28px] border border-stone-200/80 bg-white/90 p-6 shadow-2xl shadow-stone-900/10">
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

        <div className="mt-4 rounded-2xl border border-stone-200/70 bg-stone-50/70 p-4">
          <div className="text-sm font-semibold text-stone-900">Ręczny wybór kandydata</div>
          <div className="mt-2 flex flex-wrap items-end gap-3">
            <label className="flex min-w-[240px] flex-col gap-1 text-xs font-semibold uppercase tracking-[0.15em] text-stone-500">
              Kandydat (feasible)
              <select
                className="rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700 focus:border-stone-400 focus:outline-none"
                value={manualPickCandidateId}
                onChange={(event) => setManualPickCandidateId(event.target.value)}
              >
                {manualPickCandidates.length === 0 ? (
                  <option value="">Brak kandydatów</option>
                ) : (
                  manualPickCandidates.map((candidate) => (
                    <option key={candidate.id} value={candidate.id}>
                      {candidate.title ?? candidate.id}
                    </option>
                  ))
                )}
              </select>
            </label>
            <div className="flex flex-wrap gap-2">
              <Button variant="outline" className="rounded-full" onClick={fetchManualPickCandidates} disabled={manualPickLoading}>
                {manualPickLoading ? 'Ładowanie…' : 'Odśwież listę'}
              </Button>
              <Button className="rounded-full" onClick={handleManualPick} disabled={ideaDecisionLoading || !manualPickCandidateId}>
                Wybierz kandydata
              </Button>
            </div>
          </div>
          {manualPickError ? (
            <div className="mt-2 text-xs text-rose-600">{manualPickError}</div>
          ) : null}
          <div className="mt-2 text-xs text-stone-500">
            Lista obejmuje kandydatów o statusie new/later oraz capability = feasible.
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
            Wymagana klasyfikacja wszystkich propozycji. Decyzje:{' '}
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

      <section id="flow-animations-panel" className="rounded-[28px] border border-stone-200/80 bg-white/90 p-6 shadow-2xl shadow-stone-900/10">
        <div className="flex flex-col gap-4 border-b border-stone-200/70 pb-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h2 className="text-2xl font-semibold text-stone-900">Animations (Flow)</h2>
            <p className="text-sm text-stone-600">
              Skrócony podgląd dla procesu operatora. Pełna lista w zakładce Repositories.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button className="rounded-full" onClick={fetchAnimations} disabled={animationLoading}>
              Odśwież listę
            </Button>
            <Button variant="outline" className="rounded-full" onClick={() => setActiveView('repositories')}>
              Otwórz Repositories
            </Button>
          </div>
        </div>

        <div className="mt-4 overflow-x-auto">
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
            <table className="min-w-[720px] w-full text-left text-sm">
              <thead className="text-xs uppercase tracking-[0.18em] text-stone-500">
                <tr>
                  <th className="px-2 py-3">Status</th>
                  <th className="px-2 py-3">Stage</th>
                  <th className="px-2 py-3">Animation</th>
                  <th className="px-2 py-3">Render</th>
                  <th className="px-2 py-3">Updated</th>
                </tr>
              </thead>
              <tbody>
                {animationData.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-2 py-6 text-center text-stone-500">
                      No animations yet.
                    </td>
                  </tr>
                ) : (
                  animationData.slice(0, 8).map((row) => (
                    <tr key={row.id} className="border-t border-stone-200/70">
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
                      <td className="px-2 py-4 text-stone-600">{formatDate(row.updated_at)}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          )}
        </div>
      </section>

      
      <section id="operations-panel" className="rounded-[28px] border border-stone-200/80 bg-white/90 p-6 shadow-2xl shadow-stone-900/10">
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

</>
      ) : null}

      

{activeView === 'repositories' ? (
      <>
<section className="rounded-[28px] border border-stone-200/80 bg-white/90 p-6 shadow-2xl shadow-stone-900/10">
        <div className="flex flex-col gap-4 border-b border-stone-200/70 pb-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h2 className="text-2xl font-semibold text-stone-900">Idea Candidates</h2>
            <p className="text-sm text-stone-600">
              Repozytorium kandydatow wraz ze statusem decyzji i capability.
            </p>
          </div>
        </div>

        <div className="mt-4 flex flex-wrap items-end gap-3">
          <label className="flex min-w-[160px] flex-col gap-1 text-xs font-semibold uppercase tracking-[0.15em] text-stone-500">
            Status
            <select
              className="rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700 focus:border-stone-400 focus:outline-none"
              value={candidateFilterStatus}
              onChange={(event) => setCandidateFilterStatus(event.target.value)}
            >
              <option value="">All</option>
              {CANDIDATE_STATUS_ORDER.map((status) => (
                <option key={status} value={status}>
                  {status}
                </option>
              ))}
            </select>
          </label>
          <label className="flex min-w-[180px] flex-col gap-1 text-xs font-semibold uppercase tracking-[0.15em] text-stone-500">
            Capability
            <select
              className="rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700 focus:border-stone-400 focus:outline-none"
              value={candidateFilterCapability}
              onChange={(event) => setCandidateFilterCapability(event.target.value)}
            >
              <option value="">All</option>
              {CANDIDATE_CAPABILITY_ORDER.map((status) => (
                <option key={status} value={status}>
                  {status}
                </option>
              ))}
            </select>
          </label>
          <label className="flex min-w-[180px] flex-col gap-1 text-xs font-semibold uppercase tracking-[0.15em] text-stone-500">
            Similarity
            <select
              className="rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700 focus:border-stone-400 focus:outline-none"
              value={candidateFilterSimilarity}
              onChange={(event) => setCandidateFilterSimilarity(event.target.value)}
            >
              <option value="">All</option>
              {['ok', 'too_similar', 'unknown'].map((status) => (
                <option key={status} value={status}>
                  {status}
                </option>
              ))}
            </select>
          </label>
          <label className="flex min-w-[120px] flex-col gap-1 text-xs font-semibold uppercase tracking-[0.15em] text-stone-500">
            Limit
            <input
              className="rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700 focus:border-stone-400 focus:outline-none"
              value={candidateListLimit}
              onChange={(event) => setCandidateListLimit(event.target.value)}
            />
          </label>
          <div className="flex flex-wrap gap-2">
            <Button className="rounded-full" onClick={fetchCandidateList} disabled={candidateListLoading}>
              Apply filters
            </Button>
            <Button
              variant="ghost"
              className="rounded-full"
              onClick={() => {
                setCandidateFilterStatus('')
                setCandidateFilterCapability('')
                setCandidateFilterSimilarity('')
                window.setTimeout(fetchCandidateList, 0)
              }}
              disabled={candidateListLoading}
            >
              Reset
            </Button>
          </div>
        </div>

        <div className="mt-4 overflow-x-auto">
          {candidateListLoading ? (
            <div className="rounded-2xl border border-dashed border-stone-200 bg-stone-50/60 p-6 text-sm text-stone-600">
              Loading candidates…
            </div>
          ) : candidateListError ? (
            <div className="rounded-2xl border border-rose-200 bg-rose-50/70 p-6 text-sm text-rose-700">
              <div className="font-semibold">Failed to load</div>
              <div>{candidateListError}</div>
            </div>
          ) : (
            <table className="min-w-[880px] w-full text-left text-sm">
              <thead className="text-xs uppercase tracking-[0.18em] text-stone-500">
                <tr>
                  <th className="px-2 py-3">Status</th>
                  <th className="px-2 py-3">Capability</th>
                  <th className="px-2 py-3">Similarity</th>
                  <th className="px-2 py-3">Title / Details</th>
                  <th className="px-2 py-3">Created</th>
                  <th className="px-2 py-3">Actions</th>
                </tr>
              </thead>
              <tbody>
                {candidateList.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-2 py-6 text-center text-stone-500">
                      No candidates matched. Adjust filters or generate new ideas.
                    </td>
                  </tr>
                ) : (
                  candidateList.map((row) => (
                    <tr key={row.id} className="border-t border-stone-200/70">
                      <td className="px-2 py-4">
                        <Badge variant="outline" className={cn('border', chipTone(row.status))}>
                          {row.status ?? '—'}
                        </Badge>
                      </td>
                      <td className="px-2 py-4">
                        <Badge variant="outline" className={cn('border', chipTone(row.capability_status))}>
                          {row.capability_status ?? '—'}
                        </Badge>
                      </td>
                      <td className="px-2 py-4 text-stone-600">{row.similarity_status ?? '—'}</td>
                      <td className="px-2 py-4 text-stone-700">
                        <div className="font-medium text-stone-900">{row.title ?? '—'}</div>
                        <details className="mt-1 text-xs text-stone-600">
                          <summary className="cursor-pointer text-stone-500">Pokaż treść</summary>
                          {row.summary ? <div className="mt-2">Summary: {row.summary}</div> : null}
                          {row.what_to_expect ? <div className="mt-1">What to expect: {row.what_to_expect}</div> : null}
                          {row.preview ? <div className="mt-1">Preview: {row.preview}</div> : null}
                        </details>
                      </td>
                      <td className="px-2 py-4 text-stone-600">{formatDate(row.created_at)}</td>
                      <td className="px-2 py-4">
                        <div className="flex flex-wrap gap-2">
                          <Button
                            variant="outline"
                            className="rounded-full"
                            onClick={() => handleResetCandidateCapability(row.id)}
                            disabled={candidateActionLoading[row.id]}
                          >
                            Reset verify
                          </Button>
                          <Button
                            variant="outline"
                            className="rounded-full"
                            onClick={() => handleOverrideCandidateCapability(row.id, 'feasible', 'manual')}
                            disabled={candidateActionLoading[row.id]}
                          >
                            Mark feasible
                          </Button>
                          <Button
                            variant="outline"
                            className="rounded-full"
                            onClick={() => handleOverrideCandidateCapability(row.id, 'blocked_by_gaps', 'manual')}
                            disabled={candidateActionLoading[row.id]}
                          >
                            Mark blocked
                          </Button>
                          <Button
                            variant="outline"
                            className="rounded-full"
                            onClick={() => handleUndoCandidateDecision(row.id)}
                            disabled={candidateActionLoading[row.id] || row.status === 'new'}
                          >
                            Undo decision
                          </Button>
                          <Button
                            variant="destructive"
                            className="rounded-full"
                            onClick={() => handleDeleteCandidate(row.id)}
                            disabled={candidateActionLoading[row.id] || row.status === 'picked'}
                          >
                            Delete
                          </Button>
                        </div>
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

                <div className="rounded-xl border border-stone-200 bg-white/80 p-3 text-xs text-stone-600">
                  <div className="mb-2 text-[0.65rem] uppercase tracking-[0.2em] text-stone-400">
                    Publish history
                  </div>
                  {publishRecordsLoading ? (
                    <div>Loading publish records…</div>
                  ) : publishRecordsError ? (
                    <div className="text-rose-600">{publishRecordsError}</div>
                  ) : publishRecords.length === 0 ? (
                    <div>No publish records yet.</div>
                  ) : (
                    <ul className="space-y-2">
                      {publishRecords.map((item) => (
                        <li key={item.id} className="rounded-lg border border-stone-200 bg-stone-50/70 p-2">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="font-semibold text-stone-700">{item.platform_type ?? 'unknown'}</span>
                            <Badge
                              variant="outline"
                              className={cn(
                                'border',
                                item.status === 'published' || item.status === 'manual_confirmed'
                                  ? 'border-emerald-200 bg-emerald-100 text-emerald-900'
                                  : item.status === 'failed'
                                    ? 'border-rose-200 bg-rose-100 text-rose-900'
                                    : 'border-stone-200 bg-stone-100 text-stone-700',
                              )}
                            >
                              {item.status ?? 'unknown'}
                            </Badge>
                            <span className="text-[0.7rem] text-stone-500">
                              {item.created_at ? new Date(item.created_at).toLocaleString() : '—'}
                            </span>
                          </div>
                          {item.content_id ? <div className="mt-1 text-[0.75rem]">content_id: {item.content_id}</div> : null}
                          {item.url ? <div className="truncate text-[0.75rem]">url: {item.url}</div> : null}
                          {typeof item.error_payload === 'object' && item.error_payload && 'message' in item.error_payload ? (
                            <div className="text-[0.75rem] text-rose-700">
                              error: {String((item.error_payload as { message?: unknown }).message ?? '')}
                            </div>
                          ) : null}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>

                {reviewActionMessage ? (
                  <div className="rounded-xl border border-emerald-200 bg-emerald-50/80 p-3 text-xs text-emerald-800">
                    {reviewActionMessage}
                  </div>
                ) : null}
                {reviewActionError ? (
                  <div className="rounded-xl border border-rose-200 bg-rose-50/80 p-3 text-xs text-rose-700">
                    {reviewActionError}
                  </div>
                ) : null}

                <div className="grid gap-3">
                  <div className="rounded-xl border border-stone-200 bg-white/80 p-3">
                    <div className="text-xs font-semibold uppercase tracking-[0.18em] text-stone-500">
                      QC Action
                    </div>
                    <div className="mt-3 grid gap-2">
                      <label className="text-xs font-semibold uppercase tracking-[0.15em] text-stone-500">
                        Result
                        <select
                          className="mt-1 w-full rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700"
                          value={qcResultInput}
                          onChange={(event) =>
                            setQcResultInput(event.target.value as 'accepted' | 'rejected' | 'regenerate')
                          }
                        >
                          <option value="accepted">accepted</option>
                          <option value="rejected">rejected</option>
                          <option value="regenerate">regenerate</option>
                        </select>
                      </label>
                      <label className="text-xs font-semibold uppercase tracking-[0.15em] text-stone-500">
                        Notes
                        <textarea
                          className="mt-1 w-full rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700"
                          rows={3}
                          value={qcNotesInput}
                          onChange={(event) => setQcNotesInput(event.target.value)}
                          placeholder="Opcjonalna notatka QC"
                        />
                      </label>
                      <Button
                        className="rounded-full"
                        onClick={handleQcDecision}
                        disabled={qcActionLoading}
                      >
                        {qcActionLoading ? 'Zapisywanie QC…' : 'Zapisz QC'}
                      </Button>
                    </div>
                  </div>

                  <div className="rounded-xl border border-stone-200 bg-white/80 p-3">
                    <div className="text-xs font-semibold uppercase tracking-[0.18em] text-stone-500">
                      Publish Record (manual)
                    </div>
                    <div className="mt-3 grid gap-2">
                      <div className="grid gap-2 sm:grid-cols-2">
                        <label className="text-xs font-semibold uppercase tracking-[0.15em] text-stone-500">
                          Platform
                          <select
                            className="mt-1 w-full rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700"
                            value={publishPlatformInput}
                            onChange={(event) =>
                              setPublishPlatformInput(event.target.value as 'youtube' | 'tiktok')
                            }
                          >
                            <option value="youtube">youtube</option>
                            <option value="tiktok">tiktok</option>
                          </select>
                        </label>
                        <label className="text-xs font-semibold uppercase tracking-[0.15em] text-stone-500">
                          Status
                          <select
                            className="mt-1 w-full rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700"
                            value={publishStatusInput}
                            onChange={(event) =>
                              setPublishStatusInput(
                                event.target.value as
                                  | 'queued'
                                  | 'uploading'
                                  | 'published'
                                  | 'failed'
                                  | 'manual_confirmed',
                              )
                            }
                          >
                            <option value="manual_confirmed">manual_confirmed</option>
                            <option value="published">published</option>
                            <option value="queued">queued</option>
                            <option value="uploading">uploading</option>
                            <option value="failed">failed</option>
                          </select>
                        </label>
                      </div>
                      <label className="text-xs font-semibold uppercase tracking-[0.15em] text-stone-500">
                        Content ID
                        <input
                          className="mt-1 w-full rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700"
                          value={publishContentIdInput}
                          onChange={(event) => setPublishContentIdInput(event.target.value)}
                          placeholder="yt/tiktok content id"
                        />
                      </label>
                      <label className="text-xs font-semibold uppercase tracking-[0.15em] text-stone-500">
                        URL
                        <input
                          className="mt-1 w-full rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700"
                          value={publishUrlInput}
                          onChange={(event) => setPublishUrlInput(event.target.value)}
                          placeholder="https://..."
                        />
                      </label>
                      <label className="text-xs font-semibold uppercase tracking-[0.15em] text-stone-500">
                        Error (optional)
                        <input
                          className="mt-1 w-full rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700"
                          value={publishErrorInput}
                          onChange={(event) => setPublishErrorInput(event.target.value)}
                          placeholder="Opis błędu (dla status=failed)"
                        />
                      </label>
                      <Button
                        variant="outline"
                        className="rounded-full"
                        onClick={handlePublishRecord}
                        disabled={publishActionLoading || !selectedAnimation.render?.id}
                      >
                        {publishActionLoading ? 'Zapisywanie publish…' : 'Zapisz Publish Record'}
                      </Button>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
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

      
      </>
      ) : null}

      {activeView === 'settings' ? (
      <>
      <section className="rounded-[28px] border border-stone-200/80 bg-white/90 p-6 shadow-2xl shadow-stone-900/10">
        <div className="flex flex-col gap-4 border-b border-stone-200/70 pb-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h2 className="text-2xl font-semibold text-stone-900">LLM usage</h2>
            <p className="text-sm text-stone-600">
              Tokeny i koszt per task/provider/model z mediatora LLM.
            </p>
          </div>
          <div className="text-xs text-stone-500">
            <div>Updated: {llmMetricsUpdatedAt ? llmMetricsUpdatedAt.toLocaleTimeString() : 'waiting for data'}</div>
            <div>State backend: {llmMetrics?.state_backend ?? '—'}</div>
          </div>
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-2">
          <Button variant="outline" className="rounded-full" onClick={fetchLLMMetrics} disabled={llmMetricsLoading}>
            {llmMetricsLoading ? 'Refreshing…' : 'Refresh usage'}
          </Button>
          {llmMetricsError ? <span className="text-xs text-rose-600">{llmMetricsError}</span> : null}
        </div>

        {tokenBudgetAlerts.length > 0 ? (
          <div className="mt-4 rounded-2xl border border-amber-200 bg-amber-50/80 p-4 text-sm text-amber-900">
            <div className="font-semibold">Token budget warning</div>
            <div className="mt-1 text-xs text-amber-700">
              Usage is above {Math.round(TOKEN_BUDGET_ALERT_THRESHOLD * 100)}% of the configured limit.
            </div>
            <div className="mt-2 flex flex-wrap gap-2">
              {tokenBudgetAlerts.map((alert) => (
                <span
                  key={alert.label}
                  className="rounded-full border border-amber-200 bg-white/80 px-3 py-1 text-xs text-amber-900"
                >
                  {alert.label}: {alert.used.toLocaleString()} / {alert.limit.toLocaleString()}
                </span>
              ))}
            </div>
          </div>
        ) : null}

        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Card className="border border-stone-200 bg-stone-50/60 shadow-none">
            <CardContent className="pt-4">
              <div className="text-xs uppercase tracking-[0.18em] text-stone-500">Calls</div>
              <div className="mt-2 text-2xl font-semibold text-stone-900">{llmTotals.calls}</div>
            </CardContent>
          </Card>
          <Card className="border border-stone-200 bg-stone-50/60 shadow-none">
            <CardContent className="pt-4">
              <div className="text-xs uppercase tracking-[0.18em] text-stone-500">Total tokens</div>
              <div className="mt-2 text-2xl font-semibold text-stone-900">{llmTotals.tokensTotal.toLocaleString()}</div>
            </CardContent>
          </Card>
          <Card className="border border-stone-200 bg-stone-50/60 shadow-none">
            <CardContent className="pt-4">
              <div className="text-xs uppercase tracking-[0.18em] text-stone-500">Estimated cost</div>
              <div className="mt-2 text-2xl font-semibold text-stone-900">${llmTotals.costTotal.toFixed(4)}</div>
            </CardContent>
          </Card>
          <Card className="border border-stone-200 bg-stone-50/60 shadow-none">
            <CardContent className="pt-4">
              <div className="text-xs uppercase tracking-[0.18em] text-stone-500">Daily budget</div>
              <div className="mt-2 text-2xl font-semibold text-stone-900">
                ${(llmMetrics?.budget?.daily_budget_usd ?? 0).toFixed(2)}
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="mt-4 overflow-x-auto">
          {llmMetricsLoading && llmRouteRows.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-stone-200 bg-stone-50/60 p-6 text-sm text-stone-600">
              Loading usage metrics…
            </div>
          ) : (
            <table className="min-w-[960px] w-full text-left text-sm">
              <thead className="text-xs uppercase tracking-[0.18em] text-stone-500">
                <tr>
                  <th className="px-2 py-3">Task</th>
                  <th className="px-2 py-3">Provider</th>
                  <th className="px-2 py-3">Model</th>
                  <th className="px-2 py-3">Calls</th>
                  <th className="px-2 py-3">Success</th>
                  <th className="px-2 py-3">Errors</th>
                  <th className="px-2 py-3">Retries</th>
                  <th className="px-2 py-3">Tokens</th>
                  <th className="px-2 py-3">Avg latency</th>
                  <th className="px-2 py-3">Cost</th>
                </tr>
              </thead>
              <tbody>
                {llmRouteRows.length === 0 ? (
                  <tr>
                    <td colSpan={10} className="px-2 py-6 text-center text-stone-500">
                      No LLM calls yet.
                    </td>
                  </tr>
                ) : (
                  llmRouteRows.map((row) => (
                    <tr key={row.routeKey} className="border-t border-stone-200/70">
                      <td className="px-2 py-4 text-stone-800">{row.taskType}</td>
                      <td className="px-2 py-4 text-stone-600">{row.provider}</td>
                      <td className="px-2 py-4 font-mono text-xs text-stone-600">{row.model}</td>
                      <td className="px-2 py-4 text-stone-700">{row.calls}</td>
                      <td className="px-2 py-4 text-stone-700">{row.success}</td>
                      <td className="px-2 py-4 text-stone-700">{row.errors}</td>
                      <td className="px-2 py-4 text-stone-700">{row.retries}</td>
                      <td className="px-2 py-4 text-stone-700">{row.tokensTotal.toLocaleString()}</td>
                      <td className="px-2 py-4 text-stone-700">{Math.round(row.avgLatencyMs)} ms</td>
                      <td className="px-2 py-4 text-stone-700">${row.costTotal.toFixed(4)}</td>
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
                <SettingRow label="DEV_MANUAL_FLOW" value={settings.dev_manual_flow} />
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
      </>
      ) : null}
    </div>
  )
}

export default App
