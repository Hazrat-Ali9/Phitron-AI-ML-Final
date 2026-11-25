import { useState, type FormEvent } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Field, Input } from '@/components/ui/form'
import { AuthLayout } from '@/features/auth/auth-layout'
import { useAuth } from '@/features/auth/auth-context'
import { ApiError } from '@/lib/api/client'
import { api } from '@/lib/api/endpoints'
import { homePathFor } from '@/lib/roles'

export default function RegisterPage() {
  const { user, login } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ full_name: '', email: '', phone: '', password: '' })
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  if (user) return <Navigate to={homePathFor(user.role)} replace />

  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) => setForm({ ...form, [k]: e.target.value })

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')
    setErrors({})
    if (form.password.length < 8) {
      setErrors({ password: 'Use at least 8 characters' })
      return
    }
    setSubmitting(true)
    try {
      await api.auth.register(form)
      const me = await login(form.email, form.password)
      toast.success('Account created. Welcome to BariBhara!')
      navigate(homePathFor(me.role), { replace: true })
    } catch (err) {
      if (err instanceof ApiError) setErrors(err.fieldErrors)
      setError((err as Error).message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AuthLayout title="Create your account" subtitle="Tenants sign up here. Your landlord links you to your flat.">
      <form onSubmit={onSubmit} className="space-y-4">
        <Field label="Full name" error={errors.full_name}>
          <Input required value={form.full_name} onChange={set('full_name')} placeholder="e.g. Nusrat Jahan" autoComplete="name" />
        </Field>
        <Field label="Email" error={errors.email}>
          <Input type="email" required value={form.email} onChange={set('email')} placeholder="you@example.com" autoComplete="email" />
        </Field>
        <Field label="Mobile number" error={errors.phone} hint="Used by your landlord for rent reminders">
          <Input type="tel" value={form.phone} onChange={set('phone')} placeholder="01XXX-XXXXXX" autoComplete="tel" />
        </Field>
        <Field label="Password" error={errors.password} hint="At least 8 characters">
          <Input type="password" required value={form.password} onChange={set('password')} autoComplete="new-password" />
        </Field>
        {error && !Object.keys(errors).length && <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}
        <Button type="submit" className="w-full justify-center" loading={submitting}>
          Create account
        </Button>
      </form>
      <p className="mt-6 text-center text-sm text-stone-500">
        Already have an account?{' '}
        <Link to="/login" className="font-medium text-brand-700 hover:underline">
          Log in
        </Link>
      </p>
    </AuthLayout>
  )
}
