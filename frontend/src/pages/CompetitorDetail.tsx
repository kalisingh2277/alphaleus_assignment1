import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Lightbulb, RefreshCw, Sparkles } from 'lucide-react'
import { api, type MonitorScope, type MonitorStatus } from '../lib/api'
import { ChangeCard } from '../components/ChangeCard'
import { StatusBadge } from '../components/badges'

export default function CompetitorDetail() {
  const { id } = useParams<{ id: string }>()
  const competitor = useQuery({ queryKey: ['competitor', id], queryFn: () => api.getCompetitor(id!) })
  const changes = useQuery({
    queryKey: ['competitor-changes', id],
    queryFn: () => api.competitorChanges(id!),
  })
  const thesis = useQuery({ queryKey: ['thesis', id], queryFn: () => api.getThesis(id!) })

  if (competitor.isLoading) {
    return <div className="h-40 animate-pulse rounded-xl border border-slate-200 bg-white" />
  }
  if (competitor.isError || !competitor.data) {
    return <div className="text-red-600">Competitor not found.</div>
  }

  const c = competitor.data
  const chartData = [...(changes.data ?? [])]
    .reverse()
    .map((ch, i) => ({ label: `#${i + 1}`, impact: ch.impact_score ?? 0, category: ch.category }))

  return (
    <div>
      <Link to="/" className="mb-4 inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-800">
        <ArrowLeft className="h-4 w-4" /> Dashboard
      </Link>

      <header className="mb-6 flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-slate-900">{c.name}</h1>
            <StatusBadge status={c.status} />
          </div>
          <a href={c.url} target="_blank" rel="noreferrer" className="mt-1 block text-sm text-blue-600 hover:underline">
            {c.url}
          </a>
        </div>
        <ScrapeButton id={id!} />
      </header>

      <ThesisHero loading={thesis.isLoading} thesis={thesis.data} />

      <div className="mb-6 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <h3 className="mb-3 text-sm font-semibold text-slate-700">Impact over time</h3>
          <ImpactChart points={chartData} />
        </div>

        <MonitoringSettings competitor={c} />
      </div>

      <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">Change history</h3>
      {changes.isLoading ? (
        <div className="h-32 animate-pulse rounded-xl border border-slate-200 bg-white" />
      ) : (changes.data ?? []).length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-300 bg-white p-8 text-center text-slate-500">
          No changes detected yet.
        </div>
      ) : (
        <div className="space-y-4">
          {changes.data!.map((ch) => (
            <ChangeCard key={ch.id} change={ch} />
          ))}
        </div>
      )}
    </div>
  )
}

function ThesisHero({ loading, thesis }: { loading: boolean; thesis?: import('../lib/api').Thesis }) {
  if (loading) {
    return (
      <div className="mb-6 animate-pulse rounded-2xl bg-slate-900 p-6 text-slate-400">
        Synthesising competitor thesis…
      </div>
    )
  }
  if (!thesis?.available) {
    return (
      <div className="mb-6 rounded-xl border border-dashed border-slate-300 bg-white p-5 text-sm text-slate-500">
        The <span className="font-medium text-slate-700">competitor thesis</span> appears once there
        are at least 2 detected changes to synthesise into a strategy.
      </div>
    )
  }
  return (
    <div className="mb-6 rounded-2xl bg-gradient-to-br from-slate-900 to-slate-700 p-6 text-white shadow-lg">
      <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-blue-300">
        <Sparkles className="h-4 w-4" /> Competitor Thesis
      </div>
      <h2 className="mt-2 text-2xl font-bold">{thesis.headline}</h2>
      <p className="mt-3 leading-relaxed text-slate-200">{thesis.narrative}</p>
      <div className="mt-4 flex items-start gap-2 rounded-lg bg-white/10 px-4 py-3">
        <Lightbulb className="mt-0.5 h-4 w-4 shrink-0 text-blue-300" />
        <span className="text-sm text-slate-100">{thesis.recommended_focus}</span>
      </div>
      <p className="mt-3 text-xs text-slate-400">Synthesised from {thesis.change_count} changes</p>
    </div>
  )
}

