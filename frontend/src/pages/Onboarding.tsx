import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Info } from 'lucide-react'
import { api } from '../lib/api'

export default function Onboarding() {
  const qc = useQueryClient()
  const profile = useQuery({ queryKey: ['profile'], queryFn: api.getProfile })
  const [product, setProduct] = useState('')
  const [customers, setCustomers] = useState('')
  const [pricePoint, setPricePoint] = useState('')

  useEffect(() => {
    if (profile.data) {
      setProduct(profile.data.product)
      setCustomers(profile.data.customers)
      setPricePoint(profile.data.price_point)
    }
  }, [profile.data])

  const m = useMutation({
    mutationFn: () => api.updateProfile({ product, customers, price_point: pricePoint }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['profile'] }),
  })

  const field = 'mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none'

  return (
    <div className="max-w-2xl">
      <h1 className="text-2xl font-bold text-slate-900">Business Profile</h1>
      <p className="mt-1 text-sm text-slate-500">
        Tell Argus about your business — it's the lens for every impact score.
      </p>

      <div className="mt-4 flex items-start gap-2 rounded-lg bg-blue-50 px-4 py-3 text-sm text-blue-800">
        <Info className="mt-0.5 h-4 w-4 shrink-0" />
        <span>
          Argus scores each competitor change <strong>relative to this profile</strong>. A change
          overlapping your core product or undercutting your price scores higher than one in an
          unrelated area. The more specific you are, the sharper the scores.
        </span>
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault()
          m.mutate()
        }}
        className="mt-6 space-y-5 rounded-xl border border-slate-200 bg-white p-6 shadow-sm"
      >
        <div>
          <label className="text-sm font-medium text-slate-700">What your product does</label>
          <textarea
            rows={2}
            value={product}
            onChange={(e) => setProduct(e.target.value)}
            placeholder="e.g. A project management SaaS for small remote teams (boards, timelines, reporting)"
            className={field}
          />
          <p className="mt-1 text-xs text-slate-400">Be specific about the problem you solve.</p>
        </div>

        <div>
          <label className="text-sm font-medium text-slate-700">Who your customers are</label>
          <textarea
            rows={2}
            value={customers}
            onChange={(e) => setCustomers(e.target.value)}
            placeholder="e.g. Startups and small businesses, 5–50 employees"
            className={field}
          />
          <p className="mt-1 text-xs text-slate-400">Segment, size, industry — whoever you sell to.</p>
        </div>

        <div>
          <label className="text-sm font-medium text-slate-700">Your price point</label>
          <input
            value={pricePoint}
            onChange={(e) => setPricePoint(e.target.value)}
            placeholder="e.g. $59/month Pro plan"
            className={field}
          />
          <p className="mt-1 text-xs text-slate-400">Your headline pricing, so price moves are scored in context.</p>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="submit"
            disabled={m.isPending}
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {m.isPending ? 'Saving…' : m.isSuccess ? 'Saved ✓' : 'Save profile'}
          </button>
          {m.isError && <span className="text-sm text-red-600">{(m.error as Error).message}</span>}
        </div>
      </form>
    </div>
  )
}
