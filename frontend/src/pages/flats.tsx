import { useState, type FormEvent } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Pencil, Plus, Trash2, X } from 'lucide-react'
import { useSearchParams } from 'react-router-dom'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { ConfirmDialog } from '@/components/ui/confirm-dialog'
import { Dialog } from '@/components/ui/dialog'
import { EmptyState, ErrorState, LoadingBlock } from '@/components/ui/feedback'
import { Field, Input, Select, Textarea } from '@/components/ui/form'
import { PageHeader } from '@/components/ui/page-header'
import { SearchInput } from '@/components/ui/search-input'
import { Table, TBody, TD, TH, THead, TR } from '@/components/ui/table'
import { useAuth } from '@/features/auth/auth-context'
import { api, type FlatFilters } from '@/lib/api/endpoints'
import { flatStatusTone } from '@/lib/labels'
import { useApiMutation } from '@/lib/mutations'
import type { Flat, FlatInput, FlatStatus } from '@/lib/types'
import { useDebounce } from '@/lib/use-debounce'
import { formatTaka } from '@/lib/utils'

export default function FlatsPage() {
  const { user } = useAuth()
  const isAdmin = user?.role === 'admin'
  const [params, setParams] = useSearchParams()
  const [q, setQ] = useState(params.get('q') ?? '')
  const search = useDebounce(q)
  const [editing, setEditing] = useState<Flat | 'new' | null>(null)
  const [deleting, setDeleting] = useState<Flat | null>(null)

  const filters: FlatFilters = {
    q: search,
    building_id: params.get('building_id') ? Number(params.get('building_id')) : '',
    status: (params.get('status') as FlatStatus | null) ?? '',
    bedrooms: params.get('bedrooms') ? Number(params.get('bedrooms')) : '',
    max_rent: params.get('max_rent') ? Number(params.get('max_rent')) : '',
  }
  const setFilter = (key: string, value: string) => {
    const next = new URLSearchParams(params)
    if (value) next.set(key, value)
    else next.delete(key)
    setParams(next, { replace: true })
  }
  const hasFilters = ['building_id', 'status', 'bedrooms', 'max_rent'].some((k) => params.get(k)) || !!search

  const flats = useQuery({ queryKey: ['flats', filters], queryFn: () => api.flats.list(filters) })
  const buildings = useQuery({ queryKey: ['buildings', ''], queryFn: () => api.buildings.list() })

  const remove = useApiMutation((id: number) => api.flats.remove(id), {
    invalidate: ['flats'],
    success: 'Flat deleted',
    onSuccess: () => setDeleting(null),
  })

  return (
    <>
      <PageHeader
        title="Flats"
        description="Every unit across your buildings, with rent and status."
        actions={
          isAdmin && (
            <Button onClick={() => setEditing('new')}>
              <Plus className="h-4 w-4" /> Add flat
            </Button>
          )
        }
      />

      <Card className="mb-5 p-4">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-6">
          <SearchInput value={q} onChange={setQ} placeholder="Flat no, building, notes…" className="lg:col-span-2" />
          <Select value={params.get('building_id') ?? ''} onChange={(e) => setFilter('building_id', e.target.value)} aria-label="Building">
            <option value="">All buildings</option>
            {buildings.data?.map((b) => (
              <option key={b.id} value={b.id}>
                {b.name}
              </option>
            ))}
          </Select>
          <Select value={params.get('status') ?? ''} onChange={(e) => setFilter('status', e.target.value)} aria-label="Status">
            <option value="">Any status</option>
            <option value="vacant">Vacant</option>
            <option value="occupied">Occupied</option>
            <option value="maintenance">Under maintenance</option>
          </Select>
          <Select value={params.get('bedrooms') ?? ''} onChange={(e) => setFilter('bedrooms', e.target.value)} aria-label="Bedrooms">
            <option value="">Any bedrooms</option>
            {[1, 2, 3, 4, 5].map((n) => (
              <option key={n} value={n}>
                {n} bed
              </option>
            ))}
          </Select>
          <Select value={params.get('max_rent') ?? ''} onChange={(e) => setFilter('max_rent', e.target.value)} aria-label="Max rent">
            <option value="">Any rent</option>
            {[15000, 20000, 25000, 30000, 50000].map((n) => (
              <option key={n} value={n}>
                Up to {formatTaka(n)}
              </option>
            ))}
          </Select>
        </div>
        {hasFilters && (
          <button
            onClick={() => {
              setQ('')
              setParams({}, { replace: true })
            }}
            className="mt-3 inline-flex items-center gap-1 text-xs font-medium text-stone-500 hover:text-stone-800"
          >
            <X className="h-3.5 w-3.5" /> Clear filters
          </button>
        )}
      </Card>

      <Card>
        {flats.isLoading ? (
          <LoadingBlock />
        ) : flats.error ? (
          <ErrorState message={flats.error.message} onRetry={() => flats.refetch()} />
        ) : !flats.data?.length ? (
          <EmptyState
            title={hasFilters ? 'No flats match these filters' : 'No flats yet'}
            description={hasFilters ? 'Try widening your search.' : 'Add flats to your buildings to start tracking rent.'}
          />
        ) : (
          <Table>
            <THead>
              <tr>
                <TH>Flat</TH>
                <TH>Building</TH>
                <TH>Size</TH>
                <TH className="text-right">Rent</TH>
                <TH className="text-right">Service</TH>
                <TH>Status</TH>
                {isAdmin && <TH className="text-right">Actions</TH>}
              </tr>
            </THead>
            <TBody>
              {flats.data.map((f) => (
                <TR key={f.id}>
                  <TD>
                    <div className="font-semibold text-stone-900">{f.flat_no}</div>
                    <div className="text-xs text-stone-500">Floor {f.floor}</div>
                  </TD>
                  <TD>
                    <div className="text-stone-800">{f.building_name}</div>
                    <div className="text-xs text-stone-500">{f.area}</div>
                  </TD>
                  <TD>
                    <div className="text-stone-800">
                      {f.bedrooms} bed · {f.bathrooms} bath
                    </div>
                    <div className="max-w-56 truncate text-xs text-stone-500" title={f.description ?? ''}>
                      {f.size_sqft} sqft{f.description ? ` · ${f.description}` : ''}
                    </div>
                  </TD>
                  <TD className="text-right font-medium">{formatTaka(f.monthly_rent)}</TD>
                  <TD className="text-right text-stone-500">{formatTaka(f.service_charge)}</TD>
                  <TD>
                    <Badge tone={flatStatusTone[f.status]}>{f.status}</Badge>
                  </TD>
                  {isAdmin && (
                    <TD className="text-right">
                      <Button variant="ghost" size="icon" onClick={() => setEditing(f)} aria-label={`Edit flat ${f.flat_no}`}>
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <Button variant="ghost" size="icon" onClick={() => setDeleting(f)} aria-label={`Delete flat ${f.flat_no}`}>
                        <Trash2 className="h-4 w-4 text-red-600" />
                      </Button>
                    </TD>
                  )}
                </TR>
              ))}
            </TBody>
          </Table>
        )}
      </Card>

      {editing && <FlatForm flat={editing === 'new' ? null : editing} buildings={buildings.data ?? []} onClose={() => setEditing(null)} />}
      <ConfirmDialog
        open={!!deleting}
        onClose={() => setDeleting(null)}
        onConfirm={() => deleting && remove.mutate(deleting.id)}
        loading={remove.isPending}
        title="Delete flat?"
        message={`Flat ${deleting?.flat_no} in ${deleting?.building_name} will be removed. Flats with an active lease cannot be deleted.`}
      />
    </>
  )
}

