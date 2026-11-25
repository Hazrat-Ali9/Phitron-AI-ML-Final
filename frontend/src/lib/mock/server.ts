/**
 * In-memory mock of the BariBhara backend, used when VITE_API_MOCK=true.
 * It follows the same rules the real API should: roles, 401/403/404/409/422.
 * Data resets on page reload.
 */
import { ApiError } from '@/lib/api/client'
import type {
  Building,
  ChatRequest,
  ChatResponse,
  Flat,
  Lease,
  MaintenanceRequest,
  Payment,
  PaymentStatus,
  Role,
  User,
} from '@/lib/types'
import * as db from './data'

interface Ctx {
  query: Record<string, string>
  body: unknown
  token: string | null
}

const delay = (ms: number) => new Promise((r) => setTimeout(r, ms))
const nextId = (rows: { id: number }[]) => Math.max(0, ...rows.map((r) => r.id)) + 1
const publicUser = ({ password: _pw, ...u }: db.MockUser): User => u

function currentUser(ctx: Ctx): db.MockUser {
  const id = Number(ctx.token?.replace('mock.', ''))
  const user = db.users.find((u) => u.id === id)
  if (!user) throw new ApiError(401, 'Could not validate credentials')
  return user
}

function requireRole(user: db.MockUser, ...roles: Role[]) {
  if (!roles.includes(user.role)) throw new ApiError(403, 'You do not have permission to do this')
}

function required(body: Record<string, unknown>, ...fields: string[]) {
  const fieldErrors: Record<string, string> = {}
  for (const f of fields) if (body[f] === undefined || body[f] === null || body[f] === '') fieldErrors[f] = 'Field required'
  if (Object.keys(fieldErrors).length) {
    const [field] = Object.keys(fieldErrors)
    throw new ApiError(422, `${field}: Field required`, fieldErrors)
  }
}

function find<T extends { id: number }>(rows: T[], id: number, label: string): T {
  const row = rows.find((r) => r.id === id)
  if (!row) throw new ApiError(404, `${label} not found`)
  return row
}

function activeLeaseOf(userId: number) {
  return db.leases.find((l) => l.tenant_id === userId && l.is_active)
}

const includes = (hay: string | null | undefined, needle?: string) => !needle || (hay ?? '').toLowerCase().includes(needle.toLowerCase())

function paymentStatus(due: number, paid: number): PaymentStatus {
  return paid <= 0 ? 'due' : paid < due ? 'partial' : 'paid'
}

type Handler = (ctx: Ctx, params: string[]) => unknown
const routes: [string, RegExp, Handler][] = []
const route = (method: string, pattern: string, handler: Handler) =>
  routes.push([method, new RegExp(`^${pattern.replace(/:id/g, '(\\d+)')}$`), handler])

/* ---------------------------------- auth ---------------------------------- */

route('POST', '/auth/login', ({ body }) => {
  const { email, password } = body as { email?: string; password?: string }
  const user = db.users.find((u) => u.email.toLowerCase() === email?.toLowerCase())
  if (!user || user.password !== password) throw new ApiError(401, 'Incorrect email or password')
  return { access_token: `mock.${user.id}`, token_type: 'bearer', expires_in: 3600 }
})

route('POST', '/auth/register', ({ body }) => {
  const b = body as Record<string, string>
  required(b, 'full_name', 'email', 'password')
  if (b.password.length < 8) throw new ApiError(422, 'password: must be at least 8 characters', { password: 'Must be at least 8 characters' })
  if (db.users.some((u) => u.email.toLowerCase() === b.email.toLowerCase())) throw new ApiError(409, 'An account with this email already exists')
  const user: db.MockUser = {
    id: nextId(db.users),
    full_name: b.full_name,
    email: b.email,
    phone: b.phone || null,
    password: b.password,
    role: 'tenant',
    is_active: true,
    created_at: new Date().toISOString(),
  }
  db.users.push(user)
  return publicUser(user)
})

route('GET', '/auth/me', (ctx) => publicUser(currentUser(ctx)))

route('GET', '/users', (ctx) => {
  requireRole(currentUser(ctx), 'admin', 'staff')
  return db.users
    .filter((u) => !ctx.query.role || u.role === ctx.query.role)
    .filter((u) => includes(`${u.full_name} ${u.email} ${u.phone}`, ctx.query.q))
    .map(publicUser)
})

/* -------------------------------- buildings -------------------------------- */

route('GET', '/buildings', (ctx) => {
  currentUser(ctx)
  return db.buildings.filter((b) => includes(`${b.name} ${b.address}`, ctx.query.q) && includes(b.area, ctx.query.area))
})

