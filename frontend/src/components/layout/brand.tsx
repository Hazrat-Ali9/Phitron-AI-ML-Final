import { Home } from 'lucide-react'
import { cn } from '@/lib/utils'

export function Brand({ className, light }: { className?: string; light?: boolean }) {
  return (
    <div className={cn('flex items-center gap-2.5', className)}>
      <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-700 text-white shadow-sm">
        <Home className="h-5 w-5" />
      </div>
      <div className="leading-tight">
        <div className={cn('text-base font-semibold tracking-tight', light ? 'text-white' : 'text-stone-900')}>BariBhara</div>
        <div className={cn('text-[11px]', light ? 'text-brand-100' : 'text-stone-500')}>বাড়িভাড়া · rent manager</div>
      </div>
    </div>
  )
}