const NEW_FLAT: Omit<FlatInput, 'building_id'> = {
  flat_no: '',
  floor: 1,
  bedrooms: 3,
  bathrooms: 2,
  size_sqft: 1200,
  monthly_rent: 20000,
  service_charge: 2000,
  status: 'vacant',
  description: '',
}

function FlatForm({ flat, buildings, onClose }: { flat: Flat | null; buildings: { id: number; name: string }[]; onClose: () => void }) {
  const [form, setForm] = useState<FlatInput>(() => {
    if (!flat) return { ...NEW_FLAT, building_id: buildings[0]?.id ?? 0 }
    const { id: _id, building_name: _b, area: _a, ...rest } = flat
    return rest
  })
  const save = useApiMutation((data: FlatInput) => (flat ? api.flats.update(flat.id, data) : api.flats.create(data)), {
    invalidate: ['flats'],
    success: flat ? 'Flat updated' : 'Flat added',
    onSuccess: onClose,
  })
  const errors = (save.error as { fieldErrors?: Record<string, string> } | null)?.fieldErrors ?? {}
  const num = (k: keyof FlatInput) => (e: React.ChangeEvent<HTMLInputElement>) => setForm({ ...form, [k]: Number(e.target.value) })

  const submit = (e: FormEvent) => {
    e.preventDefault()
    save.mutate({ ...form, description: form.description || null })
  }

  return (
    <Dialog
      open
      onClose={onClose}
      title={flat ? `Edit flat ${flat.flat_no}` : 'Add flat'}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" form="flat-form" loading={save.isPending}>
            Save
          </Button>
        </>
      }
    >
      <form id="flat-form" onSubmit={submit} className="grid grid-cols-2 gap-4">
        <Field label="Building" className="col-span-2" error={errors.building_id}>
          <Select value={form.building_id} onChange={(e) => setForm({ ...form, building_id: Number(e.target.value) })}>
            {buildings.map((b) => (
              <option key={b.id} value={b.id}>
                {b.name}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Flat no" error={errors.flat_no}>
          <Input required value={form.flat_no} onChange={(e) => setForm({ ...form, flat_no: e.target.value.toUpperCase() })} placeholder="4B" />
        </Field>
        <Field label="Floor" error={errors.floor}>
          <Input type="number" min={0} required value={form.floor} onChange={num('floor')} />
        </Field>
        <Field label="Bedrooms" error={errors.bedrooms}>
          <Input type="number" min={1} required value={form.bedrooms} onChange={num('bedrooms')} />
        </Field>
        <Field label="Bathrooms" error={errors.bathrooms}>
          <Input type="number" min={1} required value={form.bathrooms} onChange={num('bathrooms')} />
        </Field>
        <Field label="Size (sqft)" error={errors.size_sqft}>
          <Input type="number" min={100} required value={form.size_sqft} onChange={num('size_sqft')} />
        </Field>
        <Field label="Status" error={errors.status}>
          <Select value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value as FlatStatus })}>
            <option value="vacant">Vacant</option>
            <option value="occupied">Occupied</option>
            <option value="maintenance">Under maintenance</option>
          </Select>
        </Field>
        <Field label="Monthly rent (৳)" error={errors.monthly_rent}>
          <Input type="number" min={0} step={500} required value={form.monthly_rent} onChange={num('monthly_rent')} />
        </Field>
        <Field label="Service charge (৳)" error={errors.service_charge} hint="Gas, water, guard, lift">
          <Input type="number" min={0} step={100} required value={form.service_charge} onChange={num('service_charge')} />
        </Field>
        <Field label="Notes" className="col-span-2" error={errors.description}>
          <Textarea
            className="min-h-16"
            value={form.description ?? ''}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            placeholder="South-facing, 2 balconies, car parking…"
          />
        </Field>
      </form>
    </Dialog>
  )
}
