/**
 * Realistic demo data for the in-memory mock API (VITE_API_MOCK=true).
 * This is only used by the frontend while the backend is not available.
 */
import type { Building, Flat, Lease, MaintenanceRequest, Payment, PaymentMethod, User } from '@/lib/types'

export interface MockUser extends User {
  password: string
}

const iso = (daysAgo: number) => new Date(Date.now() - daysAgo * 86_400_000).toISOString()

function monthOffset(offset: number) {
  const d = new Date()
  d.setDate(1)
  d.setMonth(d.getMonth() + offset)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
}

export const users: MockUser[] = [
  { id: 1, full_name: 'Abdur Rahman', email: 'rahman@baribhara.app', phone: '01711-482913', role: 'admin', password: 'admin123', is_active: true, created_at: iso(400) },
  { id: 2, full_name: 'Md. Karim Uddin', email: 'karim@baribhara.app', phone: '01819-205577', role: 'staff', password: 'staff123', is_active: true, created_at: iso(380) },
  { id: 3, full_name: 'Tanvir Hasan', email: 'tanvir.hasan@gmail.com', phone: '01712-334455', role: 'tenant', password: 'tenant123', is_active: true, created_at: iso(300) },
  { id: 4, full_name: 'Nusrat Jahan', email: 'nusrat.jahan@gmail.com', phone: '01915-667788', role: 'tenant', password: 'tenant123', is_active: true, created_at: iso(290) },
  { id: 5, full_name: 'Farhana Akter', email: 'farhana.akter@yahoo.com', phone: '01633-901122', role: 'tenant', password: 'tenant123', is_active: true, created_at: iso(250) },
  { id: 6, full_name: 'Mahmudul Islam', email: 'mahmud.islam@gmail.com', phone: '01556-778899', role: 'tenant', password: 'tenant123', is_active: true, created_at: iso(210) },
  { id: 7, full_name: 'Shirin Sultana', email: 'shirin.sultana@gmail.com', phone: '01799-110022', role: 'tenant', password: 'tenant123', is_active: true, created_at: iso(180) },
  { id: 8, full_name: 'Rafiqul Alam', email: 'rafiq.alam@outlook.com', phone: '01711-908070', role: 'tenant', password: 'tenant123', is_active: true, created_at: iso(330) },
  { id: 9, full_name: 'Sabbir Ahmed', email: 'sabbir.ahmed@gmail.com', phone: '01844-556677', role: 'tenant', password: 'tenant123', is_active: true, created_at: iso(150) },
  { id: 10, full_name: 'Ayesha Siddiqua', email: 'ayesha.s@gmail.com', phone: '01977-223344', role: 'tenant', password: 'tenant123', is_active: true, created_at: iso(120) },
  { id: 11, full_name: 'Imran Hossain', email: 'imran.hossain@gmail.com', phone: '01722-889900', role: 'tenant', password: 'tenant123', is_active: true, created_at: iso(95) },
]

export const buildings: Building[] = [
  { id: 1, name: 'Rahman Villa', address: 'House 12, Road 5, Section 10, Mirpur, Dhaka 1216', area: 'Mirpur', total_floors: 6, created_at: iso(400) },
  { id: 2, name: 'Nur Manzil', address: 'House 34/A, Road 9/A, Dhanmondi, Dhaka 1209', area: 'Dhanmondi', total_floors: 7, created_at: iso(390) },
  { id: 3, name: 'Shanti Neer', address: 'House 7, Road 14, Sector 11, Uttara, Dhaka 1230', area: 'Uttara', total_floors: 5, created_at: iso(200) },
]

type FlatSeed = [number, string, number, number, number, number, number, number, Flat['status'], string | null]
const flatSeeds: FlatSeed[] = [
  // building, flat_no, floor, beds, baths, sqft, rent, service, status, description
  [1, '2A', 2, 3, 2, 1250, 22000, 2000, 'occupied', 'South-facing, 2 balconies'],
  [1, '2B', 2, 2, 2, 950, 18000, 2000, 'occupied', null],
  [1, '3A', 3, 3, 2, 1250, 22000, 2000, 'occupied', 'South-facing, 2 balconies'],
  [1, '3B', 3, 2, 2, 950, 18000, 2000, 'vacant', 'Newly painted, gas line connected'],
  [1, '4A', 4, 3, 2, 1250, 22500, 2000, 'occupied', null],
  [1, '4B', 4, 2, 2, 950, 18500, 2000, 'maintenance', 'Bathroom tiles being replaced'],
  [1, '5A', 5, 3, 3, 1300, 23500, 2000, 'vacant', 'Top floor, roof access'],
  [1, '5B', 5, 2, 2, 950, 19000, 2000, 'occupied', null],
  [2, '3A', 3, 3, 3, 1800, 45000, 5000, 'vacant', 'Lake-view, servant room, 1 car parking'],
  [2, '4A', 4, 3, 3, 1800, 46000, 5000, 'occupied', '1 car parking'],
  [2, '5A', 5, 3, 3, 1800, 47000, 5000, 'occupied', '1 car parking'],
  [2, '6A', 6, 4, 3, 2100, 55000, 5000, 'vacant', 'Duplex-style, 2 car parking'],
  [3, '2A', 2, 3, 2, 1350, 26000, 3000, 'occupied', 'Near Sector 11 market'],
  [3, '2B', 2, 3, 2, 1350, 25000, 3000, 'vacant', null],
  [3, '3A', 3, 3, 2, 1350, 26500, 3000, 'vacant', 'Generator backup'],
  [3, '3B', 3, 3, 2, 1350, 26000, 3000, 'occupied', 'Generator backup'],
]

