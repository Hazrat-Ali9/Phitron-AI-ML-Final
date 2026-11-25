import type { BadgeTone } from '@/components/ui/badge'
import type { FlatStatus, MaintenanceCategory, MaintenancePriority, MaintenanceStatus, PaymentMethod, PaymentStatus, Role } from '@/lib/types'

export const AREAS = ['Mirpur', 'Dhanmondi', 'Uttara', 'Mohammadpur', 'Bashundhara', 'Gulshan', 'Banani', 'Badda', 'Rampura', 'Khilgaon']

export const flatStatusTone: Record<FlatStatus, BadgeTone> = { vacant: 'green', occupied: 'blue', maintenance: 'amber' }
export const paymentStatusTone: Record<PaymentStatus, BadgeTone> = { paid: 'green', partial: 'amber', due: 'red' }
export const maintenanceStatusTone: Record<MaintenanceStatus, BadgeTone> = { open: 'red', in_progress: 'amber', resolved: 'green' }
export const priorityTone: Record<MaintenancePriority, BadgeTone> = { low: 'gray', medium: 'blue', high: 'amber', urgent: 'red' }
export const roleTone: Record<Role, BadgeTone> = { admin: 'violet', staff: 'blue', tenant: 'green' }

export const roleLabel: Record<Role, string> = { admin: 'Owner', staff: 'Caretaker', tenant: 'Tenant' }
export const maintenanceStatusLabel: Record<MaintenanceStatus, string> = { open: 'Open', in_progress: 'In progress', resolved: 'Resolved' }

export const paymentMethodLabel: Record<PaymentMethod, string> = { bkash: 'bKash', nagad: 'Nagad', cash: 'Cash', bank: 'Bank transfer' }

export const maintenanceCategories: MaintenanceCategory[] = ['plumbing', 'electrical', 'gas', 'lift', 'painting', 'other']
export const maintenancePriorities: MaintenancePriority[] = ['low', 'medium', 'high', 'urgent']
