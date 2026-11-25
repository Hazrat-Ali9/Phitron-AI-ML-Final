import { useState, type FormEvent } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Field, Input } from '@/components/ui/form'
import { AuthLayout } from '@/features/auth/auth-layout'
import { useAuth } from '@/features/auth/auth-context'
import { USE_MOCK } from '@/lib/api/client'
import { homePathFor } from '@/lib/roles'

const DEMO = [
  { label: 'Owner', email: 'rahman@baribhara.app', password: 'admin123' },
  { label: 'Caretaker', email: 'karim@baribhara.app', password: 'staff123' },
  { label: 'Tenant', email: 'tanvir.hasan@gmail.com', password: 'tenant123' },
]

export default function LoginPage() {
  const { user, login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  if (user) return <Navigate to={homePathFor(user.role)} replace />

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      const me = await login(email, password)
      const from = (location.state as { from?: string } | null)?.from
      navigate(from ?? homePathFor(me.role), { replace: true })
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AuthLayout title="Welcome back" subtitle="Log in to manage your building or check your rent.">
      <form onSubmit={onSubmit} className="space-y-4">
        <Field label="Email">
          <Input type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" />
        </Field>
        <Field label="Password">
          <Input type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" />
        </Field>
        {error && <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}
        <Button type="submit" className="w-full justify-center" loading={submitting}>
          Log in
        </Button>
      </form>

      <p className="mt-6 text-center text-sm text-stone-500">
        New tenant?{' '}
        <Link to="/register" className="font-medium text-brand-700 hover:underline">
          Create an account
        </Link>
      </p>

      {USE_MOCK && (
        <div className="mt-8 rounded-xl border border-dashed border-stone-300 p-4">
          <p className="mb-3 text-xs font-medium tracking-wide text-stone-500 uppercase">Demo accounts</p>
          <div className="grid grid-cols-3 gap-2">
            {DEMO.map((d) => (
              <Button
                key={d.label}
                type="button"
                variant="secondary"
                size="sm"
                className="justify-center"
                onClick={() => {
                  setEmail(d.email)
                  setPassword(d.password)
                }}
              >
                {d.label}
              </Button>
            ))}
          </div>
        </div>
      )}
    </AuthLayout>
  )
}