export const flats: Flat[] = flatSeeds.map(([building_id, flat_no, floor, bedrooms, bathrooms, size_sqft, monthly_rent, service_charge, status, description], i) => {
  const b = buildings.find((x) => x.id === building_id)!
  return { id: i + 1, building_id, building_name: b.name, area: b.area, flat_no, floor, bedrooms, bathrooms, size_sqft, monthly_rent, service_charge, status, description }
})

type LeaseSeed = [number, number, number, string, number]
const leaseSeeds: LeaseSeed[] = [
  // tenant, flat id, months ago started, NID, family
  [3, 1, 14, '1992384756', 4],
  [4, 2, 10, '1995472831', 2],
  [5, 3, 8, '1988726351423', 3],
  [6, 5, 7, '1990183746', 5],
  [7, 8, 5, '1987364521', 3],
  [8, 10, 11, '1979283746', 4],
  [9, 11, 4, '1993746152', 2],
  [10, 13, 3, '1996152837', 3],
  [11, 16, 2, '1991827364', 4],
]

export const leases: Lease[] = leaseSeeds.map(([tenant_id, flat_id, monthsAgo, nid_number, family_members], i) => {
  const t = users.find((u) => u.id === tenant_id)!
  const f = flats.find((x) => x.id === flat_id)!
  return {
    id: i + 1,
    flat_id,
    tenant_id,
    tenant_name: t.full_name,
    tenant_phone: t.phone,
    flat_no: f.flat_no,
    building_name: f.building_name,
    start_date: `${monthOffset(-monthsAgo)}-01`,
    end_date: null,
    monthly_rent: f.monthly_rent + f.service_charge,
    advance_amount: f.monthly_rent * 2,
    nid_number,
    family_members,
    is_active: true,
  }
})

const methods: PaymentMethod[] = ['bkash', 'nagad', 'bank', 'cash', 'bkash']
const trx = (n: number) => {
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
  let s = ''
  let x = n * 7919 + 104729
  for (let i = 0; i < 10; i++) {
    s += chars[x % chars.length]
    x = Math.floor(x / chars.length) + n * 31 + i * 17
  }
  return s
}

export const payments: Payment[] = []
let paymentId = 1
for (const offset of [-2, -1, 0]) {
  const month = monthOffset(offset)
  for (const lease of leases) {
    if (lease.start_date.slice(0, 7) > month) continue
    // current month: a realistic mix of paid, partial and still-due
    let paid = lease.monthly_rent
    if (offset === 0 && [1, 5, 8].includes(lease.id)) paid = 0
    if (offset === 0 && lease.id === 4) paid = 15000
    if (offset === -1 && lease.id === 5) paid = 10000
    const method = paid > 0 ? methods[(lease.id + offset + 3) % methods.length] : null
    payments.push({
      id: paymentId++,
      lease_id: lease.id,
      tenant_name: lease.tenant_name,
      flat_no: lease.flat_no,
      building_name: lease.building_name,
      month,
      amount_due: lease.monthly_rent,
      amount_paid: paid,
      method,
      trx_id: method && method !== 'cash' ? trx(paymentId) : null,
      paid_at: paid > 0 ? `${month}-${String(3 + (lease.id % 6)).padStart(2, '0')}T10:30:00Z` : null,
      status: paid === 0 ? 'due' : paid < lease.monthly_rent ? 'partial' : 'paid',
    })
  }
}

