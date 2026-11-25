import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Clock, Plus, Trash2, User as UserIcon } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { ConfirmDialog } from '@/components/ui/confirm-dialog'
import { ErrorState, LoadingBlock } from '@/components/ui/feedback'
import { Select } from '@/components/ui/form'
import { PageHeader } from '@/components/ui/page-header'
import { useAuth } from '@/features/auth/auth-context'
import { RequestForm } from '@/features/maintenance/request-form'
import { api } from '@/lib/api/endpoints'
import { maintenanceCategories, maintenanceStatusLabel, priorityTone } from '@/lib/labels'
import { useApiMutation } from '@/lib/mutations'
import { timeAgo } from '@/lib/time'
import type { MaintenanceCategory, MaintenanceRequest, MaintenanceStatus, MaintenanceUpdateInput } from '@/lib/types'
import { cn } from '@/lib/utils'

const COLUMNS: { status: MaintenanceStatus; accent: string }[] = [
  { status: 'open', accent: 'bg-red-500' },
  { status: 'in_progress', accent: 'bg-amber-500' },
  { status: 'resolved', accent: 'bg-emerald-500' },
]

const PRIORITY_ORDER = { urgent: 0, high: 1, medium: 2, low: 3 } as const

export default function MaintenancePage() {
  const { user } = useAuth()
  const [category, setCategory] = useState<MaintenanceCategory | ''>('')
  const [creating, setCreating] = useState(false)
  const [deleting, setDeleting] = useState<MaintenanceRequest | null>(null)

  const requests = useQuery({ queryKey: ['maintenance', category], queryFn: () => api.maintenance.list({ category }) })
  const staff = useQuery({ queryKey: ['users', 'staff'], queryFn: () => api.users.list({ role: 'staff' }) })

  const update = useApiMutation(({ id, data }: { id: number; data: MaintenanceUpdateInput }) => api.maintenance.update(id, data), {
    invalidate: ['maintenance'],
    success: 'Request updated',
  })
  const remove = useApiMutation((id: number) => api.maintenance.remove(id), {
    invalidate: ['maintenance'],
    success: 'Request deleted',
    onSuccess: () => setDeleting(null),
  })

  return (
    <>
      <PageHeader
        title="Maintenance"
        description="Repair requests from tenants — assign, track and close them."
        actions={
          <>
            <Select value={category} onChange={(e) => setCategory(e.target.value as MaintenanceCategory | '')} className="w-40" aria-label="Category">
              <option value="">All categories</option>
              {maintenanceCategories.map((c) => (
                <option key={c} value={c}>
                  {c[0].toUpperCase() + c.slice(1)}
                </option>
              ))}
            </Select>
            <Button onClick={() => setCreating(true)}>
              <Plus className="h-4 w-4" /> New request
            </Button>
          </>
        }
      />

      {requests.isLoading ? (
        <LoadingBlock />
      ) : requests.error ? (
        <Card>
          <ErrorState message={requests.error.message} onRetry={() => requests.refetch()} />
        </Card>
      ) : (
        <div className="grid gap-4 lg:grid-cols-3">
          {COLUMNS.map(({ status, accent }) => {
            const items = (requests.data ?? [])
              .filter((r) => r.status === status)
              .sort((a, b) => PRIORITY_ORDER[a.priority] - PRIORITY_ORDER[b.priority] || b.created_at.localeCompare(a.created_at))
            return (
              <section key={status} className="flex flex-col rounded-xl bg-stone-100/70 p-3">
                <header className="mb-3 flex items-center gap-2 px-1">
                  <span className={cn('h-2 w-2 rounded-full', accent)} />
                  <h2 className="text-sm font-semibold text-stone-700">{maintenanceStatusLabel[status]}</h2>
                  <span className="ml-auto rounded-full bg-white px-2 text-xs font-medium text-stone-500">{items.length}</span>
                </header>
                <div className="space-y-3">
                  {items.length === 0 && <p className="px-1 py-6 text-center text-sm text-stone-400">Nothing here</p>}
                  {items.map((r) => (
                    <Card key={r.id} className="p-4">
                      <div className="mb-1 flex items-start justify-between gap-2">
                        <h3 className="text-sm font-semibold text-stone-900">{r.title}</h3>
                        <Badge tone={priorityTone[r.priority]}>{r.priority}</Badge>
                      </div>
                      <p className="mb-3 line-clamp-2 text-sm text-stone-600">{r.description}</p>
                      <div className="mb-3 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-stone-500">
                        <span className="font-medium text-stone-700">
                          {r.building_name} {r.flat_no}
                        </span>
                        <span className="capitalize">{r.category}</span>
                        <span className="inline-flex items-center gap-1">
                          <Clock className="h-3 w-3" /> {timeAgo(r.created_at)}
                        </span>
                        <span className="inline-flex items-center gap-1">
                          <UserIcon className="h-3 w-3" /> {r.reported_by_name}
                        </span>
                      </div>
                      <div className="flex gap-2 border-t border-stone-100 pt-3">
                        <Select
                          value={r.status}
                          onChange={(e) => update.mutate({ id: r.id, data: { status: e.target.value as MaintenanceStatus } })}
                          className="h-8 flex-1 text-xs"
                          aria-label="Status"
                        >
                          {COLUMNS.map((c) => (
                            <option key={c.status} value={c.status}>
                              {maintenanceStatusLabel[c.status]}
                            </option>
                          ))}
                        </Select>
                        <Select
                          value={r.assigned_to_id ?? ''}
                          onChange={(e) => update.mutate({ id: r.id, data: { assigned_to_id: e.target.value ? Number(e.target.value) : null } })}
                          className="h-8 flex-1 text-xs"
                          aria-label="Assigned to"
                        >
                          <option value="">Unassigned</option>
                          {staff.data?.map((s) => (
                            <option key={s.id} value={s.id}>
                              {s.full_name}
                            </option>
                          ))}
                        </Select>
                        {user?.role === 'admin' && (
                          <Button variant="ghost" size="icon" onClick={() => setDeleting(r)} aria-label="Delete request">
                            <Trash2 className="h-4 w-4 text-red-600" />
                          </Button>
                        )}
                      </div>
                    </Card>
                  ))}
                </div>
              </section>
            )
          })}
        </div>
      )}

      {creating && <RequestForm pickFlat onClose={() => setCreating(false)} />}
      <ConfirmDialog
        open={!!deleting}
        onClose={() => setDeleting(null)}
        onConfirm={() => deleting && remove.mutate(deleting.id)}
        loading={remove.isPending}
        title="Delete request?"
        message={`“${deleting?.title}” will be removed permanently.`}
      />
    </>
  )
}
