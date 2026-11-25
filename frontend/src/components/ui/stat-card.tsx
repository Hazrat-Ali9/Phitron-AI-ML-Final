import type { LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Card } from './card'

const toneText = {
  default: 'text-stone-900',
  green: 'text-emerald-700',
  red: 'text-red-600',
  amber: 'text-amber-700',
} as const

export function StatCard({
  label,
  value,
  hint,
  icon: Icon,
  tone = 'default',
}: {
  label: string
  value: string | number
  hint?: string
  icon?: LucideIcon
  tone?: keyof typeof toneText
}) {
  return (
    <Card className="p-5">
      <div className="flex items-start justify-between gap-3">
        <p className="text-sm text-stone-500">{label}</p>
        {Icon && (
          <div className="rounded-lg bg-brand-50 p-2 text-brand-700">
            <Icon className="h-4 w-4" />
          </div>
        )}
      </div>
      <p className={cn('mt-1 text-2xl font-semibold tracking-tight tabular-nums', toneText[tone])}>{value}</p>
      {hint && <p className="mt-1 text-xs text-stone-500">{hint}</p>}
    </Card>
  )
}
