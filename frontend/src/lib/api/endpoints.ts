import { http } from './client'
import type {
  Building,
  BuildingInput,
  ChatRequest,
  ChatResponse,
  Flat,
  FlatInput,
  FlatStatus,
  Lease,
  LeaseInput,
  MaintenanceCategory,
  MaintenanceCreateInput,
  MaintenanceRequest,
  MaintenanceStatus,
  MaintenanceUpdateInput,
  Payment,
  PaymentInput,
  PaymentStatus,
  Role,
  TokenResponse,
  User,
} from '@/lib/types'

export interface FlatFilters {
  q?: string
  building_id?: number | ''
  area?: string
  status?: FlatStatus | ''
  bedrooms?: number | ''
  max_rent?: number | ''
}
export interface LeaseFilters {
  q?: string
  is_active?: boolean | ''
}
export interface PaymentFilters {
  month?: string
  status?: PaymentStatus | ''
  lease_id?: number
}
export interface MaintenanceFilters {
  status?: MaintenanceStatus | ''
  category?: MaintenanceCategory | ''
}

export const api = {
  auth: {
    login: (email: string, password: string) => http.post<TokenResponse>('/auth/login', { email, password }, { auth: false }),
    register: (data: { full_name: string; email: string; phone: string; password: string }) =>
      http.post<User>('/auth/register', data, { auth: false }),
    me: () => http.get<User>('/auth/me'),
  },
  users: {
    list: (filters: { role?: Role; q?: string } = {}) => http.get<User[]>('/users', { ...filters }),
  },
  buildings: {
    list: (filters: { q?: string; area?: string } = {}) => http.get<Building[]>('/buildings', filters),
    create: (data: BuildingInput) => http.post<Building>('/buildings', data),
    update: (id: number, data: Partial<BuildingInput>) => http.patch<Building>(`/buildings/${id}`, data),
    remove: (id: number) => http.delete(`/buildings/${id}`),
  },
  flats: {
    list: (filters: FlatFilters = {}) => http.get<Flat[]>('/flats', { ...filters }),
    get: (id: number) => http.get<Flat>(`/flats/${id}`),
    create: (data: FlatInput) => http.post<Flat>('/flats', data),
    update: (id: number, data: Partial<FlatInput>) => http.patch<Flat>(`/flats/${id}`, data),
    remove: (id: number) => http.delete(`/flats/${id}`),
  },
  leases: {
    list: (filters: LeaseFilters = {}) => http.get<Lease[]>('/leases', { ...filters }),
    create: (data: LeaseInput) => http.post<Lease>('/leases', data),
    update: (id: number, data: Partial<LeaseInput>) => http.patch<Lease>(`/leases/${id}`, data),
    remove: (id: number) => http.delete(`/leases/${id}`),
  },
  payments: {
    list: (filters: PaymentFilters = {}) => http.get<Payment[]>('/payments', { ...filters }),
    create: (data: PaymentInput) => http.post<Payment>('/payments', data),
    update: (id: number, data: Partial<PaymentInput>) => http.patch<Payment>(`/payments/${id}`, data),
    remove: (id: number) => http.delete(`/payments/${id}`),
  },
  maintenance: {
    list: (filters: MaintenanceFilters = {}) => http.get<MaintenanceRequest[]>('/maintenance', { ...filters }),
    create: (data: MaintenanceCreateInput) => http.post<MaintenanceRequest>('/maintenance', data),
    update: (id: number, data: MaintenanceUpdateInput) => http.patch<MaintenanceRequest>(`/maintenance/${id}`, data),
    remove: (id: number) => http.delete(`/maintenance/${id}`),
  },
  chat: {
    send: (data: ChatRequest) => http.post<ChatResponse>('/chat', data),
  },
}
