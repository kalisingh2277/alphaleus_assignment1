// Typed client for the Argus API. Uses same-origin relative URLs (proxied to the
// backend in dev; served by FastAPI in production).

const BASE = '/api/v1'

export type MonitorStatus = 'active' | 'paused' | 'error'
export type MonitorScope = 'full_page' | 'pricing' | 'careers'
export type ChangeCategory =
  | 'pricing'
  | 'product'
  | 'hiring'
  | 'messaging'
  | 'leadership'
  | 'other'
export type CrmStatus = 'pending' | 'synced' | 'failed'

export interface Competitor {
  id: string
  name: string
  url: string
  monitor_scope: MonitorScope
  status: MonitorStatus
  check_interval_hours: number
  created_at: string
  last_checked_at: string | null
  last_error: string | null
}

export interface PriceDiff {
  before: string[]
  after: string[]
  added: string[]
  removed: string[]
  delta?: string
}

export interface StructuredDiff {
  prices?: PriceDiff
}

export interface Change {
  id: string
  competitor_id: string
  from_snapshot_id: string | null
  to_snapshot_id: string
  similarity: number | null
  is_meaningful: boolean
  category: ChangeCategory | null
  structured_diff: StructuredDiff | null
  summary: string | null
  impact_score: number | null
  recommended_action: string | null
  crm_status: CrmStatus
  detected_at: string
}

export interface BusinessProfile {
  product: string
  customers: string
  price_point: string
}

export interface Thesis {
  available: boolean
  headline: string | null
  narrative: string | null
  recommended_focus: string | null
  change_count: number
  updated_at: string | null
}

export interface ScrapeResult {
  is_first: boolean
  changed: boolean
  is_meaningful: boolean
  category: ChangeCategory | null
  structured_diff: StructuredDiff | null
  preview: string
}

export type CompetitorPatch = Partial<{
  name: string
  monitor_scope: MonitorScope
  check_interval_hours: number
  status: MonitorStatus
}>

export interface PipelineRunResult {
  competitors: number
  scraped: number
  changes: number
  meaningful: number
  filtered: number
  errors: number
  scored: number
  llm_errors: number
  synced: number
  crm_failed: number
}

function apiKey(): string {
  return localStorage.getItem('argus_api_key') || ''
}

async function req<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const res = await fetch(BASE + path, {
    ...opts,
    headers: { 'Content-Type': 'application/json', 'X-API-Key': apiKey(), ...(opts.headers || {}) },
  })
  if (!res.ok) {
    let detail = `Request failed (${res.status})`
    try {
      const body = await res.json()
      if (body?.detail) detail = body.detail
    } catch {
      /* non-JSON error body */
    }
    throw new Error(detail)
  }
  return res.status === 204 ? (null as T) : res.json()
}

export const api = {
  listCompetitors: () => req<Competitor[]>('/competitors'),
  getCompetitor: (id: string) => req<Competitor>(`/competitors/${id}`),
  addCompetitor: (body: { name: string; url: string; monitor_scope: MonitorScope }) =>
    req<Competitor>('/competitors', { method: 'POST', body: JSON.stringify(body) }),
  updateCompetitor: (id: string, body: CompetitorPatch) =>
    req<Competitor>(`/competitors/${id}`, { method: 'PATCH', body: JSON.stringify(body) }),
  scrapeNow: (id: string) =>
    req<ScrapeResult>(`/competitors/${id}/scrape`, { method: 'POST' }),
  getThesis: (id: string) => req<Thesis>(`/competitors/${id}/thesis`),
  competitorChanges: (id: string, meaningfulOnly = true) =>
    req<Change[]>(`/competitors/${id}/changes?meaningful_only=${meaningfulOnly}`),
  feed: (params: { competitor_id?: string; category?: string; meaningful_only?: boolean } = {}) => {
    const q = new URLSearchParams()
    if (params.competitor_id) q.set('competitor_id', params.competitor_id)
    if (params.category) q.set('category', params.category)
    q.set('meaningful_only', String(params.meaningful_only ?? true))
    return req<Change[]>(`/changes?${q.toString()}`)
  },
  runPipeline: () => req<PipelineRunResult>('/pipeline/run', { method: 'POST' }),
  getProfile: () => req<BusinessProfile>('/profile'),
  updateProfile: (body: BusinessProfile) =>
    req<BusinessProfile>('/profile', { method: 'PUT', body: JSON.stringify(body) }),
  unreadCount: () => req<{ unread: number }>('/changes/unread-count'),
  markRead: () => req<{ ok: boolean }>('/changes/mark-read', { method: 'POST' }),
  sendDigest: () =>
    req<{ sent: boolean; reason?: string; count: number }>('/digest/send', { method: 'POST' }),
}