route('POST', '/buildings', (ctx) => {
  requireRole(currentUser(ctx), 'admin')
  const b = ctx.body as Record<string, unknown>
  required(b, 'name', 'address', 'area', 'total_floors')
  if (db.buildings.some((x) => x.name.toLowerCase() === String(b.name).toLowerCase())) throw new ApiError(409, 'A building with this name already exists')
  const building = { ...(b as Omit<Building, 'id' | 'created_at'>), id: nextId(db.buildings), created_at: new Date().toISOString() }
  db.buildings.push(building)
  return building
})

route('PATCH', '/buildings/:id', (ctx, [id]) => {
  requireRole(currentUser(ctx), 'admin')
  const building = find(db.buildings, +id, 'Building')
  Object.assign(building, ctx.body)
  for (const f of db.flats.filter((x) => x.building_id === building.id)) Object.assign(f, { building_name: building.name, area: building.area })
  return building
})

route('DELETE', '/buildings/:id', (ctx, [id]) => {
  requireRole(currentUser(ctx), 'admin')
  find(db.buildings, +id, 'Building')
  if (db.flats.some((f) => f.building_id === +id)) throw new ApiError(409, 'Remove the flats in this building first')
  db.buildings.splice(db.buildings.findIndex((b) => b.id === +id), 1)
})

/* ---------------------------------- flats ---------------------------------- */

route('GET', '/flats', (ctx) => {
  currentUser(ctx)
  const q = ctx.query
  return db.flats.filter(
    (f) =>
      includes(`${f.flat_no} ${f.building_name} ${f.area} ${f.description ?? ''}`, q.q) &&
      (!q.building_id || f.building_id === +q.building_id) &&
      includes(f.area, q.area) &&
      (!q.status || f.status === q.status) &&
      (!q.bedrooms || f.bedrooms === +q.bedrooms) &&
      (!q.max_rent || f.monthly_rent <= +q.max_rent),
  )
})

route('GET', '/flats/:id', (ctx, [id]) => {
  currentUser(ctx)
  return find(db.flats, +id, 'Flat')
})

function checkFlatUnique(buildingId: number, flatNo: string, exceptId?: number) {
  if (db.flats.some((f) => f.building_id === buildingId && f.flat_no.toLowerCase() === flatNo.toLowerCase() && f.id !== exceptId)) {
    throw new ApiError(409, `Flat ${flatNo} already exists in this building`)
  }
}

route('POST', '/flats', (ctx) => {
  requireRole(currentUser(ctx), 'admin')
  const b = ctx.body as Partial<Flat>
  required(b as Record<string, unknown>, 'building_id', 'flat_no', 'floor', 'bedrooms', 'monthly_rent')
  const building = find(db.buildings, Number(b.building_id), 'Building')
  checkFlatUnique(building.id, b.flat_no!)
  const flat = { status: 'vacant', description: null, service_charge: 0, bathrooms: 1, size_sqft: 0, ...b, id: nextId(db.flats), building_name: building.name, area: building.area } as Flat
  db.flats.push(flat)
  return flat
})

route('PATCH', '/flats/:id', (ctx, [id]) => {
  requireRole(currentUser(ctx), 'admin')
  const flat = find(db.flats, +id, 'Flat')
  const b = ctx.body as Partial<Flat>
  const buildingId = Number(b.building_id ?? flat.building_id)
  const building = find(db.buildings, buildingId, 'Building')
  if (b.flat_no || b.building_id) checkFlatUnique(buildingId, b.flat_no ?? flat.flat_no, flat.id)
  Object.assign(flat, b, { building_name: building.name, area: building.area })
  return flat
})

route('DELETE', '/flats/:id', (ctx, [id]) => {
  requireRole(currentUser(ctx), 'admin')
  find(db.flats, +id, 'Flat')
  if (db.leases.some((l) => l.flat_id === +id && l.is_active)) throw new ApiError(409, 'This flat has an active lease')
  db.flats.splice(db.flats.findIndex((f) => f.id === +id), 1)
})

/* ---------------------------------- leases --------------------------------- */

route('GET', '/leases', (ctx) => {
  const user = currentUser(ctx)
  const q = ctx.query
  return db.leases
    .filter((l) => user.role !== 'tenant' || l.tenant_id === user.id)
    .filter((l) => includes(`${l.tenant_name} ${l.tenant_phone} ${l.flat_no} ${l.building_name}`, q.q))
    .filter((l) => q.is_active === undefined || String(l.is_active) === q.is_active)
})

