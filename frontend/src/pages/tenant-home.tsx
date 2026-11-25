import { useQuery } from '@tanstack/react-query'
import { Bot, Building2, CalendarDays, CheckCircle2, CircleAlert, Wrench } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Badge } from '@/components/ui/badge'
import { Card, CardHeader, CardTitle } from '@/components/ui/card'
import { EmptyState, ErrorState, LoadingBlock } from '@/components/ui/feedback'
import { PageHeader } from '@/components/ui/page-header'
import { Table, TBody, TD, TH, THead, TR } from '@/components/ui/table'
import { useAuth } from '@/features/auth/auth-context'
import { api } from '@/lib/api/endpoints'
import { paymentMethodLabel, paymentStatusTone } from '@/lib/labels'
import { currentMonth, formatDate, formatMonth, formatTaka } from '@/lib/utils'

export default function TenantHomePage() {
  const { user } = useAuth()
  const leases = useQuery({ queryKey: ['leases', 'mine'], queryFn: () => api.leases.list({ is_active: true }) })
  const payments = useQuery({ queryKey: ['payments', 'mine'], queryFn: () => api.payments.list() })

  if (leases.isLoading || payments.isLoading) return <LoadingBlock />
  const error = leases.error ?? payments.error
  if (error) return <ErrorState message={error.message} onRetry={() => [leases, payments].forEach((q) => q.refetch())} />

  const lease = leases.data?.[0]
  const firstName = user?.full_name.split(' ')[0]

  if (!lease) {
    return (
      <>
        <PageHeader title={`Welcome, ${firstName}`} />
        <Card>
          <EmptyState
            title="You're not linked to a flat yet"
            description="Ask your landlord to add you to your flat in BariBhara. Meanwhile, you can ask the assistant about vacant flats and house rules."
            action={
              <Link to="/assistant" className="text-sm font-medium text-brand-700 hover:underline">
                Open the assistant →
              </Link>
            }
          />
        </Card>
      </>
    )
  }

  const history = (payments.data ?? []).filter((p) => p.lease_id === lease.id)
  const thisMonth = history.find((p) => p.month === currentMonth())
  const outstanding = history.reduce((s, p) => s + (p.amount_due - p.amount_paid), 0)

  return (
    <>
      <PageHeader title={`Welcome home, ${firstName}`} description={`${lease.building_name}, flat ${lease.flat_no}`} />

      <div className="mb-6 grid gap-4 lg:grid-cols-3">
        <Card className={`p-6 lg:col-span-2 ${outstanding > 0 ? 'border-red-200 bg-red-50/40' : 'border-emerald-200 bg-emerald-50/40'}`}>
          <div className="flex items-start gap-4">
            <div className={`rounded-xl p-3 ${outstanding > 0 ? 'bg-red-100 text-red-600' : 'bg-emerald-100 text-emerald-600'}`}>
              {outstanding > 0 ? <CircleAlert className="h-6 w-6" /> : <CheckCircle2 className="h-6 w-6" />}
            </div>
            <div>
              <p className="text-sm text-stone-600">{outstanding > 0 ? 'You have rent outstanding' : 'You are all paid up'}</p>
              <p className="mt-1 text-3xl font-semibold tracking-tight tabular-nums">{formatTaka(outstanding)}</p>
              <p className="mt-2 text-sm text-stone-600">
                {thisMonth
                  ? `${formatMonth(thisMonth.month)}: ${thisMonth.status === 'paid' ? `paid ${formatTaka(thisMonth.amount_paid)}` : `${formatTaka(thisMonth.amount_due - thisMonth.amount_paid)} due by the 7th`}`
                  : `${formatMonth(currentMonth())}'s rent hasn't been billed yet.`}
              </p>
            </div>
          </div>
        </Card>

        <Card className="p-6">
          <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-stone-900">
            <Building2 className="h-4 w-4 text-brand-700" /> My lease
          </div>
          <dl className="space-y-2 text-sm">
            <Row label="Flat" value={`${lease.building_name} ${lease.flat_no}`} />
            <Row label="Monthly" value={formatTaka(lease.monthly_rent)} />
            <Row label="Advance held" value={formatTaka(lease.advance_amount)} />
            <Row label="Since" value={formatDate(lease.start_date)} />
          </dl>
        </Card>
      </div>

      <div className="mb-6 grid gap-4 sm:grid-cols-2">
        <Link to="/assistant" className="group">
          <Card className="flex items-center gap-4 p-5 transition-colors group-hover:border-brand-300">
            <div className="rounded-xl bg-brand-50 p-3 text-brand-700">
              <Bot className="h-5 w-5" />
            </div>
            <div>
              <div className="font-medium text-stone-900">Ask the assistant</div>
              <div className="text-sm text-stone-500">“Gas bill ki service charge e included?”</div>
            </div>
          </Card>
        </Link>
        <Link to="/my-requests" className="group">
          <Card className="flex items-center gap-4 p-5 transition-colors group-hover:border-brand-300">
            <div className="rounded-xl bg-amber-50 p-3 text-amber-600">
              <Wrench className="h-5 w-5" />
            </div>
            <div>
              <div className="font-medium text-stone-900">Report a problem</div>
              <div className="text-sm text-stone-500">Leaks, electrical, lift, gas — track it to fixed.</div>
            </div>
          </Card>
        </Link>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <CalendarDays className="h-4 w-4 text-stone-400" /> Payment history
          </CardTitle>
        </CardHeader>
        {history.length === 0 ? (
          <EmptyState title="No rent records yet" />
        ) : (
          <Table>
            <THead>
              <tr>
                <TH>Month</TH>
                <TH className="text-right">Due</TH>
                <TH className="text-right">Paid</TH>
                <TH>Method</TH>
                <TH>Status</TH>
              </tr>
            </THead>
            <TBody>
              {history.map((p) => (
                <TR key={p.id}>
                  <TD className="font-medium">{formatMonth(p.month)}</TD>
                  <TD className="text-right">{formatTaka(p.amount_due)}</TD>
                  <TD className="text-right">{formatTaka(p.amount_paid)}</TD>
                  <TD>
                    {p.method ? paymentMethodLabel[p.method] : '—'}
                    {p.trx_id && <span className="ml-2 font-mono text-xs text-stone-500">{p.trx_id}</span>}
                  </TD>
                  <TD>
                    <Badge tone={paymentStatusTone[p.status]}>{p.status}</Badge>
                  </TD>
                </TR>
              ))}
            </TBody>
          </Table>
        )}
      </Card>
    </>
  )
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-3">
      <dt className="text-stone-500">{label}</dt>
      <dd className="font-medium text-stone-900">{value}</dd>
    </div>
  )
}
