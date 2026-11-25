/**
 * Shapes the frontend expects from the BariBhara backend (/api/v1).
 * See frontend/API_CONTRACT.md for the full endpoint list.
 */

export type Role = 'admin' | 'staff' | 'tenant'

export interface User {
  id: number
  full_name: string
  email: string
  phone: string | null
  role: Role
  is_active: boolean
  created_at: string
}

export interface TokenResponse {
  access_token: string
  token_type: 'bearer'
  expires_in?: number
}

export interface Building {
  id: number
  name: string
  address: string
  area: string
  total_floors: number
  created_at: string
}
export type BuildingInput = Omit<Building, 'id' | 'created_at'>

export type FlatStatus = 'vacant' | 'occupied' | 'maintenance'

export interface Flat {
  id: number
  building_id: number
  building_name: string
  area: string
  flat_no: string
  floor: number
  bedrooms: number
  bathrooms: number
  size_sqft: number
  monthly_rent: number
  service_charge: number
  status: FlatStatus
  description: string | null
}
export type FlatInput = Omit<Flat, 'id' | 'building_name' | 'area'>

export interface Lease {
  id: number
  flat_id: number
  tenant_id: number
  tenant_name: string
  tenant_phone: string | null
  flat_no: string
  building_name: string
  start_date: string
  end_date: string | null
  monthly_rent: number
  advance_amount: number
  nid_number: string
  family_members: number
  is_active: boolean
}
export type LeaseInput = Pick<
  Lease,
  'flat_id' | 'tenant_id' | 'start_date' | 'end_date' | 'monthly_rent' | 'advance_amount' | 'nid_number' | 'family_members' | 'is_active'
>

export type PaymentStatus = 'paid' | 'partial' | 'due'
export type PaymentMethod = 'bkash' | 'nagad' | 'cash' | 'bank'

export interface Payment {
  id: number
  lease_id: number
  tenant_name: string
  flat_no: string
  building_name: string
  /** "YYYY-MM" */
  month: string
  amount_due: number
  amount_paid: number
  method: PaymentMethod | null
  trx_id: string | null
  paid_at: string | null
  /** computed by the backend from amount_due / amount_paid */
  status: PaymentStatus
}
export type PaymentInput = Pick<Payment, 'lease_id' | 'month' | 'amount_due' | 'amount_paid' | 'method' | 'trx_id' | 'paid_at'>

export type MaintenanceCategory = 'plumbing' | 'electrical' | 'gas' | 'lift' | 'painting' | 'other'
export type MaintenancePriority = 'low' | 'medium' | 'high' | 'urgent'
export type MaintenanceStatus = 'open' | 'in_progress' | 'resolved'

export interface MaintenanceRequest {
  id: number
  flat_id: number
  flat_no: string
  building_name: string
  reported_by_id: number
  reported_by_name: string
  title: string
  description: string
  category: MaintenanceCategory
  priority: MaintenancePriority
  status: MaintenanceStatus
  assigned_to_id: number | null
  assigned_to_name: string | null
  created_at: string
  resolved_at: string | null
}
/** Tenants may omit flat_id: the backend uses their active lease's flat. */
export interface MaintenanceCreateInput {
  flat_id?: number
  title: string
  description: string
  category: MaintenanceCategory
  priority: MaintenancePriority
}
export type MaintenanceUpdateInput = Partial<Pick<MaintenanceRequest, 'status' | 'priority' | 'assigned_to_id'>>

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}
export interface ChatToolCall {
  name: string
  arguments: Record<string, unknown>
}
export interface ChatSource {
  title: string
  snippet: string
  score: number
}
export interface ChatRequest {
  message: string
  history: ChatMessage[]
}
export interface ChatResponse {
  reply: string
  tool_calls: ChatToolCall[]
  sources: ChatSource[]
}
