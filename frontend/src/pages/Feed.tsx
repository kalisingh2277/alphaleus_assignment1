import { useEffect, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api, type ChangeCategory } from '../lib/api'
import { ChangeCard } from '../components/ChangeCard'

const CATEGORIES: Array<ChangeCategory | ''> = [
  '',
  'pricing',
  'product',
  'hiring',
  'messaging',
  'leadership',
  'other',
]

const SELECT =
  'rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm capitalize text-slate-700 focus:border-blue-500 focus:outline-none'

export default function Feed() {
  const qc = useQueryClient()
  const [competitorId, setCompetitorId] = useState('')
  const [category, setCategory] = useState('')
  const [showNoise, setShowNoise] = useState(false)

  const competitors = useQuery({ queryKey: ['competitors'], queryFn: api.listCompetitors })
  const feed = useQuery({
    queryKey: ['feed', { competitorId, category, showNoise }],
    queryFn: () =>
      api.feed({
        competitor_id: competitorId || undefined,
        category: category || undefined,
        meaningful_only: !showNoise,
      }),
  })

  // Viewing the feed clears the unread badge.
  useEffect(() => {
    api.markRead().then(() => qc.invalidateQueries({ queryKey: ['unread'] }))
  }, [qc])

  const nameOf = (id: string) => competitors.data?.find((c) => c.id === id)?.name
  const changes = feed.data ?? []

  return (
    <div>
      <header className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900">Intelligence Feed</h1>
        <p className="mt-1 text-sm text-slate-500">Every detected change, newest first.</p>
      </header>

      <div className="mb-5 flex flex-wrap items-center gap-3">
        <select value={competitorId} onChange={(e) => setCompetitorId(e.target.value)} className={SELECT}>
          <option value="">All competitors</option>
          {competitors.data?.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
        <select value={category} onChange={(e) => setCategory(e.target.value)} className={SELECT}>
          {CATEGORIES.map((c) => (
            <option key={c} value={c}>
              {c === '' ? 'All categories' : c}
            </option>
          ))}
        </select>
        <label className="flex items-center gap-2 text-sm text-slate-600">
          <input
            type="checkbox"
            checked={showNoise}
            onChange={(e) => setShowNoise(e.target.checked)}
            className="h-4 w-4 rounded border-slate-300"
          />
          Show filtered noise
        </label>
      </div>

      {feed.isLoading ? (
        <div className="space-y-4">
          {[0, 1, 2].map((i) => (
            <div key={i} className="h-32 animate-pulse rounded-xl border border-slate-200 bg-white" />
          ))}
        </div>
      ) : feed.isError ? (
        <div className="rounded-xl border border-red-200 bg-red-50 p-5 text-sm text-red-700">
          Could not load the feed: {(feed.error as Error).message}.
        </div>
      ) : changes.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-300 bg-white p-10 text-center text-slate-500">
          No changes match these filters yet.
        </div>
      ) : (
        <div className="space-y-4">
          {changes.map((c) => (
            <ChangeCard key={c.id} change={c} competitorName={nameOf(c.competitor_id)} />
          ))}
        </div>
      )}
    </div>
  )
}