function ImpactChart({
  points,
}: {
  points: Array<{ label: string; impact: number; category: string | null }>
}) {
  if (points.length === 0) return <p className="text-sm text-slate-400">No changes yet.</p>

  const W = 340
  const H = 170
  const padX = 26
  const padY = 16
  const n = points.length
  const xFor = (i: number) =>
    n === 1 ? W / 2 : padX + (i / (n - 1)) * (W - 2 * padX)
  const yFor = (v: number) => H - padY - (v / 10) * (H - 2 * padY)
  const color = (v: number) => (v >= 8 ? '#dc2626' : v >= 5 ? '#d97706' : '#16a34a')
  const line = points.map((p, i) => `${i === 0 ? 'M' : 'L'}${xFor(i).toFixed(1)},${yFor(p.impact).toFixed(1)}`).join(' ')

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ maxHeight: 190 }}>
      {[0, 5, 10].map((g) => {
        const yy = yFor(g)
        return (
          <g key={g}>
            <line x1={padX} y1={yy} x2={W - 6} y2={yy} stroke="#eef2f7" />
            <text x={padX - 6} y={yy + 3} textAnchor="end" fontSize="9" fill="#94a3b8">
              {g}
            </text>
          </g>
        )
      })}
      {n > 1 && <path d={line} fill="none" stroke="#2563eb" strokeWidth="2" />}
      {points.map((p, i) => (
        <g key={i}>
          <circle cx={xFor(i)} cy={yFor(p.impact)} r="4.5" fill={color(p.impact)}>
            <title>{`${p.category ?? 'change'}: ${p.impact}/10`}</title>
          </circle>
          <text x={xFor(i)} y={H - 3} textAnchor="middle" fontSize="9" fill="#94a3b8">
            {p.label}
          </text>
        </g>
      ))}
    </svg>
  )
}

function ScrapeButton({ id }: { id: string }) {
  const qc = useQueryClient()
  const m = useMutation({
    mutationFn: () => api.scrapeNow(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['competitor-changes', id] }),
  })
  return (
    <div className="text-right">
      <button
        onClick={() => m.mutate()}
        disabled={m.isPending}
        className="inline-flex items-center gap-2 rounded-lg bg-white px-3.5 py-2 text-sm font-medium text-slate-700 ring-1 ring-slate-200 hover:bg-slate-50 disabled:opacity-50"
      >
        <RefreshCw className={`h-4 w-4 ${m.isPending ? 'animate-spin' : ''}`} /> Scrape now
      </button>
      {m.isError && <p className="mt-1 max-w-xs text-xs text-red-600">{(m.error as Error).message}</p>}
      {m.isSuccess && (
        <p className="mt-1 text-xs text-slate-500">
          {m.data.is_first ? 'First snapshot saved.' : m.data.changed ? 'Change detected.' : 'No change.'}
        </p>
      )}
    </div>
  )
}

function MonitoringSettings({ competitor }: { competitor: import('../lib/api').Competitor }) {
  const qc = useQueryClient()
  const [scope, setScope] = useState<MonitorScope>(competitor.monitor_scope)
  const [intervalHours, setIntervalHours] = useState(competitor.check_interval_hours)
  const [status, setStatus] = useState<MonitorStatus>(competitor.status)

  const m = useMutation({
    mutationFn: () =>
      api.updateCompetitor(competitor.id, {
        monitor_scope: scope,
        check_interval_hours: intervalHours,
        status,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['competitor', competitor.id] })
      qc.invalidateQueries({ queryKey: ['competitors'] })
    },
  })

  const field = 'mt-1 w-full rounded-lg border border-slate-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none'

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <h3 className="mb-3 text-sm font-semibold text-slate-700">Monitoring settings</h3>
      <div className="space-y-3">
        <label className="block text-xs font-medium text-slate-500">
          Monitored section
          <select value={scope} onChange={(e) => setScope(e.target.value as MonitorScope)} className={field}>
            <option value="full_page">Full page</option>
            <option value="pricing">Pricing</option>
            <option value="careers">Careers</option>
          </select>
        </label>
        <label className="block text-xs font-medium text-slate-500">
          Check interval (hours, min 6)
          <input
            type="number"
            min={6}
            value={intervalHours}
            onChange={(e) => setIntervalHours(Number(e.target.value))}
            className={field}
          />
        </label>
        <label className="block text-xs font-medium text-slate-500">
          Status
          <select value={status} onChange={(e) => setStatus(e.target.value as MonitorStatus)} className={field}>
            <option value="active">Active</option>
            <option value="paused">Paused</option>
          </select>
        </label>
      </div>
      <button
        onClick={() => m.mutate()}
        disabled={m.isPending}
        className="mt-4 rounded-lg bg-blue-600 px-3.5 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50"
      >
        {m.isPending ? 'Saving…' : m.isSuccess ? 'Saved ✓' : 'Save settings'}
      </button>
    </div>
  )
}
