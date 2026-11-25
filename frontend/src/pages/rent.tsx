import { useState, type FormEvent } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { CalendarPlus, CheckCircle2, ChevronLeft, ChevronRight, Pencil, Trash2 } from 'lucide-react'
import { toast } from 'sonner'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { ConfirmDialog } from '@/components/ui/confirm-dialog'
import { Dialog } from '@/components/ui/dialog'
import { EmptyState, ErrorState, LoadingBlock } from '@/components/ui/feedback'
import { Field, Input, Select } from '@/components/ui/form'
import { PageHeader } from '@/components/ui/page-header'
import { StatCard } from '@/components/ui/stat-card'
import { Table, TBody, TD, TH, THead, TR } from '@/components/ui/table'
import { api } from '@/lib/api/endpoints'
import { paymentMethodLabel, paymentStatusTone } from '@/lib/labels'
import { useApiMutation } from '@/lib/mutations'
import type { Payment, PaymentInput, PaymentMethod, PaymentStatus } from '@/lib/types'
import { currentMonth, formatDate, formatMonth, formatTaka } from '@/lib/utils'

function shiftMonth(month: string, delta: number) {
  const [y, m] = month.split('-').map(Number)
  const d = new Date(y, m - 1 + delta, 1)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
}

export default function RentPage() {
  const qc = useQueryClient()
  const [month, setMonth] = useState(currentMonth())
  const [status, setStatus] = useState<PaymentStatus | ''>('')
  const [recording, setRecording] = useState<Payment | null>(null)
  const [deleting, setDeleting] = useState<Payment | null>(null)
  const [generating, setGenerating] = useState(false)

  const payments = useQuery({ queryKey: ['payments', month], queryFn: () => api.payments.list({ month }) })
  const leases = useQuery({ queryKey: ['leases', '', 'true'], queryFn: () => api.leases.list({ is_active: true }) })

  const rows = (payments.data ?? []).filter((p) => !status || p.status === status)
  const all = payments.data ?? []
  const expected = all.reduce((s, p) => s + p.amount_due, 0)
  const collected = all.reduce((s, p) => s + p.amount_paid, 0)
  const outstanding = expected - collected
  const missing = (leases.data ?? []).filter((l) => l.start_date.slice(0, 7) <= month && !all.some((p) => p.lease_id === l.id))

  const remove = useApiMutation((id: number) => api.payments.remove(id), {
    invalidate: ['payments'],
    success: 'Rent record deleted',
    onSuccess: () => setDeleting(null),
  })

  async function generateMonth() {
    setGenerating(true)
    const results = await Promise.allSettled(
      missing.map((l) => api.payments.create({ lease_id: l.id, month, amount_due: l.monthly_rent, amount_paid: 0, method: null, trx_id: null, paid_at: null })),
    )
    setGenerating(false)
    const ok = results.filter((r) => r.status === 'fulfilled').length
    const failed = results.length - ok
    qc.invalidateQueries({ queryKey: ['payments'] })
    if (ok) toast.success(`Created ${ok} rent record${ok > 1 ? 's' : ''} for ${formatMonth(month)}`)
    if (failed) toast.error(`${failed} record${failed > 1 ? 's' : ''} could not be created`)
  }

  return (
    <>
      <PageHeader
        title="Rent ledger"
        description="Who has paid, how, and who still owes — month by month."
        actions={
          missing.length > 0 && (
            <Button onClick={generateMonth} loading={generating}>
              <CalendarPlus className="h-4 w-4" /> Create {missing.length} missing record{missing.length > 1 ? 's' : ''}
            </Button>
          )
        }
      />

      <div className="mb-5 flex flex-wrap items-center gap-3">
        <div className="inline-flex items-center rounded-lg border border-stone-300 bg-white shadow-sm">
          <button className="p-2 text-stone-500 hover:text-stone-900" onClick={() => setMonth(shiftMonth(month, -1))} aria-label="Previous month">
            <ChevronLeft className="h-4 w-4" />
          </button>
          <input type="month" value={month} onChange={(e) => e.target.value && setMonth(e.target.value)} className="h-9 bg-transparent px-1 text-sm font-medium focus:outline-none" aria-label="Month" />
          <button className="p-2 text-stone-500 hover:text-stone-900" onClick={() => setMonth(shiftMonth(month, 1))} aria-label="Next month">
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
        <Select value={status} onChange={(e) => setStatus(e.target.value as PaymentStatus | '')} className="w-40" aria-label="Status">
          <option value="">All statuses</option>
          <option value="paid">Paid</option>
          <option value="partial">Partial</option>
          <option value="due">Due</option>
        </Select>
      </div>

      <div className="mb-5 grid gap-4 sm:grid-cols-3">
        <StatCard label={`Expected · ${formatMonth(month)}`} value={formatTaka(expected)} hint={`${all.length} rent records`} />
        <StatCard label="Collected" value={formatTaka(collected)} hint={expected ? `${Math.round((collected / expected) * 100)}% of expected` : '—'} tone="green" />
        <StatCard label="Outstanding" value={formatTaka(outstanding)} hint={`${all.filter((p) => p.status !== 'paid').length} tenants pending`} tone={outstanding > 0 ? 'red' : 'green'} />
      </div>

      <Card>
        {payments.isLoading ? (
          <LoadingBlock />
        ) : payments.error ? (
          <ErrorState message={payments.error.message} onRetry={() => payments.refetch()} />
        ) : !rows.length ? (
          <EmptyState
            title={all.length ? 'No records with this status' : `No rent records for ${formatMonth(month)}`}
            description={all.length ? undefined : 'Create this month’s records for every active lease in one click.'}
            action={
              !all.length &&
              missing.length > 0 && (
                <Button onClick={generateMonth} loading={generating}>
                  Create records
                </Button>
              )
            }
          />
        ) : (
          <Table>
            <THead>
              <tr>
                <TH>Tenant</TH>
                <TH>Flat</TH>
                <TH className="text-right">Due</TH>
                <TH className="text-right">Paid</TH>
                <TH>Method</TH>
                <TH>Paid on</TH>
                <TH>Status</TH>
                <TH className="text-right">Actions</TH>
              </tr>
            </THead>
            <TBody>
              {rows.map((p) => (
                <TR key={p.id}>
                  <TD className="font-medium text-stone-900">{p.tenant_name}</TD>
                  <TD>
                    <span className="font-medium">{p.flat_no}</span> <span className="text-xs text-stone-500">{p.building_name}</span>
                  </TD>
                  <TD className="text-right">{formatTaka(p.amount_due)}</TD>
                  <TD className="text-right font-medium">{formatTaka(p.amount_paid)}</TD>
                  <TD>
                    {p.method ? (
                      <div>
                        <div>{paymentMethodLabel[p.method]}</div>
                        {p.trx_id && <div className="font-mono text-xs text-stone-500">{p.trx_id}</div>}
                      </div>
                    ) : (
                      <span className="text-stone-400">—</span>
                    )}
                  </TD>
                  <TD className="text-stone-600">{formatDate(p.paid_at)}</TD>
                  <TD>
                    <Badge tone={paymentStatusTone[p.status]}>{p.status}</Badge>
                  </TD>
                  <TD className="text-right">
                    {p.status !== 'paid' ? (
                      <Button size="sm" variant="secondary" onClick={() => setRecording(p)}>
                        <CheckCircle2 className="h-4 w-4 text-brand-700" /> Record
                      </Button>
                    ) : (
                      <Button variant="ghost" size="icon" onClick={() => setRecording(p)} aria-label="Edit payment">
                        <Pencil className="h-4 w-4" />
                      </Button>
                    )}
                    <Button variant="ghost" size="icon" onClick={() => setDeleting(p)} aria-label="Delete record">
                      <Trash2 className="h-4 w-4 text-red-600" />
                    </Button>
                  </TD>
                </TR>
              ))}
            </TBody>
          </Table>
        )}
      </Card>

      {recording && <PaymentForm payment={recording} onClose={() => setRecording(null)} />}
      <ConfirmDialog
        open={!!deleting}
        onClose={() => setDeleting(null)}
        onConfirm={() => deleting && remove.mutate(deleting.id)}
        loading={remove.isPending}
        title="Delete rent record?"
        message={`The ${deleting ? formatMonth(deleting.month) : ''} record for ${deleting?.tenant_name} will be removed.`}
      />
    </>
  )
}