function syncFlatStatus(flatId: number) {
  const flat = db.flats.find((f) => f.id === flatId)
  if (!flat || flat.status === 'maintenance') return
  flat.status = db.leases.some((l) => l.flat_id === flatId && l.is_active) ? 'occupied' : 'vacant'
}

route('POST', '/leases', (ctx) => {
  requireRole(currentUser(ctx), 'admin')
  const b = ctx.body as Partial<Lease>
  required(b as Record<string, unknown>, 'flat_id', 'tenant_id', 'start_date', 'monthly_rent', 'nid_number')
  const flat = find(db.flats, Number(b.flat_id), 'Flat')
  const tenant = find(db.users, Number(b.tenant_id), 'Tenant')
  if (tenant.role !== 'tenant') throw new ApiError(422, 'tenant_id: user is not a tenant', { tenant_id: 'User is not a tenant' })
  if ((b.is_active ?? true) && db.leases.some((l) => l.flat_id === flat.id && l.is_active)) throw new ApiError(409, `Flat ${flat.flat_no} already has an active lease`)
  const lease = {
    end_date: null, advance_amount: 0, family_members: 1, is_active: true,
    ...b,
    id: nextId(db.leases), tenant_name: tenant.full_name, tenant_phone: tenant.phone, flat_no: flat.flat_no, building_name: flat.building_name,
  } as Lease
  db.leases.push(lease)
  syncFlatStatus(flat.id)
  return lease
})

route('PATCH', '/leases/:id', (ctx, [id]) => {
  requireRole(currentUser(ctx), 'admin')
  const lease = find(db.leases, +id, 'Lease')
  const prevFlat = lease.flat_id
  Object.assign(lease, ctx.body)
  const flat = find(db.flats, lease.flat_id, 'Flat')
  const tenant = find(db.users, lease.tenant_id, 'Tenant')
  Object.assign(lease, { flat_no: flat.flat_no, building_name: flat.building_name, tenant_name: tenant.full_name, tenant_phone: tenant.phone })
  syncFlatStatus(prevFlat)
  syncFlatStatus(lease.flat_id)
  return lease
})

route('DELETE', '/leases/:id', (ctx, [id]) => {
  requireRole(currentUser(ctx), 'admin')
  const lease = find(db.leases, +id, 'Lease')
  db.leases.splice(db.leases.indexOf(lease), 1)
  syncFlatStatus(lease.flat_id)
})

/* --------------------------------- payments -------------------------------- */

route('GET', '/payments', (ctx) => {
  const user = currentUser(ctx)
  const q = ctx.query
  const own = new Set(db.leases.filter((l) => l.tenant_id === user.id).map((l) => l.id))
  return db.payments
    .filter((p) => user.role !== 'tenant' || own.has(p.lease_id))
    .filter((p) => (!q.month || p.month === q.month) && (!q.status || p.status === q.status) && (!q.lease_id || p.lease_id === +q.lease_id))
    .sort((a, b) => b.month.localeCompare(a.month) || a.building_name.localeCompare(b.building_name) || a.flat_no.localeCompare(b.flat_no))
})

route('POST', '/payments', (ctx) => {
  requireRole(currentUser(ctx), 'admin')
  const b = ctx.body as Partial<Payment>
  required(b as Record<string, unknown>, 'lease_id', 'month', 'amount_due')
  const lease = find(db.leases, Number(b.lease_id), 'Lease')
  if (db.payments.some((p) => p.lease_id === lease.id && p.month === b.month)) throw new ApiError(409, `A rent record for ${b.month} already exists for this lease`)
  const amount_paid = Number(b.amount_paid ?? 0)
  const payment = {
    method: null, trx_id: null, paid_at: null,
    ...b,
    amount_paid,
    id: nextId(db.payments), tenant_name: lease.tenant_name, flat_no: lease.flat_no, building_name: lease.building_name,
    status: paymentStatus(Number(b.amount_due), amount_paid),
  } as Payment
  db.payments.push(payment)
  return payment
})

route('PATCH', '/payments/:id', (ctx, [id]) => {
  requireRole(currentUser(ctx), 'admin')
  const payment = find(db.payments, +id, 'Payment')
  Object.assign(payment, ctx.body)
  payment.status = paymentStatus(payment.amount_due, payment.amount_paid)
  return payment
})

route('DELETE', '/payments/:id', (ctx, [id]) => {
  requireRole(currentUser(ctx), 'admin')
  db.payments.splice(db.payments.indexOf(find(db.payments, +id, 'Payment')), 1)
})

