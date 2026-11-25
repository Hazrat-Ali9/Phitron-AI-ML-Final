import { useState, type FormEvent } from 'react'
import { useQuery } from '@tanstack/react-query'
import { DoorClosed, Pencil, Phone, Plus, Trash2 } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { ConfirmDialog } from '@/components/ui/confirm-dialog'
import { Dialog } from '@/components/ui/dialog'
import { EmptyState, ErrorState, LoadingBlock } from '@/components/ui/feedback'
import { Field, Input, Select } from '@/components/ui/form'
import { PageHeader } from '@/components/ui/page-header'
import { SearchInput } from '@/components/ui/search-input'
import { Table, TBody, TD, TH, THead, TR } from '@/components/ui/table'
import { api } from '@/lib/api/endpoints'
import { useApiMutation } from '@/lib/mutations'
import type { Lease, LeaseInput } from '@/lib/types'
import { useDebounce } from '@/lib/use-debounce'
import { formatDate, formatTaka } from '@/lib/utils'

const today = () => new Date().toISOString().slice(0, 10)

export default function TenantsPage() {
  const [q, setQ] = useState('')
  const search = useDebounce(q)
  const [active, setActive] = useState<'' | 'true' | 'false'>('true')
  const [editing, setEditing] = useState<Lease | 'new' | null>(null)
  const [ending, setEnding] = useState<Lease | null>(null)
  const [deleting, setDeleting] = useState<Lease | null>(null)

  const leases = useQuery({
    queryKey: ['leases', search, active],
    queryFn: () => api.leases.list({ q: search, is_active: active === '' ? '' : active === 'true' }),
  })

  const end = useApiMutation((l: Lease) => api.leases.update(l.id, { is_active: false, end_date: today() }), {
    invalidate: ['leases', 'flats'],
    success: 'Lease ended and flat marked vacant',
    onSuccess: () => setEnding(null),
  })
  const remove = useApiMutation((id: number) => api.leases.remove(id), {
    invalidate: ['leases', 'flats'],
    success: 'Lease deleted',
    onSuccess: () => setDeleting(null),
  })

  return (
    <>
      <PageHeader
        title="Tenants & leases"
        description="Who lives where, since when, and on what terms."
        actions={
          <Button onClick={() => setEditing('new')}>
            <Plus className="h-4 w-4" /> New lease
          </Button>
        }
      />

      <div className="mb-5 flex flex-col gap-3 sm:flex-row">
        <SearchInput value={q} onChange={setQ} placeholder="Tenant name, phone or flat…" className="sm:w-80" />
        <div className="inline-flex rounded-lg border border-stone-300 bg-white p-0.5 shadow-sm">
          {(
            [
              ['true', 'Active'],
              ['false', 'Ended'],
              ['', 'All'],
            ] as const
          ).map(([value, label]) => (
            <button
              key={label}
              onClick={() => setActive(value)}
              className={`rounded-md px-3 py-1.5 text-sm font-medium ${active === value ? 'bg-brand-700 text-white' : 'text-stone-600 hover:bg-stone-100'}`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      <Card>
        {leases.isLoading ? (
          <LoadingBlock />
        ) : leases.error ? (
          <ErrorState message={leases.error.message} onRetry={() => leases.refetch()} />
        ) : !leases.data?.length ? (
          <EmptyState title="No leases found" description="Create a lease to link a registered tenant to a flat." />
        ) : (
          <Table>
            <THead>
              <tr>
                <TH>Tenant</TH>
                <TH>Flat</TH>
                <TH>Since</TH>
                <TH className="text-right">Monthly</TH>
                <TH className="text-right">Advance</TH>
                <TH>Family</TH>
                <TH>Status</TH>
                <TH className="text-right">Actions</TH>
              </tr>
            </THead>
            <TBody>
              {leases.data.map((l) => (
                <TR key={l.id}>
                  <TD>
                    <div className="font-medium text-stone-900">{l.tenant_name}</div>
                    {l.tenant_phone && (
                      <a href={`tel:${l.tenant_phone}`} className="inline-flex items-center gap-1 text-xs text-stone-500 hover:text-brand-700">
                        <Phone className="h-3 w-3" /> {l.tenant_phone}
                      </a>
                    )}
                  </TD>
                  <TD>
                    <div className="font-medium">{l.flat_no}</div>
                    <div className="text-xs text-stone-500">{l.building_name}</div>
                  </TD>
                  <TD>
                    <div>{formatDate(l.start_date)}</div>
                    {l.end_date && <div className="text-xs text-stone-500">to {formatDate(l.end_date)}</div>}
                  </TD>
                  <TD className="text-right font-medium">{formatTaka(l.monthly_rent)}</TD>
                  <TD className="text-right text-stone-600">{formatTaka(l.advance_amount)}</TD>
                  <TD className="text-stone-600">{l.family_members} people</TD>
                  <TD>
                    <Badge tone={l.is_active ? 'green' : 'gray'}>{l.is_active ? 'Active' : 'Ended'}</Badge>
                  </TD>
                  <TD className="text-right">
                    <Button variant="ghost" size="icon" onClick={() => setEditing(l)} aria-label="Edit lease">
                      <Pencil className="h-4 w-4" />
                    </Button>
                    {l.is_active && (
                      <Button variant="ghost" size="icon" onClick={() => setEnding(l)} aria-label="End lease" title="End lease (tenant moved out)">
                        <DoorClosed className="h-4 w-4 text-amber-600" />
                      </Button>
                    )}
                    <Button variant="ghost" size="icon" onClick={() => setDeleting(l)} aria-label="Delete lease">
                      <Trash2 className="h-4 w-4 text-red-600" />
                    </Button>
                  </TD>
                </TR>
              ))}
            </TBody>
          </Table>
        )}
      </Card>

      {editing && <LeaseForm lease={editing === 'new' ? null : editing} onClose={() => setEditing(null)} />}
      <ConfirmDialog
        open={!!ending}
        onClose={() => setEnding(null)}
        onConfirm={() => ending && end.mutate(ending)}
        loading={end.isPending}
        title="End this lease?"
        confirmLabel="End lease"
        message={`${ending?.tenant_name} is moving out of ${ending?.building_name} ${ending?.flat_no}. The lease ends today and the flat becomes vacant. Rent history is kept.`}
      />
      <ConfirmDialog
        open={!!deleting}
        onClose={() => setDeleting(null)}
        onConfirm={() => deleting && remove.mutate(deleting.id)}
        loading={remove.isPending}
        title="Delete lease?"
        message="Only delete leases created by mistake. To record a tenant moving out, use “End lease” instead."
      />
    </>
  )
}

function LeaseForm({ lease, onClose }: { lease: Lease | null; onClose: () => void }) {
  const tenants = useQuery({ queryKey: ['users', 'tenant'], queryFn: () => api.users.list({ role: 'tenant' }) })
  const flats = useQuery({ queryKey: ['flats', 'all'], queryFn: () => api.flats.list() })

  const [form, setForm] = useState<LeaseInput>(
    lease
      ? {
          flat_id: lease.flat_id,
          tenant_id: lease.tenant_id,
          start_date: lease.start_date,
          end_date: lease.end_date,
          monthly_rent: lease.monthly_rent,
          advance_amount: lease.advance_amount,
          nid_number: lease.nid_number,
          family_members: lease.family_members,
          is_active: lease.is_active,
        }
      : { flat_id: 0, tenant_id: 0, start_date: today(), end_date: null, monthly_rent: 0, advance_amount: 0, nid_number: '', family_members: 1, is_active: true },
  )

  const save = useApiMutation((data: LeaseInput) => (lease ? api.leases.update(lease.id, data) : api.leases.create(data)), {
    invalidate: ['leases', 'flats'],
    success: lease ? 'Lease updated' : 'Lease created — flat marked occupied',
    onSuccess: onClose,
  })
  const errors = (save.error as { fieldErrors?: Record<string, string> } | null)?.fieldErrors ?? {}

  const flatOptions = (flats.data ?? []).filter((f) => f.status === 'vacant' || f.id === form.flat_id)

  const pickFlat = (id: number) => {
    const flat = flats.data?.find((f) => f.id === id)
    if (!flat || lease) return setForm({ ...form, flat_id: id })
    // New lease: pre-fill the usual Dhaka terms — rent + service charge, 2 months advance
    setForm({ ...form, flat_id: id, monthly_rent: flat.monthly_rent + flat.service_charge, advance_amount: flat.monthly_rent * 2 })
  }

  const submit = (e: FormEvent) => {
    e.preventDefault()
    save.mutate({ ...form, end_date: form.end_date || null })
  }

  return (
    <Dialog
      open
      onClose={onClose}
      title={lease ? 'Edit lease' : 'New lease'}
      description={lease ? `${lease.tenant_name} · ${lease.building_name} ${lease.flat_no}` : 'Link a registered tenant to a vacant flat.'}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" form="lease-form" loading={save.isPending}>
            Save
          </Button>
        </>
      }
    >
      <form id="lease-form" onSubmit={submit} className="grid grid-cols-2 gap-4">
        <Field label="Tenant" className="col-span-2" error={errors.tenant_id} hint="The tenant must register an account first.">
          <Select required value={form.tenant_id || ''} onChange={(e) => setForm({ ...form, tenant_id: Number(e.target.value) })}>
            <option value="" disabled>
              {tenants.isLoading ? 'Loading tenants…' : 'Select a tenant'}
            </option>
            {tenants.data?.map((t) => (
              <option key={t.id} value={t.id}>
                {t.full_name} — {t.phone ?? t.email}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Flat" className="col-span-2" error={errors.flat_id}>
          <Select required value={form.flat_id || ''} onChange={(e) => pickFlat(Number(e.target.value))}>
            <option value="" disabled>
              {flats.isLoading ? 'Loading flats…' : 'Select a vacant flat'}
            </option>
            {flatOptions.map((f) => (
              <option key={f.id} value={f.id}>
                {f.building_name} {f.flat_no} — {f.bedrooms} bed, {formatTaka(f.monthly_rent)}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Start date" error={errors.start_date}>
          <Input type="date" required value={form.start_date} onChange={(e) => setForm({ ...form, start_date: e.target.value })} />
        </Field>
        <Field label="End date" error={errors.end_date} hint="Leave empty for open-ended">
          <Input type="date" value={form.end_date ?? ''} onChange={(e) => setForm({ ...form, end_date: e.target.value })} />
        </Field>
        <Field label="Monthly total (৳)" error={errors.monthly_rent} hint="Rent + service charge">
          <Input type="number" min={0} step={500} required value={form.monthly_rent} onChange={(e) => setForm({ ...form, monthly_rent: Number(e.target.value) })} />
        </Field>
        <Field label="Advance (৳)" error={errors.advance_amount}>
          <Input type="number" min={0} step={1000} required value={form.advance_amount} onChange={(e) => setForm({ ...form, advance_amount: Number(e.target.value) })} />
        </Field>
        <Field label="Tenant NID number" error={errors.nid_number}>
          <Input required inputMode="numeric" pattern="\d{10}|\d{13}|\d{17}" title="10, 13 or 17 digits" value={form.nid_number} onChange={(e) => setForm({ ...form, nid_number: e.target.value })} />
        </Field>
        <Field label="Family members" error={errors.family_members}>
          <Input type="number" min={1} max={20} required value={form.family_members} onChange={(e) => setForm({ ...form, family_members: Number(e.target.value) })} />
        </Field>
      </form>
    </Dialog>
  )
}
