import { Lightbulb } from 'lucide-react'
import type { Change } from '../lib/api'
import { relativeTime } from '../lib/format'
import { CategoryBadge, CrmBadge, ImpactBadge } from './badges'

export function ChangeCard({
  change,
  competitorName,
}: {
  change: Change
  competitorName?: string
}) {
  const priceDelta = change.structured_diff?.prices?.delta
  const dimmed = !change.is_meaningful

  return (
    <div
      className={`rounded-xl border p-5 shadow-sm ${
        dimmed ? 'border-slate-200 bg-slate-50 opacity-70' : 'border-slate-200 bg-white'
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          {competitorName && <span className="font-semibold text-slate-900">{competitorName}</span>}
          <CategoryBadge category={change.category} />
          {dimmed && <span className="text-xs text-slate-400">filtered as noise</span>}
        </div>
        <div className="flex shrink-0 items-center gap-3">
          {change.is_meaningful && <ImpactBadge score={change.impact_score} />}
          <span className="text-xs text-slate-400">{relativeTime(change.detected_at)}</span>
        </div>
      </div>

      {priceDelta && (
        <div className="mt-3 inline-flex items-center gap-2 rounded-lg bg-slate-900 px-3 py-1.5 text-sm font-semibold text-white">
          {priceDelta}
        </div>
      )}

      {change.summary && <p className="mt-3 text-sm leading-relaxed text-slate-700">{change.summary}</p>}

      {change.recommended_action && (
        <div className="mt-3 flex items-start gap-2 rounded-lg bg-blue-50 px-3 py-2 text-sm text-blue-800">
          <Lightbulb className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{change.recommended_action}</span>
        </div>
      )}

      <div className="mt-3 flex items-center justify-between">
        <CrmBadge status={change.crm_status} />
        {change.similarity != null && (
          <span className="text-xs text-slate-300" title="Semantic similarity to the previous version">
            sim {change.similarity.toFixed(3)}
          </span>
        )}
      </div>
    </div>
  )
}
