import { useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import {
  Bot,
  Building2,
  DoorOpen,
  FlaskConical,
  Home,
  LayoutDashboard,
  LogOut,
  Menu,
  ReceiptText,
  Users,
  Wrench,
  X,
  type LucideIcon,
} from 'lucide-react'
import { useAuth } from '@/features/auth/auth-context'
import { USE_MOCK } from '@/lib/api/client'
import { roleLabel } from '@/lib/labels'
import type { Role } from '@/lib/types'
import { cn, initials } from '@/lib/utils'
import { Brand } from './brand'

interface NavItem {
  to: string
  label: string
  icon: LucideIcon
  roles: Role[]
}

const NAV: NavItem[] = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard, roles: ['admin', 'staff'] },
  { to: '/buildings', label: 'Buildings', icon: Building2, roles: ['admin'] },
  { to: '/flats', label: 'Flats', icon: DoorOpen, roles: ['admin', 'staff'] },
  { to: '/tenants', label: 'Tenants & leases', icon: Users, roles: ['admin'] },
  { to: '/rent', label: 'Rent ledger', icon: ReceiptText, roles: ['admin'] },
  { to: '/maintenance', label: 'Maintenance', icon: Wrench, roles: ['admin', 'staff'] },
  { to: '/home', label: 'My home', icon: Home, roles: ['tenant'] },
  { to: '/my-requests', label: 'My requests', icon: Wrench, roles: ['tenant'] },
  { to: '/assistant', label: 'AI assistant', icon: Bot, roles: ['admin', 'staff', 'tenant'] },
]

export function AppLayout() {
  const { user, logout } = useAuth()
  const [open, setOpen] = useState(false)
  if (!user) return null
  const items = NAV.filter((n) => n.roles.includes(user.role))

  const sidebar = (
    <div className="flex h-full flex-col">
      <div className="flex h-16 items-center justify-between px-5">
        <Brand />
        <button className="rounded-md p-1 text-stone-500 lg:hidden" onClick={() => setOpen(false)} aria-label="Close menu">
          <X className="h-5 w-5" />
        </button>
      </div>
      <nav className="flex-1 space-y-0.5 px-3 py-2">
        {items.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            onClick={() => setOpen(false)}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                isActive ? 'bg-brand-50 text-brand-800' : 'text-stone-600 hover:bg-stone-100 hover:text-stone-900',
              )
            }
          >
            <Icon className="h-4.5 w-4.5" />
            {label}
          </NavLink>
        ))}
      </nav>
      <div className="border-t border-stone-200 p-3">
        <div className="flex items-center gap-3 rounded-lg px-2 py-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-brand-100 text-sm font-semibold text-brand-800">
            {initials(user.full_name)}
          </div>
          <div className="min-w-0 flex-1">
            <div className="truncate text-sm font-medium text-stone-900">{user.full_name}</div>
            <div className="text-xs text-stone-500">{roleLabel[user.role]}</div>
          </div>
          <button onClick={logout} className="rounded-md p-1.5 text-stone-400 hover:bg-stone-100 hover:text-stone-700" title="Log out" aria-label="Log out">
            <LogOut className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  )

  return (
    <div className="flex min-h-full">
      <aside className="fixed inset-y-0 left-0 hidden w-64 border-r border-stone-200 bg-white lg:block">{sidebar}</aside>

      {open && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div className="absolute inset-0 bg-stone-900/40" onClick={() => setOpen(false)} />
          <aside className="absolute inset-y-0 left-0 w-72 bg-white shadow-xl">{sidebar}</aside>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col lg:pl-64">
        <header className="sticky top-0 z-30 flex h-14 items-center gap-3 border-b border-stone-200 bg-white/90 px-4 backdrop-blur lg:hidden">
          <button onClick={() => setOpen(true)} className="rounded-md p-1.5 text-stone-600 hover:bg-stone-100" aria-label="Open menu">
            <Menu className="h-5 w-5" />
          </button>
          <Brand />
        </header>
        {USE_MOCK && (
          <div className="flex items-center justify-center gap-2 bg-amber-50 px-4 py-1.5 text-xs text-amber-800">
            <FlaskConical className="h-3.5 w-3.5" /> Mock mode — data is simulated in the browser and resets on reload.
          </div>
        )}
        <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
