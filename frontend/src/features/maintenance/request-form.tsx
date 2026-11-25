import { useState, type FormEvent } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import { Dialog } from '@/components/ui/dialog'
import { Field, Input, Select, Textarea } from '@/components/ui/form'
import { api } from '@/lib/api/endpoints'
import { maintenanceCategories, maintenancePriorities } from '@/lib/labels'
import { useApiMutation } from '@/lib/mutations'
import type { MaintenanceCreateInput } from '@/lib/types'

/**
 * Tenants report for their own flat (the backend uses their active lease).
 * Owners and caretakers pick the flat.
 */
export function RequestForm({ onClose, pickFlat }: { onClose: () => void; pickFlat: boolean }) {
  const flats = useQuery({ queryKey: ['flats', 'all'], queryFn: () => api.flats.list(), enabled: pickFlat })
  const [form, setForm] = useState<MaintenanceCreateInput>({ title: '', description: '', category: 'plumbing', priority: 'medium' })

  const save = useApiMutation((data: MaintenanceCreateInput) => api.maintenance.create(data), {
    invalidate: ['maintenance'],
    success: 'Request sent to the caretaker',
    onSuccess: onClose,
  })
  const errors = (save.error as { fieldErrors?: Record<string, string> } | null)?.fieldErrors ?? {}

  const submit = (e: FormEvent) => {
    e.preventDefault()
    save.mutate(form)
  }

  return (
    <Dialog
      open
      onClose={onClose}
      title="Report a problem"
      description="Describe what's wrong. The caretaker will be notified."
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" form="request-form" loading={save.isPending}>
            Submit request
          </Button>
        </>
      }
    >
      <form id="request-form" onSubmit={submit} className="grid grid-cols-2 gap-4">
        {pickFlat && (
          <Field label="Flat" className="col-span-2" error={errors.flat_id}>
            <Select required value={form.flat_id ?? ''} onChange={(e) => setForm({ ...form, flat_id: Number(e.target.value) })}>
              <option value="" disabled>
                Select a flat
              </option>
              {flats.data?.map((f) => (
                <option key={f.id} value={f.id}>
                  {f.building_name} {f.flat_no}
                </option>
              ))}
            </Select>
          </Field>
        )}
        <Field label="What's the problem?" className="col-span-2" error={errors.title}>
          <Input required maxLength={120} value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} placeholder="e.g. Kitchen sink leaking" />
        </Field>
        <Field label="Category" error={errors.category}>
          <Select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value as MaintenanceCreateInput['category'] })} className="capitalize">
            {maintenanceCategories.map((c) => (
              <option key={c} value={c}>
                {c[0].toUpperCase() + c.slice(1)}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Priority" error={errors.priority}>
          <Select value={form.priority} onChange={(e) => setForm({ ...form, priority: e.target.value as MaintenanceCreateInput['priority'] })}>
            {maintenancePriorities.map((p) => (
              <option key={p} value={p}>
                {p[0].toUpperCase() + p.slice(1)}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Details" className="col-span-2" error={errors.description}>
          <Textarea required value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} placeholder="Since when, where exactly, anything the caretaker should know…" />
        </Field>
      </form>
    </Dialog>
  )
}
