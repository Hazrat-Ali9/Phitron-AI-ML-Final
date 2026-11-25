# BariBhara — Frontend
# 
React UI for BariBhara, the AI rent and building manager for Dhaka landlords.

**Stack:** React 19 · TypeScript · Vite · Tailwind CSS v4 · TanStack Query · React Router

## Screens

| Role | Pages |
|---|---|
| Owner (`admin`) | Dashboard · Buildings · Flats · Tenants & leases · Rent ledger · Maintenance board · AI assistant |
| Caretaker (`staff`) | Dashboard · Flats (read-only) · Maintenance board · AI assistant |
| Tenant | My home (dues + payment history) · My requests · AI assistant |

The AI assistant keeps the conversation (multi-turn) and shows which **tools** the agent used and which **document sources** (RAG) it answered from.

## Run locally

```bash
cd frontend
cp .env.example .env          # set VITE_API_URL to your backend
npm install
npm run dev                   # http://localhost:5173
```

### Mock mode (no backend needed)

Set `VITE_API_MOCK=true` in `.env`. Every request is then served by an in-memory mock (`src/lib/mock/`) with realistic demo data. It applies the same role and error rules as the real API.

| Demo login | Email | Password |
|---|---|---|
| Owner | rahman@baribhara.app | admin123 |
| Caretaker | karim@baribhara.app | staff123 |
| Tenant | tanvir.hasan@gmail.com | tenant123 |

The mock code is loaded only when mock mode is on, so it is not bundled in a normal build.

## API

Every endpoint, payload and status code the UI uses is documented in [API_CONTRACT.md](./API_CONTRACT.md).

## Scripts

| Command | What it does |
|---|---|
| `npm run dev` | dev server |
| `npm run build` | type-check + production build to `dist/` |
| `npm run lint` | oxlint |
| `npm run preview` | serve the production build |

## Deploy

This is a static SPA. It works on Vercel (`vercel.json`), Netlify (`public/_redirects`) or a Render Static Site with root directory `frontend`, build command `npm ci && npm run build` and publish directory `dist`. Set `VITE_API_URL` to the live backend URL.
