import { useQuery } from '@tanstack/react-query'
import { ArrowRight, DoorOpen, Home, ReceiptText, Wrench } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Badge } from '@/components/ui/badge'
import { Card, CardBody, CardHeader, CardTitle } from '@/components/ui/card'
import { ErrorState, LoadingBlock } from '@/components/ui/feedback'
import { PageHeader } from '@/components/ui/page-header'
import { StatCard } from '@/components/ui/stat-card'
import { useAuth } from '@/features/auth/auth-context'
import { api } from '@/lib/api/endpoints'
import { maintenanceStatusLabel, paymentStatusTone, priorityTone } from '@/lib/labels'
import { timeAgo } from '@/lib/time'
import { currentMonth, formatMonth, formatTaka } from '@/lib/utils'

export default function DashboardPage() {
  const { user } = useAuth()
  const isAdmin = user?.role === 'admin'
  const month = currentMonth()

  const flats = useQuery({ queryKey: ['flats', 'all'], queryFn: () => api.flats.list() })
  const maintenance = useQuery({ queryKey: ['maintenance', ''], queryFn: () => api.maintenance.list() })
  const payments = useQuery({ queryKey: ['payments', month], queryFn: () => api.payments.list({ month }), enabled: isAdmin })

  if (flats.isLoading || maintenance.isLoading || (isAdmin && payments.isLoading)) return <LoadingBlock label="Loading your buildings…" />
  const error = flats.error ?? maintenance.error ?? payments.error
  if (error) return <ErrorState message={error.message} onRetry={() => [flats, maintenance, payments].forEach((q) => q.refetch())} />

  const allFlats = flats.data ?? []
  const occupied = allFlats.filter((f) => f.status === 'occupied').length
  const vacant = allFlats.filter((f) => f.status === 'vacant')
  const openRequests = (maintenance.data ?? []).filter((r) => r.status !== 'resolved')
  const urgent = openRequests.filter((r) => r.priority === 'urgent' || r.priority === 'high').length

  const pay = payments.data ?? []
  const expected = pay.reduce((s, p) => s + p.amount_due, 0)
  const collected = pay.reduce((s, p) => s + p.amount_paid, 0)
  const pending = pay.filter((p) => p.status !== 'paid')

  const byBuilding = Object.values(
    pay.reduce<Record<string, { name: string; due: number; paid: number }>>((acc, p) => {
      acc[p.building_name] ??= { name: p.building_name, due: 0, paid: 0 }
      acc[p.building_name].due += p.amount_due
      acc[p.building_name].paid += p.amount_paid
      return acc
    }, {}),
  )

  const firstName = user?.full_name.split(' ').at(-1)

  return (
    <>
      <PageHeader title={`Assalamu Alaikum, ${firstName}`} description={`Here's how your buildings are doing in ${formatMonth(month)}.`} />

      <div className="mb-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Occupancy" value={`${allFlats.length ? Math.round((occupied / allFlats.length) * 100) : 0}%`} hint={`${occupied} of ${allFlats.length} flats occupied`} icon={Home} />
        <StatCard label="Vacant flats" value={vacant.length} hint="Ready to let" icon={DoorOpen} tone={vacant.length ? 'amber' : 'default'} />
        {isAdmin && (
          <StatCard
            label="Collected this month"
            value={formatTaka(collected)}
            hint={`${expected ? Math.round((collected / expected) * 100) : 0}% of ${formatTaka(expected)}`}
            icon={ReceiptText}
            tone="green"
          />
        )}
        <StatCard label="Open repairs" value={openRequests.length} hint={urgent ? `${urgent} high priority` : 'Nothing urgent'} icon={Wrench} tone={urgent ? 'red' : 'default'} />
      </div>

      <div className="grid gap-6 lg:grid-cols-5">
        {isAdmin && (
          <Card className="lg:col-span-3">
            <CardHeader>
              <CardTitle>Collection by building</CardTitle>
              <Link to="/rent" className="inline-flex items-center gap-1 text-xs font-medium text-brand-700 hover:underline">
                Rent ledger <ArrowRight className="h-3 w-3" />
              </Link>
            </CardHeader>
            <CardBody className="space-y-5">
              {byBuilding.length === 0 && <p className="text-sm text-stone-500">No rent records for this month yet.</p>}
              {byBuilding.map((b) => {
                const pct = b.due ? Math.round((b.paid / b.due) * 100) : 0
                return (
                  <div key={b.name}>
                    <div className="mb-1.5 flex justify-between text-sm">
                      <span className="font-medium text-stone-800">{b.name}</span>
                      <span className="text-stone-500 tabular-nums">
                        {formatTaka(b.paid)} / {formatTaka(b.due)}
                      </span>
                    </div>
                    <div className="h-2.5 overflow-hidden rounded-full bg-stone-100" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100} aria-label={`${b.name} collection`}>
                      <div className="h-full rounded-full bg-brand-600 transition-all" style={{ width: `${pct}%` }} />
                    </div>
                  </div>
                )
              })}
            </CardBody>
          </Card>
        )}

        {isAdmin && (
          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle>Rent still pending</CardTitle>
              <span className="text-xs text-stone-500">{pending.length} tenants</span>
            </CardHeader>
            <ul className="divide-y divide-stone-100">
              {pending.length === 0 && <li className="px-5 py-6 text-center text-sm text-stone-500">Everyone has paid 🎉</li>}
              {pending.slice(0, 6).map((p) => (
                <li key={p.id} className="flex items-center justify-between gap-3 px-5 py-3">
                  <div className="min-w-0">
                    <div className="truncate text-sm font-medium text-stone-900">{p.tenant_name}</div>
                    <div className="text-xs text-stone-500">
                      {p.building_name} {p.flat_no}
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-sm font-semibold text-red-600 tabular-nums">{formatTaka(p.amount_due - p.amount_paid)}</div>
                    <Badge tone={paymentStatusTone[p.status]}>{p.status}</Badge>
                  </div>
                </li>
              ))}
            </ul>
          </Card>
        )}

        <Card className="lg:col-span-3">
          <CardHeader>
            <CardTitle>Active repair requests</CardTitle>
            <Link to="/maintenance" className="inline-flex items-center gap-1 text-xs font-medium text-brand-700 hover:underline">
              Maintenance board <ArrowRight className="h-3 w-3" />
            </Link>
          </CardHeader>
          <ul className="divide-y divide-stone-100">
            {openRequests.length === 0 && <li className="px-5 py-6 text-center text-sm text-stone-500">No open requests</li>}
            {openRequests.slice(0, 5).map((r) => (
              <li key={r.id} className="flex items-center justify-between gap-3 px-5 py-3">
                <div className="min-w-0">
                  <div className="truncate text-sm font-medium text-stone-900">{r.title}</div>
                  <div className="text-xs text-stone-500">
                    {r.building_name} {r.flat_no} · {maintenanceStatusLabel[r.status]} · {timeAgo(r.created_at)}
                  </div>
                </div>
                <Badge tone={priorityTone[r.priority]}>{r.priority}</Badge>
              </li>
            ))}
          </ul>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Vacant flats</CardTitle>
            <Link to="/flats?status=vacant" className="inline-flex items-center gap-1 text-xs font-medium text-brand-700 hover:underline">
              All flats <ArrowRight className="h-3 w-3" />
            </Link>
          </CardHeader>
          <ul className="divide-y divide-stone-100">
            {vacant.length === 0 && <li className="px-5 py-6 text-center text-sm text-stone-500">All flats are let</li>}
            {vacant.slice(0, 5).map((f) => (
              <li key={f.id} className="flex items-center justify-between gap-3 px-5 py-3">
                <div>
                  <div className="text-sm font-medium text-stone-900">
                    {f.building_name} {f.flat_no}
                  </div>
                  <div className="text-xs text-stone-500">
                    {f.area} · {f.bedrooms} bed · {f.size_sqft} sqft
                  </div>
                </div>
                <div className="text-sm font-semibold tabular-nums">{formatTaka(f.monthly_rent)}</div>
              </li>
            ))}
          </ul>
        </Card>
      </div>
    </>
  )
}
