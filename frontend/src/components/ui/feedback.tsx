import type { ReactNode } from 'react'
import { AlertTriangle, Inbox, Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'

export function Spinner({ className }: { className?: string }) {
  return <Loader2 className={cn('h-5 w-5 animate-spin text-brand-700', className)} />
}

export function LoadingBlock({ label = 'Loading…' }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-2 py-16 text-sm text-stone-500">
      <Spinner /> {label}
    </div>
  )
}

export function EmptyState({ title, description, action }: { title: string; description?: string; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 px-6 py-14 text-center">
      <div className="rounded-full bg-stone-100 p-3 text-stone-400">
        <Inbox className="h-6 w-6" />
      </div>
      <p className="font-medium text-stone-800">{title}</p>
      {description && <p className="max-w-sm text-sm text-stone-500">{description}</p>}
      {action && <div className="mt-2">{action}</div>}
    </div>
  )
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 px-6 py-14 text-center">
      <div className="rounded-full bg-red-50 p-3 text-red-500">
        <AlertTriangle className="h-6 w-6" />
      </div>
      <p className="font-medium text-stone-800">Something went wrong</p>
      <p className="max-w-sm text-sm text-stone-500">{message}</p>
      {onRetry && (
        <button onClick={onRetry} className="mt-1 text-sm font-medium text-brand-700 hover:underline">
          Try again
        </button>
      )}
    </div>
  )
}
