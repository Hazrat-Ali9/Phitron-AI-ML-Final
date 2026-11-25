import { Search } from 'lucide-react'
import { cn } from '@/lib/utils'

export function SearchInput({ value, onChange, placeholder, className }: { value: string; onChange: (v: string) => void; placeholder?: string; className?: string }) {
  return (
    <div className={cn('relative', className)}>
      <Search className="pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-stone-400" />
      <input
        type="search"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="h-10 w-full rounded-lg border border-stone-300 bg-white pr-3 pl-9 text-sm shadow-sm placeholder:text-stone-400 focus:border-brand-600 focus:ring-2 focus:ring-brand-600/20 focus:outline-none"
      />
    </div>
  )
}
