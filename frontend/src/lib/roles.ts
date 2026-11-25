import type { Role } from '@/lib/types'

export function homePathFor(role: Role) {
  return role === 'tenant' ? '/home' : '/dashboard'
}
