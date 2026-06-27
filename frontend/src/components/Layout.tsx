import { NavLink, Outlet } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Eye, LayoutDashboard, Rss, Settings as SettingsIcon, UserCog } from 'lucide-react'
import { api } from '../lib/api'

const navItems = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/feed', label: 'Intelligence Feed', icon: Rss, end: false },
  { to: '/onboarding', label: 'Business Profile', icon: UserCog, end: false },
  { to: '/settings', label: 'Settings', icon: SettingsIcon, end: false },
]

export default function Layout() {
  const unread = useQuery({ queryKey: ['unread'], queryFn: api.unreadCount, refetchInterval: 30_000 })

  return (
    <div className="flex min-h-screen bg-slate-50 text-slate-900">
      <aside className="flex w-60 shrink-0 flex-col bg-slate-900 text-slate-300">
        <div className="flex items-center gap-2 px-5 py-5 text-white">
          <Eye className="h-6 w-6 text-blue-400" />
          <span className="text-lg font-semibold tracking-tight">Argus</span>
        </div>
        <nav className="flex-1 space-y-1 px-3">
          {navItems.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `flex items-center justify-between rounded-lg px-3 py-2 text-sm font-medium transition ${
                  isActive ? 'bg-blue-600 text-white' : 'hover:bg-slate-800 hover:text-white'
                }`
              }
            >
              <span className="flex items-center gap-3">
                <Icon className="h-4 w-4" /> {label}
              </span>
              {to === '/feed' && (unread.data?.unread ?? 0) > 0 && (
                <span className="rounded-full bg-red-500 px-1.5 text-xs font-semibold text-white">
                  {unread.data!.unread}
                </span>
              )}
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-slate-800 px-5 py-4 text-xs text-slate-500">
          Competitor intelligence, automated.
        </div>
      </aside>
      <main className="flex-1 overflow-auto">
        <div className="mx-auto max-w-6xl px-8 py-8">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