export const maintenance: MaintenanceRequest[] = [
  { id: 1, flat_id: 1, flat_no: '2A', building_name: 'Rahman Villa', reported_by_id: 3, reported_by_name: 'Tanvir Hasan', title: 'Kitchen sink leaking', description: 'Water is leaking under the kitchen sink since last night. The cabinet below is getting wet.', category: 'plumbing', priority: 'high', status: 'open', assigned_to_id: null, assigned_to_name: null, created_at: iso(1), resolved_at: null },
  { id: 2, flat_id: 5, flat_no: '4A', building_name: 'Rahman Villa', reported_by_id: 6, reported_by_name: 'Mahmudul Islam', title: 'Bedroom fan regulator not working', description: 'Fan only runs at full speed, regulator seems burnt.', category: 'electrical', priority: 'medium', status: 'in_progress', assigned_to_id: 2, assigned_to_name: 'Md. Karim Uddin', created_at: iso(3), resolved_at: null },
  { id: 3, flat_id: 10, flat_no: '4A', building_name: 'Nur Manzil', reported_by_id: 8, reported_by_name: 'Rafiqul Alam', title: 'Lift stops between 3rd and 4th floor', description: 'Lift stopped twice this week between floors. Elderly parents live with us, please check urgently.', category: 'lift', priority: 'urgent', status: 'in_progress', assigned_to_id: 2, assigned_to_name: 'Md. Karim Uddin', created_at: iso(2), resolved_at: null },
  { id: 4, flat_id: 13, flat_no: '2A', building_name: 'Shanti Neer', reported_by_id: 10, reported_by_name: 'Ayesha Siddiqua', title: 'Low gas pressure in the morning', description: 'Gas burner flame is very low between 7am and 10am.', category: 'gas', priority: 'medium', status: 'open', assigned_to_id: null, assigned_to_name: null, created_at: iso(5), resolved_at: null },
  { id: 5, flat_id: 3, flat_no: '3A', building_name: 'Rahman Villa', reported_by_id: 5, reported_by_name: 'Farhana Akter', title: 'Damp patch on bedroom wall', description: 'Seepage on the north wall after the rain, paint is peeling.', category: 'painting', priority: 'low', status: 'resolved', assigned_to_id: 2, assigned_to_name: 'Md. Karim Uddin', created_at: iso(20), resolved_at: iso(12) },
  { id: 6, flat_id: 8, flat_no: '5B', building_name: 'Rahman Villa', reported_by_id: 7, reported_by_name: 'Shirin Sultana', title: 'Bathroom flush broken', description: 'The flush handle broke off, water keeps running.', category: 'plumbing', priority: 'high', status: 'resolved', assigned_to_id: 2, assigned_to_name: 'Md. Karim Uddin', created_at: iso(9), resolved_at: iso(8) },
]

/** Short excerpts standing in for the RAG knowledge base in mock mode. */
export const knowledge: { title: string; keywords: string[]; text: string }[] = [
  { title: 'House Rules — Rahman Villa', keywords: ['guest', 'visitor', 'night', 'gate', 'rule', 'noise'], text: 'The main gate is locked at 11:30 PM. Guests staying overnight must be registered with the caretaker (Karim, 01819-205577) with their NID. Loud music is not allowed after 10:30 PM.' },
  { title: 'House Rules — Rahman Villa', keywords: ['garbage', 'waste', 'trash', 'dustbin'], text: 'Garbage is collected from each floor daily at 9:00 AM. Keep the bag outside your door before 9 AM. Do not leave garbage on the stairs.' },
  { title: 'House Rules — Rahman Villa', keywords: ['pet', 'cat', 'dog'], text: 'Cats and small caged birds are allowed. Dogs need written permission from the owner. Pets must not be left in common areas.' },
  { title: 'Utility Guide — Electricity & Gas', keywords: ['meter', 'electricity', 'desco', 'prepaid', 'recharge', 'current'], text: 'Each flat has its own DESCO prepaid meter. Recharge via bKash/Nagad (Pay Bill → DESCO) using the 12-digit meter number printed on the meter. If the balance runs out, power cuts until recharged; there is a ৳200 emergency balance.' },
  { title: 'Utility Guide — Electricity & Gas', keywords: ['gas', 'titas', 'burner', 'cylinder'], text: 'Gas is a Titas double-burner line. The monthly gas bill (৳1,080) is included in the service charge. Low pressure in the morning is common in the area; report persistent problems to the caretaker.' },
  { title: 'Tenancy Agreement — Standard Terms', keywords: ['advance', 'deposit', 'refund', 'leave', 'notice', 'move out', 'vacate'], text: 'The advance is two months of basic rent. To vacate, the tenant must give a two-month written notice. The advance is refunded within 7 days of handover, after deducting unpaid dues and damage beyond normal wear.' },
  { title: 'Tenancy Agreement — Standard Terms', keywords: ['rent', 'date', 'deadline', 'late', 'fine', 'pay'], text: 'Rent and service charge must be paid by the 7th of each month via bKash, Nagad, bank transfer or cash against a signed receipt. A late fee of ৳500 applies after the 10th.' },
  { title: 'Premises Rent Control Act 1991 — Summary', keywords: ['law', 'act', 'increase', 'raise', 'legal', 'eviction'], text: 'Under the Premises Rent Control Act 1991, the landlord must give a receipt for every rent payment, cannot demand more than one month of advance without agreement, and rent should not be increased more than once in two years without mutual agreement.' },
  { title: 'Building Facilities', keywords: ['parking', 'car', 'bike', 'generator', 'lift', 'roof', 'water'], text: 'Generator backup covers lights, fans and the lift. Car parking is allotted per flat; motorbikes park on the left side of the ground floor. The rooftop is open 7 AM–9 PM. The water tank is cleaned every 3 months.' },
]
