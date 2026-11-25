/* oxlint-disable react/only-export-components -- route table, not a component module */
import { lazy } from 'react'
import { createBrowserRouter } from 'react-router-dom'
import { AppLayout } from '@/components/layout/app-layout'
import { HomeRedirect, RequireAuth, RequireRole } from '@/components/layout/guards'
import type { Role } from '@/lib/types'
import LoginPage from '@/pages/login'
import RegisterPage from '@/pages/register'

const DashboardPage = lazy(() => import('@/pages/dashboard'))
const BuildingsPage = lazy(() => import('@/pages/buildings'))
const FlatsPage = lazy(() => import('@/pages/flats'))
const TenantsPage = lazy(() => import('@/pages/tenants'))
const RentPage = lazy(() => import('@/pages/rent'))
const MaintenancePage = lazy(() => import('@/pages/maintenance'))
const TenantHomePage = lazy(() => import('@/pages/tenant-home'))
const MyRequestsPage = lazy(() => import('@/pages/my-requests'))
const AssistantPage = lazy(() => import('@/pages/assistant'))

const ALL: Role[] = ['admin', 'staff', 'tenant']
const MANAGERS: Role[] = ['admin', 'staff']
const ADMIN: Role[] = ['admin']

export const router = createBrowserRouter([
  { path: '/login', element: <LoginPage /> },
  { path: '/register', element: <RegisterPage /> },
  {
    element: <RequireAuth />,
    children: [
      {
        element: <AppLayout />,
        children: [
          { index: true, element: <HomeRedirect /> },
          { path: 'dashboard', element: <RequireRole roles={MANAGERS}><DashboardPage /></RequireRole> },
          { path: 'buildings', element: <RequireRole roles={ADMIN}><BuildingsPage /></RequireRole> },
          { path: 'flats', element: <RequireRole roles={MANAGERS}><FlatsPage /></RequireRole> },
          { path: 'tenants', element: <RequireRole roles={ADMIN}><TenantsPage /></RequireRole> },
          { path: 'rent', element: <RequireRole roles={ADMIN}><RentPage /></RequireRole> },
          { path: 'maintenance', element: <RequireRole roles={MANAGERS}><MaintenancePage /></RequireRole> },
          { path: 'home', element: <RequireRole roles={['tenant']}><TenantHomePage /></RequireRole> },
          { path: 'my-requests', element: <RequireRole roles={['tenant']}><MyRequestsPage /></RequireRole> },
          { path: 'assistant', element: <RequireRole roles={ALL}><AssistantPage /></RequireRole> },
          { path: '*', element: <HomeRedirect /> },
        ],
      },
    ],
  },
])
