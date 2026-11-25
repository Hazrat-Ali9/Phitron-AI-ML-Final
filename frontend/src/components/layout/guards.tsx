import { Suspense, type ReactNode } from 'react'
import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { LoadingBlock } from '@/components/ui/feedback'
import { useAuth } from '@/features/auth/auth-context'
import { homePathFor } from '@/lib/roles'
import type { Role } from '@/lib/types'

export function RequireAuth() {
  const { user, loading } = useAuth()
  const location = useLocation()
  if (loading) return <LoadingBlock label="Checking your session…" />
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />
  return <Outlet />
}

export function RequireRole({ roles, children }: { roles: Role[]; children: ReactNode }) {
  const { user } = useAuth()
  if (!user) return null
  if (!roles.includes(user.role)) return <Navigate to={homePathFor(user.role)} replace />
  return <Suspense fallback={<LoadingBlock />}>{children}</Suspense>
}

export function HomeRedirect() {
  const { user } = useAuth()
  return <Navigate to={user ? homePathFor(user.role) : '/login'} replace />
}
