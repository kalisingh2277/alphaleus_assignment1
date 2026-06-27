import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Activity, AlertTriangle, Building2, Plus, RefreshCw, type LucideIcon } from 'lucide-react'
import { api, type MonitorScope } from '../lib/api'
import { StatusBadge } from '../components/badges'
import { relativeTime, withinDays } from '../lib/format'

export default function Dashboard() {
  const qc = useQueryClient()
  const competitors = useQuery({ queryKey: ['competitors'], queryFn: api.listCompetitors })
  const feed = useQuery({ queryKey: ['feed', {}], queryFn: () => api.feed() })
  const [showAdd, setShowAdd] = useState(false)

  const run = useMutation({ mutationFn: api.runPipeline, onSuccess: () => qc.invalidateQueries() })

  const list = competitors.data ?? []
  const changes = feed.data ?? []
  const weeklyChanges = (id: string) =>
    changes.filter((c) => c.competitor_id === id && withinDays(c.detected_at, 7)).length
  const totalChangesWeek = changes.filter((c) => withinDays(c.detected_at, 7)).length
  const highImpact = changes.filter((c) => (c.impact_score ?? 0) >= 8).length

  return (
    <div>
      <header className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Dashboard</h1>
          <p className="mt-1 text-sm text-slate-500">Competitors you're monitoring</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => run.mutate()}
            disabled={run.isPending}
            className="inline-flex items-center gap-2 whitespace-nowrap rounded-lg bg-white px-3.5 py-2 text-sm font-medium text-slate-700 ring-1 ring-slate-200 hover:bg-slate-50 disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${run.isPending ? 'animate-spin' : ''}`} /> Run check
          </button>
          <button
            onClick={() => setShowAdd((v) => !v)}
            className="inline-flex items-center gap-2 whitespace-nowrap rounded-lg bg-blue-600 px-3.5 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-700"
          >
            <Plus className="h-4 w-4" /> Add competitor
          </button>
        </div>
      </header>

      {run.isSuccess && (
        <div className="mb-4 rounded-lg bg-blue-50 px-4 py-2 text-sm text-blue-700 ring-1 ring-blue-100">
          Last run: scraped {run.data.scraped}, {run.data.meaningful} meaningful change(s),{' '}
          {run.data.scored} scored, {run.data.synced} synced to CRM.
        </div>
      )}

      {showAdd && (
        <AddCompetitorForm
          onDone={() => {
            setShowAdd(false)
            qc.invalidateQueries({ queryKey: ['competitors'] })
          }}
        />
      )}

      <div className="mb-6 grid grid-cols-3 gap-4">
        <StatCard icon={Building2} label="Competitors" value={list.length} />
        <StatCard icon={Activity} label="Changes this week" value={totalChangesWeek} />
        <StatCard icon={AlertTriangle} label="High-impact (8+)" value={highImpact} accent="text-red-600" />
      </div>

      {competitors.isLoading ? (
        <GridSkeleton />
      ) : competitors.isError ? (
        <ErrorBox message={(competitors.error as Error).message} />
      ) : list.length === 0 ? (
        <EmptyState onAdd={() => setShowAdd(true)} />
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {list.map((c) => (
            <Link
              key={c.id}
              to={`/competitors/${c.id}`}
              className="group rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition hover:border-blue-300 hover:shadow-md"
            >
              <div className="flex items-start justify-between">
                <h3 className="font-semibold text-slate-900 group-hover:text-blue-700">{c.name}</h3>
                <StatusBadge status={c.status} />
              </div>
              <p className="mt-1 truncate text-xs text-slate-400">{c.url}</p>
              <div className="mt-4 flex items-center justify-between text-sm">
                <span className="text-slate-600">
                  <span className="font-semibold text-slate-900">{weeklyChanges(c.id)}</span> changes
                  this week
                </span>
                <span className="text-slate-400">checked {relativeTime(c.last_checked_at)}</span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}

function StatCard({
  icon: Icon,
  label,
  value,
  accent,
}: {
  icon: LucideIcon
  label: string
  value: number
  accent?: string
}) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-center gap-2 text-slate-400">
        <Icon className="h-4 w-4" />
        <span className="text-xs font-medium uppercase tracking-wide">{label}</span>
      </div>
      <div className={`mt-2 text-2xl font-bold ${accent ?? 'text-slate-900'}`}>{value}</div>
    </div>
  )
}

function AddCompetitorForm({ onDone }: { onDone: () => void }) {
  const [name, setName] = useState('')
  const [url, setUrl] = useState('')
  const [scope, setScope] = useState<MonitorScope>('full_page')
  const m = useMutation({
    mutationFn: () => api.addCompetitor({ name, url, monitor_scope: scope }),
    onSuccess: onDone,
  })

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault()
        m.mutate()
      }}
      className="mb-6 rounded-xl border border-slate-200 bg-white p-5 shadow-sm"
    >
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-[1fr_1.5fr_auto]">
        <input
          required
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Competitor name"
          className="rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
        />
        <input
          required
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://competitor.com/pricing"
          className="rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
        />
        <select
          value={scope}
          onChange={(e) => setScope(e.target.value as MonitorScope)}
          className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
        >
          <option value="full_page">Full page</option>
          <option value="pricing">Pricing</option>
          <option value="careers">Careers</option>
        </select>
      </div>
      <div className="mt-3 flex items-center gap-3">
        <button
          type="submit"
          disabled={m.isPending}
          className="rounded-lg bg-blue-600 px-3.5 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {m.isPending ? 'Adding…' : 'Add competitor'}
        </button>
        {m.isError && <span className="text-sm text-red-600">{(m.error as Error).message}</span>}
      </div>
    </form>
  )
}

function GridSkeleton() {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {[0, 1, 2].map((i) => (
        <div key={i} className="h-28 animate-pulse rounded-xl border border-slate-200 bg-white" />
      ))}
    </div>
  )
}

function ErrorBox({ message }: { message: string }) {
  return (
    <div className="rounded-xl border border-red-200 bg-red-50 p-5 text-sm text-red-700">
      Could not load competitors: {message}. Is the backend running?
    </div>
  )
}

function EmptyState({ onAdd }: { onAdd: () => void }) {
  return (
    <div className="rounded-xl border border-dashed border-slate-300 bg-white p-10 text-center">
      <p className="text-slate-600">No competitors yet.</p>
      <button
        onClick={onAdd}
        className="mt-3 inline-flex items-center gap-2 rounded-lg bg-blue-600 px-3.5 py-2 text-sm font-semibold text-white hover:bg-blue-700"
      >
        <Plus className="h-4 w-4" /> Add your first competitor
      </button>
    </div>
  )
}