function PaymentForm({ payment, onClose }: { payment: Payment; onClose: () => void }) {
  const [form, setForm] = useState<Pick<PaymentInput, 'amount_paid' | 'method' | 'trx_id' | 'paid_at'>>(() => ({
    amount_paid: payment.amount_paid || payment.amount_due,
    method: payment.method ?? 'bkash',
    trx_id: payment.trx_id ?? '',
    paid_at: (payment.paid_at ?? new Date().toISOString()).slice(0, 10),
  }))
  const save = useApiMutation((data: Partial<PaymentInput>) => api.payments.update(payment.id, data), {
    invalidate: ['payments'],
    success: 'Payment recorded',
    onSuccess: onClose,
  })
  const errors = (save.error as { fieldErrors?: Record<string, string> } | null)?.fieldErrors ?? {}
  const needsTrx = form.method === 'bkash' || form.method === 'nagad' || form.method === 'bank'

  const submit = (e: FormEvent) => {
    e.preventDefault()
    save.mutate({ ...form, trx_id: needsTrx ? form.trx_id || null : null, paid_at: form.paid_at ? `${form.paid_at}T00:00:00Z` : null })
  }

  return (
    <Dialog
      open
      onClose={onClose}
      title="Record payment"
      description={`${payment.tenant_name} · ${payment.building_name} ${payment.flat_no} · ${formatMonth(payment.month)}`}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" form="payment-form" loading={save.isPending}>
            Save payment
          </Button>
        </>
      }
    >
      <form id="payment-form" onSubmit={submit} className="grid grid-cols-2 gap-4">
        <Field label="Amount paid (৳)" error={errors.amount_paid} hint={`Due: ${formatTaka(payment.amount_due)}`}>
          <Input type="number" min={0} required value={form.amount_paid} onChange={(e) => setForm({ ...form, amount_paid: Number(e.target.value) })} />
        </Field>
        <Field label="Paid on" error={errors.paid_at}>
          <Input type="date" value={form.paid_at ?? ''} onChange={(e) => setForm({ ...form, paid_at: e.target.value })} />
        </Field>
        <Field label="Method" error={errors.method}>
          <Select value={form.method ?? ''} onChange={(e) => setForm({ ...form, method: e.target.value as PaymentMethod })}>
            {(Object.keys(paymentMethodLabel) as PaymentMethod[]).map((m) => (
              <option key={m} value={m}>
                {paymentMethodLabel[m]}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Transaction ID" error={errors.trx_id} hint={needsTrx ? 'From the bKash/Nagad/bank SMS' : 'Not needed for cash'}>
          <Input disabled={!needsTrx} value={needsTrx ? (form.trx_id ?? '') : ''} onChange={(e) => setForm({ ...form, trx_id: e.target.value.toUpperCase() })} placeholder="e.g. BKH8K2L9QX" className="font-mono" />
        </Field>
      </form>
    </Dialog>
  )
}