/* -------------------------------- maintenance ------------------------------- */

route('GET', '/maintenance', (ctx) => {
  const user = currentUser(ctx)
  const q = ctx.query
  return db.maintenance
    .filter((m) => user.role !== 'tenant' || m.reported_by_id === user.id)
    .filter((m) => (!q.status || m.status === q.status) && (!q.category || m.category === q.category))
    .sort((a, b) => b.created_at.localeCompare(a.created_at))
})

function createMaintenance(user: db.MockUser, b: Partial<MaintenanceRequest>) {
  required(b as Record<string, unknown>, 'title', 'description', 'category')
  let flatId = b.flat_id
  if (user.role === 'tenant') {
    const lease = activeLeaseOf(user.id)
    if (!lease) throw new ApiError(403, 'You do not have an active lease')
    flatId = lease.flat_id
  }
  if (!flatId) throw new ApiError(422, 'flat_id: Field required', { flat_id: 'Field required' })
  const flat = find(db.flats, Number(flatId), 'Flat')
  const req = {
    priority: 'medium',
    ...b,
    id: nextId(db.maintenance), flat_id: flat.id, flat_no: flat.flat_no, building_name: flat.building_name,
    reported_by_id: user.id, reported_by_name: user.full_name, status: 'open',
    assigned_to_id: null, assigned_to_name: null, created_at: new Date().toISOString(), resolved_at: null,
  } as MaintenanceRequest
  db.maintenance.push(req)
  return req
}

route('POST', '/maintenance', (ctx) => createMaintenance(currentUser(ctx), ctx.body as Partial<MaintenanceRequest>))

route('PATCH', '/maintenance/:id', (ctx, [id]) => {
  requireRole(currentUser(ctx), 'admin', 'staff')
  const req = find(db.maintenance, +id, 'Maintenance request')
  const b = ctx.body as Partial<MaintenanceRequest>
  Object.assign(req, b)
  if (b.assigned_to_id !== undefined) req.assigned_to_name = db.users.find((u) => u.id === b.assigned_to_id)?.full_name ?? null
  if (b.status) req.resolved_at = b.status === 'resolved' ? new Date().toISOString() : null
  return req
})

route('DELETE', '/maintenance/:id', (ctx, [id]) => {
  requireRole(currentUser(ctx), 'admin')
  db.maintenance.splice(db.maintenance.indexOf(find(db.maintenance, +id, 'Maintenance request')), 1)
})

/* ----------------------------------- chat ---------------------------------- */

route('POST', '/chat', (ctx) => mockChat(currentUser(ctx), ctx.body as ChatRequest))

const taka = (n: number) => `৳${n.toLocaleString('en-IN')}`

