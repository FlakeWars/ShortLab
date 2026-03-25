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

type PublishConnectorStatusResponse = {
  updated_at?: string
  connectors?: Record<
    string,
    {
      ready?: boolean
      mode?: string
    }
  >
}

type PlannerSettings = {
  timezone?: string
  daily_publish_hour?: number
  daily_publish_minute?: number
  publish_window_minutes?: number
  target_per_day?: number
}

type PlannerStatusResponse = {
  timezone?: string
  now_utc?: string
  now_local?: string
  local_day?: string
  window_start_local?: string
  window_end_local?: string
  window_minutes?: number
  target_per_day?: number
  published_today?: number
  pending_jobs_today?: number
  in_window?: boolean
  should_enqueue?: boolean
  reason?: string
  settings?: PlannerSettings
}

type InsightsWindow = {
  days?: number
  from_date?: string
  views?: number
  likes?: number
  comments?: number
  shares?: number
  watch_time_seconds?: number
  avg_view_percentage?: number | null
  engagement_rate?: number | null
  published_count?: number
}

type InsightsSummaryResponse = {
  generated_at?: string
  windows?: Record<string, InsightsWindow>
  top_content_14d?: Array<{
    platform?: string
    content_id?: string
    views?: number
    engagement_rate?: number | null
    watch_time_seconds?: number
  }>
  audio_profiles_14d?: Array<{
    audio_profile?: string
    rows?: number
    views?: number
    watch_time_seconds?: number
    avg_view_percentage?: number | null
    avg_view_duration_seconds?: number | null
  }>
  intro_translate_14d?: {
    rows_total?: number
    attempted?: number
    translated?: number
    fallback?: number
    empty_result?: number
    disabled?: number
    other?: number
    fallback_share_attempted?: number | null
  }
  recommendation_code?: string
  recommendation?: string
}

type PublishReadinessSummaryResponse = {
  generated_at?: string
  overall_pass?: boolean
  components?: Record<
    string,
    {
      pass?: boolean
      reason?: string
    }
  >
  source_file?: string
}

type GodotManualStepResult = {
  ok?: boolean
  mode?: 'validate' | 'estimate' | 'intent_check' | 'preview' | 'render' | 'intro_overlay' | 'audio_mix'
  script_path?: string
  input_path?: string
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
  estimate?: {
    reached?: boolean
    effect_time_s?: number
    threshold?: number
    hold_s?: number
    progress?: number
    support?: boolean
  }
  target_duration_s?: number
  scout_seconds?: number
  tail_seconds?: number
  recommended_sim_duration_s?: number
  recommended_speed_factor?: number
  intent_reached?: boolean
  intent_reached_at_s?: number | null
  intent_progress?: number | null
  target_runtime_s?: number
  runtime_override_s?: number | null
  intro_text?: string
  language?: string
  duration_s?: number
  font_size?: number
  music_path?: string | null
  sfx_path?: string | null
  keep_source_audio?: boolean
  music_gain_db?: number
  sfx_gain_db?: number
  normalize_loudness?: boolean
  target_lufs?: number
  true_peak_db?: number
  audio_profile?: string | null
  intent_status?: string
  blocking_reason?: string | null
  confidence?: number
  method?: string
}

type GodotManualHistoryRow = {
  id: string
  recorded_at?: string | null
  step?: 'compile' | 'validate' | 'estimate' | 'intent_check' | 'preview' | 'render' | string | null
  ok?: boolean | null
  actor_user_id?: string | null
  idea_id?: string | null
  script_path?: string | null
  out_path?: string | null
  out_exists?: boolean | null
  log_file?: string | null
  exit_code?: number | null
  script_hash?: string | null
  estimate?: Record<string, unknown> | null
  recommended_sim_duration_s?: number | null
  recommended_speed_factor?: number | null
  target_duration_s?: number | null
  target_runtime_s?: number | null
  intent_reached?: boolean | null
  intent_reached_at_s?: number | null
  intent_progress?: number | null
  intent_status?: string | null
  blocking_reason?: string | null
  confidence?: number | null
  method?: string | null
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
const MANUAL_STEP_ORDER = ['compile', 'validate', 'estimate', 'preview', 'intent_check', 'render', 'intro_overlay', 'audio_mix'] as const
const MANUAL_STEP_LABELS: Record<(typeof MANUAL_STEP_ORDER)[number], string> = {
  compile: 'Kompilacja',
  validate: 'Walidacja',
  estimate: 'Estymacja',
  preview: 'Podgląd',
  intent_check: 'Sprawdzenie intencji',
  render: 'Render finalny',
  intro_overlay: 'Intro',
  audio_mix: 'Miks audio',
}
const MANUAL_STEP_STATUS_LABELS: Record<'idle' | 'success' | 'fail', string> = {
  idle: 'oczekuje',
  success: 'sukces',
  fail: 'błąd',
}
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
  idea_candidates: 'Kandydaci na pomysł',
  ideas: 'Pomysły',
  dsl_gaps: 'Braki DSL',
  animations: 'Animacje',
  renders: 'Rendery',
  artifacts: 'Artefakty',
  jobs: 'Zadania',
  sfx: 'SFX',
  music: 'Muzyka',
}

const REPO_HINTS: Record<(typeof REPO_CARD_ORDER)[number], string> = {
  idea_candidates: 'Surowe propozycje przed decyzją operatora (new/later/picked/rejected).',
  ideas: 'Pomysły w pipeline (unverified/ready/blocked/feasible/compiled).',
  dsl_gaps: 'Braki DSL blokujące realizację pomysłu.',
  animations: 'Animacje powiązane z pomysłami.',
  renders: 'Zadania renderu i ich statusy.',
  artifacts: 'Pliki wynikowe (wideo/metadane).',
  jobs: 'Zadania pipeline (queued/running/failed).',
  sfx: 'Repozytorium efektów dźwiękowych (planowane).',
  music: 'Repozytorium muzyki (planowane).',
}

