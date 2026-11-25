import type { ReactNode } from 'react'
import { Bot, ReceiptText, Wrench } from 'lucide-react'
import { Brand } from '@/components/layout/brand'

const points = [
  { icon: ReceiptText, title: 'No more rent khata', text: 'Every month’s rent, bKash/Nagad trx ID and due amount in one ledger.' },
  { icon: Wrench, title: 'Repairs that don’t get lost', text: 'Tenants report problems, the caretaker tracks them to done.' },
  { icon: Bot, title: 'An assistant that knows your building', text: 'Answers dues, house rules and to-let questions in Bangla or English, 24/7.' },
]

export function AuthLayout({ title, subtitle, children }: { title: string; subtitle: string; children: ReactNode }) {
  return (
    <div className="grid min-h-full lg:grid-cols-2">
      <div className="relative hidden overflow-hidden bg-brand-800 p-12 text-white lg:flex lg:flex-col lg:justify-between">
        <div className="absolute -top-24 -right-24 h-96 w-96 rounded-full bg-brand-700/60" />
        <div className="absolute -bottom-32 -left-16 h-80 w-80 rounded-full bg-brand-900/60" />
        <Brand light className="relative" />
        <div className="relative max-w-md">
          <h2 className="text-3xl leading-tight font-semibold">Manage your flats, tenants and rent — without the phone calls.</h2>
          <ul className="mt-8 space-y-5">
            {points.map(({ icon: Icon, title, text }) => (
              <li key={title} className="flex gap-3">
                <div className="mt-0.5 rounded-lg bg-white/10 p-2">
                  <Icon className="h-4.5 w-4.5" />
                </div>
                <div>
                  <div className="font-medium">{title}</div>
                  <div className="text-sm text-brand-100">{text}</div>
                </div>
              </li>
            ))}
          </ul>
        </div>
        <p className="relative text-xs text-brand-200">Built for landlords and building committees in Dhaka.</p>
      </div>
      <div className="flex items-center justify-center px-4 py-12 sm:px-8">
        <div className="w-full max-w-sm">
          <Brand className="mb-8 lg:hidden" />
          <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
          <p className="mt-1 mb-8 text-sm text-stone-500">{subtitle}</p>
          {children}
        </div>
      </div>
    </div>
  )
}
