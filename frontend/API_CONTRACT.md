# BariBhara — API contract used by the frontend

This is what the React app sends and expects. Build the backend to match it, or
change `src/lib/types.ts` and `src/lib/api/endpoints.ts` if you decide on a different shape.

- Base URL: `${VITE_API_URL}/api/v1`
- Auth: `Authorization: Bearer <access_token>` on every request except login/register
- Request and response bodies: JSON
- List endpoints return a **plain JSON array**. Empty or missing query params mean "no filter".
- Dates: `YYYY-MM-DD`. Datetimes: ISO 8601. Months: `YYYY-MM`. Money: whole taka (integer).

## Errors

The UI reads any of these shapes, so FastAPI's defaults work:

```json
{ "detail": "Flat not found" }
{ "detail": [{ "loc": ["body", "flat_no"], "msg": "Field required" }] }
{ "error": { "code": "conflict", "message": "Flat 2A already exists in this building" } }
```

| Status | When | UI behaviour |
|---|---|---|
| 201 | created | success toast |
| 204 | deleted | success toast |
| 401 | missing, invalid or expired token; wrong login | logs the user out (or shows the login error) |
| 403 | wrong role | shows the message in a toast |
| 404 | missing record | shows the message in a toast |
| 409 | duplicate (email, flat_no in a building, active lease on a flat, rent record for a month) | shows the message in a toast |
| 422 | validation | marks the field in the form |

The login error must be identical for a wrong email and a wrong password.

## Roles

| Role | Shown in UI as | Can |
|---|---|---|
| `admin` | Owner | everything |
| `staff` | Caretaker | read flats; list users; read and update maintenance; chat |
| `tenant` | Tenant | read **own** lease, payments and requests; create own requests; chat |

## Auth

| Method | Path | Body | Response |
|---|---|---|---|
| POST | `/auth/register` | `{full_name, email, phone, password}` (password ≥ 8) | `201 User` (role = `tenant`) |
| POST | `/auth/login` | `{email, password}` | `{access_token, token_type: "bearer", expires_in?}` |
| GET | `/auth/me` | – | `User` |

`User = {id, full_name, email, phone, role, is_active, created_at}`

| Method | Path | Query | Roles |
|---|---|---|---|
| GET | `/users` | `role`, `q` | admin, staff |

## Buildings (writes: admin)

`Building = {id, name, address, area, total_floors, created_at}`

| Method | Path | Notes |
|---|---|---|
| GET | `/buildings?q=&area=` | `q` searches name and address |
| POST | `/buildings` | `{name, address, area, total_floors}` → 201 |
| PATCH | `/buildings/{id}` | partial |
| DELETE | `/buildings/{id}` | 409 if the building still has flats |

## Flats (writes: admin) — main domain table

`Flat = {id, building_id, building_name, area, flat_no, floor, bedrooms, bathrooms, size_sqft, monthly_rent, service_charge, status, description}`
`status ∈ vacant | occupied | maintenance`

| Method | Path | Notes |
|---|---|---|
| GET | `/flats?q=&building_id=&area=&status=&bedrooms=&max_rent=` | `q` searches flat_no, building and description |
| GET | `/flats/{id}` | |
| POST | `/flats` | 409 if `flat_no` already exists in the building |
| PATCH | `/flats/{id}` | partial |
| DELETE | `/flats/{id}` | 409 if the flat has an active lease |

## Leases (writes: admin)

`Lease = {id, flat_id, tenant_id, tenant_name, tenant_phone, flat_no, building_name, start_date, end_date, monthly_rent, advance_amount, nid_number, family_members, is_active}`

| Method | Path | Notes |
|---|---|---|
| GET | `/leases?q=&is_active=` | tenants only get their own |
| POST | `/leases` | 409 if the flat already has an active lease; sets flat → `occupied` |
| PATCH | `/leases/{id}` | "End lease" sends `{is_active: false, end_date}`; flat → `vacant` |
| DELETE | `/leases/{id}` | |

## Rent payments (writes: admin)

`Payment = {id, lease_id, tenant_name, flat_no, building_name, month, amount_due, amount_paid, method, trx_id, paid_at, status}`
`method ∈ bkash | nagad | cash | bank | null`. `status ∈ paid | partial | due` is **computed by the backend** from the amounts.

| Method | Path | Notes |
|---|---|---|
| GET | `/payments?month=&status=&lease_id=` | tenants only get their own |
| POST | `/payments` | `{lease_id, month, amount_due, amount_paid, method, trx_id, paid_at}`; 409 if a record for that lease+month exists |
| PATCH | `/payments/{id}` | "Record payment" sends `{amount_paid, method, trx_id, paid_at}` |
| DELETE | `/payments/{id}` | |

## Maintenance requests

`MaintenanceRequest = {id, flat_id, flat_no, building_name, reported_by_id, reported_by_name, title, description, category, priority, status, assigned_to_id, assigned_to_name, created_at, resolved_at}`
`category ∈ plumbing | electrical | gas | lift | painting | other`
`priority ∈ low | medium | high | urgent`
`status ∈ open | in_progress | resolved`

| Method | Path | Roles | Notes |
|---|---|---|---|
| GET | `/maintenance?status=&category=` | all | tenants only get their own |
| POST | `/maintenance` | all | `{title, description, category, priority, flat_id?}`; for tenants the backend uses their active lease's flat |
| PATCH | `/maintenance/{id}` | admin, staff | `{status?, priority?, assigned_to_id?}`; set `resolved_at` when resolved |
| DELETE | `/maintenance/{id}` | admin | |

## Chat (AI agent)

`POST /chat`

```json
// request — history holds the previous turns (multi-turn), oldest first
{
  "message": "How much rent do I owe?",
  "history": [
    { "role": "user", "content": "Hi" },
    { "role": "assistant", "content": "Hello! How can I help?" }
  ]
}

// response
{
  "reply": "You have **৳24,000** outstanding for November 2026…",
  "tool_calls": [{ "name": "get_my_rent_status", "arguments": {} }],
  "sources": [{ "title": "Tenancy Agreement — Standard Terms", "snippet": "Rent … by the 7th…", "score": 0.82 }]
}
```

- `reply` may contain Markdown (bold, lists).
- `tool_calls` lists the tools the model used. The UI shows them as chips. Known names get a friendly label:
  `get_my_rent_status`, `list_vacant_flats`, `create_maintenance_request`, `get_collection_summary`, `search_knowledge`.
- `sources` lists the RAG chunks used. Send `[]` when nothing relevant was found, and make the reply say so.

## CORS

Allow the frontend origin, e.g. `http://localhost:5173` and your deployed frontend URL.