function mockChat(user: db.MockUser, { message }: ChatRequest): ChatResponse {
  const text = message.toLowerCase()
  const has = (...words: string[]) => words.some((w) => text.includes(w))

  if (has('vacant', 'khali', 'খালি', 'to-let', 'to let', 'available flat', 'empty flat')) {
    const area = db.buildings.map((b) => b.area).find((a) => text.includes(a.toLowerCase()))
    const maxRent = Number(text.match(/(\d{2,3})\s*(k|000|হাজার)/)?.[1] ?? 0) * 1000 || undefined
    const beds = Number(text.match(/(\d)\s*(bed|room|রুম)/)?.[1]) || undefined
    const args = { area, max_rent: maxRent, bedrooms: beds }
    const found = db.flats.filter((f) => f.status === 'vacant' && (!area || f.area === area) && (!maxRent || f.monthly_rent <= maxRent) && (!beds || f.bedrooms === beds))
    const reply = found.length
      ? `I found ${found.length} vacant flat${found.length > 1 ? 's' : ''}:\n\n${found
          .map((f) => `- **${f.building_name} ${f.flat_no}** (${f.area}) — ${f.bedrooms} bed, ${f.size_sqft} sqft, ${taka(f.monthly_rent)} + ${taka(f.service_charge)} service charge`)
          .join('\n')}\n\nCall the caretaker on 01819-205577 to arrange a visit.`
      : 'There are no vacant flats matching that right now.'
    return { reply, tool_calls: [{ name: 'list_vacant_flats', arguments: clean(args) }], sources: [] }
  }

  if (user.role === 'admin' && has('collection', 'collected', 'summary', 'kemon', 'আদায়')) {
    const month = new Date().toISOString().slice(0, 7)
    const rows = db.payments.filter((p) => p.month === month)
    const collected = rows.reduce((s, p) => s + p.amount_paid, 0)
    const due = rows.reduce((s, p) => s + p.amount_due - p.amount_paid, 0)
    const pending = rows.filter((p) => p.status !== 'paid')
    return {
      reply: `This month you have collected **${taka(collected)}** and **${taka(due)}** is still outstanding.\n\nPending:\n${pending.map((p) => `- ${p.tenant_name} (${p.building_name} ${p.flat_no}) — ${taka(p.amount_due - p.amount_paid)} ${p.status}`).join('\n')}`,
      tool_calls: [{ name: 'get_collection_summary', arguments: { month } }],
      sources: [],
    }
  }

  if (has('due', 'owe', 'baki', 'বাকি', 'ভাড়া', 'bhara', 'my rent', 'paid')) {
    if (user.role !== 'tenant') return { reply: 'Rent dues are shown per tenant. Open the Rent ledger page, or ask me for "this month\'s collection summary".', tool_calls: [], sources: [] }
    const lease = activeLeaseOf(user.id)
    const rows = db.payments.filter((p) => p.lease_id === lease?.id).sort((a, b) => b.month.localeCompare(a.month))
    const unpaid = rows.filter((p) => p.status !== 'paid')
    const total = unpaid.reduce((s, p) => s + p.amount_due - p.amount_paid, 0)
    const reply = unpaid.length
      ? `You have **${taka(total)}** outstanding:\n\n${unpaid.map((p) => `- ${p.month}: paid ${taka(p.amount_paid)} of ${taka(p.amount_due)}`).join('\n')}\n\nRent is due by the 7th; a ৳500 late fee applies after the 10th.`
      : `You're all paid up 🎉 Your last payment was ${taka(rows[0]?.amount_paid ?? 0)} for ${rows[0]?.month}.`
    return { reply, tool_calls: [{ name: 'get_my_rent_status', arguments: {} }], sources: [] }
  }

  const repairWords: Record<string, MaintenanceRequest['category']> = {
    leak: 'plumbing', tap: 'plumbing', flush: 'plumbing', pipe: 'plumbing', water: 'plumbing',
    light: 'electrical', fan: 'electrical', switch: 'electrical', socket: 'electrical',
    lift: 'lift', gas: 'gas', paint: 'painting', wall: 'painting',
  }
  if (user.role === 'tenant' && has('broken', 'not working', 'leak', 'repair', 'fix', 'kaj kore na', 'নষ্ট')) {
    const category = Object.entries(repairWords).find(([w]) => text.includes(w))?.[1] ?? 'other'
    const title = message.length > 60 ? `${message.slice(0, 57)}…` : message
    const req = createMaintenance(user, { title, description: message, category, priority: has('urgent', 'emergency') ? 'urgent' : 'medium' })
    return {
      reply: `I've logged a **${category}** request (#${req.id}) for flat ${req.flat_no}, ${req.building_name}. The caretaker will be notified; you can track it under **My requests**.`,
      tool_calls: [{ name: 'create_maintenance_request', arguments: { category, description: message } }],
      sources: [],
    }
  }

  const hits = db.knowledge
    .map((k) => ({ k, score: k.keywords.filter((w) => text.includes(w)).length }))
    .filter((h) => h.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, 2)
  if (hits.length) {
    return {
      reply: hits.map((h) => h.k.text).join('\n\n'),
      tool_calls: [{ name: 'search_knowledge', arguments: { query: message } }],
      sources: hits.map((h) => ({ title: h.k.title, snippet: h.k.text.slice(0, 140) + '…', score: Math.min(0.95, 0.62 + h.score * 0.1) })),
    }
  }

  return {
    reply: "I couldn't find anything about that in the building's documents. Please contact the caretaker (01819-205577) or the owner for help.",
    tool_calls: [{ name: 'search_knowledge', arguments: { query: message } }],
    sources: [],
  }
}

function clean(obj: Record<string, unknown>) {
  return Object.fromEntries(Object.entries(obj).filter(([, v]) => v !== undefined))
}

/* --------------------------------- dispatch -------------------------------- */

export async function mockRequest<T>(method: string, path: string, ctx: Ctx): Promise<T> {
  await delay(method === 'POST' && path === '/chat' ? 700 : 200)
  for (const [m, re, handler] of routes) {
    const match = m === method && path.match(re)
    if (match) return structuredClone(handler(ctx, match.slice(1)) ?? null) as T
  }
  throw new ApiError(404, `Not found: ${method} ${path}`)
}
