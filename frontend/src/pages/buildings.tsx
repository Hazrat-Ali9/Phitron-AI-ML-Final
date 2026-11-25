import { useState, type FormEvent } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Building2, MapPin, Pencil, Plus, Trash2 } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { ConfirmDialog } from '@/components/ui/confirm-dialog'
import { Dialog } from '@/components/ui/dialog'
import { EmptyState, ErrorState, LoadingBlock } from '@/components/ui/feedback'
import { Field, Input, Select } from '@/components/ui/form'
import { PageHeader } from '@/components/ui/page-header'
import { SearchInput } from '@/components/ui/search-input'
import { api } from '@/lib/api/endpoints'
import { AREAS } from '@/lib/labels'
import { useApiMutation } from '@/lib/mutations'
import type { Building, BuildingInput } from '@/lib/types'
import { useDebounce } from '@/lib/use-debounce'

const EMPTY: BuildingInput = { name: '', address: '', area: 'Mirpur', total_floors: 6 }

export default function BuildingsPage() {
  const [q, setQ] = useState('')
  const search = useDebounce(q)
  const [editing, setEditing] = useState<Building | 'new' | null>(null)
  const [deleting, setDeleting] = useState<Building | null>(null)

  const buildings = useQuery({ queryKey: ['buildings', search], queryFn: () => api.buildings.list({ q: search }) })
  const flats = useQuery({ queryKey: ['flats', 'all'], queryFn: () => api.flats.list() })

  const remove = useApiMutation((id: number) => api.buildings.remove(id), {
    invalidate: ['buildings'],
    success: 'Building deleted',
    onSuccess: () => setDeleting(null),
  })

  const statsFor = (id: number) => {
    const list = flats.data?.filter((f) => f.building_id === id) ?? []
    return { total: list.length, occupied: list.filter((f) => f.status === 'occupied').length, vacant: list.filter((f) => f.status === 'vacant').length }
  }

  return (
    <>
      <PageHeader
        title="Buildings"
        description="The properties you own or manage."
        actions={
          <Button onClick={() => setEditing('new')}>
            <Plus className="h-4 w-4" /> Add building
          </Button>
        }
      />
      <SearchInput value={q} onChange={setQ} placeholder="Search by name or address…" className="mb-5 max-w-sm" />

      {buildings.isLoading ? (
        <LoadingBlock />
      ) : buildings.error ? (
        <ErrorState message={buildings.error.message} onRetry={() => buildings.refetch()} />
      ) : !buildings.data?.length ? (
        <Card>
          <EmptyState
            title={search ? 'No buildings match your search' : 'No buildings yet'}
            description="Add your first building, then add its flats."
            action={!search && <Button onClick={() => setEditing('new')}>Add building</Button>}
          />
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {buildings.data.map((b) => {
            const s = statsFor(b.id)
            const pct = s.total ? Math.round((s.occupied / s.total) * 100) : 0
            return (
              <Card key={b.id} className="flex flex-col">
                <div className="flex items-start gap-3 p-5">
                  <div className="rounded-lg bg-brand-50 p-2.5 text-brand-700">
                    <Building2 className="h-5 w-5" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <h3 className="font-semibold text-stone-900">{b.name}</h3>
                    <p className="mt-0.5 flex items-start gap-1 text-sm text-stone-500">
                      <MapPin className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                      {b.address}
                    </p>
                  </div>
                  <div className="flex gap-0.5">
                    <Button variant="ghost" size="icon" onClick={() => setEditing(b)} aria-label="Edit building">
                      <Pencil className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="icon" onClick={() => setDeleting(b)} aria-label="Delete building">
                      <Trash2 className="h-4 w-4 text-red-600" />
                    </Button>
                  </div>
                </div>
                <div className="mt-auto border-t border-stone-100 px-5 py-4">
                  <div className="mb-2 flex justify-between text-sm">
                    <span className="text-stone-500">
                      {b.total_floors} floors · {s.total} flats
                    </span>
                    <span className="font-medium text-stone-700">{pct}% occupied</span>
                  </div>
                  <div className="h-2 overflow-hidden rounded-full bg-stone-100">
                    <div className="h-full rounded-full bg-brand-600" style={{ width: `${pct}%` }} />
                  </div>
                  <div className="mt-3 flex justify-between text-xs text-stone-500">
                    <span>{s.vacant} vacant</span>
                    <Link to={`/flats?building_id=${b.id}`} className="font-medium text-brand-700 hover:underline">
                      View flats →
                    </Link>
                  </div>
                </div>
              </Card>
            )
          })}
        </div>
      )}

      {editing && <BuildingForm building={editing === 'new' ? null : editing} onClose={() => setEditing(null)} />}
      <ConfirmDialog
        open={!!deleting}
        onClose={() => setDeleting(null)}
        onConfirm={() => deleting && remove.mutate(deleting.id)}
        loading={remove.isPending}
        title="Delete building?"
        message={`“${deleting?.name}” will be removed permanently. Buildings that still have flats cannot be deleted.`}
      />
    </>
  )
}

function BuildingForm({ building, onClose }: { building: Building | null; onClose: () => void }) {
  const [form, setForm] = useState<BuildingInput>(building ? { name: building.name, address: building.address, area: building.area, total_floors: building.total_floors } : EMPTY)
  const save = useApiMutation((data: BuildingInput) => (building ? api.buildings.update(building.id, data) : api.buildings.create(data)), {
    invalidate: ['buildings', 'flats'],
    success: building ? 'Building updated' : 'Building added',
    onSuccess: onClose,
  })
  const fieldErrors = (save.error as { fieldErrors?: Record<string, string> } | null)?.fieldErrors ?? {}

  const submit = (e: FormEvent) => {
    e.preventDefault()
    save.mutate(form)
  }

  return (
    <Dialog
      open
      onClose={onClose}
      title={building ? 'Edit building' : 'Add building'}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" form="building-form" loading={save.isPending}>
            Save
          </Button>
        </>
      }
    >
      <form id="building-form" onSubmit={submit} className="space-y-4">
        <Field label="Building name" error={fieldErrors.name}>
          <Input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="e.g. Rahman Villa" />
        </Field>
        <Field label="Address" error={fieldErrors.address}>
          <Input required value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} placeholder="House 12, Road 5, Section 10, Mirpur" />
        </Field>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Area" error={fieldErrors.area}>
            <Select value={form.area} onChange={(e) => setForm({ ...form, area: e.target.value })}>
              {AREAS.map((a) => (
                <option key={a}>{a}</option>
              ))}
            </Select>
          </Field>
          <Field label="Floors" error={fieldErrors.total_floors}>
            <Input type="number" min={1} max={30} required value={form.total_floors} onChange={(e) => setForm({ ...form, total_floors: Number(e.target.value) })} />
          </Field>
        </div>
      </form>
    </Dialog>
  )
}