function getViewFromUrl(): AppView {
  if (typeof window === 'undefined') return 'home'
  const params = new URLSearchParams(window.location.search)
  const value = params.get('view')?.toLowerCase().trim()
  if (value && VIEW_SLUG_ALIASES[value]) {
    return VIEW_SLUG_ALIASES[value]
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
const SYSTEM_STATUS_POLL_MS = 15000
const SYSTEM_STATUS_TIMEOUT_MS = 8000
const SYSTEM_STATUS_STALE_MS = 60000
const SYSTEM_STATUS_SLO_MS = 3000
const ANIMATION_POLL_MS = 20000
const FLOW_ANIMATION_PREVIEW_LIMIT = 8
const AUDIO_PROFILE_PRESETS = {
  balanced: { targetLufs: '-16', truePeakDb: '-1', musicGainDb: '-18', sfxGainDb: '-6', normalizeLoudness: true },
  speech: { targetLufs: '-15', truePeakDb: '-1', musicGainDb: '-24', sfxGainDb: '-8', normalizeLoudness: true },
  music: { targetLufs: '-14', truePeakDb: '-1', musicGainDb: '-14', sfxGainDb: '-10', normalizeLoudness: true },
  sfx_heavy: { targetLufs: '-16', truePeakDb: '-1', musicGainDb: '-20', sfxGainDb: '-3', normalizeLoudness: true },
} as const
const INTENT_CHECK_PRESETS = {
  balanced: { threshold: '0.85', holdSeconds: '2', tailSeconds: '2' },
  fast_hook: { threshold: '0.78', holdSeconds: '1.2', tailSeconds: '1.5' },
  gradual_reveal: { threshold: '0.9', holdSeconds: '3', tailSeconds: '3' },
  loop_pattern: { threshold: '0.82', holdSeconds: '2.5', tailSeconds: '2' },
} as const

const VIEW_TITLE_MAP: Record<AppView, string> = {
  home: 'Panel główny',
  plan: 'Plan i analityka',
  flow: 'Przepływ operatora',
  repositories: 'Repozytoria',
  settings: 'Ustawienia',
}

const VIEW_SLUG_ALIASES: Record<string, AppView> = {
  home: 'home',
  todzień: 'home',
  flow: 'flow',
  operator_flow: 'flow',
  plan: 'plan',
  insights: 'plan',
  repositories: 'repositories',
  repo: 'repositories',
  settings: 'settings',
}

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

function viewLabel(view: AppView, singleVideoMode: boolean): string {
  if (singleVideoMode) {
    if (view === 'home') return 'todzień'
    if (view === 'plan') return 'insights'
  }
  return view
}

function viewSlug(view: AppView, singleVideoMode: boolean): string {
  if (singleVideoMode) {
    if (view === 'home') return 'todzień'
    if (view === 'plan') return 'insights'
  }
  return view
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

function isValidIanaTimeZone(timeZone: string): boolean {
  try {
    new Intl.DateTimeFormat('en-US', { timeZone }).format(new Date())
    return true
  } catch {
    return false
  }
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
  operator_single_video_mode?: string
  operator_target_runtime_s?: string
  operator_intro_language?: string
  operator_later_max_age_days?: string
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
    budget_dzień?: string
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
  const [systemStatusLastOkAt, setSystemStatusLastOkAt] = useState<Date | null>(null)
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
  const [planPublishFilterPlatform, setPlanPublishFilterPlatform] = useState('')
  const [planPublishFilterStatus, setPlanPublishFilterStatus] = useState('')
  const [planPublishFilterDateFrom, setPlanPublishFilterDateFrom] = useState('')
  const [planPublishFilterDateTo, setPlanPublishFilterDateTo] = useState('')
  const [planMetricsRows, setPlanMetricsRows] = useState<MetricsDailyRow[]>([])
  const [planMetricsError, setPlanMetricsError] = useState<string | null>(null)
  const [planMetricsLoading, setPlanMetricsLoading] = useState(false)
  const [insightsSummary, setInsightsSummary] = useState<InsightsSummaryResponse | null>(null)
  const [insightsSummaryError, setInsightsSummaryError] = useState<string | null>(null)
  const [insightsSummaryLoading, setInsightsSummaryLoading] = useState(false)
  const [publishReadinessSummary, setPublishReadinessSummary] = useState<PublishReadinessSummaryResponse | null>(null)
  const [publishReadinessError, setPublishReadinessError] = useState<string | null>(null)
  const [publishReadinessLoading, setPublishReadinessLoading] = useState(false)
  const [publishReadinessRefreshLoading, setPublishReadinessRefreshLoading] = useState(false)
  const [publishReadinessRefreshMessage, setPublishReadinessRefreshMessage] = useState<string | null>(null)
  const [publishReadinessRefreshError, setPublishReadinessRefreshError] = useState<string | null>(null)
  const [plannerSettings, setPlannerSettings] = useState<PlannerSettings | null>(null)
  const [plannerSettingsLoading, setPlannerSettingsLoading] = useState(false)
  const [plannerSettingsError, setPlannerSettingsError] = useState<string | null>(null)
  const [plannerSettingsMessage, setPlannerSettingsMessage] = useState<string | null>(null)
  const [plannerTimezoneInput, setPlannerTimezoneInput] = useState('UTC')
  const [plannerHourInput, setPlannerHourInput] = useState('18')
  const [plannerMinuteInput, setPlannerMinuteInput] = useState('00')
  const [plannerWindowInput, setPlannerWindowInput] = useState('120')
  const [plannerTargetInput, setPlannerTargetInput] = useState('1')
  const [plannerStatus, setPlannerStatus] = useState<PlannerStatusResponse | null>(null)
  const [plannerStatusLoading, setPlannerStatusLoading] = useState(false)
  const [plannerStatusError, setPlannerStatusError] = useState<string | null>(null)
  const [plannerTickLoading, setPlannerTickLoading] = useState(false)
  const [plannerTickMessage, setPlannerTickMessage] = useState<string | null>(null)
  const [plannerTickError, setPlannerTickError] = useState<string | null>(null)
  const [metricsImportLoading, setMetricsImportLoading] = useState(false)
  const [metricsImportMessage, setMetricsImportMessage] = useState<string | null>(null)
  const [metricsImportError, setMetricsImportError] = useState<string | null>(null)
  const [metricsImportPlatform, setMetricsImportPlatform] = useState<'youtube' | 'tiktok'>('youtube')
  const [metricsImportContentId, setMetricsImportContentId] = useState('')
  const [metricsImportDate, setMetricsImportDate] = useState(new Date().toISOString().slice(0, 10))
  const [metricsImportViews, setMetricsImportViews] = useState('0')
  const [metricsImportLikes, setMetricsImportLikes] = useState('0')
  const [metricsImportComments, setMetricsImportComments] = useState('0')
  const [metricsImportShares, setMetricsImportShares] = useState('0')
  const [metricsImportWatchTime, setMetricsImportWatchTime] = useState('0')
  const [metricsImportAudioProfile, setMetricsImportAudioProfile] = useState<
    '' | 'balanced' | 'speech' | 'music' | 'sfx_heavy'
  >('')
  const [metricsImportAvgPercent, setMetricsImportAvgPercent] = useState('')
  const [metricsImportAvgDuration, setMetricsImportAvgDuration] = useState('')
  const [reviewActionMessage, setReviewActionMessage] = useState<string | null>(null)
  const [reviewActionError, setReviewActionError] = useState<string | null>(null)
  const [qcActionLoading, setQcActionLoading] = useState(false)
  const [publishActionLoading, setPublishActionLoading] = useState(false)
  const [publishConnectorStatus, setPublishConnectorStatus] = useState<PublishConnectorStatusResponse | null>(null)
  const [publishConnectorStatusError, setPublishConnectorStatusError] = useState<string | null>(null)
  const [qcResultInput, setQcResultInput] = useState<'accepted' | 'rejected' | 'regenerate'>('accepted')
  const [qcNotesInput, setQcNotesInput] = useState('')
  const [qcIdeaIntentOk, setQcIdeaIntentOk] = useState(true)
  const [qcIntroReadabilityOk, setQcIntroReadabilityOk] = useState(true)
  const [qcAudioQualityOk, setQcAudioQualityOk] = useState(true)
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

  const [ideaSampleCount, setIdeaSampleCount] = useState('1')
  const [ideaDecisions, setIdeaDecisions] = useState<Record<string, string>>({})
  const [ideaDecisionError, setIdeaDecisionError] = useState<string | null>(null)
  const [ideaDecisionMessage, setIdeaDecisionMessage] = useState<string | null>(null)
  const [ideaDecisionLoading, setIdeaDecisionLoading] = useState(false)
  const [manualPickCandidates, setManualPickCandidates] = useState<IdeaCandidate[]>([])
  const [manualPickCandidateId, setManualPickCandidateId] = useState('')
  const [manualPickLoading, setManualPickLoading] = useState(false)
  const [manualPickError, setManualPickError] = useState<string | null>(null)
  const [generatorMode, setGeneratorMode] = useState<'llm' | 'text' | 'file'>('llm')
  const [generatorLimit, setGeneratorLimit] = useState('1')
  const [generatorPrompt, setGeneratorPrompt] = useState('')
  const [generatorText, setGeneratorText] = useState('')
  const [generatorFileName, setGeneratorFileName] = useState('')
  const [generatorFileContent, setGeneratorFileContent] = useState('')
  const [generatorMessage, setGeneratorMessage] = useState<string | null>(null)
  const [generatorSkipSummary, setGeneratorSkipSummary] = useState<Record<string, number>>({})
  const [generatorSkipExamples, setGeneratorSkipExamples] = useState<Array<{ title?: string; reason?: string }>>([])
  const [generatorError, setGeneratorError] = useState<string | null>(null)
  const [generatorLoading, setGeneratorLoading] = useState(false)
  const [showLegacyDslPanels, setShowLegacyDslPanels] = useState(false)

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
  const [godotSekundy, setGodotSekundy] = useState('2')
  const [godotFps, setGodotFps] = useState('12')
  const [godotMaxNodes, setGodotMaxNodes] = useState('200')
  const [godotPreviewScale, setGodotPreviewScale] = useState('0.5')
  const [godotTargetDuration, setGodotTargetDuration] = useState('60')
  const [godotScoutSekundy, setGodotScoutSekundy] = useState('60')
  const [godotEstimatePróg, setGodotEstimatePróg] = useState('0.85')
  const [godotEstimateHoldSekundy, setGodotEstimateHoldSekundy] = useState('2')
  const [godotEstimateTailSekundy, setGodotEstimateTailSekundy] = useState('2')
  const [intentCheckPreset, setIntentCheckPreset] = useState<keyof typeof INTENT_CHECK_PRESETS>('balanced')
  const [introInputPath, setIntroInputPath] = useState('')
  const [introOutPath, setIntroOutPath] = useState('')
  const [introText, setIntroText] = useState('')
  const [introCzas, setIntroCzas] = useState('1.5')
  const [introFontSize, setIntroFontSize] = useState('52')
  const [audioInputPath, setAudioInputPath] = useState('')
  const [audioOutPath, setAudioOutPath] = useState('')
  const [audioMusicPath, setAudioMusicPath] = useState('')
  const [audioSfxPath, setAudioSfxPath] = useState('')
  const [audioKeepSource, setAudioKeepSource] = useState(false)
  const [audioMusicGainDb, setAudioMusicGainDb] = useState('-18')
  const [audioSfxGainDb, setAudioSfxGainDb] = useState('-6')
  const [audioNormalizeLoudness, setAudioNormalizeLoudness] = useState(true)
  const [audioTargetLufs, setAudioTargetLufs] = useState('-16')
  const [audioTruePeakDb, setAudioTruePeakDb] = useState('-1')
  const [audioProfile, setAudioProfile] = useState<keyof typeof AUDIO_PROFILE_PRESETS>('balanced')
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
  const [laterCleanupMaxAgeDays, setLaterCleanupMaxAgeDays] = useState('30')
  const [laterCleanupDryRun, setLaterCleanupDryRun] = useState(true)
  const [laterCleanupLoading, setLaterCleanupLoading] = useState(false)
  const [laterCleanupMessage, setLaterCleanupMessage] = useState<string | null>(null)
  const [laterCleanupError, setLaterCleanupError] = useState<string | null>(null)
  const manualFlowEnabled = settings?.dev_manual_flow === '1'
  const singleVideoMode = (settings?.operator_single_video_mode ?? '1') !== '0'
  const [showAdvancedFlowPanels, setShowAdvancedFlowPanels] = useState(false)
  const [showManualTechnicalParams, setShowManualTechnicalParams] = useState(false)
  const primaryOperatorViews: readonly AppView[] = singleVideoMode ? ['home', 'flow', 'plan'] : APP_VIEWS
  const activeViewTitle = VIEW_TITLE_MAP[activeView]

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

  const summarizePayload = (payload: unknown) => {
    if (!payload || typeof payload !== 'object') return String(payload ?? '')
    const row = payload as Record<string, unknown>
    const keys = [
      'status',
      'result',
      'job_id',
      'animation_id',
      'render_id',
      'idea_id',
      'out_path',
      'intent_status',
      'queued',
      'cleaned',
      'updated',
    ]
    const parts = keys
      .map((key) => {
        const value = row[key]
        if (value === undefined || value === null || value === '') return null
        return `${key}=${String(value)}`
      })
      .filter((value): value is string => Boolean(value))
    if (typeof row.deleted_count === 'number' || typeof row.expired_count === 'number' || typeof row.skipped_count === 'number') {
      parts.push(
        `expired=${Number(row.expired_count ?? 0)}`,
        `deleted=${Number(row.deleted_count ?? 0)}`,
        `skipped=${Number(row.skipped_count ?? 0)}`,
      )
    }
    return parts.length ? parts.join(' | ') : JSON.stringify(payload)
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
    const controller = new AbortController()
    const timeoutId = window.setTimeout(() => controller.abort(), SYSTEM_STATUS_TIMEOUT_MS)
    try {
      const response = await fetch(`${API_BASE}/system/status`, { signal: controller.signal })
      if (!response.ok) {
        if (response.status === 404) {
          throw new Error(
            'Brak endpointu /system/status. Wykryto niezgodność wersji backend/UI. Uruchom ponownie backend (`make run-dev`) i odśwież UI.',
          )
        }
        throw new Error(await readApiError(response))
      }
      const payload = (await response.json()) as SystemStatusResponse
      if (!payload || typeof payload !== 'object' || !('service_status' in payload) || !('repo_counts' in payload)) {
        throw new Error(
          'Niezgodność kontraktu API dla /system/status. Backend jest prawdopodobnie nieaktualny. Uruchom ponownie backend (`make run-dev`) i odśwież UI.',
        )
      }
      setSystemStatus(payload)
      setSystemStatusLastOkAt(new Date())
    } catch (err) {
      if (err instanceof DOMException && err.name === 'AbortError') {
        setSystemStatusError(
          `System status timeout after ${SYSTEM_STATUS_TIMEOUT_MS}ms. Check API load/health and try again.`,
        )
      } else {
        setSystemStatusError(err instanceof Error ? err.message : 'Nieznany błąd')
      }
    } finally {
      window.clearTimeout(timeoutId)
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
      setAnimationError(err instanceof Error ? err.message : 'Nieznany błąd')
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
      setArtifactsError(err instanceof Error ? err.message : 'Nieznany błąd')
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
      setPublishRecordsError(err instanceof Error ? err.message : 'Nieznany błąd')
    } finally {
      setPublishRecordsLoading(false)
    }
  }

  const fetchPlanPublishRecords = async (filters?: { platform?: string; status?: string }) => {
    setPlanPublishRecordsLoading(true)
    setPlanPublishRecordsError(null)
    try {
      const params = new URLSearchParams()
      params.set('limit', '50')
      const platform = filters?.platform ?? planPublishFilterPlatform
      const status = filters?.status ?? planPublishFilterStatus
      if (platform) params.set('platform_type', platform)
      if (status) params.set('status', status)
      const response = await fetch(`${API_BASE}/publish-records?${params.toString()}`)
      if (!response.ok) {
        throw new Error(await readApiError(response))
      }
      const payload = (await response.json()) as PublishRecordRow[]
      setPlanPublishRecords(payload)
    } catch (err) {
      setPlanPublishRecordsError(err instanceof Error ? err.message : 'Nieznany błąd')
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
      setPlanMetricsError(err instanceof Error ? err.message : 'Nieznany błąd')
    } finally {
      setPlanMetricsLoading(false)
    }
  }

  const fetchPublishConnectorStatus = async () => {
    setPublishConnectorStatusError(null)
    try {
      const response = await fetch(`${API_BASE}/publish/connectors/status`, {
        headers: opsHeaders(),
      })
      if (!response.ok) {
        throw new Error(await readApiError(response))
      }
      const payload = (await response.json()) as PublishConnectorStatusResponse
      setPublishConnectorStatus(payload)
    } catch (err) {
      setPublishConnectorStatusError(err instanceof Error ? err.message : 'Nieznany błąd')
    }
  }

  const fetchInsightsSummary = async () => {
    setInsightsSummaryLoading(true)
    setInsightsSummaryError(null)
    try {
      const response = await fetch(`${API_BASE}/insights/summary`, {
        headers: opsHeaders(),
      })
      if (!response.ok) {
        throw new Error(await readApiError(response))
      }
      const payload = (await response.json()) as InsightsSummaryResponse
      setInsightsSummary(payload)
    } catch (err) {
      setInsightsSummaryError(err instanceof Error ? err.message : 'Nieznany błąd')
    } finally {
      setInsightsSummaryLoading(false)
    }
  }

  const fetchPublishReadinessSummary = async () => {
    setPublishReadinessLoading(true)
    setPublishReadinessError(null)
    try {
      const response = await fetch(`${API_BASE}/publish/readiness-summary`, {
        headers: opsHeaders(),
      })
      if (!response.ok) {
        throw new Error(await readApiError(response))
      }
      const payload = (await response.json()) as PublishReadinessSummaryResponse
      setPublishReadinessSummary(payload)
    } catch (err) {
      setPublishReadinessError(err instanceof Error ? err.message : 'Nieznany błąd')
    } finally {
      setPublishReadinessLoading(false)
    }
  }

  const runPublishReadinessRefresh = async () => {
    setPublishReadinessRefreshLoading(true)
    setPublishReadinessRefreshError(null)
    setPublishReadinessRefreshMessage(null)
    try {
      const response = await fetch(`${API_BASE}/ops/publish/readiness-refresh`, {
        method: 'POST',
        headers: opsHeaders(),
        body: JSON.stringify({
          run_mcp_audit: true,
          run_compliance_check: true,
          run_oauth_smoke: true,
          oauth_online: false,
          oauth_require: 'passed_if_configured',
          mcp_audit_fail_on_risk_level: 'none',
          compliance_require: 'none',
          summary_max_allowed_risk: 'medium',
          summary_require_pass: false,
        }),
      })
      if (!response.ok) {
        throw new Error(await readApiError(response))
      }
      const payload = (await response.json()) as {
        ok?: boolean
        scripts_ok?: boolean
        overall_pass?: boolean
      }
      setPublishReadinessRefreshMessage(
        `Odświeżenie bramki zakończone (ok=${String(payload.ok ?? false)}, scripts_ok=${String(payload.scripts_ok ?? false)}, overall_pass=${String(payload.overall_pass ?? false)}).`,
      )
      fetchPublishReadinessSummary()
      fetchAuditEvents()
    } catch (err) {
      setPublishReadinessRefreshError(err instanceof Error ? err.message : 'Nieznany błąd')
    } finally {
      setPublishReadinessRefreshLoading(false)
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
      setPlannerSettingsError(err instanceof Error ? err.message : 'Nieznany błąd')
    } finally {
      setPlannerSettingsLoading(false)
    }
  }

  const fetchPlannerStatus = async () => {
    setPlannerStatusLoading(true)
    setPlannerStatusError(null)
    try {
      const response = await fetch(`${API_BASE}/planner/status`)
      if (!response.ok) {
        throw new Error(await readApiError(response))
      }
      const payload = (await response.json()) as PlannerStatusResponse
      setPlannerStatus(payload)
    } catch (err) {
      setPlannerStatusError(err instanceof Error ? err.message : 'Nieznany błąd')
    } finally {
      setPlannerStatusLoading(false)
    }
  }

  const savePlannerSettings = async () => {
    const timezone = plannerTimezoneInput.trim() || 'UTC'
    if (!isValidIanaTimeZone(timezone)) {
      setPlannerSettingsError('Nieprawidłowa strefa czasowa. Użyj formatu IANA (np. Europe/Warsaw, UTC).')
      setPlannerSettingsMessage(null)
      return
    }
    setPlannerSettingsLoading(true)
    setPlannerSettingsError(null)
    setPlannerSettingsMessage(null)
    try {
      const body = {
        timezone,
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
      fetchPlannerStatus()
    } catch (err) {
      setPlannerSettingsError(err instanceof Error ? err.message : 'Nieznany błąd')
    } finally {
      setPlannerSettingsLoading(false)
    }
  }

  const runPlannerTick = async (force = false) => {
    setPlannerTickLoading(true)
    setPlannerTickError(null)
    setPlannerTickMessage(null)
    try {
      const response = await fetch(`${API_BASE}/ops/planner/tick`, {
        method: 'POST',
        headers: opsHeaders(),
        body: JSON.stringify({ force }),
      })
      if (!response.ok) {
        throw new Error(await readApiError(response))
      }
      const payload = (await response.json()) as Record<string, unknown>
      setPlannerTickMessage(`Tick planera: ${summarizePayload(payload)}`)
      fetchPlannerStatus()
      fetchSummary()
      fetchAnimations()
      fetchAuditEvents()
    } catch (err) {
      setPlannerTickError(err instanceof Error ? err.message : 'Nieznany błąd')
    } finally {
      setPlannerTickLoading(false)
    }
  }

  const handleManualMetricsImport = async () => {
    setMetricsImportLoading(true)
    setMetricsImportError(null)
    setMetricsImportMessage(null)
    try {
      const contentId = metricsImportContentId.trim()
      if (!contentId) {
        throw new Error('Podaj ID treści dla metryk.')
      }
      if (!metricsImportDate) {
        throw new Error('Podaj datę metryk.')
      }
      const body: Record<string, unknown> = {
        platform_type: metricsImportPlatform,
        content_id: contentId,
        date: metricsImportDate,
        views: Math.max(0, Math.floor(parseNumberInput(metricsImportViews, 0))),
        likes: Math.max(0, Math.floor(parseNumberInput(metricsImportLikes, 0))),
        comments: Math.max(0, Math.floor(parseNumberInput(metricsImportComments, 0))),
        shares: Math.max(0, Math.floor(parseNumberInput(metricsImportShares, 0))),
        watch_time_seconds: Math.max(0, Math.floor(parseNumberInput(metricsImportWatchTime, 0))),
      }
      if (metricsImportAudioProfile) {
        body.audio_profile = metricsImportAudioProfile
      }
      if (metricsImportAvgPercent.trim()) {
        body.avg_view_percentage = Math.max(0, Math.min(100, parseNumberInput(metricsImportAvgPercent, 0)))
      }
      if (metricsImportAvgDuration.trim()) {
        body.avg_view_duration_seconds = Math.max(0, Math.floor(parseNumberInput(metricsImportAvgDuration, 0)))
      }
      const response = await fetch(`${API_BASE}/ops/metrics-daily`, {
        method: 'POST',
        headers: opsHeaders(),
        body: JSON.stringify(body),
      })
      if (!response.ok) {
        throw new Error(await readApiError(response))
      }
      const payload = (await response.json()) as Record<string, unknown>
      setMetricsImportMessage(`Zapisano metryki: ${summarizePayload(payload)}`)
      fetchPlanMetrics()
      fetchAuditEvents()
    } catch (err) {
      setMetricsImportError(err instanceof Error ? err.message : 'Nieznany błąd')
    } finally {
      setMetricsImportLoading(false)
    }
  }

  const prefillMetricsFromPublishRecord = (row: PublishRecordRow) => {
    if (row.platform_type === 'youtube' || row.platform_type === 'tiktok') {
      setMetricsImportPlatform(row.platform_type)
    }
    if (row.content_id) {
      setMetricsImportContentId(row.content_id)
    }
    const sourceDate = row.published_at || row.created_at
    if (sourceDate) {
      setMetricsImportDate(new Date(sourceDate).toISOString().slice(0, 10))
    }
    setMetricsImportMessage(null)
    setMetricsImportError(null)
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
      setGodotHistoryError(err instanceof Error ? err.message : 'Nieznany błąd')
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
      const count = Number(ideaSampleCount || '1')
      const limit = singleVideoMode ? 1 : Number.isNaN(count) ? 1 : Math.max(1, Math.min(count, 10))
      const response = await fetch(`${API_BASE}/idea-repo/sample?limit=${limit}`)
      if (!response.ok) {
        throw new Error(`API error ${response.status}`)
      }
      const payload = (await response.json()) as IdeaCandidate[]
      if (payload.length === 0) {
        setIdeaError(
          manualFlowEnabled
            ? 'Brak kandydatów. Wygeneruj nowe propozycje w Generatorze pomysłów.'
            : 'Brak kandydatów. Sprawdź, czy istnieją propozycje o statusie feasible.'
        )
      }
      setIdeaCandidates(payload)
      setIdeaDecisions({})
      setIdeaUpdatedAt(new Date())
      setSelectedIdea(payload[0] ?? null)
    } catch (err) {
      setIdeaError(err instanceof Error ? err.message : 'Nieznany błąd')
    } finally {
      setIdeaLoading(false)
    }
  }

  const fetchManualPickCandidates = async () => {
    setManualPickLoading(true)
    setManualPickError(null)
    try {
      const params = new URLSearchParams()
      if (!manualFlowEnabled) {
        params.set('capability_status', 'feasible')
      }
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
      setManualPickError(err instanceof Error ? err.message : 'Nieznany błąd')
    } finally {
      setManualPickLoading(false)
    }
  }

  const handleGenerateCandidates = async () => {
    setGeneratorLoading(true)
    setGeneratorError(null)
    setGeneratorMessage(null)
    setGeneratorSkipSummary({})
    setGeneratorSkipExamples([])
    try {
      const payload: Record<string, unknown> = { mode: generatorMode }
      if (generatorMode === 'llm') {
        const limit = Number(generatorLimit || '1')
        payload.limit = singleVideoMode ? 1 : Number.isNaN(limit) ? 1 : Math.max(1, Math.min(limit, 50))
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
      const result = (await response.json()) as {
        created?: number
        skipped?: number
        skip_summary?: Record<string, number>
        skip_examples?: Array<{ title?: string; reason?: string }>
      }
      setGeneratorMessage(`Utworzono ${result.created ?? 0} kandydatów, pominięto ${result.skipped ?? 0}.`)
      setGeneratorSkipSummary(result.skip_summary ?? {})
      setGeneratorSkipExamples(result.skip_examples ?? [])
      fetchSystemStatus()
      fetchIdeaCandidates()
      fetchCandidateList()
      if (manualFlowEnabled) {
        fetchManualPickCandidates()
      }
    } catch (err) {
      setGeneratorError(err instanceof Error ? err.message : 'Nieznany błąd')
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
        throw new Error('Brak propozycji do sklasyfikowania.')
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
        throw new Error('Wybierz dokładnie jedną propozycję do generacji.')
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
        setIdeaDecisionMessage('Zapisano wybrany pomysł. Uruchom ręczną kompilację w sekcji manualnej.')
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
        setIdeaDecisionMessage('Wybrany pomysł wysłano do pipeline.')
        fetchSummary()
      }
      fetchAuditEvents()
    } catch (err) {
      setIdeaDecisionError(err instanceof Error ? err.message : 'Nieznany błąd')
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
      setIdeaDecisionMessage('Wybrano kandydata ręcznie.')
      fetchSystemStatus()
      fetchCandidateList()
      fetchSummary()
      fetchAuditEvents()
    } catch (err) {
      setIdeaDecisionError(err instanceof Error ? err.message : 'Nieznany błąd')
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

  const handleCleanupLaterCandidates = async () => {
    setLaterCleanupLoading(true)
    setLaterCleanupError(null)
    setLaterCleanupMessage(null)
    try {
      const body = {
        max_age_days: Math.max(1, Math.floor(parseNumberInput(laterCleanupMaxAgeDays, 30))),
        dry_run: laterCleanupDryRun,
      }
      const response = await fetch(`${API_BASE}/ops/idea-candidates/cleanup-later`, {
        method: 'POST',
        headers: opsHeaders(),
        body: JSON.stringify(body),
      })
      if (!response.ok) {
        throw new Error(await readApiError(response))
      }
      const payload = (await response.json()) as {
        expired_count?: number
        deleted_count?: number
        skipped_count?: number
        dry_run?: boolean
      }
      setLaterCleanupMessage(
        `Czyszczenie later (${payload.dry_run ? 'dry-run' : 'apply'}): wygasłe=${payload.expired_count ?? 0}, usunięte=${payload.deleted_count ?? 0}, pominięte=${payload.skipped_count ?? 0}`,
      )
      fetchCandidateList()
      fetchSystemStatus()
      fetchAuditEvents()
    } catch (err) {
      setLaterCleanupError(err instanceof Error ? err.message : 'Nieznany błąd')
    } finally {
      setLaterCleanupLoading(false)
    }
  }

  useEffect(() => {
    if (!singleVideoMode) return
    if (ideaSampleCount !== '1') setIdeaSampleCount('1')
    if (generatorLimit !== '1') setGeneratorLimit('1')
  }, [singleVideoMode, ideaSampleCount, generatorLimit])

  useEffect(() => {
    const runtimeRaw = settings?.operator_target_runtime_s
    if (!runtimeRaw) return
    const runtime = Number(runtimeRaw)
    if (!Number.isFinite(runtime) || runtime <= 0) return
    const normalized = String(Math.floor(runtime))
    setGodotTargetDuration((prev) => (prev === normalized ? prev : normalized))
  }, [settings?.operator_target_runtime_s])

  useEffect(() => {
    const maxAgeRaw = settings?.operator_later_max_age_days
    if (!maxAgeRaw) return
    const maxAge = Number(maxAgeRaw)
    if (!Number.isFinite(maxAge) || maxAge <= 0) return
    const normalized = String(Math.floor(maxAge))
    setLaterCleanupMaxAgeDays((prev) => (prev === normalized ? prev : normalized))
  }, [settings?.operator_later_max_age_days])

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
      setAuditError(err instanceof Error ? err.message : 'Nieznany błąd')
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
      setOpsMessage(`Dodano do kolejki: ${summarizePayload(payload)}`)
      fetchSummary()
    } catch (err) {
      setOpsError(err instanceof Error ? err.message : 'Nieznany błąd')
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
      setManualCompileMessage(`Skompilowano: ${summarizePayload(payload)}`)
      fetchSystemStatus()
      fetchAuditEvents()
    } catch (err) {
      setManualCompileError(err instanceof Error ? err.message : 'Nieznany błąd')
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
      setManualPipelineMessage(`Uruchomiono pipeline: ${summarizePayload(payload)}`)
      fetchSummary()
      fetchAuditEvents()
    } catch (err) {
      setManualPipelineError(err instanceof Error ? err.message : 'Nieznany błąd')
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

  const applyIntentCheckPreset = () => {
    const preset = INTENT_CHECK_PRESETS[intentCheckPreset]
    setGodotEstimatePróg(preset.threshold)
    setGodotEstimateHoldSekundy(preset.holdSeconds)
    setGodotEstimateTailSekundy(preset.tailSeconds)
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
          validate: true,
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
      setGodotStepOutcome(step, 'fail', err instanceof Error ? err.message : 'Nieznany błąd', null)
    } finally {
      setGodotStepLoadingState(step, false)
      fetchGodotManualRuns()
    }
  }

  const handleGodotRunStep = async (step: 'validate' | 'estimate' | 'intent_check' | 'preview' | 'render') => {
    setGodotStepLoadingState(step, true)
    setGodotStepOutcome(step, 'idle', null)
    try {
      if (!godotScriptPath.trim()) {
        throw new Error('Najpierw wykonaj kompilację GDScript albo podaj ścieżkę skryptu.')
      }
      const body: Record<string, unknown> = {
        script_path: godotScriptPath.trim(),
        seconds: Math.max(0.1, parseNumberInput(godotSekundy, 2)),
        fps: Math.max(1, Math.floor(parseNumberInput(godotFps, 12))),
        max_nodes: Math.max(10, Math.floor(parseNumberInput(godotMaxNodes, 200))),
      }
      if (step === 'estimate') {
        body.target_duration_s = Math.max(1, parseNumberInput(godotTargetDuration, 30))
        body.scout_seconds = Math.max(2, parseNumberInput(godotScoutSekundy, 60))
        body.threshold = Math.max(0.1, Math.min(1, parseNumberInput(godotEstimatePróg, 0.85)))
        body.hold_seconds = Math.max(0.1, parseNumberInput(godotEstimateHoldSekundy, 2))
        body.sample_seconds = 0.5
        body.tail_seconds = Math.max(0, parseNumberInput(godotEstimateTailSekundy, 2))
      }
      if (step === 'intent_check') {
        body.runtime_override_s = Math.max(1, parseNumberInput(godotTargetDuration, 60))
        body.scout_seconds = Math.max(2, parseNumberInput(godotScoutSekundy, 60))
        body.threshold = Math.max(0.1, Math.min(1, parseNumberInput(godotEstimatePróg, 0.85)))
        body.hold_seconds = Math.max(0.1, parseNumberInput(godotEstimateHoldSekundy, 2))
        body.sample_seconds = 0.5
        body.tail_seconds = Math.max(0, parseNumberInput(godotEstimateTailSekundy, 2))
      }
      if (step === 'preview') {
        body.scale = Math.max(0.1, parseNumberInput(godotPreviewScale, 0.5))
      }
      const endpoint = step === 'intent_check' ? 'intent-check' : step
      const response = await fetch(`${API_BASE}/ops/godot/${endpoint}`, {
        method: 'POST',
        headers: opsHeaders(),
        body: JSON.stringify(body),
      })
      if (!response.ok) {
        throw new Error(await readApiError(response))
      }
      const payload = (await response.json()) as GodotManualStepResult
      setGodotStepOutcome(step, 'success', null, payload)
      if (step === 'render' && payload.out_path) {
        setIntroInputPath(payload.out_path)
        setAudioInputPath(payload.out_path)
      }
      fetchAuditEvents()
    } catch (err) {
      setGodotStepOutcome(step, 'fail', err instanceof Error ? err.message : 'Nieznany błąd', null)
    } finally {
      setGodotStepLoadingState(step, false)
      fetchGodotManualRuns()
    }
  }

  const handleIntroOverlay = async () => {
    const step = 'intro_overlay'
    setGodotStepLoadingState(step, true)
    setGodotStepOutcome(step, 'idle', null)
    try {
      const inputPath = introInputPath.trim() || godotStepResult.render?.out_path?.trim() || ''
      if (!inputPath) {
        throw new Error('Podaj ścieżkę wejściową wideo (finalny render).')
      }
      const body: Record<string, unknown> = {
        input_path: inputPath,
        intro_text: introText.trim() || undefined,
        duration_s: Math.max(0.5, parseNumberInput(introCzas, 1.5)),
        font_size: Math.max(16, Math.floor(parseNumberInput(introFontSize, 52))),
      }
      if (introOutPath.trim()) {
        body.out_path = introOutPath.trim()
      }
      const introLanguage = (settings?.operator_intro_language ?? 'en').trim().toLowerCase()
      if (introLanguage === 'pl' || introLanguage === 'en') {
        body.language = introLanguage
      }
      const response = await fetch(`${API_BASE}/ops/overlay/intro`, {
        method: 'POST',
        headers: opsHeaders(),
        body: JSON.stringify(body),
      })
      if (!response.ok) {
        throw new Error(await readApiError(response))
      }
      const payload = (await response.json()) as GodotManualStepResult
      setGodotStepOutcome(step, 'success', null, payload)
      if (payload.out_path) {
        setIntroOutPath(payload.out_path)
        setAudioInputPath(payload.out_path)
      }
      fetchAuditEvents()
    } catch (err) {
      setGodotStepOutcome(step, 'fail', err instanceof Error ? err.message : 'Nieznany błąd', null)
    } finally {
      setGodotStepLoadingState(step, false)
    }
  }

  const handleAudioMix = async () => {
    const step = 'audio_mix'
    setGodotStepLoadingState(step, true)
    setGodotStepOutcome(step, 'idle', null)
    try {
      const inputPath = audioInputPath.trim() || godotStepResult.intro_overlay?.out_path?.trim() || godotStepResult.render?.out_path?.trim() || ''
      if (!inputPath) {
        throw new Error('Podaj ścieżkę wejściową wideo dla miksu audio.')
      }
      if (!audioKeepSource && !audioMusicPath.trim() && !audioSfxPath.trim()) {
        throw new Error('Podaj co najmniej music_path lub sfx_path (albo włącz zachowanie dźwięku źródłowego).')
      }
      const body: Record<string, unknown> = {
        input_path: inputPath,
        keep_source_audio: audioKeepSource,
        music_gain_db: parseNumberInput(audioMusicGainDb, -18),
        sfx_gain_db: parseNumberInput(audioSfxGainDb, -6),
        normalize_loudness: audioNormalizeLoudness,
        target_lufs: parseNumberInput(audioTargetLufs, -16),
        true_peak_db: parseNumberInput(audioTruePeakDb, -1),
        audio_profile: audioProfile,
      }
      if (audioOutPath.trim()) {
        body.out_path = audioOutPath.trim()
      }
      if (audioMusicPath.trim()) {
        body.music_path = audioMusicPath.trim()
      }
      if (audioSfxPath.trim()) {
        body.sfx_path = audioSfxPath.trim()
      }
      const response = await fetch(`${API_BASE}/ops/audio/mix`, {
        method: 'POST',
        headers: opsHeaders(),
        body: JSON.stringify(body),
      })
      if (!response.ok) {
        throw new Error(await readApiError(response))
      }
      const payload = (await response.json()) as GodotManualStepResult
      setGodotStepOutcome(step, 'success', null, payload)
      if (payload.out_path) {
        setAudioOutPath(payload.out_path)
      }
      fetchAuditEvents()
    } catch (err) {
      setGodotStepOutcome(step, 'fail', err instanceof Error ? err.message : 'Nieznany błąd', null)
    } finally {
      setGodotStepLoadingState(step, false)
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
      setOpsMessage(`Ponowne renderowanie dodane do kolejki: ${summarizePayload(payload)}`)
      fetchSummary()
    } catch (err) {
      setOpsError(err instanceof Error ? err.message : 'Nieznany błąd')
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
      setOpsMessage(`Czyszczenie zakończone: ${summarizePayload(payload)}`)
      fetchSummary()
    } catch (err) {
      setOpsError(err instanceof Error ? err.message : 'Nieznany błąd')
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
      if (qcResultInput === 'accepted' && (!qcIdeaIntentOk || !qcIntroReadabilityOk || !qcAudioQualityOk)) {
        throw new Error('Akceptacja QC wymaga: zgodnieści z intencją pomysłu, czytelnego intro i jakości audio.')
      }
      const response = await fetch(`${API_BASE}/ops/qc-decide`, {
        method: 'POST',
        headers: opsHeaders(),
        body: JSON.stringify({
          animation_id: selectedAnimation.id,
          result: qcResultInput,
          notes: qcNotesInput.trim() || undefined,
          decision_payload: {
            idea_intent_ok: qcIdeaIntentOk,
            intro_readability_ok: qcIntroReadabilityOk,
            audio_quality_ok: qcAudioQualityOk,
          },
        }),
      })
      if (!response.ok) {
        throw new Error(await readApiError(response))
      }
      const payload = (await response.json()) as Record<string, unknown>
      setReviewActionMessage(`Zapisano QC: ${summarizePayload(payload)}`)
      await fetchAnimations()
      fetchSystemStatus()
      fetchAuditEvents()
    } catch (err) {
      setReviewActionError(err instanceof Error ? err.message : 'Nieznany błąd')
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
        throw new Error('Dla statusu published/manual_confirmed podaj ID treści lub URL.')
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
          błąd: errorText || undefined,
        }),
      })
      if (!response.ok) {
        throw new Error(await readApiError(response))
      }
      const payload = (await response.json()) as Record<string, unknown>
      setReviewActionMessage(`Zapisano publikację: ${summarizePayload(payload)}`)
      await fetchAnimations()
      fetchPublishRecords(renderId, selectedAnimation?.id ?? null)
      fetchSystemStatus()
      fetchAuditEvents()
    } catch (err) {
      setReviewActionError(err instanceof Error ? err.message : 'Nieznany błąd')
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
      setSettingsError(err instanceof Error ? err.message : 'Nieznany błąd')
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
      setLlmMetricsError(err instanceof Error ? err.message : 'Nieznany błąd')
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
      setDslGapsError(err instanceof Error ? err.message : 'Nieznany błąd')
    } finally {
      setDslGapsLoading(false)
    }
  }

  const buildGapPrompt = (gap: DslGap) => {
    const currentDslVersion = systemStatus?.dsl_version_current ?? 'v1'
    return [
      'You are a coding assistant. Your task is to implement a GAP in DSL.',
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
      `- powód: ${gap.reason ?? '—'}`,
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
      '1) Provide a short GAP implementation plan.',
      '2) Zidentyfikuj pliki do zmiany (specyfikacja, walidacja, renderer, modele).',
      '3) Wprowadz zmiany w kodzie.',
      '4) Add/update tests where applicable.',
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
      '- Follow AGENTS.md workflow rules (branches, commit, merge).',
      '- Zwracaj uwage na kompatybilniesc z aktualna wersja DSL.',
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
      setDslVersionsError(err instanceof Error ? err.message : 'Nieznany błąd')
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
      // Non-critical panel, igniere transient fetch issues.
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
      setCandidateListError(err instanceof Error ? err.message : 'Nieznany błąd')
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
      setOpsMessage(`Weryfikacja zakończona: ${summarizePayload(payload)}`)
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
      setOpsError(err instanceof Error ? err.message : 'Nieznany błąd')
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
      setOpsMessage(`Zaktualizowano gap: ${summarizePayload(payload)}`)
      fetchDslGaps()
      fetchDslVersions()
      fetchIdeaCandidates()
      fetchSystemStatus()
      fetchBlockedCandidates()
    } catch (err) {
      setOpsError(err instanceof Error ? err.message : 'Nieznany błąd')
    } finally {
      setGapActionLoading((prev) => ({ ...prev, [gapId]: false }))
    }
  }

  // Intentional polling loop initialized once on mount.
  /* eslint-disable react-hooks/exhaustive-deps */
  useEffect(() => {
    fetchSystemStatus()
    const interval = window.setInterval(fetchSystemStatus, SYSTEM_STATUS_POLL_MS)
    return () => window.clearInterval(interval)
  }, [])
  /* eslint-enable react-hooks/exhaustive-deps */

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
    params.set('view', viewSlug(activeView, singleVideoMode))
    const nextUrl = `${window.location.pathname}?${params.toString()}`
    window.history.replaceState(null, '', nextUrl)
  }, [activeView, singleVideoMode])

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

  /* eslint-disable react-hooks/exhaustive-deps */
  // Intentional one-shot/bootstrap and view-driven fetch effects.
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
    fetchInsightsSummary()
    fetchPublishReadinessSummary()
    fetchPlannerSettings()
    fetchPlannerStatus()
  }, [activeView])

  useEffect(() => {
    if (activeView !== 'plan') return
    fetchPlanPublishRecords()
  }, [activeView, planPublishFilterPlatform, planPublishFilterStatus])

  useEffect(() => {
    if (!manualFlowEnabled) return
    if (activeView !== 'flow') return
    fetchGodotManualRuns()
    fetchPublishConnectorStatus()
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

  // Poll animation list in operator-facing views (flow/repositories).
  /* eslint-disable react-hooks/exhaustive-deps */
  useEffect(() => {
    if (!(activeView === 'flow' || activeView === 'repositories')) return
    const interval = window.setInterval(() => {
      fetchAnimations()
    }, ANIMATION_POLL_MS)
    return () => window.clearInterval(interval)
  }, [activeView, animationStatus, pipelineStage, ideaId])
  /* eslint-enable react-hooks/exhaustive-deps */

  useEffect(() => {
    fetchArtifacts(selectedAnimation?.render?.id ?? null)
  }, [selectedAnimation?.render?.id])

  /* eslint-disable react-hooks/exhaustive-deps */
  useEffect(() => {
    fetchPublishRecords(selectedAnimation?.render?.id ?? null, selectedAnimation?.id ?? null)
  }, [selectedAnimation?.render?.id, selectedAnimation?.id])
  /* eslint-enable react-hooks/exhaustive-deps */

  useEffect(() => {
    setReviewActionError(null)
    setReviewActionMessage(null)
  }, [selectedAnimation?.id])

  const summary = useMemo(() => summaryData?.summary ?? {}, [summaryData])
  const services = useMemo(() => systemStatus?.service_status ?? [], [systemStatus])
  const systemStatusFresh = useMemo(() => {
    if (!systemStatusLastOkAt) return false
    return Date.now() - systemStatusLastOkAt.getTime() <= SYSTEM_STATUS_STALE_MS
  }, [systemStatusLastOkAt])
  const repoCards = useMemo(() => systemStatus?.repo_counts ?? {}, [systemStatus])
  type RepoKey = (typeof REPO_CARD_ORDER)[number]
  const repoCardCta: Partial<Record<RepoKey, { label: string; view: AppView }>> = {
    ideas: { label: 'Otwórz przepływ', view: 'flow' },
    idea_candidates: { label: 'Otwórz przepływ', view: 'flow' },
    dsl_gaps: { label: 'Otwórz repozytoria', view: 'repositories' },
    animations: { label: 'Otwórz repozytoria', view: 'repositories' },
    renders: { label: 'Otwórz repozytoria', view: 'repositories' },
    artifacts: { label: 'Otwórz repozytoria', view: 'repositories' },
    jobs: { label: 'Otwórz repozytoria', view: 'repositories' },
  }
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
  const filteredPlanPublishRecords = useMemo(() => {
    return planPublishRecords.filter((row) => {
      if (planPublishFilterPlatform && (row.platform_type || '') !== planPublishFilterPlatform) {
        return false
      }
      if (planPublishFilterStatus && (row.status || '') !== planPublishFilterStatus) {
        return false
      }
      const sourceDate = row.published_at || row.created_at
      if (!sourceDate) {
        return !planPublishFilterDateFrom && !planPublishFilterDateTo
      }
      const sourceTime = new Date(sourceDate).getTime()
      if (!Number.isFinite(sourceTime)) {
        return false
      }
      if (planPublishFilterDateFrom) {
        const from = new Date(`${planPublishFilterDateFrom}T00:00:00`).getTime()
        if (sourceTime < from) return false
      }
      if (planPublishFilterDateTo) {
        const to = new Date(`${planPublishFilterDateTo}T23:59:59`).getTime()
        if (sourceTime > to) return false
      }
      return true
    })
  }, [
    planPublishRecords,
    planPublishFilterPlatform,
    planPublishFilterStatus,
    planPublishFilterDateFrom,
    planPublishFilterDateTo,
  ])
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
  const plannerTimezoneInputValid = useMemo(
    () => isValidIanaTimeZone(plannerTimezoneInput.trim() || 'UTC'),
    [plannerTimezoneInput],
  )
  const todzieńPlanKey = useMemo(() => dateKeyInTimezone(new Date(), plannerTimezone), [plannerTimezone])
  const planPublishedTodayCount = useMemo(() => {
    return planPublishRecords.filter((row) => {
      if (!(row.status === 'published' || row.status === 'manual_confirmed')) return false
      const sourceTs = row.published_at || row.created_at
      if (!sourceTs) return false
      try {
        return dateKeyInTimezone(sourceTs, plannerTimezone) === todzieńPlanKey
      } catch {
        return false
      }
    }).length
  }, [planPublishRecords, plannerTimezone, todzieńPlanKey])
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
  const activeManualStep = useMemo(() => {
    for (const step of MANUAL_STEP_ORDER) {
      if (godotStepStatus[step] !== 'success') return step
    }
    return MANUAL_STEP_ORDER[MANUAL_STEP_ORDER.length - 1]
  }, [godotStepStatus])
  const visibleManualSteps = useMemo(() => {
    if (!singleVideoMode) return MANUAL_STEP_ORDER
    return MANUAL_STEP_ORDER.filter((step) => step === activeManualStep || godotStepStatus[step] === 'fail')
  }, [singleVideoMode, activeManualStep, godotStepStatus])
  const canRunManualStep = (step: (typeof MANUAL_STEP_ORDER)[number]) => {
    if (!singleVideoMode) return true
    return step === activeManualStep
  }
  const manualStepQuickSummary = (
    step: (typeof MANUAL_STEP_ORDER)[number],
    result: GodotManualStepResult | null | undefined,
    error: string | null | undefined,
  ) => {
    if (error) return `Błąd: ${error}`
    if (!result) return 'Brak wyniku'
    if (step === 'estimate' || step === 'intent_check') {
      if (typeof result.intent_status === 'string' && result.intent_status) {
        return `Status intencji: ${result.intent_status}`
      }
      if (typeof result.recommended_sim_duration_s === 'number') {
        return `Rekomendowany sim: ${result.recommended_sim_duration_s.toFixed(2)}s`
      }
    }
    if (step === 'intro_overlay' && typeof result.intro_text === 'string' && result.intro_text) {
      return `Intro: ${result.intro_text}`
    }
    if (step === 'audio_mix' && result.out_path) {
      return `Audio gotowe: ${result.out_path}`
    }
    if (result.out_path) return `Wynik: ${result.out_path}`
    if (typeof result.exit_code === 'number') return `Exit code: ${result.exit_code}`
    return result.ok ? 'Krok zakończony sukcesem' : 'Krok zakończony'
  }
  const introFallbackShare = insightsSummary?.intro_translate_14d?.fallback_share_attempted
  const introFallbackSharePct = typeof introFallbackShare === 'number' ? introFallbackShare * 100 : null
  const introFallbackHigh = typeof introFallbackSharePct === 'number' && introFallbackSharePct > 10

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
              Pulpit ShortLab
            </p>
            <h1 className="mt-3 font-serif text-4xl font-semibold text-stone-900 md:text-5xl">
              Puls pipeline
            </h1>
            <p className="mt-3 max-w-2xl text-base text-stone-600">
              Widok na żywo: obciążenie kolejki, stan wykonania i najnowsze zadania pipeline. Monitoruj rytm pracy, wykrywaj wąskie gardła i reaguj szybko.
            </p>
          </div>
          <div className="flex flex-col gap-3 lg:items-end">
            <div className="flex flex-wrap items-center justify-end gap-2">
              <div className="flex items-center gap-2 rounded-full border border-white/60 bg-white/70 px-3 py-1.5 text-xs font-medium text-stone-600 shadow">
                <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-emerald-500" />
                Auto-odświeżanie co 15 s
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
                <span className="text-[10px] uppercase tracking-[0.2em] text-stone-500">Motyw</span>
                <div className="flex overflow-hidden rounded-full border border-stone-200 bg-white">
                  <button
                    type="button"
                    className={cn(
                      'px-2 py-1 text-[10px] uppercase tracking-[0.18em]',
                      uiTheme === 'light' ? 'bg-stone-900 text-white' : 'text-stone-600',
                    )}
                    onClick={() => setUiTheme('light')}
                  >
                    Jasny
                  </button>
                  <button
                    type="button"
                    className={cn(
                      'px-2 py-1 text-[10px] uppercase tracking-[0.18em]',
                      uiTheme === 'dark' ? 'bg-stone-900 text-white' : 'text-stone-600',
                    )}
                    onClick={() => setUiTheme('dark')}
                  >
                    Ciemny
                  </button>
                </div>
              </div>
            </div>
            <Button variant="outline" className="rounded-full" onClick={fetchSummary} disabled={summaryLoading}>
              Odśwież teraz
            </Button>
          </div>
        </div>
      </header>

      <nav className="flex flex-wrap gap-2">
        {primaryOperatorViews.map((view) => (
          <Button
            key={view}
            variant={activeView === view ? 'default' : 'outline'}
            className="rounded-full capitalize"
            onClick={() => setActiveView(view)}
          >
            {viewLabel(view, singleVideoMode)}
          </Button>
        ))}
        {singleVideoMode ? (
          <>
            <Button
              variant={activeView === 'repositories' ? 'default' : 'outline'}
              className="rounded-full"
              onClick={() => setActiveView('repositories')}
            >
              Repozytoria
            </Button>
            <Button
              variant={activeView === 'settings' ? 'default' : 'outline'}
              className="rounded-full"
              onClick={() => setActiveView('settings')}
            >
              Ustawienia
            </Button>
          </>
        ) : null}
      </nav>
      <div className="rounded-2xl border border-stone-200/80 bg-white/80 px-4 py-2 text-xs text-stone-600">
        <span className="font-semibold text-stone-900">Widok:</span> {activeViewTitle} · Slug URL: <code>view={viewSlug(activeView, singleVideoMode)}</code>
      </div>

      {activeView === 'home' ? (
        <>
      <section className="rounded-[28px] border border-stone-200/80 bg-white/90 p-6 shadow-2xl shadow-stone-900/10">
        <div className="flex flex-col gap-4 border-b border-stone-200/70 pb-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h2 className="text-2xl font-semibold text-stone-900">{singleVideoMode ? 'Dziś' : 'Status systemu'}</h2>
            <p className="text-sm text-stone-600">
              {singleVideoMode
                ? 'Ekran startowy operatora: co dalej, czy system jest gotowy i co zrobić teraz.'
                : 'Status usług i liczniki repozytoriów. Pierwszy punkt kontroli przed uruchomieniem pipeline.'}
            </p>
            <p className="mt-1 text-xs text-stone-500">
              SLO statusu: odpytywanie {SYSTEM_STATUS_POLL_MS / 1000}s, timeout {SYSTEM_STATUS_TIMEOUT_MS / 1000}s, cel odpowiedzi {'<='}{SYSTEM_STATUS_SLO_MS}ms.
              {' '}Ostatni poprawny odczyt: {systemStatusLastOkAt ? systemStatusLastOkAt.toLocaleTimeString() : 'brak'}.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" className="rounded-full" onClick={fetchSystemStatus} disabled={systemStatusLoading}>
              {systemStatusLoading ? 'Odświeżanie…' : 'Odśwież status'}
            </Button>
          </div>
        </div>
        {!systemStatusFresh && systemStatusLastOkAt ? (
          <div className="mt-4 rounded-2xl border border-amber-200 bg-amber-50/70 p-4 text-xs text-amber-900">
            Status systemu jest nieaktualny ({Math.floor((Date.now() - systemStatusLastOkAt.getTime()) / 1000)}s od ostatniego udanego odświeżenia).
          </div>
        ) : null}
        {systemStatusError ? (
          <div className="mt-4 rounded-2xl border border-rose-200 bg-rose-50/70 p-4 text-xs text-rose-700">
            {systemStatusError}
          </div>
        ) : null}
        {systemStatus?.partial_failures && systemStatus.partial_failures.length > 0 ? (
          <div className="mt-4 rounded-2xl border border-amber-200 bg-amber-50/70 p-4 text-xs text-amber-900">
            Częściowe błędy: {systemStatus.partial_failures.join(', ')}
          </div>
        ) : null}

        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          {services.length === 0 ? (
            <div className="col-span-full rounded-xl border border-dashed border-stone-200 bg-stone-50/60 p-4 text-sm text-stone-500">
              Brak danych o usługach.
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
          <div className="text-xs uppercase tracking-[0.18em] text-stone-500">Wersja DSL</div>
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
                      planowane
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
                {repoCardCta[name] ? (
                  <Button
                    variant="outline"
                    className="mt-3 h-7 rounded-full px-3 text-[11px]"
                    onClick={() => setActiveView(repoCardCta[name]!.view)}
                  >
                    {repoCardCta[name]!.label}
                  </Button>
                ) : null}
              </CardContent>
            </Card>
          ))}
        </div>
        <p className="mt-3 text-xs text-stone-500">
          Zaktualizowano: {formatDate(systemStatus?.updated_at)}
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
            <CardTitle className="text-lg text-stone-900">Następny krok: Bramka pomysłu</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-stone-600">
            <p>Gotowe propozycje: <span className="font-semibold text-stone-900">{readyCandidates}</span></p>
            <p>Zablokowane przez braki: <span className="font-semibold text-stone-900">{blockedCandidatesCount}</span></p>
            <Button className="rounded-full" onClick={() => setActiveView('flow')}>
              Przejdź do przepływu
            </Button>
          </CardContent>
        </Card>
        <Card className="border border-stone-200 bg-white/90 shadow-lg shadow-stone-900/5">
          <CardHeader>
            <CardTitle className="text-lg text-stone-900">Następny krok: Produkcja</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-stone-600">
            <p>Zadania w toku: <span className="font-semibold text-stone-900">{queuedJobs}</span></p>
            <p>Worker: <span className="font-semibold text-stone-900">{worker?.online ? 'online' : 'offline'}</span></p>
            <Button className="rounded-full" onClick={() => setActiveView('plan')}>
              Otwórz plan
            </Button>
          </CardContent>
        </Card>
        <Card className="border border-stone-200 bg-white/90 shadow-lg shadow-stone-900/5">
          <CardHeader>
            <CardTitle className="text-lg text-stone-900">Następny krok: Diagniestyka</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-stone-600">
            <p>Sprawdź artefakty, zdarzenia audytu i metryki LLM.</p>
            <div className="flex gap-2">
              <Button variant="outline" className="rounded-full" onClick={() => setActiveView('repositories')}>
                Repozytoria
              </Button>
              <Button variant="outline" className="rounded-full" onClick={() => setActiveView('settings')}>
                Ustawienia
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
            <h2 className="text-2xl font-semibold text-stone-900">Plan / Kalendarz</h2>
            <p className="text-sm text-stone-600">
              Widok operacyjny: co jest gotowe, co zablokowane i co wymaga decyzji.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
          <Button variant="outline" className="rounded-full" onClick={fetchAnimations}>
            Odśwież plan
          </Button>
          <Button variant="outline" className="rounded-full" onClick={() => {
            fetchPlanPublishRecords()
            fetchPlanMetrics()
            fetchInsightsSummary()
            fetchPublishReadinessSummary()
          }}>
            Odśwież publikacje/metryki
          </Button>
          </div>
        </div>
        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Card className="border border-stone-200 bg-stone-50/60 shadow-none">
            <CardContent className="pt-4">
              <div className="text-xs uppercase tracking-[0.18em] text-stone-500">Gotowe do publikacji</div>
              <div className="mt-2 text-2xl font-semibold text-stone-900">{animationData.filter((a) => a.status === 'accepted').length}</div>
            </CardContent>
          </Card>
          <Card className="border border-stone-200 bg-stone-50/60 shadow-none">
            <CardContent className="pt-4">
              <div className="text-xs uppercase tracking-[0.18em] text-stone-500">Opublikowane/potwierdzone ręcznie</div>
              <div className="mt-2 text-2xl font-semibold text-stone-900">{(planPublishStatusCounts.published ?? 0) + (planPublishStatusCounts.manual_confirmed ?? 0)}</div>
            </CardContent>
          </Card>
          <Card className="border border-stone-200 bg-stone-50/60 shadow-none">
            <CardContent className="pt-4">
              <div className="text-xs uppercase tracking-[0.18em] text-stone-500">W kolejce/wysyłane</div>
              <div className="mt-2 text-2xl font-semibold text-stone-900">{(planPublishStatusCounts.queued ?? 0) + (planPublishStatusCounts.uploading ?? 0)}</div>
            </CardContent>
          </Card>
          <Card className="border border-stone-200 bg-stone-50/60 shadow-none">
            <CardContent className="pt-4">
              <div className="text-xs uppercase tracking-[0.18em] text-stone-500">Najnowsze wyświetlenia metryk (snapshot)</div>
              <div className="mt-2 text-2xl font-semibold text-stone-900">{planMetricsTotals.views}</div>
              <div className="text-xs text-stone-500">likes: {planMetricsTotals.likes}</div>
            </CardContent>
          </Card>
        </div>
        <div className="mt-4 rounded-2xl border border-stone-200 bg-white/80 p-4">
          <div className="flex items-center justify-between gap-2">
            <div>
              <div className="text-sm font-semibold text-stone-900">Bramka gotowości publikacji</div>
              <div className="text-xs text-stone-500">
                Brama zbiorcza: audyt MCP + compliance + OAuth smoke.
              </div>
            </div>
            <Button
              variant="outline"
              className="h-7 rounded-full px-3 text-[11px]"
              onClick={fetchPublishReadinessSummary}
              disabled={publishReadinessLoading}
            >
              {publishReadinessLoading ? 'Ładowanie…' : 'Odśwież bramkę'}
            </Button>
            <Button
              className="h-7 rounded-full px-3 text-[11px]"
              onClick={runPublishReadinessRefresh}
              disabled={publishReadinessRefreshLoading}
            >
              {publishReadinessRefreshLoading ? 'Uruchamianie…' : 'Uruchom sprawdzenia bramki'}
            </Button>
          </div>
          {publishReadinessError ? (
            <div className="mt-3 rounded-xl border border-rose-200 bg-rose-50/70 p-3 text-xs text-rose-700">
              {publishReadinessError}
            </div>
          ) : null}
          {publishReadinessRefreshError ? (
            <div className="mt-3 rounded-xl border border-rose-200 bg-rose-50/70 p-3 text-xs text-rose-700">
              {publishReadinessRefreshError}
            </div>
          ) : null}
          {publishReadinessRefreshMessage ? (
            <div className="mt-3 rounded-xl border border-emerald-200 bg-emerald-50/70 p-3 text-xs text-emerald-800">
              {publishReadinessRefreshMessage}
            </div>
          ) : null}
          {publishReadinessSummary ? (
            <div className="mt-3 rounded-xl border border-stone-200 bg-stone-50/60 p-3 text-xs">
              <div className="flex items-center gap-2">
                <span className="font-semibold text-stone-800">ogólnie:</span>
                <Badge
                  variant="outline"
                  className={cn(
                    'border',
                    publishReadinessSummary.overall_pass
                      ? 'border-emerald-200 bg-emerald-100 text-emerald-900'
                      : 'border-amber-200 bg-amber-100 text-amber-900',
                  )}
                >
                  {publishReadinessSummary.overall_pass ? 'OK' : 'ZABLOKOWANE'}
                </Badge>
              </div>
              <div className="mt-2 space-y-1 text-stone-600">
                {Object.entries(publishReadinessSummary.components ?? {}).map(([name, row]) => (
                  <div key={name}>
                    <span className="font-semibold text-stone-800">{name}</span>
                    : {row.pass ? 'ok' : 'fail'} ({row.reason ?? '—'})
                  </div>
                ))}
              </div>
              {publishReadinessSummary.generated_at ? (
                <div className="mt-2 text-[11px] text-stone-500">
                  wygenerowanie: {new Date(publishReadinessSummary.generated_at).toLocaleString()}
                </div>
              ) : null}
            </div>
          ) : (
            <div className="mt-3 text-xs text-stone-500">Brak danych bramki gotowości. Kliknij odśwież.</div>
          )}
        </div>
        <div className="mt-4 rounded-2xl border border-stone-200 bg-white/80 p-4">
          <div className="flex items-center justify-between gap-2">
            <div>
              <div className="text-sm font-semibold text-stone-900">Podsumowanie analityki (24h / 72h / 7d / 14d)</div>
              <div className="text-xs text-stone-500">
                Agregat metryk i rekomendacja dla kolejnego filmu.
              </div>
            </div>
            <Button
              variant="outline"
              className="h-7 rounded-full px-3 text-[11px]"
              onClick={fetchInsightsSummary}
              disabled={insightsSummaryLoading}
            >
              {insightsSummaryLoading ? 'Ładowanie…' : 'Odśwież analitykę'}
            </Button>
          </div>
          {insightsSummaryError ? (
            <div className="mt-3 rounded-xl border border-rose-200 bg-rose-50/70 p-3 text-xs text-rose-700">{insightsSummaryError}</div>
          ) : null}
          {insightsSummary ? (
            <>
              <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4 text-xs">
                {(['24h', '72h', '7d', '14d'] as const).map((windowKey) => {
                  const row = insightsSummary.windows?.[windowKey]
                  return (
                    <div key={windowKey} className="rounded-xl border border-stone-200 bg-stone-50/60 p-3">
                      <div className="font-semibold uppercase tracking-[0.15em] text-stone-700">{windowKey}</div>
                      <div className="mt-1 text-stone-600">wyświetlenia: <span className="font-semibold text-stone-900">{row?.views ?? 0}</span></div>
                      <div className="text-stone-600">publikacje: <span className="font-semibold text-stone-900">{row?.published_count ?? 0}</span></div>
                      <div className="text-stone-600">retencja: <span className="font-semibold text-stone-900">{typeof row?.avg_view_percentage === 'number' ? `${row.avg_view_percentage.toFixed(1)}%` : '—'}</span></div>
                      <div className="text-stone-600">zaangażowanie: <span className="font-semibold text-stone-900">{typeof row?.engagement_rate === 'number' ? `${(row.engagement_rate * 100).toFixed(2)}%` : '—'}</span></div>
                    </div>
                  )
                })}
              </div>
              <div className="mt-3 rounded-xl border border-amber-200 bg-amber-50/70 p-3 text-xs text-amber-900">
                <div className="font-semibold uppercase tracking-[0.15em]">Rekomendacja</div>
                <div className="mt-1">{insightsSummary.recommendation ?? '—'}</div>
                <div className="mt-1 text-[11px] text-amber-800">kod: {insightsSummary.recommendation_code ?? '—'}</div>
              </div>
              <div className="mt-3 rounded-xl border border-stone-200 bg-stone-50/60 p-3 text-xs">
                <div className="font-semibold uppercase tracking-[0.15em] text-stone-700">Najlepsze treści (14d)</div>
                {insightsSummary.top_content_14d && insightsSummary.top_content_14d.length > 0 ? (
                  <div className="mt-2 space-y-1 text-stone-600">
                    {insightsSummary.top_content_14d.map((item, idx) => (
                      <div key={`${item.platform}-${item.content_id}-${idx}`} className="flex flex-wrap gap-2">
                        <span className="font-semibold text-stone-800">{item.platform}</span>
                        <span>{item.content_id}</span>
                        <span>wyświetlenia: <span className="font-semibold text-stone-800">{item.views ?? 0}</span></span>
                        <span>eng: <span className="font-semibold text-stone-800">{typeof item.engagement_rate === 'number' ? `${(item.engagement_rate * 100).toFixed(2)}%` : '—'}</span></span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="mt-2 text-stone-500">Brak danych top treści z ostatnich 14 dni.</div>
                )}
              </div>
              <div className="mt-3 rounded-xl border border-stone-200 bg-stone-50/60 p-3 text-xs">
                <div className="font-semibold uppercase tracking-[0.15em] text-stone-700">Profile audio (14d)</div>
                {insightsSummary.audio_profiles_14d && insightsSummary.audio_profiles_14d.length > 0 ? (
                  <div className="mt-2 space-y-1 text-stone-600">
                    {insightsSummary.audio_profiles_14d.map((item, idx) => (
                      <div key={`${item.audio_profile ?? 'unknown'}-${idx}`} className="flex flex-wrap gap-2">
                        <span className="font-semibold text-stone-800">{item.audio_profile ?? 'unknown'}</span>
                        <span>wyświetlenia: <span className="font-semibold text-stone-800">{item.views ?? 0}</span></span>
                        <span>czas oglądania: <span className="font-semibold text-stone-800">{item.watch_time_seconds ?? 0}s</span></span>
                        <span>retencja: <span className="font-semibold text-stone-800">{typeof item.avg_view_percentage === 'number' ? `${item.avg_view_percentage.toFixed(1)}%` : '—'}</span></span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="mt-2 text-stone-500">Brak danych profili audio z ostatnich 14 dni.</div>
                )}
              </div>
              <div className="mt-3 rounded-xl border border-stone-200 bg-stone-50/60 p-3 text-xs">
                <div className="font-semibold uppercase tracking-[0.15em] text-stone-700">Intro translate (14d)</div>
                {introFallbackHigh ? (
                  <div className="mt-2 rounded-lg border border-amber-200 bg-amber-50/80 px-2 py-1 text-[11px] text-amber-900">
                    Uwaga: fallback tłumaczenia intro przekracza 10% prób. Sprawdź routing/model `intro_translate`.
                  </div>
                ) : null}
                <div className="mt-2 flex flex-wrap gap-2 text-stone-600">
                  <span>próbek: <span className="font-semibold text-stone-800">{insightsSummary.intro_translate_14d?.rows_total ?? 0}</span></span>
                  <span>próby tłumaczenia: <span className="font-semibold text-stone-800">{insightsSummary.intro_translate_14d?.attempted ?? 0}</span></span>
                  <span>przetłumaczone: <span className="font-semibold text-stone-800">{insightsSummary.intro_translate_14d?.translated ?? 0}</span></span>
                  <span>fallback: <span className="font-semibold text-stone-800">{(insightsSummary.intro_translate_14d?.fallback ?? 0) + (insightsSummary.intro_translate_14d?.empty_result ?? 0)}</span></span>
                  <span>wyłączone: <span className="font-semibold text-stone-800">{insightsSummary.intro_translate_14d?.disabled ?? 0}</span></span>
                  <span>
                    udział fallback:
                    <span className="font-semibold text-stone-800">
                      {typeof introFallbackSharePct === 'number'
                        ? ` ${introFallbackSharePct.toFixed(1)}%`
                        : ' —'}
                    </span>
                  </span>
                </div>
              </div>
            </>
          ) : (
            <div className="mt-3 text-xs text-stone-500">Brak podsumowania analityki. Kliknij odśwież.</div>
          )}
        </div>
        <div className="mt-4 rounded-2xl border border-stone-200 bg-white/80 p-4">
          <div className="flex flex-col gap-2 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <div className="text-sm font-semibold text-stone-900">Dzienny harmonogram publikacji (MVP)</div>
              <div className="text-xs text-stone-500">
                Skonfiguruj okno publikacji i dzienny cel w widoku Plan. Automatyczny scheduler jest nadal wyłączony.
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
              Dziś {planPublishedTodayCount}/{Number(plannerTargetInput || 1)} ({plannerTimezone})
            </Badge>
          </div>
          <div className="mt-3 grid gap-3 lg:grid-cols-[1.2fr_repeat(4,minmax(0,1fr))]">
            <label className="text-xs font-semibold uppercase tracking-[0.15em] text-stone-500">
              Strefa czasowa
              <input
                className={cn(
                  'mt-1 w-full rounded-xl border bg-white px-3 py-2 text-sm text-stone-700',
                  plannerTimezoneInputValid ? 'border-stone-200' : 'border-rose-300',
                )}
                value={plannerTimezoneInput}
                onChange={(event) => setPlannerTimezoneInput(event.target.value)}
                placeholder="Europe/Warsaw / UTC"
              />
              {!plannerTimezoneInputValid ? (
                <div className="mt-1 text-[11px] normal-case tracking-normal text-rose-700">
                  Nieprawidłowa strefa IANA (np. Europe/Warsaw, UTC).
                </div>
              ) : null}
            </label>
            <label className="text-xs font-semibold uppercase tracking-[0.15em] text-stone-500">
              Godzina
              <input
                className="mt-1 w-full rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700"
                value={plannerHourInput}
                onChange={(event) => setPlannerHourInput(event.target.value)}
                inputMode="numeric"
              />
            </label>
            <label className="text-xs font-semibold uppercase tracking-[0.15em] text-stone-500">
              Minuta
              <input
                className="mt-1 w-full rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700"
                value={plannerMinuteInput}
                onChange={(event) => setPlannerMinuteInput(event.target.value)}
                inputMode="numeric"
              />
            </label>
            <label className="text-xs font-semibold uppercase tracking-[0.15em] text-stone-500">
              Oknie (min)
              <input
                className="mt-1 w-full rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700"
                value={plannerWindowInput}
                onChange={(event) => setPlannerWindowInput(event.target.value)}
                inputMode="numeric"
              />
            </label>
            <label className="text-xs font-semibold uppercase tracking-[0.15em] text-stone-500">
              Cel / dzień
              <input
                className="mt-1 w-full rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700"
                value={plannerTargetInput}
                onChange={(event) => setPlannerTargetInput(event.target.value)}
                inputMode="numeric"
              />
            </label>
          </div>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <Button
              className="rounded-full"
              onClick={savePlannerSettings}
              disabled={plannerSettingsLoading || !plannerTimezoneInputValid}
            >
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
              Zapisanie: {String(plannerSettings.daily_publish_hour ?? 18).padStart(2, '0')}:
              {String(plannerSettings.daily_publish_minute ?? 0).padStart(2, '0')}
              {' '}({plannerSettings.publish_window_minutes ?? 120} oknie min), target {plannerSettings.target_per_day ?? 1}/dzień
            </div>
          ) : null}
          <div className="mt-4 rounded-xl border border-stone-200 bg-stone-50/60 p-3 text-xs">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="font-semibold text-stone-900">Status planera (MVP)</div>
              <div className="flex flex-wrap gap-2">
                <Button
                  variant="outline"
                  className="h-7 rounded-full px-3 text-[11px]"
                  onClick={fetchPlannerStatus}
                  disabled={plannerStatusLoading}
                >
                  {plannerStatusLoading ? 'Ładowanie…' : 'Odśwież status'}
                </Button>
                <Button
                  className="h-7 rounded-full px-3 text-[11px]"
                  onClick={() => runPlannerTick(false)}
                  disabled={plannerTickLoading}
                >
                  {plannerTickLoading ? 'Tick…' : 'Uruchom tick planera'}
                </Button>
                <Button
                  variant="outline"
                  className="h-7 rounded-full px-3 text-[11px]"
                  onClick={() => runPlannerTick(true)}
                  disabled={plannerTickLoading}
                >
                  Wymuś tick
                </Button>
              </div>
            </div>
            {plannerStatusError ? <div className="mt-2 text-rose-700">{plannerStatusError}</div> : null}
            {plannerTickError ? <div className="mt-2 text-rose-700">{plannerTickError}</div> : null}
            {plannerTickMessage ? <div className="mt-2 text-emerald-700">{plannerTickMessage}</div> : null}
            {plannerStatus ? (
              <div className="mt-2 grid gap-1 text-stone-600 sm:grid-cols-2">
                <div>dzień lokalny: <span className="font-semibold text-stone-800">{plannerStatus.local_day ?? '—'}</span></div>
                <div>strefa: <span className="font-semibold text-stone-800">{plannerStatus.timezone ?? '—'}</span></div>
                <div>start okna: <span className="font-semibold text-stone-800">{plannerStatus.window_start_local ? new Date(plannerStatus.window_start_local).toLocaleString() : '—'}</span></div>
                <div>koniec okna: <span className="font-semibold text-stone-800">{plannerStatus.window_end_local ? new Date(plannerStatus.window_end_local).toLocaleString() : '—'}</span></div>
                <div>opublikowano dziś: <span className="font-semibold text-stone-800">{plannerStatus.published_today ?? 0}</span></div>
                <div>oczekujące zadania: <span className="font-semibold text-stone-800">{plannerStatus.pending_jobs_today ?? 0}</span></div>
                <div>w oknie: <span className="font-semibold text-stone-800">{String(plannerStatus.in_window ?? false)}</span></div>
                <div>czy kolejkować: <span className="font-semibold text-stone-800">{String(plannerStatus.should_enqueue ?? false)}</span></div>
                <div className="sm:col-span-2">powód: <span className="font-semibold text-stone-800">{plannerStatus.reason ?? '—'}</span></div>
              </div>
            ) : null}
          </div>
        </div>
        <div className="mt-4 grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
          <div className="rounded-2xl border border-stone-200 bg-white/80 p-4">
            <div className="flex items-center justify-between gap-2">
              <div>
                <div className="text-sm font-semibold text-stone-900">Ostatnie rekordy publikacji</div>
                <div className="text-xs text-stone-500">Statusy publikacji i ręczne potwierdzenia (YouTube/TikTok)</div>
              </div>
              <div className="text-xs text-stone-500">{filteredPlanPublishRecords.length} / {planPublishRecords.length} wierszy</div>
            </div>
            <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
              <label className="text-xs font-semibold uppercase tracking-[0.12em] text-stone-500">
                Platform
                <select
                  className="mt-1 w-full rounded-xl border border-stone-200 bg-white px-2 py-1.5 text-xs text-stone-700"
                  value={planPublishFilterPlatform}
                  onChange={(event) => setPlanPublishFilterPlatform(event.target.value)}
                >
                  <option value="">wszystkie</option>
                  <option value="youtube">youtube</option>
                  <option value="tiktok">tiktok</option>
                </select>
              </label>
              <label className="text-xs font-semibold uppercase tracking-[0.12em] text-stone-500">
                Status
                <select
                  className="mt-1 w-full rounded-xl border border-stone-200 bg-white px-2 py-1.5 text-xs text-stone-700"
                  value={planPublishFilterStatus}
                  onChange={(event) => setPlanPublishFilterStatus(event.target.value)}
                >
                  <option value="">wszystkie</option>
                  <option value="manual_confirmed">manual_confirmed</option>
                  <option value="published">published</option>
                  <option value="queued">queued</option>
                  <option value="uploading">uploading</option>
                  <option value="failed">failed</option>
                </select>
              </label>
              <label className="text-xs font-semibold uppercase tracking-[0.12em] text-stone-500">
                Data od
                <input
                  type="date"
                  className="mt-1 w-full rounded-xl border border-stone-200 bg-white px-2 py-1.5 text-xs text-stone-700"
                  value={planPublishFilterDateFrom}
                  onChange={(event) => setPlanPublishFilterDateFrom(event.target.value)}
                />
              </label>
              <label className="text-xs font-semibold uppercase tracking-[0.12em] text-stone-500">
                Data do
                <input
                  type="date"
                  className="mt-1 w-full rounded-xl border border-stone-200 bg-white px-2 py-1.5 text-xs text-stone-700"
                  value={planPublishFilterDateTo}
                  onChange={(event) => setPlanPublishFilterDateTo(event.target.value)}
                />
              </label>
            </div>
            {planPublishRecordsLoading ? (
              <div className="mt-3 text-sm text-stone-600">Ładowanie rekordów publikacji…</div>
            ) : planPublishRecordsError ? (
              <div className="mt-3 rounded-xl border border-rose-200 bg-rose-50/70 p-3 text-xs text-rose-700">{planPublishRecordsError}</div>
            ) : filteredPlanPublishRecords.length === 0 ? (
              <div className="mt-3 rounded-xl border border-dashed border-stone-200 bg-stone-50/60 p-4 text-sm text-stone-600">
                Brak rekordów publikacji dla bieżących filtrów.
              </div>
            ) : (
              <div className="mt-3 space-y-2">
                {filteredPlanPublishRecords.slice(0, 24).map((row) => (
                  <div key={row.id} className="rounded-xl border border-stone-200 bg-stone-50/60 p-3 text-xs">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-semibold text-stone-800">{row.platform_type ?? 'nieznane'}</span>
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
                        {row.status ?? 'nieznany'}
                      </Badge>
                      <span className="text-stone-500">
                        {row.created_at ? new Date(row.created_at).toLocaleString() : '—'}
                      </span>
                    </div>
                    <div className="mt-1 grid gap-1 text-stone-600">
                      {row.content_id ? <div><span className="font-semibold text-stone-800">treść:</span> {row.content_id}</div> : null}
                      {row.url ? <div className="truncate"><span className="font-semibold text-stone-800">url:</span> {row.url}</div> : null}
                      {row.scheduled_for ? <div><span className="font-semibold text-stone-800">zaplanowano:</span> {new Date(row.scheduled_for).toLocaleString()}</div> : null}
                      {row.published_at ? <div><span className="font-semibold text-stone-800">opublikowanie:</span> {new Date(row.published_at).toLocaleString()}</div> : null}
                      {row.error_payload && typeof row.error_payload === 'object' && 'message' in row.error_payload ? (
                        <div className="text-rose-700">
                          <span className="font-semibold">błąd:</span> {String((row.error_payload as { message?: unknown }).message ?? '')}
                        </div>
                      ) : null}
                      {(row.status === 'published' || row.status === 'manual_confirmed') && row.content_id ? (
                        <div className="mt-2">
                          <Button
                            variant="outline"
                            className="h-7 rounded-full px-3 text-[11px]"
                            onClick={() => prefillMetricsFromPublishRecord(row)}
                          >
                            Uzupełnij import metryk
                          </Button>
                        </div>
                      ) : null}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
          <div className="rounded-2xl border border-stone-200 bg-white/80 p-4">
            <div className="rounded-xl border border-stone-200 bg-stone-50/60 p-3 text-xs">
              <div className="font-semibold text-stone-900">Ręczny import metryk (MVP)</div>
              <div className="mt-1 text-stone-500">
                Ręczny zapis do `metrics_daily` dla opublikowanych treści (integracje manual-first).
              </div>
              <div className="mt-3 grid gap-2 sm:grid-cols-2">
                <label className="text-xs font-semibold uppercase tracking-[0.15em] text-stone-500">
                  Platform
                  <select
                    className="mt-1 w-full rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700"
                    value={metricsImportPlatform}
                    onChange={(event) => setMetricsImportPlatform(event.target.value as 'youtube' | 'tiktok')}
                  >
                    <option value="youtube">youtube</option>
                    <option value="tiktok">tiktok</option>
                  </select>
                </label>
                <label className="text-xs font-semibold uppercase tracking-[0.15em] text-stone-500">
                  Data
                  <input
                    type="date"
                    className="mt-1 w-full rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700"
                    value={metricsImportDate}
                    onChange={(event) => setMetricsImportDate(event.target.value)}
                  />
                </label>
                <label className="sm:col-span-2 text-xs font-semibold uppercase tracking-[0.15em] text-stone-500">
                  ID treści
                  <input
                    className="mt-1 w-full rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700"
                    value={metricsImportContentId}
                    onChange={(event) => setMetricsImportContentId(event.target.value)}
                    placeholder="ID treści youtube/tiktok"
                  />
                </label>
                <label className="sm:col-span-2 text-xs font-semibold uppercase tracking-[0.15em] text-stone-500">
                  Profil audio (opcjonalnie)
                  <select
                    className="mt-1 w-full rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700"
                    value={metricsImportAudioProfile}
                    onChange={(event) =>
                      setMetricsImportAudioProfile(
                        event.target.value as '' | 'balanced' | 'speech' | 'music' | 'sfx_heavy',
                      )
                    }
                  >
                    <option value="">brak</option>
                    <option value="balanced">balanced</option>
                    <option value="speech">speech</option>
                    <option value="music">music</option>
                    <option value="sfx_heavy">sfx_heavy</option>
                  </select>
                </label>
                <label className="text-xs font-semibold uppercase tracking-[0.15em] text-stone-500">
                  Wyświetlenia
                  <input className="mt-1 w-full rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700" value={metricsImportViews} onChange={(e) => setMetricsImportViews(e.target.value)} />
                </label>
                <label className="text-xs font-semibold uppercase tracking-[0.15em] text-stone-500">
                  Polubienia
                  <input className="mt-1 w-full rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700" value={metricsImportLikes} onChange={(e) => setMetricsImportLikes(e.target.value)} />
                </label>
                <label className="text-xs font-semibold uppercase tracking-[0.15em] text-stone-500">
                  Komentarze
                  <input className="mt-1 w-full rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700" value={metricsImportComments} onChange={(e) => setMetricsImportComments(e.target.value)} />
                </label>
                <label className="text-xs font-semibold uppercase tracking-[0.15em] text-stone-500">
                  Udostępnienia
                  <input className="mt-1 w-full rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700" value={metricsImportShares} onChange={(e) => setMetricsImportShares(e.target.value)} />
                </label>
                <label className="text-xs font-semibold uppercase tracking-[0.15em] text-stone-500">
                  Czas oglądania (s)
                  <input className="mt-1 w-full rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700" value={metricsImportWatchTime} onChange={(e) => setMetricsImportWatchTime(e.target.value)} />
                </label>
                <label className="text-xs font-semibold uppercase tracking-[0.15em] text-stone-500">
                  Średni % obejrzenia
                  <input className="mt-1 w-full rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700" value={metricsImportAvgPercent} onChange={(e) => setMetricsImportAvgPercent(e.target.value)} placeholder="opcjonalnie" />
                </label>
                <label className="text-xs font-semibold uppercase tracking-[0.15em] text-stone-500">
                  Średni czas obejrzenia (s)
                  <input className="mt-1 w-full rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700" value={metricsImportAvgDuration} onChange={(e) => setMetricsImportAvgDuration(e.target.value)} placeholder="opcjonalnie" />
                </label>
              </div>
              <div className="mt-3 flex flex-wrap items-center gap-2">
                <Button className="rounded-full" onClick={handleManualMetricsImport} disabled={metricsImportLoading}>
                  {metricsImportLoading ? 'Zapisywanie metryk…' : 'Zapisz metryki'}
                </Button>
                {metricsImportMessage ? <span className="text-xs text-emerald-700">{metricsImportMessage}</span> : null}
                {metricsImportError ? <span className="text-xs text-rose-700">{metricsImportError}</span> : null}
              </div>
            </div>
            <div className="flex items-center justify-between gap-2">
              <div>
                <div className="text-sm font-semibold text-stone-900">Najnowszy snapshot metryk</div>
                <div className="text-xs text-stone-500">Najnowszy rekord `metrics_daily` per platforma/treść</div>
              </div>
              <div className="text-xs text-stone-500">{planLatestMetricsByContent.length} pozycji</div>
            </div>
            {planMetricsLoading ? (
              <div className="mt-3 text-sm text-stone-600">Ładowanie metryk…</div>
            ) : planMetricsError ? (
              <div className="mt-3 rounded-xl border border-rose-200 bg-rose-50/70 p-3 text-xs text-rose-700">{planMetricsError}</div>
            ) : planLatestMetricsByContent.length === 0 ? (
              <div className="mt-3 rounded-xl border border-dashed border-stone-200 bg-stone-50/60 p-4 text-sm text-stone-600">
                Brak danych `metrics_daily`. To oczekiwane, dopóki pobieranie metryk pozostaje manualne.
              </div>
            ) : (
              <div className="mt-3 space-y-2">
                {planLatestMetricsByContent.slice(0, 12).map((row) => (
                  <div key={row.id} className="rounded-xl border border-stone-200 bg-stone-50/60 p-3 text-xs">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-semibold text-stone-800">{row.platform_type ?? 'nieznane'}</span>
                      <span className="text-stone-500">{row.content_id ?? 'nieznana-treść'}</span>
                      <span className="text-stone-500">{row.date ?? '—'}</span>
                    </div>
                    <div className="mt-1 grid grid-cols-2 gap-1 text-stone-600">
                      <div>wyświetlenia: <span className="font-semibold text-stone-800">{row.views ?? 0}</span></div>
                      <div>polubienia: <span className="font-semibold text-stone-800">{row.likes ?? 0}</span></div>
                      <div>komentarze: <span className="font-semibold text-stone-800">{row.comments ?? 0}</span></div>
                      <div>udostępnienia: <span className="font-semibold text-stone-800">{row.shares ?? 0}</span></div>
                      <div>średni %: <span className="font-semibold text-stone-800">{row.avg_view_percentage ?? '—'}</span></div>
                      <div>średni czas: <span className="font-semibold text-stone-800">{row.avg_view_duration_seconds ?? '—'}</span>s</div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
          <div className="flex items-center justify-between rounded-2xl border border-stone-200/70 bg-stone-50/60 p-3 text-xs text-stone-600">
            <div>
              Tryb operatora Godot jest domyślny. Panele legacy DSL są opcjonalne i tylko diagniestyczne.
            </div>
            <Button
              variant={showLegacyDslPanels ? 'outline' : 'ghost'}
              className="rounded-full"
              onClick={() => setShowLegacyDslPanels((prev) => !prev)}
            >
              {showLegacyDslPanels ? 'Ukryj legacy DSL' : 'Pokaż legacy DSL'}
            </Button>
          </div>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          <Button className="rounded-full" onClick={() => setActiveView('flow')}>Przejdź do przepływu</Button>
          <Button variant="outline" className="rounded-full" onClick={() => setActiveView(singleVideoMode ? 'plan' : 'repositories')}>
            {singleVideoMode ? 'Przejdź do analityki' : 'Otwórz repozytoria'}
          </Button>
        </div>
      </section>
      ) : null}

      {activeView === 'flow' ? (
      <>
      <section className="rounded-[28px] border border-stone-200/80 bg-white/90 p-6 shadow-2xl shadow-stone-900/10">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h2 className="text-2xl font-semibold text-stone-900">Przepływ</h2>
            <p className="text-sm text-stone-600">
              {singleVideoMode
                ? 'Sekwencja single-video: Pomysł -> Bramka -> Kompilacja -> Render -> QC -> Publikacja.'
                : 'Sekwencja operatora: Generator pomysłów -> Bramka pomysłu -> Kompilacja -> Render -> QC -> Publikacja.'}
            </p>
            {manualFlowEnabled ? (
              <div className="mt-2 inline-flex items-center gap-2 rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-xs text-amber-700">
                Tryb manualny włączony (bez automatycznych akcji).
              </div>
            ) : null}
          </div>
          <div className="flex flex-wrap gap-2">
            {['Generator pomysłów', 'Bramka pomysłu', 'Kompilacja', 'Render', 'QC', 'Publikacja'].map((step) => (
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
            Odśwież przepływ
          </Button>
          {singleVideoMode ? (
            <Button
              variant={showAdvancedFlowPanels ? 'outline' : 'ghost'}
              className="rounded-full"
              onClick={() => setShowAdvancedFlowPanels((prev) => !prev)}
            >
              {showAdvancedFlowPanels ? 'Ukryj zaawansowane panele' : 'Pokaż zaawansowane panele'}
            </Button>
          ) : null}
          <Button variant="ghost" className="rounded-full" onClick={() => setActiveView('home')}>
            Powrót do panelu głównego
          </Button>
        </div>
        {singleVideoMode && !showAdvancedFlowPanels ? (
          <p className="mt-2 text-xs text-stone-500">
            Tryb uproszczony: panele `Logi operacyjne` i `Operacje` są ukryte.
          </p>
        ) : null}
        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-6">
          <Card className="border border-stone-200 bg-stone-50/60 shadow-none">
            <CardContent className="pt-4 space-y-2">
              <div className="text-xs uppercase tracking-[0.18em] text-stone-500">Generator pomysłów</div>
              <div className="text-2xl font-semibold text-stone-900">{candidateCapabilitySummary.unverified ?? 0}</div>
              <div className="text-xs text-stone-500">kandydaci unverified</div>
              <Button variant="outline" className="w-full rounded-full" onClick={() => scrollToSection('idea-generator-panel')}>
                Zobacz
              </Button>
            </CardContent>
          </Card>
          <Card className="border border-stone-200 bg-stone-50/60 shadow-none">
            <CardContent className="pt-4 space-y-2">
              <div className="text-xs uppercase tracking-[0.18em] text-stone-500">Bramka pomysłu</div>
              <div className="text-2xl font-semibold text-stone-900">{readyCandidates}</div>
              <div className="text-xs text-stone-500">gotowe do wyboru</div>
              <Button className="w-full rounded-full" onClick={() => scrollToSection('idea-gate-panel')}>
                Otwórz
              </Button>
            </CardContent>
          </Card>
          <Card className="border border-stone-200 bg-stone-50/60 shadow-none">
            <CardContent className="pt-4 space-y-2">
              <div className="text-xs uppercase tracking-[0.18em] text-stone-500">Kompilacja</div>
              <div className="text-2xl font-semibold text-stone-900">{compiledIdeas}</div>
              <div className="text-xs text-stone-500">skompilowane pomysły</div>
              <Button
                variant="outline"
                className="w-full rounded-full"
                onClick={() => (showLegacyDslPanels ? scrollToSection('dsl-capability-panel') : scrollToSection('flow-manual-panel'))}
              >
                {showLegacyDslPanels ? 'Braki DSL' : 'Godot ręczny przebieg'}
              </Button>
            </CardContent>
          </Card>
          <Card className="border border-stone-200 bg-stone-50/60 shadow-none">
            <CardContent className="pt-4 space-y-2">
              <div className="text-xs uppercase tracking-[0.18em] text-stone-500">Render</div>
              <div className="text-2xl font-semibold text-stone-900">{renderQueue}</div>
              <div className="text-xs text-stone-500">w toku / w kolejce</div>
              <Button variant="outline" className="w-full rounded-full" onClick={() => scrollToSection('flow-animations-panel')}>
                Animacje
              </Button>
            </CardContent>
          </Card>
          <Card className="border border-stone-200 bg-stone-50/60 shadow-none">
            <CardContent className="pt-4 space-y-2">
              <div className="text-xs uppercase tracking-[0.18em] text-stone-500">QC</div>
              <div className="text-2xl font-semibold text-stone-900">{qcQueue}</div>
              <div className="text-xs text-stone-500">oczekuje na decyzję QC</div>
              <Button variant="outline" className="w-full rounded-full" onClick={() => scrollToSection('flow-animations-panel')}>
                Przegląd
              </Button>
            </CardContent>
          </Card>
          <Card className="border border-stone-200 bg-stone-50/60 shadow-none">
            <CardContent className="pt-4 space-y-2">
              <div className="text-xs uppercase tracking-[0.18em] text-stone-500">Publikacja</div>
              <div className="text-2xl font-semibold text-stone-900">{publishReady}</div>
              <div className="text-xs text-stone-500">gotowe do publikacji</div>
              <Button variant="outline" className="w-full rounded-full" onClick={() => setActiveView('plan')}>
                Plan
              </Button>
            </CardContent>
          </Card>
        </div>
      </section>

{manualFlowEnabled ? (
      <section id="flow-manual-panel" className="rounded-[28px] border border-amber-200/80 bg-amber-50/40 p-6 shadow-2xl shadow-amber-900/10">
        <div className="flex flex-col gap-2 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h3 className="text-xl font-semibold text-stone-900">Przepływ ręczny</h3>
            <p className="text-sm text-stone-600">Kroki uruchamiane ręcznie przez operatora.</p>
          </div>
        </div>
        <div className="mt-4 grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
          <div className="rounded-2xl border border-amber-200/70 bg-white/80 p-4">
            <label className="flex flex-col gap-1 text-xs font-semibold uppercase tracking-[0.15em] text-stone-500">
              ID pomysłu
              <input
                className="rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700 focus:border-stone-400 focus:outline-none"
                placeholder="UUID"
                value={manualIdeaId}
                onChange={(event) => setManualIdeaId(event.target.value)}
              />
            </label>
            <div className="mt-3 flex flex-wrap gap-2">
              <Button className="rounded-full" onClick={handleManualCompile} disabled={manualCompileLoading}>
                {manualCompileLoading ? 'Kompilacja…' : 'Kompiluj DSL'}
              </Button>
              <Button variant="outline" className="rounded-full" onClick={handleManualPipeline} disabled={manualPipelineLoading}>
                {manualPipelineLoading ? 'Uruchamianie…' : 'Uruchom pipeline (kompilacja+render)'}
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
                  <div className="text-sm font-semibold text-stone-900">Godot ręczny przebieg (Etap B)</div>
                  <div className="text-xs text-stone-600">
                    Kolejność: kompilacja, walidacja, estymacja, podgląd, sprawdzenie intencji, render, intro, audio.
                  </div>
                </div>
              </div>
              <div className="mt-3 flex flex-wrap items-center justify-between gap-2 rounded-xl border border-sky-200/70 bg-white/70 px-3 py-2">
                <div className="text-xs text-stone-600">Parametry techniczne (opcjonalne)</div>
                <Button
                  variant="ghost"
                  className="h-7 rounded-full px-3 text-[11px]"
                  onClick={() => setShowManualTechnicalParams((prev) => !prev)}
                >
                  {showManualTechnicalParams ? 'Ukryj parametry' : 'Pokaż parametry'}
                </Button>
              </div>
              <div className="mt-3 grid gap-3 lg:grid-cols-2">
                <label className="flex flex-col gap-1 text-xs font-semibold uppercase tracking-[0.15em] text-stone-500">
                  Ścieżka GDScript
                  <input
                    className="rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700"
                    placeholder="out/manual-godot/idea-.../script.gd"
                    value={godotScriptPath}
                    onChange={(event) => setGodotScriptPath(event.target.value)}
                  />
                </label>
              </div>
              {showManualTechnicalParams ? (
                <>
                  <div className="mt-3 grid gap-3 sm:grid-cols-4">
                    <label className="flex flex-col gap-1 text-xs font-semibold uppercase tracking-[0.15em] text-stone-500">
                      Sekundy
                      <input
                        className="rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700"
                        value={godotSekundy}
                        onChange={(event) => setGodotSekundy(event.target.value)}
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
                      Maks. węzłów
                      <input
                        className="rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700"
                        value={godotMaxNodes}
                        onChange={(event) => setGodotMaxNodes(event.target.value)}
                      />
                    </label>
                    <label className="flex flex-col gap-1 text-xs font-semibold uppercase tracking-[0.15em] text-stone-500">
                      Skala podglądu
                      <input
                        className="rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700"
                        value={godotPreviewScale}
                        onChange={(event) => setGodotPreviewScale(event.target.value)}
                      />
                    </label>
                  </div>
                  <div className="mt-3 grid gap-3 sm:grid-cols-5">
                    <label className="flex flex-col gap-1 text-xs font-semibold uppercase tracking-[0.15em] text-stone-500">
                      Docelowy czas (s)
                      <input
                        className="rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700"
                        value={godotTargetDuration}
                        onChange={(event) => setGodotTargetDuration(event.target.value)}
                      />
                    </label>
                    <label className="flex flex-col gap-1 text-xs font-semibold uppercase tracking-[0.15em] text-stone-500">
                      Scout (s)
                      <input
                        className="rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700"
                        value={godotScoutSekundy}
                        onChange={(event) => setGodotScoutSekundy(event.target.value)}
                      />
                    </label>
                    <label className="flex flex-col gap-1 text-xs font-semibold uppercase tracking-[0.15em] text-stone-500">
                      Próg
                      <input
                        className="rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700"
                        value={godotEstimatePróg}
                        onChange={(event) => setGodotEstimatePróg(event.target.value)}
                      />
                    </label>
                    <label className="flex flex-col gap-1 text-xs font-semibold uppercase tracking-[0.15em] text-stone-500">
                      Hold (s)
                      <input
                        className="rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700"
                        value={godotEstimateHoldSekundy}
                        onChange={(event) => setGodotEstimateHoldSekundy(event.target.value)}
                      />
                    </label>
                    <label className="flex flex-col gap-1 text-xs font-semibold uppercase tracking-[0.15em] text-stone-500">
                      Tail (s)
                      <input
                        className="rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700"
                        value={godotEstimateTailSekundy}
                        onChange={(event) => setGodotEstimateTailSekundy(event.target.value)}
                      />
                    </label>
                  </div>
                  <div className="mt-2 grid gap-3 sm:grid-cols-[1fr_auto]">
                    <label className="flex flex-col gap-1 text-xs font-semibold uppercase tracking-[0.15em] text-stone-500">
                      Preset intent check
                      <select
                        className="rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700"
                        value={intentCheckPreset}
                        onChange={(event) => setIntentCheckPreset(event.target.value as keyof typeof INTENT_CHECK_PRESETS)}
                      >
                        <option value="balanced">zbalansowany</option>
                        <option value="fast_hook">szybki hook</option>
                        <option value="gradual_reveal">wolne ujawnianie</option>
                        <option value="loop_pattern">pętla/pattern</option>
                      </select>
                    </label>
                    <Button variant="outline" className="rounded-full self-end" onClick={applyIntentCheckPreset}>
                      Zastosuj preset
                    </Button>
                  </div>
                </>
              ) : (
                <div className="mt-2 text-xs text-stone-500">
                  Parametry techniczne są ukryte. Używane są obecne wartości i profile.
                </div>
              )}
              <div className="mt-3 rounded-2xl border border-sky-200/80 bg-white/80 p-3">
                <div className="text-xs font-semibold uppercase tracking-[0.15em] text-stone-500">Intro overlay</div>
                <div className="mt-2 grid gap-3 lg:grid-cols-2">
                  <label className="flex flex-col gap-1 text-xs font-semibold uppercase tracking-[0.15em] text-stone-500">
                    Ścieżka wejściowa wideo
                    <input
                      className="rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700"
                      placeholder="out/manual-godot/.../final.mp4"
                      value={introInputPath}
                      onChange={(event) => setIntroInputPath(event.target.value)}
                    />
                  </label>
                  <label className="flex flex-col gap-1 text-xs font-semibold uppercase tracking-[0.15em] text-stone-500">
                    Tekst intro
                    <input
                      className="rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700"
                      placeholder="Zasada animacji: ..."
                      value={introText}
                      onChange={(event) => setIntroText(event.target.value)}
                    />
                  </label>
                </div>
                <div className="mt-2 grid gap-3 sm:grid-cols-3">
                  <label className="flex flex-col gap-1 text-xs font-semibold uppercase tracking-[0.15em] text-stone-500">
                    Czas (s)
                    <input
                      className="rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700"
                      value={introCzas}
                      onChange={(event) => setIntroCzas(event.target.value)}
                    />
                  </label>
                  <label className="flex flex-col gap-1 text-xs font-semibold uppercase tracking-[0.15em] text-stone-500">
                    Rozmiar fontu
                    <input
                      className="rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700"
                      value={introFontSize}
                      onChange={(event) => setIntroFontSize(event.target.value)}
                    />
                  </label>
                  <label className="flex flex-col gap-1 text-xs font-semibold uppercase tracking-[0.15em] text-stone-500">
                    Ścieżka wyjściowa (opcjonalnie)
                    <input
                      className="rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700"
                      value={introOutPath}
                      onChange={(event) => setIntroOutPath(event.target.value)}
                    />
                  </label>
                </div>
                <div className="mt-2 text-[11px] text-stone-500">
                  Domyślny język intro: {(settings?.operator_intro_language ?? 'en').toUpperCase()}
                </div>
              </div>
              <div className="mt-3 rounded-2xl border border-sky-200/80 bg-white/80 p-3">
                <div className="text-xs font-semibold uppercase tracking-[0.15em] text-stone-500">Miks audio</div>
                <div className="mt-2 grid gap-3 lg:grid-cols-2">
                  <label className="flex flex-col gap-1 text-xs font-semibold uppercase tracking-[0.15em] text-stone-500">
                    Ścieżka wejściowa wideo
                    <input
                      className="rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700"
                      placeholder="out/manual-godot/.../final.intro.mp4"
                      value={audioInputPath}
                      onChange={(event) => setAudioInputPath(event.target.value)}
                    />
                  </label>
                  <label className="flex flex-col gap-1 text-xs font-semibold uppercase tracking-[0.15em] text-stone-500">
                    Ścieżka wyjściowa (opcjonalnie)
                    <input
                      className="rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700"
                      value={audioOutPath}
                      onChange={(event) => setAudioOutPath(event.target.value)}
                    />
                  </label>
                </div>
                <div className="mt-2 grid gap-3 lg:grid-cols-2">
                  <label className="flex flex-col gap-1 text-xs font-semibold uppercase tracking-[0.15em] text-stone-500">
                    Ścieżka muzyki (opcjonalnie)
                    <input
                      className="rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700"
                      placeholder="assets/audio/music.mp3"
                      value={audioMusicPath}
                      onChange={(event) => setAudioMusicPath(event.target.value)}
                    />
                  </label>
                  <label className="flex flex-col gap-1 text-xs font-semibold uppercase tracking-[0.15em] text-stone-500">
                    Ścieżka SFX (opcjonalnie)
                    <input
                      className="rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700"
                      placeholder="assets/audio/sfx.wav"
                      value={audioSfxPath}
                      onChange={(event) => setAudioSfxPath(event.target.value)}
                    />
                  </label>
                </div>
                <div className="mt-2 grid gap-3 sm:grid-cols-[1fr_auto]">
                  <label className="flex flex-col gap-1 text-xs font-semibold uppercase tracking-[0.15em] text-stone-500">
                    Profil audio
                    <select
                      className="rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700"
                      value={audioProfile}
                      onChange={(event) => setAudioProfile(event.target.value as keyof typeof AUDIO_PROFILE_PRESETS)}
                    >
                      <option value="balanced">zbalansowany</option>
                      <option value="speech">mowa</option>
                      <option value="music">muzyka</option>
                      <option value="sfx_heavy">mocne SFX</option>
                    </select>
                  </label>
                  <Button
                    variant="outline"
                    className="rounded-full self-end"
                    onClick={() => {
                      const preset = AUDIO_PROFILE_PRESETS[audioProfile]
                      setAudioTargetLufs(preset.targetLufs)
                      setAudioTruePeakDb(preset.truePeakDb)
                      setAudioMusicGainDb(preset.musicGainDb)
                      setAudioSfxGainDb(preset.sfxGainDb)
                      setAudioNormalizeLoudness(preset.normalizeLoudness)
                    }}
                  >
                    Zastosuj profil
                  </Button>
                </div>
                <div className="mt-2 grid gap-3 sm:grid-cols-3">
                  <label className="flex flex-col gap-1 text-xs font-semibold uppercase tracking-[0.15em] text-stone-500">
                    Wzmocnienie muzyki (dB)
                    <input
                      className="rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700"
                      value={audioMusicGainDb}
                      onChange={(event) => setAudioMusicGainDb(event.target.value)}
                    />
                  </label>
                  <label className="flex flex-col gap-1 text-xs font-semibold uppercase tracking-[0.15em] text-stone-500">
                    Wzmocnienie SFX (dB)
                    <input
                      className="rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700"
                      value={audioSfxGainDb}
                      onChange={(event) => setAudioSfxGainDb(event.target.value)}
                    />
                  </label>
                  <label className="flex items-center gap-2 rounded-xl border border-stone-200 bg-white px-3 py-2 text-xs font-semibold uppercase tracking-[0.15em] text-stone-500">
                    <input
                      type="checkbox"
                      checked={audioKeepSource}
                      onChange={(event) => setAudioKeepSource(event.target.checked)}
                    />
                    Zachowaj dźwięk źródłowy
                  </label>
                </div>
                <div className="mt-2 grid gap-3 sm:grid-cols-3">
                  <label className="flex flex-col gap-1 text-xs font-semibold uppercase tracking-[0.15em] text-stone-500">
                    Docelowe LUFS
                    <input
                      className="rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700"
                      value={audioTargetLufs}
                      onChange={(event) => setAudioTargetLufs(event.target.value)}
                    />
                  </label>
                  <label className="flex flex-col gap-1 text-xs font-semibold uppercase tracking-[0.15em] text-stone-500">
                    True peak (dB)
                    <input
                      className="rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700"
                      value={audioTruePeakDb}
                      onChange={(event) => setAudioTruePeakDb(event.target.value)}
                    />
                  </label>
                  <label className="flex items-center gap-2 rounded-xl border border-stone-200 bg-white px-3 py-2 text-xs font-semibold uppercase tracking-[0.15em] text-stone-500">
                    <input
                      type="checkbox"
                      checked={audioNormalizeLoudness}
                      onChange={(event) => setAudioNormalizeLoudness(event.target.checked)}
                    />
                    Normalizacja głośności
                  </label>
                </div>
                <div className="mt-2 text-[11px] text-stone-500">
                  Domyślna ochrona: loudnorm + limiter (target -16 LUFS, true peak -1 dB).
                </div>
              </div>

              <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-8">
                <Button
                  className="rounded-full"
                  onClick={handleGodotCompile}
                  disabled={!!godotStepLoading.compile || !canRunManualStep('compile')}
                >
                  {godotStepLoading.compile ? 'Kompilacja…' : '1. Kompiluj GDScript'}
                </Button>
                <Button
                  variant="outline"
                  className="rounded-full"
                  onClick={() => handleGodotRunStep('validate')}
                  disabled={!!godotStepLoading.validate || !canRunManualStep('validate')}
                >
                  {godotStepLoading.validate ? 'Walidacja…' : '2. Waliduj'}
                </Button>
                <Button
                  variant="outline"
                  className="rounded-full"
                  onClick={() => handleGodotRunStep('estimate')}
                  disabled={!!godotStepLoading.estimate || !canRunManualStep('estimate')}
                >
                  {godotStepLoading.estimate ? 'Estymacja…' : '3. Estymuj czas'}
                </Button>
                <Button
                  variant="outline"
                  className="rounded-full"
                  onClick={() => handleGodotRunStep('preview')}
                  disabled={!!godotStepLoading.preview || !canRunManualStep('preview')}
                >
                  {godotStepLoading.preview ? 'Renderowanie podglądu…' : '4. Podgląd'}
                </Button>
                <Button
                  variant="outline"
                  className="rounded-full"
                  onClick={() => handleGodotRunStep('intent_check')}
                  disabled={!!godotStepLoading.intent_check || !canRunManualStep('intent_check')}
                >
                  {godotStepLoading.intent_check ? 'Sprawdzanie…' : '5. Sprawdzenie intencji'}
                </Button>
                <Button
                  variant="outline"
                  className="rounded-full"
                  onClick={() => handleGodotRunStep('render')}
                  disabled={!!godotStepLoading.render || !canRunManualStep('render')}
                >
                  {godotStepLoading.render ? 'Renderowanie finalne…' : '6. Render finalny'}
                </Button>
                <Button
                  variant="outline"
                  className="rounded-full"
                  onClick={handleIntroOverlay}
                  disabled={!!godotStepLoading.intro_overlay || !canRunManualStep('intro_overlay')}
                >
                  {godotStepLoading.intro_overlay ? 'Nakładanie…' : '7. Intro overlay'}
                </Button>
                <Button
                  variant="outline"
                  className="rounded-full"
                  onClick={handleAudioMix}
                  disabled={!!godotStepLoading.audio_mix || !canRunManualStep('audio_mix')}
                >
                  {godotStepLoading.audio_mix ? 'Miksowanie…' : '8. Miks audio'}
                </Button>
              </div>
              {singleVideoMode ? (
                <div className="mt-2 text-xs text-stone-500">
                  Aktywny krok: <span className="font-semibold text-stone-800">{MANUAL_STEP_LABELS[activeManualStep]}</span>
                </div>
              ) : null}

              <div className="mt-4 grid gap-3 lg:grid-cols-2">
                {visibleManualSteps.map((step) => {
                  const result = godotStepResult[step]
                  const error = godotStepError[step]
                  const status = godotStepStatus[step] ?? 'idle'
                  const stepOrder = MANUAL_STEP_ORDER.indexOf(step) + 1
                  return (
                    <div key={step} className="rounded-xl border border-stone-200 bg-white/80 p-3 text-xs">
                      <div className="flex items-center justify-between">
                        <div className="font-semibold text-stone-900 uppercase tracking-[0.15em]">
                          {stepOrder}/{MANUAL_STEP_ORDER.length} · {MANUAL_STEP_LABELS[step]}
                        </div>
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
                          {MANUAL_STEP_STATUS_LABELS[status]}
                        </Badge>
                      </div>
                      <div className="mt-2 rounded-lg border border-stone-200 bg-stone-50 px-2 py-1 text-[11px] text-stone-600">
                        {manualStepQuickSummary(step, result, error)}
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
                          {(step === 'estimate' || step === 'intent_check') && typeof result.recommended_sim_duration_s === 'number' ? (
                            <div><span className="font-semibold text-stone-800">rekomendowany sim:</span> {result.recommended_sim_duration_s.toFixed(2)}s</div>
                          ) : null}
                          {(step === 'estimate' || step === 'intent_check') && typeof result.target_runtime_s === 'number' ? (
                            <div><span className="font-semibold text-stone-800">docelowy runtime:</span> {result.target_runtime_s.toFixed(0)}s</div>
                          ) : null}
                          {(step === 'estimate' || step === 'intent_check') && typeof result.intent_reached === 'boolean' ? (
                            <div><span className="font-semibold text-stone-800">intencja osiągnięta:</span> {result.intent_reached ? 'tak' : 'nie'}</div>
                          ) : null}
                          {(step === 'estimate' || step === 'intent_check') && typeof result.intent_reached_at_s === 'number' ? (
                            <div><span className="font-semibold text-stone-800">intencja przy:</span> {result.intent_reached_at_s.toFixed(2)}s</div>
                          ) : null}
                          {(step === 'estimate' || step === 'intent_check') && typeof result.recommended_speed_factor === 'number' ? (
                            <div><span className="font-semibold text-stone-800">współczynnik prędkości:</span> {result.recommended_speed_factor.toFixed(3)}</div>
                          ) : null}
                          {(step === 'estimate' || step === 'intent_check') && typeof result.confidence === 'number' ? (
                            <div><span className="font-semibold text-stone-800">pewność:</span> {result.confidence.toFixed(2)}</div>
                          ) : null}
                          {(step === 'estimate' || step === 'intent_check') && typeof result.intent_status === 'string' ? (
                            <div><span className="font-semibold text-stone-800">status intencji:</span> {result.intent_status}</div>
                          ) : null}
                          {(step === 'estimate' || step === 'intent_check') && typeof result.blocking_reason === 'string' && result.blocking_reason ? (
                            <div><span className="font-semibold text-stone-800">blokada:</span> {result.blocking_reason}</div>
                          ) : null}
                          {step === 'intro_overlay' && typeof result.intro_text === 'string' ? (
                            <div><span className="font-semibold text-stone-800">tekst:</span> {result.intro_text}</div>
                          ) : null}
                          {step === 'intro_overlay' && typeof result.language === 'string' ? (
                            <div><span className="font-semibold text-stone-800">język:</span> {result.language}</div>
                          ) : null}
                          {step === 'intro_overlay' && typeof result.duration_s === 'number' ? (
                            <div><span className="font-semibold text-stone-800">czas intro:</span> {result.duration_s.toFixed(2)}s</div>
                          ) : null}
                          {step === 'audio_mix' && typeof result.music_path === 'string' ? (
                            <div><span className="font-semibold text-stone-800">muzyka:</span> {result.music_path}</div>
                          ) : null}
                          {step === 'audio_mix' && typeof result.sfx_path === 'string' ? (
                            <div><span className="font-semibold text-stone-800">SFX:</span> {result.sfx_path}</div>
                          ) : null}
                          {step === 'audio_mix' && typeof result.keep_source_audio === 'boolean' ? (
                            <div><span className="font-semibold text-stone-800">zachowaj źródło:</span> {result.keep_source_audio ? 'tak' : 'nie'}</div>
                          ) : null}
                          {(step === 'estimate' || step === 'intent_check') && result.estimate ? (
                            <div>
                              <span className="font-semibold text-stone-800">efekt:</span>{' '}
                              {result.estimate.reached ? `osiągnięty @ ${Number(result.estimate.effect_time_s ?? -1).toFixed(2)}s` : 'nieosiągnięty w oknie scout'}
                            </div>
                          ) : null}
                          {(step === 'estimate' || step === 'intent_check') && typeof result.recommended_sim_duration_s === 'number' ? (
                            <div className="mt-2">
                              <Button
                                variant="outline"
                                className="h-7 rounded-full px-3 text-[11px]"
                                onClick={() => setGodotSekundy(String(result.recommended_sim_duration_s))}
                              >
                                Użyj rekomendacji
                              </Button>
                            </div>
                          ) : null}
                          {(step === 'preview' || step === 'render' || step === 'intro_overlay' || step === 'audio_mix') &&
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
                  <div className="font-semibold uppercase tracking-[0.15em] text-stone-900">ostatnie ręczne uruchomienia</div>
                  <Button
                    variant="outline"
                    className="h-7 rounded-full px-3 text-[11px]"
                    onClick={fetchGodotManualRuns}
                    disabled={godotHistoryLoading}
                  >
                    {godotHistoryLoading ? 'Ładowanie…' : 'Odśwież'}
                  </Button>
                </div>
                {godotHistoryError ? <div className="mt-2 text-rose-700">{godotHistoryError}</div> : null}
                {godotHistoryRows.length === 0 && !godotHistoryLoading && !godotHistoryError ? (
                  <div className="mt-2 text-stone-500">Brak zapisanych uruchomień.</div>
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
                          {row.ok ? 'sukces' : 'błąd'}
                        </Badge>
                        <span className="font-semibold uppercase tracking-[0.15em] text-stone-700">{row.step ?? 'nieznany'}</span>
                        <span className="text-stone-500">{row.recorded_at ? new Date(row.recorded_at).toLocaleString() : '—'}</span>
                        {typeof row.exit_code === 'number' ? <span className="text-stone-500">exit={row.exit_code}</span> : null}
                      </div>
                      <div className="mt-1 space-y-1 text-stone-600">
                        {row.script_path ? <div><span className="font-semibold text-stone-800">script:</span> {row.script_path}</div> : null}
                        {row.out_path ? <div><span className="font-semibold text-stone-800">out:</span> {row.out_path}</div> : null}
                        {row.log_file ? <div><span className="font-semibold text-stone-800">log:</span> {row.log_file}</div> : null}
                        {(row.step === 'estimate' || row.step === 'intent_check') && typeof row.recommended_sim_duration_s === 'number' ? (
                          <div><span className="font-semibold text-stone-800">rekomendowany sim:</span> {row.recommended_sim_duration_s.toFixed(2)}s</div>
                        ) : null}
                        {(row.step === 'estimate' || row.step === 'intent_check') && typeof row.target_duration_s === 'number' ? (
                          <div><span className="font-semibold text-stone-800">target duration:</span> {row.target_duration_s.toFixed(2)}s</div>
                        ) : null}
                        {row.error ? <div className="text-rose-700"><span className="font-semibold">błąd:</span> {row.error}</div> : null}
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
              <li>Brak automatycznego enqueue po Bramce pomysłu.</li>
              <li>Weryfikacja i kompilacja są uruchamiane ręcznie.</li>
              <li>Etap B: Godot ręczny przebieg uruchamia compile/validate/estimate/preview/intent_check/render/intro_overlay/audio_mix z GUI.</li>
            </ul>
          </div>
        </div>
      </section>
) : null}

{(!singleVideoMode || showAdvancedFlowPanels) ? (
<section id="flow-logs-panel" className="rounded-[28px] border border-stone-200/80 bg-white/90 p-6 shadow-2xl shadow-stone-900/10">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h3 className="text-xl font-semibold text-stone-900">Logi operacyjne</h3>
            <p className="text-sm text-stone-600">Najnowsze zdarzenia audytu i błędy operacyjne.</p>
          </div>
          <div className="flex flex-wrap items-center gap-2 text-xs text-stone-500">
            <span>Zaktualizowano: {auditUpdatedAt ? auditUpdatedAt.toLocaleTimeString() : '—'}</span>
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
              Ładowanie zdarzeń…
            </div>
          ) : auditError ? (
            <div className="rounded-2xl border border-rose-200 bg-rose-50/70 p-6 text-sm text-rose-700">
              <div className="font-semibold">Nie udało się wczytać</div>
              <div>{auditError}</div>
            </div>
          ) : (
            <table className="min-w-[900px] w-full text-left text-sm">
              <thead className="text-xs uppercase tracking-[0.18em] text-stone-500">
                <tr>
                  <th className="px-2 py-3">Czas</th>
                  <th className="px-2 py-3">Typ</th>
                  <th className="px-2 py-3">Źródło</th>
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
) : null}

<section id="idea-generator-panel" className="rounded-[28px] border border-stone-200/80 bg-white/90 p-6 shadow-2xl shadow-stone-900/10">
        <div className="flex flex-col gap-4 border-b border-stone-200/70 pb-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h2 className="text-2xl font-semibold text-stone-900">Generator pomysłów</h2>
            <p className="text-sm text-stone-600">
              Punkt wejścia przepływu: niewi kandydaci dla ścieżki Godot. Panele legacy DSL są opcjonalne i domyślnie ukryte.
            </p>
          </div>
        </div>

        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Card className="border border-stone-200 bg-stone-50/60 shadow-none">
            <CardContent className="pt-4">
              <div className="text-xs uppercase tracking-[0.18em] text-stone-500">Niezweryfikowane</div>
              <div className="mt-2 text-2xl font-semibold text-stone-900">
                {candidateCapabilitySummary.unverified ?? 0}
              </div>
            </CardContent>
          </Card>
          <Card className="border border-stone-200 bg-stone-50/60 shadow-none">
            <CardContent className="pt-4">
              <div className="text-xs uppercase tracking-[0.18em] text-stone-500">Wykonalne</div>
              <div className="mt-2 text-2xl font-semibold text-stone-900">
                {candidateCapabilitySummary.feasible ?? 0}
              </div>
            </CardContent>
          </Card>
          <Card className="border border-stone-200 bg-stone-50/60 shadow-none">
            <CardContent className="pt-4">
              <div className="text-xs uppercase tracking-[0.18em] text-stone-500">Zablokowane przez braki</div>
              <div className="mt-2 text-2xl font-semibold text-stone-900">
                {candidateCapabilitySummary.blocked_by_gaps ?? 0}
              </div>
            </CardContent>
          </Card>
          <Card className="border border-stone-200 bg-stone-50/60 shadow-none">
            <CardContent className="pt-4">
              <div className="text-xs uppercase tracking-[0.18em] text-stone-500">Nowe/Później/Wybrane</div>
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
                {singleVideoMode ? (
                  <div className="rounded-2xl border border-sky-200 bg-sky-50/70 p-3 text-xs text-sky-800">
                    Tryb single-video: generator tworzy dokładnie 1 propozycję.
                  </div>
                ) : (
                  <label className="flex flex-col gap-1 text-xs uppercase tracking-[0.18em] text-stone-500">
                    Limit
                    <input
                      className="rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700"
                      value={generatorLimit}
                      onChange={(event) => setGeneratorLimit(event.target.value)}
                    />
                  </label>
                )}
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
                Resetuj
              </Button>
            </div>
            {generatorMessage ? (
              <div className="mt-3 rounded-2xl border border-emerald-200 bg-emerald-50/70 p-3 text-xs text-emerald-800">
                {generatorMessage}
              </div>
            ) : null}
            {Object.keys(generatorSkipSummary).length > 0 ? (
              <div className="mt-3 rounded-2xl border border-amber-200 bg-amber-50/70 p-3 text-xs text-amber-900">
                <div className="font-semibold">Powody pominięcia</div>
                <div className="mt-2 flex flex-wrap gap-2">
                  {Object.entries(generatorSkipSummary).map(([reason, count]) => (
                    <Badge key={reason} variant="outline" className="border-amber-300 text-amber-800">
                      {reason}: {count}
                    </Badge>
                  ))}
                </div>
                {generatorSkipExamples.length > 0 ? (
                  <div className="mt-2 space-y-1 text-amber-800">
                    {generatorSkipExamples.map((item, idx) => (
                      <div key={`${item.reason ?? 'skip'}-${idx}`}>
                        {(item.title || '—')}: {item.reason || 'nieznany'}
                      </div>
                    ))}
                  </div>
                ) : null}
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
              <li>LLM: generuje propozycje na bazie promptu (w single-video domyślnie 1 pomysł).</li>
              <li>Text: jedna propozycja na bazie własnego opisu.</li>
              <li>File: wczytanie wielu pomysłów z pliku.</li>
            </ul>
          </div>
        </div>

        <div className="mt-4 flex flex-wrap gap-2 text-xs text-stone-500">
          <span>Generator dostępny z UI oraz CLI: `make idea-generate`.</span>
          <span>Weryfikacja legacy DSL (opcjonalnie): `make idea-verify-capability`.</span>
          <span>Similarity: porównanie kandydatów z historią pomysłów (embedding + cosine similarity).</span>
        </div>
      </section>

      
      {showLegacyDslPanels ? (
      <section id="dsl-capability-panel" className="rounded-[28px] border border-stone-200/80 bg-white/90 p-6 shadow-2xl shadow-stone-900/10">
        <div className="flex flex-col gap-4 border-b border-stone-200/70 pb-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h2 className="text-2xl font-semibold text-stone-900">Możliwości DSL</h2>
            <p className="text-sm text-stone-600">
              Weryfikacja kandydatów i zarządzanie listą `dsl_gap`.
            </p>
          </div>
          <div className="text-xs text-stone-500">
            <div>Zaktualizowano: {dslGapsUpdatedAt ? dslGapsUpdatedAt.toLocaleTimeString() : 'brak danych'}</div>
            {verifierInfo ? (
              <div>
                Weryfikator: {verifierInfo.fallbackUsed ? 'tryb awaryjny' : 'LLM'}
                {verifierInfo.provider ? ` / ${verifierInfo.provider}` : ''}
                {verifierInfo.model ? ` / ${verifierInfo.model}` : ''}
                {verifierInfo.verified ? ` (zweryfikowano: ${verifierInfo.verified})` : ''}
              </div>
            ) : null}
          </div>
        </div>

        <div className="mt-4 flex flex-wrap items-end gap-3">
          <label className="flex min-w-[200px] flex-col gap-1 text-xs font-semibold uppercase tracking-[0.15em] text-stone-500">
            Limit weryfikacji
            <input
              className="rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700 focus:border-stone-400 focus:outline-none"
              value={verifyLimit}
              onChange={(event) => setVerifyLimit(event.target.value)}
            />
          </label>
          <div className="flex flex-wrap gap-2">
            <Button className="rounded-full" onClick={handleVerifyCandidates} disabled={verifyLoading}>
              {verifyLoading ? 'Weryfikacja…' : 'Zweryfikuj kandydatów'}
            </Button>
            <Button variant="outline" className="rounded-full" onClick={fetchDslGaps} disabled={dslGapsLoading}>
              Odśwież braki
            </Button>
          </div>
        </div>

        {blockedCandidates.length > 0 ? (
          <div className="mt-4 rounded-2xl border border-amber-200 bg-amber-50/70 p-4 text-xs text-amber-900">
            <div className="font-semibold">
              {blockedCandidates.length} kandydat(ów) zablokowanych przez braki DSL i wykluczonych z losowania.
            </div>
            <div className="mt-2 space-y-1">
              {blockedCandidates.map((candidate) => (
                <div key={candidate.id}>
                  {candidate.title}:{' '}
                  {(candidate.gaps ?? []).map((gap) => gap.feature).filter(Boolean).join(', ') || 'brak'}
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
              Ładowanie braków DSL…
            </div>
          ) : dslGapsError ? (
            <div className="rounded-2xl border border-rose-200 bg-rose-50/70 p-6 text-sm text-rose-700">
              <div className="font-semibold">Nie udało się wczytać</div>
              <div>{dslGapsError}</div>
            </div>
          ) : (
            <table className="min-w-[900px] w-full text-left text-sm">
              <thead className="text-xs uppercase tracking-[0.18em] text-stone-500">
                <tr>
                  <th className="px-2 py-3">Funkcja</th>
                  <th className="px-2 py-3">Status</th>
                  <th className="px-2 py-3">Wprowadzonie</th>
                  <th className="px-2 py-3">Wdrożonie</th>
                  <th className="px-2 py-3">Powód</th>
                  <th className="px-2 py-3">Akcje</th>
                </tr>
              </thead>
              <tbody>
                {dslGaps.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-2 py-6 text-center text-stone-500">
                      Brak braków DSL.
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
                            Akceptuj
                          </Button>
                          <Button
                            variant="outline"
                            className="rounded-full"
                            onClick={() => handleGapStatus(gap.id, 'in_progress')}
                            disabled={gapActionLoading[gap.id]}
                          >
                            W toku
                          </Button>
                          <Button
                            className="rounded-full"
                            onClick={() => handleGapStatus(gap.id, 'implemented')}
                            disabled={gapActionLoading[gap.id]}
                          >
                            Wdrożonie
                          </Button>
                          <Button
                            variant="outline"
                            className="rounded-full"
                            onClick={() =>
                              setDslGapPromptId((prev) => (prev === gap.id ? null : gap.id))
                            }
                          >
                            Prompt AI
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
                Prompt do wdrożenia GAP: {selectedGap.feature ?? 'gap'}
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
                  Kopiuj prompt
                </Button>
                <Button
                  variant="ghost"
                  className="rounded-full"
                  onClick={() => setDslGapPromptId(null)}
                >
                  Zamknij
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
      ) : null}

      {showLegacyDslPanels ? (
      <section className="mt-6 rounded-[28px] border border-stone-200/80 bg-white/90 p-6 shadow-2xl shadow-stone-900/10">
        <div className="flex flex-col gap-4 border-b border-stone-200/70 pb-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h2 className="text-2xl font-semibold text-stone-900">Wersje DSL</h2>
            <p className="text-sm text-stone-600">Historia wersji DSL oraz gapy wprowadzone w wersjach.</p>
          </div>
          <div className="text-xs text-stone-500">
            <div>Zaktualizowano: {dslVersionsUpdatedAt ? dslVersionsUpdatedAt.toLocaleTimeString() : 'brak danych'}</div>
          </div>
        </div>

        <div className="mt-4 flex flex-wrap gap-2">
          <Button variant="outline" className="rounded-full" onClick={fetchDslVersions} disabled={dslVersionsLoading}>
            {dslVersionsLoading ? 'Odświeżanie…' : 'Odśwież wersje'}
          </Button>
          {dslVersionsError ? <span className="text-xs text-rose-600">{dslVersionsError}</span> : null}
        </div>

        <div className="mt-4 overflow-x-auto">
          {dslVersionsLoading ? (
            <div className="rounded-2xl border border-dashed border-stone-200 bg-stone-50/60 p-6 text-sm text-stone-600">
              Ładowanie wersji DSL…
            </div>
          ) : (
            <table className="min-w-[820px] w-full text-left text-sm">
              <thead className="text-xs uppercase tracking-[0.18em] text-stone-500">
                <tr>
                  <th className="px-2 py-3">Wersja</th>
                  <th className="px-2 py-3">Aktywna</th>
                  <th className="px-2 py-3">Wprowadzone braki</th>
                  <th className="px-2 py-3">Wdrożone braki</th>
                  <th className="px-2 py-3">Notatki</th>
                  <th className="px-2 py-3">Utworzenie</th>
                </tr>
              </thead>
              <tbody>
                {dslVersions.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-2 py-6 text-center text-stone-500">
                      Brak wersji DSL.
                    </td>
                  </tr>
                ) : (
                  dslVersions.map((row) => (
                    <tr key={row.id} className="border-t border-stone-200/70">
                      <td className="px-2 py-4 text-stone-800">{row.version}</td>
                      <td className="px-2 py-4 text-stone-600">
                        {row.is_active ? 'tak' : 'nie'}
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
      ) : null}

      <section id="idea-gate-panel" className="rounded-[28px] border border-stone-200/80 bg-white/90 p-6 shadow-2xl shadow-stone-900/10">
        <div className="flex flex-col gap-4 border-b border-stone-200/70 pb-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h2 className="text-2xl font-semibold text-stone-900">Bramka pomysłu</h2>
            <p className="text-sm text-stone-600">
              {singleVideoMode
                ? 'Pobierz jedną propozycję i zdecyduj: akceptuj / później / kosz.'
                : 'Pobierz propozycje z repozytorium i sklasyfikuj każdą.'}
            </p>
          </div>
          <div className="text-xs text-stone-500">
            <div>Zaktualizowano: {ideaUpdatedAt ? ideaUpdatedAt.toLocaleTimeString() : 'brak danych'}</div>
          </div>
        </div>

        <div className="mt-4 flex flex-wrap items-end gap-3">
          {singleVideoMode ? (
            <div className="rounded-xl border border-sky-200 bg-sky-50/70 px-3 py-2 text-xs text-sky-800">
              Tryb single-video: losowanie 1 propozycji.
            </div>
          ) : (
            <label className="flex min-w-[180px] flex-col gap-1 text-xs font-semibold uppercase tracking-[0.15em] text-stone-500">
              Liczba propozycji
              <input
                className="rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700 focus:border-stone-400 focus:outline-none"
                value={ideaSampleCount}
                onChange={(event) => setIdeaSampleCount(event.target.value)}
              />
            </label>
          )}
          <div className="flex flex-wrap gap-2">
            <Button className="rounded-full" onClick={fetchIdeaCandidates} disabled={ideaLoading}>
              {singleVideoMode ? 'Pobierz 1 propozycję' : 'Pobierz propozycje'}
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
              Resetuj
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
            Lista zawiera kandydatów ze statusem `new/later` i capability = `feasible`.
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
                Ładowanie pomysłów…
              </div>
            ) : ideaError ? (
              <div className="rounded-2xl border border-rose-200 bg-rose-50/70 p-6 text-sm text-rose-700">
                <div className="font-semibold">Nie udało się wczytać</div>
                <div>{ideaError}</div>
              </div>
            ) : ideaCandidates.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-stone-200 bg-stone-50/60 p-6 text-sm text-stone-600">
                {singleVideoMode ? 'Nie pobranie jeszcze propozycji. Kliknij „Pobierz 1 propozycję”.' : 'Nie pobranie jeszcze pomysłów. Kliknij „Pobierz propozycje”.'}
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
                          {idea.title ?? 'Bez tytułu'}
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
                      <span>Źródło: {idea.generator_source ?? '—'}</span>
                    </div>
                    <div className="mt-4 flex flex-wrap gap-2">
                      <Button
                        variant={decision === 'picked' ? 'default' : 'outline'}
                        className="rounded-full"
                        onClick={() =>
                          setIdeaDecisions((prev) => ({ ...prev, [idea.id]: 'picked' }))
                        }
                      >
                        Akceptuj
                      </Button>
                      <Button
                        variant={decision === 'later' ? 'default' : 'outline'}
                        className="rounded-full"
                        onClick={() =>
                          setIdeaDecisions((prev) => ({ ...prev, [idea.id]: 'later' }))
                        }
                      >
                        Później
                      </Button>
                      <Button
                        variant={decision === 'rejected' ? 'destructive' : 'outline'}
                        className="rounded-full"
                        onClick={() =>
                          setIdeaDecisions((prev) => ({ ...prev, [idea.id]: 'rejected' }))
                        }
                      >
                        Kosz
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
                <h3 className="text-lg font-semibold text-stone-900">Szczegóły pomysłu</h3>
                <p className="text-xs text-stone-500">Sygnały selekcji i podgląd narracji.</p>
              </div>
              {selectedIdea?.similarity_status && (
                <Badge variant="outline" className={cn('border', similarityTone(selectedIdea.similarity_status))}>
                  {selectedIdea.similarity_status}
                </Badge>
              )}
            </div>

            {!selectedIdea ? (
              <div className="mt-4 rounded-xl border border-dashed border-stone-200 bg-white/70 p-4 text-sm text-stone-500">
                Wybierz kandydata, aby zobaczyć szczegóły.
              </div>
            ) : (
              <div className="mt-4 space-y-4 text-sm text-stone-700">
                <div>
                  <div className="text-xs uppercase tracking-[0.2em] text-stone-400">Tytuł</div>
                  <div className="mt-1 text-base font-semibold text-stone-900">
                    {selectedIdea.title ?? 'Bez tytułu'}
                  </div>
                </div>
                <div>
                  <div className="text-xs uppercase tracking-[0.2em] text-stone-400">Podsumowanie</div>
                  <div className="mt-1 text-sm text-stone-700">
                    {selectedIdea.summary ?? '—'}
                  </div>
                </div>
                <div>
                  <div className="text-xs uppercase tracking-[0.2em] text-stone-400">Czego się spodziewać</div>
                  <div className="mt-1 text-sm text-stone-700">
                    {selectedIdea.what_to_expect ?? '—'}
                  </div>
                </div>
                <div>
                  <div className="text-xs uppercase tracking-[0.2em] text-stone-400">Podgląd</div>
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
                    <span>Decyzja</span>
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
            {singleVideoMode
              ? `Ustaw decyzję dla bieżącej propozycji: ${Object.values(ideaDecisions).filter(Boolean).length}/${ideaCandidates.length}`
              : `Wszystkie propozycje muszą zostać sklasyfikowane. Decyzje: ${Object.values(ideaDecisions).filter(Boolean).length}/${ideaCandidates.length}`}
          </div>
          <Button
            className="rounded-full"
            onClick={submitIdeaDecisions}
            disabled={ideaDecisionLoading || ideaCandidates.length === 0}
          >
            {ideaDecisionLoading ? 'Zapisywanie…' : singleVideoMode ? 'Potwierdź decyzję' : 'Potwierdź wybór i uruchom'}
          </Button>
        </div>
      </section>

      <section id="flow-animations-panel" className="rounded-[28px] border border-stone-200/80 bg-white/90 p-6 shadow-2xl shadow-stone-900/10">
        <div className="flex flex-col gap-4 border-b border-stone-200/70 pb-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h2 className="text-2xl font-semibold text-stone-900">Animacje (Przepływ)</h2>
            <p className="text-sm text-stone-600">
              Mini lista operatora: szybki podgląd najnowszych animacji do podjęcia decyzji.
            </p>
            <p className="mt-1 text-xs text-stone-500">
              Mini podgląd: {Math.min(animationData.length, FLOW_ANIMATION_PREVIEW_LIMIT)} / {animationData.length}. Pełna lista i szczegóły są w Repozytoriach.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button className="rounded-full" onClick={fetchAnimations} disabled={animationLoading}>
              Odśwież listę
            </Button>
            <Button variant="outline" className="rounded-full" onClick={() => setActiveView('repositories')}>
              Otwórz repozytoria
            </Button>
          </div>
        </div>
        <div className="mt-3 rounded-2xl border border-stone-200 bg-stone-50/70 p-3">
          <div className="flex flex-col gap-2 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <div className="text-sm font-semibold text-stone-900">Polityka czyszczenia `later`</div>
              <div className="text-xs text-stone-500">Usuwa kandydatów `later` starszych niż wybrany maksymalny wiek.</div>
            </div>
            <div className="flex flex-wrap items-end gap-2">
              <label className="flex min-w-[120px] flex-col gap-1 text-xs font-semibold uppercase tracking-[0.15em] text-stone-500">
                Maksymalny wiek (dni)
                <input
                  className="rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700 focus:border-stone-400 focus:outline-none"
                  value={laterCleanupMaxAgeDays}
                  onChange={(event) => setLaterCleanupMaxAgeDays(event.target.value)}
                />
              </label>
              <label className="flex items-center gap-2 rounded-xl border border-stone-200 bg-white px-3 py-2 text-xs font-semibold uppercase tracking-[0.15em] text-stone-500">
                <input
                  type="checkbox"
                  checked={laterCleanupDryRun}
                  onChange={(event) => setLaterCleanupDryRun(event.target.checked)}
                />
                Próba na sucho
              </label>
              <Button className="rounded-full" onClick={handleCleanupLaterCandidates} disabled={laterCleanupLoading}>
                {laterCleanupLoading ? 'Czyszczenie…' : 'Wyczyść `later`'}
              </Button>
            </div>
          </div>
          {laterCleanupMessage ? <div className="mt-2 text-xs text-emerald-700">{laterCleanupMessage}</div> : null}
          {laterCleanupError ? <div className="mt-2 text-xs text-rose-700">{laterCleanupError}</div> : null}
        </div>

        <div className="mt-4 overflow-x-auto">
          {animationLoading ? (
            <div className="rounded-2xl border border-dashed border-stone-200 bg-stone-50/60 p-6 text-sm text-stone-600">
              Ładowanie animacji…
            </div>
          ) : animationError ? (
            <div className="rounded-2xl border border-rose-200 bg-rose-50/70 p-6 text-sm text-rose-700">
              <div className="font-semibold">Nie udało się wczytać</div>
              <div>{animationError}</div>
            </div>
          ) : (
            <table className="min-w-[720px] w-full text-left text-sm">
              <thead className="text-xs uppercase tracking-[0.18em] text-stone-500">
                <tr>
                  <th className="px-2 py-3">Status</th>
                  <th className="px-2 py-3">Etap</th>
                  <th className="px-2 py-3">Animacja</th>
                  <th className="px-2 py-3">Render</th>
                  <th className="px-2 py-3">Aktualizacja</th>
                </tr>
              </thead>
              <tbody>
                {animationData.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-2 py-6 text-center text-stone-500">
                      Brak animacji.
                    </td>
                  </tr>
                ) : (
                  animationData.slice(0, FLOW_ANIMATION_PREVIEW_LIMIT).map((row) => (
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
                      <td className="px-2 py-4 font-monie text-xs text-stone-600">{row.id}</td>
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

      
      {(!singleVideoMode || showAdvancedFlowPanels) ? (
      <section id="operations-panel" className="rounded-[28px] border border-stone-200/80 bg-white/90 p-6 shadow-2xl shadow-stone-900/10">
        <div className="flex flex-col gap-4 border-b border-stone-200/70 pb-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h2 className="text-2xl font-semibold text-stone-900">Operacje</h2>
            <p className="text-sm text-stone-600">
              Uruchamiaj akcje pipeline (enqueue, rerun, cleanup) bezpośrednio z panelu.
            </p>
          </div>
          <Badge variant="outline" className="border border-amber-200 text-amber-800">
            tylko operator
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
            <div className="text-sm font-semibold text-stone-900">Uruchom pipeline</div>
            <div className="text-xs text-stone-500">Rozpocznij nowy przebieg pipeline.</div>
            <div className="mt-3 space-y-2 text-sm">
              <label className="flex flex-col gap-1 text-xs uppercase tracking-[0.18em] text-stone-500">
                Szablon DSL
                <input
                  className="rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700"
                  value={enqueueDsl}
                  onChange={(event) => setEnqueueDsl(event.target.value)}
                />
              </label>
              <label className="flex flex-col gap-1 text-xs uppercase tracking-[0.18em] text-stone-500">
                Katalog wyjściowy
                <input
                  className="rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700"
                  value={enqueueOutRoot}
                  onChange={(event) => setEnqueueOutRoot(event.target.value)}
                />
              </label>
              <Button className="w-full rounded-full" onClick={handleEnqueue} disabled={opsEnqueueLoading}>
                {opsEnqueueLoading ? 'Dodawanie do kolejki…' : 'Dodaj do kolejki'}
              </Button>
            </div>
          </div>

          <div className="rounded-2xl border border-stone-200 bg-stone-50/70 p-4">
            <div className="text-sm font-semibold text-stone-900">Uruchom render ponownie</div>
            <div className="text-xs text-stone-500">Ponownie zakolejkuj render dla wybranej animacji.</div>
            <div className="mt-3 space-y-2 text-sm">
              <label className="flex flex-col gap-1 text-xs uppercase tracking-[0.18em] text-stone-500">
                ID animacji
                <input
                  className="rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700"
                  placeholder="UUID"
                  value={rerunAnimationId}
                  onChange={(event) => setRerunAnimationId(event.target.value)}
                />
              </label>
              <label className="flex flex-col gap-1 text-xs uppercase tracking-[0.18em] text-stone-500">
                Katalog wyjściowy
                <input
                  className="rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700"
                  value={rerunOutRoot}
                  onChange={(event) => setRerunOutRoot(event.target.value)}
                />
              </label>
              <Button className="w-full rounded-full" onClick={handleRerun} disabled={opsRerunLoading}>
                {opsRerunLoading ? 'Ponowne kolejkowanie…' : 'Uruchom render ponownie'}
              </Button>
            </div>
          </div>

          <div className="rounded-2xl border border-stone-200 bg-stone-50/70 p-4">
            <div className="text-sm font-semibold text-stone-900">Czyszczenie zadań</div>
            <div className="text-xs text-stone-500">Oznacz przestarzałe zadania `running` jako `failed`.</div>
            <div className="mt-3 space-y-2 text-sm">
              <label className="flex flex-col gap-1 text-xs uppercase tracking-[0.18em] text-stone-500">
                Starsze niż (min)
                <input
                  className="rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700"
                  value={cleanupOlderMin}
                  onChange={(event) => setCleanupOlderMin(event.target.value)}
                />
              </label>
              <Button className="w-full rounded-full" onClick={handleCleanup} disabled={opsCleanupLoading}>
                {opsCleanupLoading ? 'Czyszczenie…' : 'Czyszczenie zadań'}
              </Button>
            </div>
          </div>
        </div>
      </section>
      ) : null}

</>
      ) : null}

      

{activeView === 'repositories' ? (
      <>
<section className="rounded-[28px] border border-stone-200/80 bg-white/90 p-6 shadow-2xl shadow-stone-900/10">
        <div className="flex flex-col gap-4 border-b border-stone-200/70 pb-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h2 className="text-2xl font-semibold text-stone-900">Kandydaci na pomysł</h2>
            <p className="text-sm text-stone-600">
              Repozytorium kandydatów ze statusami decyzji i możliwości.
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
              <option value="">Wszystkie</option>
              {CANDIDATE_STATUS_ORDER.map((status) => (
                <option key={status} value={status}>
                  {status}
                </option>
              ))}
            </select>
          </label>
          <label className="flex min-w-[180px] flex-col gap-1 text-xs font-semibold uppercase tracking-[0.15em] text-stone-500">
            Możliwość
            <select
              className="rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700 focus:border-stone-400 focus:outline-none"
              value={candidateFilterCapability}
              onChange={(event) => setCandidateFilterCapability(event.target.value)}
            >
              <option value="">Wszystkie</option>
              {CANDIDATE_CAPABILITY_ORDER.map((status) => (
                <option key={status} value={status}>
                  {status}
                </option>
              ))}
            </select>
          </label>
          <label className="flex min-w-[180px] flex-col gap-1 text-xs font-semibold uppercase tracking-[0.15em] text-stone-500">
            Podobieństwo
            <select
              className="rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700 focus:border-stone-400 focus:outline-none"
              value={candidateFilterSimilarity}
              onChange={(event) => setCandidateFilterSimilarity(event.target.value)}
            >
              <option value="">Wszystkie</option>
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
              Zastosuj filtry
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
              Resetuj
            </Button>
          </div>
        </div>

        <div className="mt-4 overflow-x-auto">
          {candidateListLoading ? (
            <div className="rounded-2xl border border-dashed border-stone-200 bg-stone-50/60 p-6 text-sm text-stone-600">
              Ładowanie kandydatów…
            </div>
          ) : candidateListError ? (
            <div className="rounded-2xl border border-rose-200 bg-rose-50/70 p-6 text-sm text-rose-700">
              <div className="font-semibold">Nie udało się wczytać</div>
              <div>{candidateListError}</div>
            </div>
          ) : (
            <table className="min-w-[880px] w-full text-left text-sm">
              <thead className="text-xs uppercase tracking-[0.18em] text-stone-500">
                <tr>
                  <th className="px-2 py-3">Status</th>
                  <th className="px-2 py-3">Możliwość</th>
                  <th className="px-2 py-3">Podobieństwo</th>
                  <th className="px-2 py-3">Tytuł / Szczegóły</th>
                  <th className="px-2 py-3">Utworzenie</th>
                  <th className="px-2 py-3">Akcje</th>
                </tr>
              </thead>
              <tbody>
                {candidateList.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-2 py-6 text-center text-stone-500">
                      Brak kandydatów dla filtrów. Zmień filtry lub wygeneruj nowe pomysły.
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
                          {row.summary ? <div className="mt-2">Podsumowanie: {row.summary}</div> : null}
                          {row.what_to_expect ? <div className="mt-1">Czego się spodziewać: {row.what_to_expect}</div> : null}
                          {row.preview ? <div className="mt-1">Podgląd: {row.preview}</div> : null}
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
                            Resetuj weryfikację
                          </Button>
                          <Button
                            variant="outline"
                            className="rounded-full"
                            onClick={() => handleOverrideCandidateCapability(row.id, 'feasible', 'manual')}
                            disabled={candidateActionLoading[row.id]}
                          >
                            Oznacz jako feasible
                          </Button>
                          <Button
                            variant="outline"
                            className="rounded-full"
                            onClick={() => handleOverrideCandidateCapability(row.id, 'blocked_by_gaps', 'manual')}
                            disabled={candidateActionLoading[row.id]}
                          >
                            Oznacz jako blocked
                          </Button>
                          <Button
                            variant="outline"
                            className="rounded-full"
                            onClick={() => handleUndoCandidateDecision(row.id)}
                            disabled={candidateActionLoading[row.id] || row.status === 'new'}
                          >
                            Cofnij decyzję
                          </Button>
                          <Button
                            variant="destructive"
                            className="rounded-full"
                            onClick={() => handleDeleteCandidate(row.id)}
                            disabled={candidateActionLoading[row.id] || row.status === 'picked'}
                          >
                            Kosz (trwałe usunięcie)
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
            <h2 className="text-2xl font-semibold text-stone-900">Animacje</h2>
            <p className="text-sm text-stone-600">
              Pełna lista animacji: filtry, podgląd renderu, QC i historia publikacji.
            </p>
            <p className="mt-1 text-xs text-stone-500">
              Widok diagnostyczny. `Przepływ` pokazuje tylko mini listę.
            </p>
          </div>
          <div className="text-xs text-stone-500">
            <div>Zaktualizowano: {animationUpdatedAt ? animationUpdatedAt.toLocaleTimeString() : 'brak danych'}</div>
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
              <option value="">Wszystkie</option>
              {ANIMATION_STATUSES.map((status) => (
                <option key={status} value={status}>
                  {status}
                </option>
              ))}
            </select>
          </label>
          <label className="flex min-w-[180px] flex-col gap-1 text-xs font-semibold uppercase tracking-[0.15em] text-stone-500">
            Etap
            <select
              className="rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700 focus:border-stone-400 focus:outline-none"
              value={pipelineStage}
              onChange={(event) => setPipelineStage(event.target.value)}
            >
              <option value="">Wszystkie</option>
              {PIPELINE_STAGES.map((stage) => (
                <option key={stage} value={stage}>
                  {stage}
                </option>
              ))}
            </select>
          </label>
          <label className="flex min-w-[240px] flex-1 flex-col gap-1 text-xs font-semibold uppercase tracking-[0.15em] text-stone-500">
            ID pomysłu
            <input
              className="rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700 focus:border-stone-400 focus:outline-none"
              placeholder="UUID"
              value={ideaId}
              onChange={(event) => setIdeaId(event.target.value)}
            />
          </label>
          <div className="flex flex-wrap gap-2">
            <Button className="rounded-full" onClick={fetchAnimations} disabled={animationLoading}>
              Odśwież
            </Button>
            <Button variant="outline" className="rounded-full" onClick={fetchAnimations} disabled={animationLoading}>
              Zastosuj filtry
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
              Resetuj
            </Button>
          </div>
        </div>

        <div className="mt-4 grid gap-6 lg:grid-cols-[1.3fr_0.9fr]">
          <div className="overflow-x-auto">
            {animationLoading ? (
              <div className="rounded-2xl border border-dashed border-stone-200 bg-stone-50/60 p-6 text-sm text-stone-600">
                Ładowanie animacji…
              </div>
            ) : animationError ? (
              <div className="rounded-2xl border border-rose-200 bg-rose-50/70 p-6 text-sm text-rose-700">
                <div className="font-semibold">Nie udało się wczytać</div>
                <div>{animationError}</div>
              </div>
            ) : (
              <table className="min-w-[780px] w-full text-left text-sm">
                <thead className="text-xs uppercase tracking-[0.18em] text-stone-500">
                  <tr>
                    <th className="px-2 py-3">Status</th>
                    <th className="px-2 py-3">Etap</th>
                    <th className="px-2 py-3">Animacja</th>
                    <th className="px-2 py-3">Render</th>
                    <th className="px-2 py-3">QC</th>
                    <th className="px-2 py-3">Aktualizacja</th>
                  </tr>
                </thead>
                <tbody>
                  {animationData.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="px-2 py-6 text-center text-stone-500">
                        Brak animacji dla filtrów. Zmień filtry albo uruchom pipeline.
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
                        <td className="px-2 py-4 font-monie text-xs text-stone-600">{row.id}</td>
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
                <h3 className="text-lg font-semibold text-stone-900">Preview renderu</h3>
                <p className="text-xs text-stone-500">Szczegóły wybranej animacji i status QC.</p>
              </div>
              {selectedAnimation?.status && (
                <Badge variant="outline" className={cn('border', chipTone(selectedAnimation.status))}>
                  {statusLabel(selectedAnimation.status)}
                </Badge>
              )}
            </div>

            {!selectedAnimation ? (
              <div className="mt-4 rounded-xl border border-dashed border-stone-200 bg-white/70 p-4 text-sm text-stone-500">
                Wybierz wiersz animacji, aby zobaczyć szczegóły renderu.
              </div>
            ) : (
              <div className="mt-4 space-y-4">
                <div className="aspect-[9/16] w-full overflow-hidden rounded-2xl border border-stone-200 bg-stone-900">
                  {previewUrl ? (
                    <video className="h-full w-full object-cover" controls src={previewUrl} />
                  ) : (
                    <div className="flex h-full w-full items-center justify-center text-sm text-stone-300">
                      Nie znalezionie artefaktu wideo.
                    </div>
                  )}
                </div>

                <div className="space-y-2 text-xs text-stone-600">
                  <div className="flex items-center justify-between">
                    <span>Etap pipeline</span>
                    <span className="font-semibold text-stone-800">
                      {selectedAnimation.pipeline_stage ?? '—'}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Wynik QC</span>
                    <span className="font-semibold text-stone-800">
                      {selectedAnimation.qc?.result ?? '—'}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Status renderu</span>
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
                    <span>Czas</span>
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
                    Artefakty
                  </div>
                  {artifactsLoading ? (
                    <div>Ładowanie artefaktów…</div>
                  ) : artifactsError ? (
                    <div className="text-rose-600">{artifactsError}</div>
                  ) : artifacts.length === 0 ? (
                    <div>Brak dostępnych artefaktów.</div>
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
                    Historia publikacji
                  </div>
                  {publishRecordsLoading ? (
                    <div>Ładowanie rekordów publikacji…</div>
                  ) : publishRecordsError ? (
                    <div className="text-rose-600">{publishRecordsError}</div>
                  ) : publishRecords.length === 0 ? (
                    <div>Brak rekordów publikacji.</div>
                  ) : (
                    <ul className="space-y-2">
                      {publishRecords.map((item) => (
                        <li key={item.id} className="rounded-lg border border-stone-200 bg-stone-50/70 p-2">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="font-semibold text-stone-700">{item.platform_type ?? 'nieznana'}</span>
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
                              {item.status ?? 'nieznany'}
                            </Badge>
                            <span className="text-[0.7rem] text-stone-500">
                              {item.created_at ? new Date(item.created_at).toLocaleString() : '—'}
                            </span>
                          </div>
                          {item.content_id ? <div className="mt-1 text-[0.75rem]">content_id: {item.content_id}</div> : null}
                          {item.url ? <div className="truncate text-[0.75rem]">url: {item.url}</div> : null}
                          {typeof item.error_payload === 'object' && item.error_payload && 'message' in item.error_payload ? (
                            <div className="text-[0.75rem] text-rose-700">
                              błąd: {String((item.error_payload as { message?: unknown }).message ?? '')}
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
                      Akcja QC
                    </div>
                    <div className="mt-3 grid gap-2">
                      <label className="text-xs font-semibold uppercase tracking-[0.15em] text-stone-500">
                        Wynik
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
                        Notatki
                        <textarea
                          className="mt-1 w-full rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700"
                          rows={3}
                          value={qcNotesInput}
                          onChange={(event) => setQcNotesInput(event.target.value)}
                          placeholder="Opcjonalna nietatka QC"
                        />
                      </label>
                      <div className="grid gap-2 rounded-xl border border-stone-200 bg-stone-50/70 p-3 text-xs text-stone-700">
                        <label className="flex items-center gap-2">
                          <input
                            type="checkbox"
                            checked={qcIdeaIntentOk}
                            onChange={(event) => setQcIdeaIntentOk(event.target.checked)}
                          />
                          Idea intent OK
                        </label>
                        <label className="flex items-center gap-2">
                          <input
                            type="checkbox"
                            checked={qcIntroReadabilityOk}
                            onChange={(event) => setQcIntroReadabilityOk(event.target.checked)}
                          />
                          Intro readability OK
                        </label>
                        <label className="flex items-center gap-2">
                          <input
                            type="checkbox"
                            checked={qcAudioQualityOk}
                            onChange={(event) => setQcAudioQualityOk(event.target.checked)}
                          />
                          Audio quality OK
                        </label>
                      </div>
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
                      Rekord publikacji (manualny)
                    </div>
                    <div className="mt-2 rounded-xl border border-stone-200 bg-stone-50/70 p-3 text-xs text-stone-600">
                      <div className="flex items-center justify-between gap-2">
                        <div className="font-semibold uppercase tracking-[0.15em] text-stone-500">Preflight connectorów</div>
                        <button
                          type="button"
                          className="rounded-full border border-stone-300 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.12em] text-stone-600 transition hover:border-stone-400 hover:text-stone-800"
                          onClick={fetchPublishConnectorStatus}
                        >
                          Odśwież
                        </button>
                      </div>
                      {publishConnectorStatusError ? (
                        <div className="mt-2 text-rose-600">{publishConnectorStatusError}</div>
                      ) : (
                        <div className="mt-2 grid gap-2 sm:grid-cols-2">
                          {(['youtube', 'tiktok'] as const).map((platform) => {
                            const connector = publishConnectorStatus?.connectors?.[platform]
                            const ready = connector?.ready === true
                            const mode = connector?.mode ?? 'nieznany'
                            return (
                              <div
                                key={platform}
                                className={cn(
                                  'rounded-lg border px-3 py-2',
                                  ready
                                    ? 'border-emerald-200 bg-emerald-50/70 text-emerald-800'
                                    : 'border-amber-200 bg-amber-50/70 text-amber-800',
                                )}
                              >
                                <div className="font-semibold">{platform}</div>
                                <div>gotowy: {ready ? 'tak' : 'nie'}</div>
                                <div>tryb: {mode}</div>
                              </div>
                            )
                          })}
                        </div>
                      )}
                    </div>
                    <div className="mt-3 grid gap-2">
                      <div className="grid gap-2 sm:grid-cols-2">
                        <label className="text-xs font-semibold uppercase tracking-[0.15em] text-stone-500">
                        Platforma
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
                        ID treści
                        <input
                          className="mt-1 w-full rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700"
                          value={publishContentIdInput}
                          onChange={(event) => setPublishContentIdInput(event.target.value)}
                          placeholder="yt/tiktok ID treści"
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
                        Błąd (opcjonalnie)
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
                        {publishActionLoading ? 'Zapisywanie publikacji…' : 'Zapisz rekord publikacji'}
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
            <h2 className="text-2xl font-semibold text-stone-900">Log audytu</h2>
            <p className="text-sm text-stone-600">Chronielogiczny strumień akcji systemu z filtrami.</p>
          </div>
          <div className="text-xs text-stone-500">
            <div>Zaktualizowano: {auditUpdatedAt ? auditUpdatedAt.toLocaleTimeString() : 'brak danych'}</div>
          </div>
        </div>

        <div className="mt-4 flex flex-wrap items-end gap-3">
          <label className="flex min-w-[200px] flex-col gap-1 text-xs font-semibold uppercase tracking-[0.15em] text-stone-500">
            Typ zdarzenia
            <input
              className="rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700 focus:border-stone-400 focus:outline-none"
              placeholder="qc_decision / publish_record"
              value={auditType}
              onChange={(event) => setAuditType(event.target.value)}
            />
          </label>
          <label className="flex min-w-[200px] flex-col gap-1 text-xs font-semibold uppercase tracking-[0.15em] text-stone-500">
            Źródło
            <input
              className="rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700 focus:border-stone-400 focus:outline-none"
              placeholder="pipeline / api"
              value={auditSource}
              onChange={(event) => setAuditSource(event.target.value)}
            />
          </label>
          <label className="flex min-w-[220px] flex-1 flex-col gap-1 text-xs font-semibold uppercase tracking-[0.15em] text-stone-500">
            ID użytkownika (actor)
            <input
              className="rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700 focus:border-stone-400 focus:outline-none"
              placeholder="UUID"
              value={auditActor}
              onChange={(event) => setAuditActor(event.target.value)}
            />
          </label>
          <div className="flex flex-wrap gap-2">
            <Button className="rounded-full" onClick={fetchAuditEvents} disabled={auditLoading}>
              Zastosuj filtry
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
              Resetuj
            </Button>
          </div>
        </div>

        <div className="mt-4 overflow-x-auto">
          {auditLoading ? (
            <div className="rounded-2xl border border-dashed border-stone-200 bg-stone-50/60 p-6 text-sm text-stone-600">
              Ładowanie zdarzeń audytu…
            </div>
          ) : auditError ? (
            <div className="rounded-2xl border border-rose-200 bg-rose-50/70 p-6 text-sm text-rose-700">
              <div className="font-semibold">Nie udało się wczytać</div>
              <div>{auditError}</div>
            </div>
          ) : (
            <table className="min-w-[780px] w-full text-left text-sm">
              <thead className="text-xs uppercase tracking-[0.18em] text-stone-500">
                <tr>
                  <th className="px-2 py-3">Typ</th>
                  <th className="px-2 py-3">Źródło</th>
                  <th className="px-2 py-3">Aktor</th>
                  <th className="px-2 py-3">Wystąpiło</th>
                  <th className="px-2 py-3">Payload</th>
                </tr>
              </thead>
              <tbody>
                {auditEvents.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-2 py-6 text-center text-stone-500">
                      Brak zdarzeń audytu dla filtrów. Wykonaj akcje, aby zapełnić log.
                    </td>
                  </tr>
                ) : (
                  auditEvents.map((event) => (
                    <tr key={event.id} className="border-t border-stone-200/70">
                      <td className="px-2 py-4 text-stone-800">{event.event_type ?? '—'}</td>
                      <td className="px-2 py-4 text-stone-600">{event.source ?? '—'}</td>
                      <td className="px-2 py-4 font-monie text-xs text-stone-600">
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
            <h2 className="text-2xl font-semibold text-stone-900">Użycie LLM</h2>
            <p className="text-sm text-stone-600">
              Tokeny i koszt per task/provider/model z mediatora LLM.
            </p>
          </div>
          <div className="text-xs text-stone-500">
            <div>Zaktualizowano: {llmMetricsUpdatedAt ? llmMetricsUpdatedAt.toLocaleTimeString() : 'brak danych'}</div>
            <div>Backend stanu: {llmMetrics?.state_backend ?? '—'}</div>
          </div>
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-2">
          <Button variant="outline" className="rounded-full" onClick={fetchLLMMetrics} disabled={llmMetricsLoading}>
            {llmMetricsLoading ? 'Odświeżanie…' : 'Odśwież użycie'}
          </Button>
          {llmMetricsError ? <span className="text-xs text-rose-600">{llmMetricsError}</span> : null}
        </div>

        {tokenBudgetAlerts.length > 0 ? (
          <div className="mt-4 rounded-2xl border border-amber-200 bg-amber-50/80 p-4 text-sm text-amber-900">
            <div className="font-semibold">Ostrzeżenie budżetu tokenów</div>
            <div className="mt-1 text-xs text-amber-700">
              Zużycie przekracza {Math.round(TOKEN_BUDGET_ALERT_THRESHOLD * 100)}% skonfigurowanego limitu.
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
              <div className="text-xs uppercase tracking-[0.18em] text-stone-500">Wywołania</div>
              <div className="mt-2 text-2xl font-semibold text-stone-900">{llmTotals.calls}</div>
            </CardContent>
          </Card>
          <Card className="border border-stone-200 bg-stone-50/60 shadow-none">
            <CardContent className="pt-4">
              <div className="text-xs uppercase tracking-[0.18em] text-stone-500">Tokeny łącznie</div>
              <div className="mt-2 text-2xl font-semibold text-stone-900">{llmTotals.tokensTotal.toLocaleString()}</div>
            </CardContent>
          </Card>
          <Card className="border border-stone-200 bg-stone-50/60 shadow-none">
            <CardContent className="pt-4">
              <div className="text-xs uppercase tracking-[0.18em] text-stone-500">Szacowany koszt</div>
              <div className="mt-2 text-2xl font-semibold text-stone-900">${llmTotals.costTotal.toFixed(4)}</div>
            </CardContent>
          </Card>
          <Card className="border border-stone-200 bg-stone-50/60 shadow-none">
            <CardContent className="pt-4">
              <div className="text-xs uppercase tracking-[0.18em] text-stone-500">Budżet dzienny</div>
              <div className="mt-2 text-2xl font-semibold text-stone-900">
                ${(llmMetrics?.budget?.daily_budget_usd ?? 0).toFixed(2)}
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="mt-4 overflow-x-auto">
          {llmMetricsLoading && llmRouteRows.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-stone-200 bg-stone-50/60 p-6 text-sm text-stone-600">
              Ładowanie metryk użycia…
            </div>
          ) : (
            <table className="min-w-[960px] w-full text-left text-sm">
              <thead className="text-xs uppercase tracking-[0.18em] text-stone-500">
                <tr>
                  <th className="px-2 py-3">Zadanie</th>
                  <th className="px-2 py-3">Dostawca</th>
                  <th className="px-2 py-3">Model</th>
                  <th className="px-2 py-3">Wywołania</th>
                  <th className="px-2 py-3">Sukces</th>
                  <th className="px-2 py-3">Błędy</th>
                  <th className="px-2 py-3">Retry</th>
                  <th className="px-2 py-3">Tokeny</th>
                  <th className="px-2 py-3">Śr. opóźnienie</th>
                  <th className="px-2 py-3">Koszt</th>
                </tr>
              </thead>
              <tbody>
                {llmRouteRows.length === 0 ? (
                  <tr>
                    <td colSpan={10} className="px-2 py-6 text-center text-stone-500">
                      Brak wywołań LLM.
                    </td>
                  </tr>
                ) : (
                  llmRouteRows.map((row) => (
                    <tr key={row.routeKey} className="border-t border-stone-200/70">
                      <td className="px-2 py-4 text-stone-800">{row.taskType}</td>
                      <td className="px-2 py-4 text-stone-600">{row.provider}</td>
                      <td className="px-2 py-4 font-monie text-xs text-stone-600">{row.model}</td>
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
            <h2 className="text-2xl font-semibold text-stone-900">Snapshot ustawień</h2>
            <p className="text-sm text-stone-600">
              Widok tylko do odczytu flag środowiskowych i timeoutów używanych przez pipeline.
            </p>
          </div>
          <Badge variant="outline" className="border border-stone-300 text-stone-600">
            tylko odczyt
          </Badge>
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-2">
          <Button variant="outline" className="rounded-full" onClick={fetchSettings} disabled={settingsLoading}>
            {settingsLoading ? 'Odświeżanie…' : 'Odśwież ustawienia'}
          </Button>
          {settingsError ? (
            <span className="text-xs text-rose-600">{settingsError}</span>
          ) : null}
        </div>

        {settingsLoading ? (
          <div className="mt-4 rounded-2xl border border-dashed border-stone-200 bg-stone-50/60 p-6 text-sm text-stone-600">
            Ładowanie ustawień…
          </div>
        ) : settings ? (
          <div className="mt-6 grid gap-4 lg:grid-cols-2">
            <div className="rounded-2xl border border-stone-200 bg-stone-50/70 p-4">
              <div className="text-sm font-semibold text-stone-900">Usługi bazowe</div>
              <div className="text-xs text-stone-500">Bieżąca konfiguracja runtime.</div>
              <div className="mt-3 space-y-2 text-sm">
                <SettingRow label="DATABASE_URL" value={settings.database_url} />
                <SettingRow label="REDIS_URL" value={settings.redis_url} />
                <SettingRow label="ARTIFACTS_BASE_DIR" value={settings.artifacts_base_dir} />
                <SettingRow label="OPERATOR_GUARD" value={settings.operator_guard ? 'włączone' : 'wyłączone'} />
              </div>
            </div>
            <div className="rounded-2xl border border-stone-200 bg-stone-50/70 p-4">
              <div className="text-sm font-semibold text-stone-900">Timeouty pipeline</div>
              <div className="text-xs text-stone-500">Progi worker/render.</div>
              <div className="mt-3 space-y-2 text-sm">
                <SettingRow label="RQ_JOB_TIMEOUT" value={settings.rq_job_timeout} />
                <SettingRow label="RQ_RENDER_TIMEOUT" value={settings.rq_render_timeout} />
                <SettingRow label="FFMPEG_TIMEOUT_S" value={settings.ffmpeg_timeout_s} />
              </div>
            </div>
            <div className="rounded-2xl border border-stone-200 bg-stone-50/70 p-4">
              <div className="text-sm font-semibold text-stone-900">Bramka pomysłu</div>
              <div className="text-xs text-stone-500">Ustawienia podobieństwa i selekcji.</div>
              <div className="mt-3 space-y-2 text-sm">
                <SettingRow label="IDEA_GATE_ENABLED" value={settings.idea_gate_enabled} />
                <SettingRow label="IDEA_GATE_COUNT" value={settings.idea_gate_count} />
                <SettingRow label="IDEA_GATE_THRESHOLD" value={settings.idea_gate_threshold} />
                <SettingRow label="IDEA_GATE_AUTO" value={settings.idea_gate_auto} />
                <SettingRow label="DEV_MANUAL_FLOW" value={settings.dev_manual_flow} />
                <SettingRow label="OPERATOR_SINGLE_VIDEO_MODE" value={settings.operator_single_video_mode} />
                <SettingRow label="OPERATOR_TARGET_RUNTIME_S" value={settings.operator_target_runtime_s} />
                <SettingRow label="OPERATOR_INTRO_LANGUAGE" value={settings.operator_intro_language} />
                <SettingRow label="OPERATOR_LATER_MAX_AGE_DAYS" value={settings.operator_later_max_age_days} />
              </div>
            </div>
            <div className="rounded-2xl border border-stone-200 bg-stone-50/70 p-4">
              <div className="text-sm font-semibold text-stone-900">Generator OpenAI</div>
              <div className="text-xs text-stone-500">Konfiguracja runtime providera LLM.</div>
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
            Ustawienia są niedostępne.
          </div>
        )}

        <p className="mt-4 text-xs text-stone-500">
          Wartości są pobierane z runtime backendu przez <code>/settings</code>.
        </p>
      </section>
      </>
      ) : null}
    </div>
  )
}

export default App
