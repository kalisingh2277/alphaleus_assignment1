import type { ChangeCategory, CrmStatus, MonitorStatus } from '../lib/api'

export function ImpactBadge({ score }: { score: number | null }) {
  const s = score ?? 0
  const cls =
    s >= 8
      ? 'bg-red-50 text-red-700 ring-red-200'
      : s >= 5
        ? 'bg-amber-50 text-amber-700 ring-amber-200'
        : 'bg-emerald-50 text-emerald-700 ring-emerald-200'
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold ring-1 ${cls}`}
      title="Business-impact score (1–10)"
    >
      {s}/10
    </span>
  )
}

export function CategoryBadge({ category }: { category: ChangeCategory | null }) {
  return (
    <span className="inline-flex items-center rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium capitalize text-slate-600 ring-1 ring-slate-200">
      {category ?? 'other'}
    </span>
  )
}

const STATUS_STYLES: Record<MonitorStatus, string> = {
  active: 'bg-emerald-50 text-emerald-700',
  paused: 'bg-slate-100 text-slate-500',
  error: 'bg-red-50 text-red-700',
}

export function StatusBadge({ status }: { status: MonitorStatus }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium capitalize ${STATUS_STYLES[status]}`}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {status}
    </span>
  )
}

const CRM_STYLES: Record<CrmStatus, { cls: string; label: string }> = {
  synced: { cls: 'text-emerald-600', label: 'Synced to CRM' },
  pending: { cls: 'text-slate-400', label: 'CRM pending' },
  failed: { cls: 'text-red-600', label: 'CRM failed — will retry' },
}

export function CrmBadge({ status }: { status: CrmStatus }) {
  const { cls, label } = CRM_STYLES[status]
  return <span className={`text-xs font-medium ${cls}`}>{label}</span>
}
