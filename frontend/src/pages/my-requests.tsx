import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { CheckCircle2, Plus, Wrench } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { EmptyState, ErrorState, LoadingBlock } from '@/components/ui/feedback'
import { PageHeader } from '@/components/ui/page-header'
import { RequestForm } from '@/features/maintenance/request-form'
import { api } from '@/lib/api/endpoints'
import { maintenanceStatusLabel, maintenanceStatusTone, priorityTone } from '@/lib/labels'
import { timeAgo } from '@/lib/time'

export default function MyRequestsPage() {
  const [creating, setCreating] = useState(false)
  const requests = useQuery({ queryKey: ['maintenance', 'mine'], queryFn: () => api.maintenance.list() })

  return (
    <>
      <PageHeader
        title="My requests"
        description="Report a problem in your flat and follow it until it's fixed."
        actions={
          <Button onClick={() => setCreating(true)}>
            <Plus className="h-4 w-4" /> Report a problem
          </Button>
        }
      />

      {requests.isLoading ? (
        <LoadingBlock />
      ) : requests.error ? (
        <Card>
          <ErrorState message={requests.error.message} onRetry={() => requests.refetch()} />
        </Card>
      ) : !requests.data?.length ? (
        <Card>
          <EmptyState
            title="No requests yet"
            description="Leaking tap? Fan not working? Report it here instead of calling — you can track the progress."
            action={<Button onClick={() => setCreating(true)}>Report a problem</Button>}
          />
        </Card>
      ) : (
        <div className="space-y-3">
          {requests.data.map((r) => (
            <Card key={r.id} className="flex gap-4 p-4 sm:p-5">
              <div className={`mt-0.5 h-fit rounded-lg p-2 ${r.status === 'resolved' ? 'bg-emerald-50 text-emerald-600' : 'bg-amber-50 text-amber-600'}`}>
                {r.status === 'resolved' ? <CheckCircle2 className="h-5 w-5" /> : <Wrench className="h-5 w-5" />}
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="font-semibold text-stone-900">{r.title}</h3>
                  <Badge tone={maintenanceStatusTone[r.status]}>{maintenanceStatusLabel[r.status]}</Badge>
                  <Badge tone={priorityTone[r.priority]}>{r.priority}</Badge>
                </div>
                <p className="mt-1 text-sm text-stone-600">{r.description}</p>
                <p className="mt-2 text-xs text-stone-500">
                  <span className="capitalize">{r.category}</span> · reported {timeAgo(r.created_at)}
                  {r.assigned_to_name && ` · ${r.assigned_to_name} is on it`}
                  {r.resolved_at && ` · fixed ${timeAgo(r.resolved_at)}`}
                </p>
              </div>
            </Card>
          ))}
        </div>
      )}

      {creating && <RequestForm pickFlat={false} onClose={() => setCreating(false)} />}
    </>
  )
}
