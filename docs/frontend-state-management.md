# Frontend State Management

## Overview

PyBase uses a **dual-state management strategy** to handle different types of application state efficiently:

1. **TanStack Query (v5.28.0)**: Server state management (API data, caching, synchronization)
2. **Zustand (v4.5.2)**: Client state management (UI state, authentication, preferences)

This separation of concerns provides optimal performance, clear boundaries, and follows React best practices for modern applications.

---

## Table of Contents

- [When to Use Each](#when-to-use-each)
- [TanStack Query (Server State)](#tanstack-query-server-state)
  - [Setup and Configuration](#setup-and-configuration)
  - [Queries Pattern](#queries-pattern)
  - [Mutations Pattern](#mutations-pattern)
  - [Query Invalidation](#query-invalidation)
  - [Advanced Patterns](#advanced-patterns)
- [Zustand (Client State)](#zustand-client-state)
  - [Store Pattern](#store-pattern)
  - [Initialization Pattern](#initialization-pattern)
  - [Usage in Components](#usage-in-components)
  - [Persistence Pattern](#persistence-pattern)
- [Integration Patterns](#integration-patterns)
- [API Integration Patterns](#api-integration-patterns)
  - [API Client Setup](#api-client-setup)
  - [API Service Layer Pattern](#api-service-layer-pattern)
  - [Error Handling Strategies](#error-handling-strategies)
  - [WebSocket Integration](#websocket-integration)
  - [Real-Time Sync Patterns](#real-time-sync-patterns)
  - [Request Retry and Timeout](#request-retry-and-timeout)
- [Best Practices](#best-practices)
- [Anti-Patterns to Avoid](#anti-patterns-to-avoid)

---

## When to Use Each

### Use TanStack Query For:

✅ **Server State** - Data that lives on the backend:
- Fetching data from API endpoints (tables, records, bases, workspaces)
- Creating, updating, deleting resources (mutations)
- Real-time data synchronization
- Data caching and background refetching
- Paginated or infinite scroll data
- Dependent queries (data that depends on other data)

**Examples:**
```typescript
// ✅ Good - Server data
useQuery({ queryKey: ['tables', tableId], queryFn: () => fetchTable(tableId) })
useQuery({ queryKey: ['bases'], queryFn: () => fetchBases() })
useMutation({ mutationFn: (data) => createRecord(tableId, data) })
```

### Use Zustand For:

✅ **Client State** - Data that lives only in the browser:
- Authentication state (user, token)
- UI preferences (theme, sidebar collapsed)
- Modal/dialog open/close state
- Form state (when not using React Hook Form)
- Client-side filters and sorting preferences
- Temporary UI state that doesn't need server persistence

**Examples:**
```typescript
// ✅ Good - Client-only state
const { user, token, isAuthenticated } = useAuthStore()
const { theme, toggleTheme } = useThemeStore()
const { sidebarOpen, toggleSidebar } = useUIStore()
```

### Decision Matrix

| Scenario | Use | Reason |
|----------|-----|--------|
| API data fetching | **TanStack Query** | Automatic caching, refetching, error handling |
| User preferences | **Zustand** | Client-side only, persists to localStorage |
| Authentication state | **Zustand** | Client-side state with localStorage persistence |
| Table/record data | **TanStack Query** | Server data with real-time sync |
| Modal open/close | **Zustand** or `useState` | Temporary UI state |
| Form submission | **TanStack Query** (mutation) | Server interaction |
| Theme/dark mode | **Zustand** | Client preference with persistence |

---

## TanStack Query (Server State)

TanStack Query (formerly React Query) manages server state with built-in caching, automatic refetching, error handling, and optimistic updates.

### Setup and Configuration

#### 1. QueryClient Configuration

```typescript
// lib/queryClient.ts
import { QueryClient } from '@tanstack/react-query'

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,        // 5 minutes - data is fresh for 5min
      cacheTime: 10 * 60 * 1000,       // 10 minutes - cache persists for 10min
      retry: 1,                         // Retry failed requests once
      refetchOnWindowFocus: true,       // Refetch on window focus
      refetchOnReconnect: true,         // Refetch on reconnect
    },
    mutations: {
      retry: 0,                         // Don't retry mutations
    },
  },
})
```

#### 2. Provider Setup

```typescript
// main.tsx
import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import { QueryClientProvider } from "@tanstack/react-query"
import { RouterProvider } from "react-router-dom"
import { queryClient } from "@/lib/queryClient"
import { router } from "@/lib/router"
import "./index.css"

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  </StrictMode>,
)
```

### Queries Pattern

Queries are for **reading data** from the server. They automatically cache results and handle refetching.

#### Basic Query

```typescript
// routes/DashboardPage.tsx
import { useQuery } from "@tanstack/react-query"
import { get } from "@/lib/api"
import type { Workspace, Base } from "@/types"

export default function DashboardPage() {
  // Fetch workspaces
  const { data: workspaces, isLoading: workspacesLoading } = useQuery({
    queryKey: ["workspaces"],
    queryFn: () => get<Workspace[]>("/workspaces"),
  })

  // Fetch bases
  const { data: bases, isLoading: basesLoading } = useQuery({
    queryKey: ["bases"],
    queryFn: () => get<Base[]>("/bases"),
  })

  if (workspacesLoading || basesLoading) {
    return <div className="flex items-center justify-center h-full">Loading...</div>
  }

  return <div>{/* Render workspaces and bases */}</div>
}
```

**Key Concepts:**
- `queryKey`: Unique identifier for caching (array format)
- `queryFn`: Async function that returns data
- `data`: Returned data (undefined until loaded)
- `isLoading`: True during first fetch
- `isFetching`: True during any fetch (including background refetch)
- `error`: Error object if query fails

#### Parameterized Query

```typescript
// routes/TableViewPage.tsx
const { tableId } = useParams<{ tableId: string }>()

// Table query - only runs when tableId exists
const { data: table } = useQuery({
  queryKey: ["tables", tableId],           // Include params in queryKey
  queryFn: () => get<Table>(`/tables/${tableId}`),
  enabled: !!tableId,                      // Conditional execution
})

// Fields query - depends on tableId
const { data: fields } = useQuery({
  queryKey: ["tables", tableId, "fields"],
  queryFn: () => get<Field[]>(`/tables/${tableId}/fields`),
  enabled: !!tableId,
})

// Records query
const { data: records, isLoading: recordsLoading } = useQuery({
  queryKey: ["tables", tableId, "records"],
  queryFn: () => get<any[]>(`/tables/${tableId}/records`),
  enabled: !!tableId,
})
```

**Query Key Best Practices:**
- Use hierarchical keys: `["tables", tableId, "records"]`
- Include all parameters that affect the query
- Consistent ordering: `["resource", id, "nested-resource"]`
- Enables targeted cache invalidation

#### Query with Options

```typescript
const { data, error, isLoading, refetch } = useQuery({
  queryKey: ["user", userId],
  queryFn: () => fetchUser(userId),

  // Configuration options
  enabled: !!userId,                    // Only run if userId exists
  staleTime: 10 * 60 * 1000,           // 10 minutes fresh
  cacheTime: 30 * 60 * 1000,           // 30 minutes in cache
  refetchOnMount: true,                // Refetch on component mount
  refetchOnWindowFocus: false,         // Don't refetch on window focus
  retry: 2,                            // Retry failed requests twice
  onSuccess: (data) => {               // Callback on success
    console.log("User loaded:", data)
  },
  onError: (error) => {                // Callback on error
    console.error("Failed to load user:", error)
  },
})
```

### Mutations Pattern

Mutations are for **writing data** to the server (create, update, delete operations).

#### Basic Mutation

```typescript
// routes/TableViewPage.tsx
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { post, patch } from "@/lib/api"

export default function TableViewPage() {
  const { tableId } = useParams()
  const queryClient = useQueryClient()

  // Create record mutation
  const createRecordMutation = useMutation({
    mutationFn: (data: any) => post(`/tables/${tableId}/records`, data),
    onSuccess: () => {
      // Invalidate and refetch records after creation
      queryClient.invalidateQueries({ queryKey: ["tables", tableId, "records"] })
    },
  })

  // Update record mutation
  const updateRecordMutation = useMutation({
    mutationFn: (variables: { recordId: string; data: any }) =>
      patch(`/records/${variables.recordId}`, variables.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tables", tableId, "records"] })
    },
  })

  // Usage in event handlers
  const handleCellUpdate = (rowId: string, fieldId: string, value: any) => {
    updateRecordMutation.mutate({
      recordId: rowId,
      data: { [fieldId]: value },
    })
  }

  const handleRowAdd = () => {
    createRecordMutation.mutate({})
  }

  return (
    <div>
      <button onClick={handleRowAdd}>Add Row</button>
      {/* Grid with onCellUpdate handler */}
    </div>
  )
}
```

**Mutation Properties:**
- `mutate(variables)`: Trigger mutation
- `mutateAsync(variables)`: Async version (returns promise)
- `isLoading`: True during mutation
- `isSuccess`: True after successful mutation
- `isError`: True if mutation failed
- `error`: Error object if mutation failed

#### Mutation with Optimistic Updates

```typescript
const updateRecordMutation = useMutation({
  mutationFn: ({ recordId, data }: { recordId: string; data: any }) =>
    patch(`/records/${recordId}`, data),

  // Optimistic update - update UI immediately
  onMutate: async (variables) => {
    // Cancel outgoing refetches
    await queryClient.cancelQueries({ queryKey: ["tables", tableId, "records"] })

    // Snapshot previous value
    const previousRecords = queryClient.getQueryData(["tables", tableId, "records"])

    // Optimistically update cache
    queryClient.setQueryData(["tables", tableId, "records"], (old: any[]) =>
      old.map((record) =>
        record.id === variables.recordId
          ? { ...record, ...variables.data }
          : record
      )
    )

    // Return context with snapshot
    return { previousRecords }
  },

  // Rollback on error
  onError: (err, variables, context) => {
    queryClient.setQueryData(
      ["tables", tableId, "records"],
      context?.previousRecords
    )
  },

  // Always refetch after error or success
  onSettled: () => {
    queryClient.invalidateQueries({ queryKey: ["tables", tableId, "records"] })
  },
})
```

### Query Invalidation

Invalidation tells TanStack Query that data is stale and should be refetched.

#### Basic Invalidation

```typescript
const queryClient = useQueryClient()

// Invalidate specific query
queryClient.invalidateQueries({ queryKey: ["tables", tableId, "records"] })

// Invalidate all table queries
queryClient.invalidateQueries({ queryKey: ["tables"] })

// Invalidate all queries
queryClient.invalidateQueries()
```

#### Invalidation with WebSocket

```typescript
// routes/TableViewPage.tsx
import { useWebSocket } from "@/hooks/useWebSocket"
import { useAuthStore } from "@/features/auth/stores/authStore"

export default function TableViewPage() {
  const queryClient = useQueryClient()
  const { token } = useAuthStore()
  const { tableId } = useParams()

  // WebSocket connection
  const { status, send } = useWebSocket({
    url: 'ws://localhost:8000/api/v1/realtime/ws',
    token: token || undefined,
    onMessage: (msg) => {
      console.log('WS Msg:', msg)

      // Invalidate queries when records change
      if (msg.event_type === 'record.created' || msg.event_type === 'record.updated') {
        queryClient.invalidateQueries({ queryKey: ["tables", tableId, "records"] })
      }
    },
  })

  // ... rest of component
}
```

### Advanced Patterns

#### Dependent Queries

```typescript
// First query - get user
const { data: user } = useQuery({
  queryKey: ["user"],
  queryFn: fetchCurrentUser,
})

// Second query - depends on user.workspaceId
const { data: workspace } = useQuery({
  queryKey: ["workspace", user?.workspaceId],
  queryFn: () => fetchWorkspace(user!.workspaceId),
  enabled: !!user?.workspaceId,  // Only run when user has workspaceId
})
```

#### Parallel Queries

```typescript
// Both queries run in parallel
const workspacesQuery = useQuery({
  queryKey: ["workspaces"],
  queryFn: fetchWorkspaces,
})

const basesQuery = useQuery({
  queryKey: ["bases"],
  queryFn: fetchBases,
})

// Or use useQueries for dynamic number of queries
const results = useQueries({
  queries: tableIds.map(id => ({
    queryKey: ["table", id],
    queryFn: () => fetchTable(id),
  })),
})
```

#### Prefetching

```typescript
// Prefetch data before navigating
const handleNavigateToTable = async (tableId: string) => {
  // Prefetch table data
  await queryClient.prefetchQuery({
    queryKey: ["tables", tableId],
    queryFn: () => fetchTable(tableId),
  })

  // Navigate
  navigate(`/tables/${tableId}`)
}
```

---

## Zustand (Client State)

Zustand is a minimal state management library for client-side state that doesn't belong on the server.

### Store Pattern

#### Basic Store Structure

```typescript
// features/auth/stores/authStore.ts
import { create } from "zustand"
import type { User } from "@/types"

interface AuthState {
  // State
  user: User | null
  token: string | null
  isAuthenticated: boolean

  // Actions
  setAuth: (user: User, token: string) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  // Initial state
  user: null,
  token: null,
  isAuthenticated: false,

  // Actions that modify state
  setAuth: (user: User, token: string) => {
    localStorage.setItem("access_token", token)
    localStorage.setItem("user", JSON.stringify(user))
    set({ user, token, isAuthenticated: true })
  },

  logout: () => {
    localStorage.removeItem("access_token")
    localStorage.removeItem("user")
    set({ user: null, token: null, isAuthenticated: false })
  },
}))
```

**Store Pattern Best Practices:**
- Single interface for state + actions
- Use TypeScript for type safety
- Actions use `set()` to update state
- Colocate related state and actions
- Keep stores focused (single responsibility)

### Initialization Pattern

```typescript
// features/auth/stores/authStore.ts (continued)

// Initialize auth state from localStorage on app load
const storedToken = localStorage.getItem("access_token")
const storedUser = localStorage.getItem("user")

if (storedToken && storedUser) {
  useAuthStore.setState({
    token: storedToken,
    user: JSON.parse(storedUser),
    isAuthenticated: true,
  })
}
```

**Initialization Best Practices:**
- Run initialization code after store creation
- Use `useStore.setState()` for direct updates (outside components)
- Handle JSON parsing errors gracefully
- Validate stored data before setting state

### Usage in Components

#### Selective Subscription

```typescript
// features/auth/components/LoginForm.tsx
import { useAuthStore } from "../stores/authStore"

export default function LoginForm() {
  // ✅ GOOD: Subscribe only to what you need
  const setAuth = useAuthStore((state) => state.setAuth)

  // Component only re-renders when setAuth reference changes (never, it's stable)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    try {
      const response = await login({ email, password })
      setAuth(response.user, response.access_token)
      navigate("/dashboard")
    } catch (err: any) {
      setError(err.response?.data?.detail || "Login failed")
    }
  }

  return <form onSubmit={handleSubmit}>...</form>
}
```

#### Multiple Values

```typescript
// Subscribe to multiple values
const { user, isAuthenticated, logout } = useAuthStore((state) => ({
  user: state.user,
  isAuthenticated: state.isAuthenticated,
  logout: state.logout,
}))

// Or with shallow comparison (from zustand/shallow)
import { shallow } from 'zustand/shallow'

const { user, isAuthenticated } = useAuthStore(
  (state) => ({ user: state.user, isAuthenticated: state.isAuthenticated }),
  shallow
)
```

#### Full Store Subscription (Use Sparingly)

```typescript
// ❌ BAD: Component re-renders on ANY state change
const authState = useAuthStore()

// ✅ GOOD: Only when you need everything
const { user, token, isAuthenticated, setAuth, logout } = useAuthStore()
```

### Persistence Pattern

#### Manual Persistence

```typescript
// features/theme/stores/themeStore.ts
import { create } from "zustand"

interface ThemeState {
  theme: "light" | "dark"
  toggleTheme: () => void
  setTheme: (theme: "light" | "dark") => void
}

export const useThemeStore = create<ThemeState>((set) => ({
  theme: (localStorage.getItem("theme") as "light" | "dark") || "light",

  toggleTheme: () => set((state) => {
    const newTheme = state.theme === "light" ? "dark" : "light"
    localStorage.setItem("theme", newTheme)
    document.documentElement.classList.toggle("dark")
    return { theme: newTheme }
  }),

  setTheme: (theme) => {
    localStorage.setItem("theme", theme)
    document.documentElement.classList.toggle("dark", theme === "dark")
    set({ theme })
  },
}))
```

#### Using Zustand Persist Middleware

```typescript
import { create } from "zustand"
import { persist } from "zustand/middleware"

interface PreferencesState {
  sidebarCollapsed: boolean
  gridRowHeight: number
  toggleSidebar: () => void
  setRowHeight: (height: number) => void
}

export const usePreferencesStore = create<PreferencesState>()(
  persist(
    (set) => ({
      sidebarCollapsed: false,
      gridRowHeight: 32,

      toggleSidebar: () => set((state) => ({
        sidebarCollapsed: !state.sidebarCollapsed
      })),

      setRowHeight: (gridRowHeight) => set({ gridRowHeight }),
    }),
    {
      name: "user-preferences", // localStorage key
    }
  )
)
```

---

## Integration Patterns

### Zustand + TanStack Query Integration

Combining both libraries for complex workflows:

```typescript
// features/auth/components/LoginForm.tsx
import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { useMutation } from "@tanstack/react-query"
import { useAuthStore } from "../stores/authStore"
import { login } from "../api/authApi"

export default function LoginForm() {
  const navigate = useNavigate()
  const setAuth = useAuthStore((state) => state.setAuth)  // Zustand
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")

  // TanStack Query mutation for API call
  const loginMutation = useMutation({
    mutationFn: login,
    onSuccess: (response) => {
      // Update Zustand store on success
      setAuth(response.user, response.access_token)
      navigate("/dashboard")
    },
  })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    loginMutation.mutate({ email, password })
  }

  return (
    <form onSubmit={handleSubmit}>
      <Input
        type="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        disabled={loginMutation.isLoading}
      />
      <Input
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        disabled={loginMutation.isLoading}
      />
      {loginMutation.isError && (
        <div className="text-destructive">
          {loginMutation.error?.response?.data?.detail || "Login failed"}
        </div>
      )}
      <Button type="submit" disabled={loginMutation.isLoading}>
        {loginMutation.isLoading ? "Logging in..." : "Login"}
      </Button>
    </form>
  )
}
```

**Pattern Benefits:**
- TanStack Query handles API call, loading, error states
- Zustand stores the resulting client state (user, token)
- Clear separation: server state vs. client state
- Both libraries work together seamlessly

### WebSocket + TanStack Query Invalidation

```typescript
// routes/TableViewPage.tsx
const queryClient = useQueryClient()
const { token } = useAuthStore()  // Zustand for auth token

// WebSocket integration
const { status, send } = useWebSocket({
  url: 'ws://localhost:8000/api/v1/realtime/ws',
  token: token || undefined,
  onMessage: (msg) => {
    // Invalidate TanStack Query cache on WebSocket events
    if (msg.event_type === 'record.created' || msg.event_type === 'record.updated') {
      queryClient.invalidateQueries({ queryKey: ["tables", tableId, "records"] })
    }
  },
})
```

---

## API Integration Patterns

### API Client Setup

PyBase uses a centralized API client (`@/lib/api`) that provides HTTP methods with built-in error handling, authentication, and type safety.

#### Core API Methods

```typescript
// lib/api.ts
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

// Generic request handler with authentication
async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = localStorage.getItem('access_token')

  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...options.headers,
  }

  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }))
    throw new Error(error.detail || `HTTP ${response.status}`)
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return undefined as T
  }

  return response.json()
}

// HTTP method helpers
export const get = <T>(endpoint: string) =>
  request<T>(endpoint, { method: 'GET' })

export const post = <T>(endpoint: string, data?: any) =>
  request<T>(endpoint, {
    method: 'POST',
    body: data ? JSON.stringify(data) : undefined,
  })

export const patch = <T>(endpoint: string, data: any) =>
  request<T>(endpoint, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })

export const del = <T>(endpoint: string) =>
  request<T>(endpoint, { method: 'DELETE' })

export const put = <T>(endpoint: string, data: any) =>
  request<T>(endpoint, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
```

**Key Features:**
- Automatic authentication via Bearer token
- Consistent error handling
- Type-safe responses with generics
- Centralized base URL configuration
- JSON serialization/deserialization

### API Service Layer Pattern

Organize API calls into service modules by feature domain:

#### Feature-Based API Organization

```typescript
// features/auth/api/authApi.ts
import type { LoginRequest, LoginResponse } from "@/types"
import { post } from "@/lib/api"

export async function login(data: LoginRequest): Promise<LoginResponse> {
  return post<LoginResponse>("/auth/login", data)
}

export async function register(data: {
  email: string
  password: string
  name?: string
}): Promise<LoginResponse> {
  return post<LoginResponse>("/auth/register", data)
}

export async function logout(): Promise<void> {
  await post("/auth/logout")
}
```

```typescript
// features/tables/api/tablesApi.ts
import { get, post, patch, del } from "@/lib/api"
import type { Table, TableCreate, TableUpdate } from "@/types"

export async function fetchTables(baseId: string): Promise<Table[]> {
  return get<Table[]>(`/bases/${baseId}/tables`)
}

export async function fetchTable(tableId: string): Promise<Table> {
  return get<Table>(`/tables/${tableId}`)
}

export async function createTable(baseId: string, data: TableCreate): Promise<Table> {
  return post<Table>(`/bases/${baseId}/tables`, data)
}

export async function updateTable(tableId: string, data: TableUpdate): Promise<Table> {
  return patch<Table>(`/tables/${tableId}`, data)
}

export async function deleteTable(tableId: string): Promise<void> {
  return del<void>(`/tables/${tableId}`)
}
```

```typescript
// features/records/api/recordsApi.ts
import { get, post, patch, del } from "@/lib/api"
import type { Record, RecordCreate, RecordUpdate } from "@/types"

export async function fetchRecords(tableId: string): Promise<Record[]> {
  return get<Record[]>(`/tables/${tableId}/records`)
}

export async function fetchRecord(recordId: string): Promise<Record> {
  return get<Record>(`/records/${recordId}`)
}

export async function createRecord(tableId: string, data: RecordCreate): Promise<Record> {
  return post<Record>(`/tables/${tableId}/records`, data)
}

export async function updateRecord(recordId: string, data: RecordUpdate): Promise<Record> {
  return patch<Record>(`/records/${recordId}`, data)
}

export async function deleteRecord(recordId: string): Promise<void> {
  return del<void>(`/records/${recordId}`)
}
```

**Service Layer Best Practices:**
- One file per feature domain (auth, tables, records, fields, etc.)
- Export typed async functions (not classes)
- Use TypeScript generics for type safety
- Descriptive function names (`fetchTable`, `createRecord`, etc.)
- Colocate types with the feature (`@/types` or feature-level types)

### Error Handling Strategies

#### API Error Handling

```typescript
// types/errors.ts
export interface APIError {
  detail: string
  code?: string
  field?: string
}

// lib/api.ts - Enhanced error handling
class APIError extends Error {
  constructor(
    public status: number,
    public detail: string,
    public code?: string,
    public field?: string
  ) {
    super(detail)
    this.name = 'APIError'
  }
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers,
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Request failed' }))
      throw new APIError(
        response.status,
        error.detail || `HTTP ${response.status}`,
        error.code,
        error.field
      )
    }

    if (response.status === 204) {
      return undefined as T
    }

    return response.json()
  } catch (err) {
    if (err instanceof APIError) {
      throw err
    }
    // Network error or other unexpected error
    throw new APIError(0, 'Network error - please check your connection')
  }
}
```

#### Component-Level Error Handling

```typescript
// routes/TableViewPage.tsx
import { useMutation } from "@tanstack/react-query"
import { updateRecord } from "@/features/records/api/recordsApi"
import { toast } from "@/components/ui/use-toast"

export default function TableViewPage() {
  const updateRecordMutation = useMutation({
    mutationFn: ({ recordId, data }: { recordId: string; data: any }) =>
      updateRecord(recordId, data),

    onSuccess: () => {
      toast({
        title: "Success",
        description: "Record updated successfully",
      })
      queryClient.invalidateQueries({ queryKey: ["tables", tableId, "records"] })
    },

    onError: (error: any) => {
      // Handle specific error cases
      if (error.status === 401) {
        toast({
          title: "Authentication Error",
          description: "Please log in again",
          variant: "destructive",
        })
        // Redirect to login
        navigate("/login")
      } else if (error.status === 403) {
        toast({
          title: "Permission Denied",
          description: "You don't have permission to update this record",
          variant: "destructive",
        })
      } else if (error.status === 422 && error.field) {
        toast({
          title: "Validation Error",
          description: `Invalid value for ${error.field}: ${error.detail}`,
          variant: "destructive",
        })
      } else {
        toast({
          title: "Error",
          description: error.detail || "Failed to update record",
          variant: "destructive",
        })
      }
    },
  })

  return <div>...</div>
}
```

#### Global Error Boundary

```typescript
// components/ErrorBoundary.tsx
import { Component, ReactNode } from "react"
import { AlertCircle } from "lucide-react"
import { Button } from "@/components/ui/button"

interface Props {
  children: ReactNode
}

interface State {
  hasError: boolean
  error?: Error
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: any) {
    console.error("ErrorBoundary caught:", error, errorInfo)
    // Log to error tracking service (Sentry, etc.)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex flex-col items-center justify-center h-full p-8">
          <AlertCircle className="w-12 h-12 text-destructive mb-4" />
          <h2 className="text-xl font-semibold mb-2">Something went wrong</h2>
          <p className="text-muted-foreground mb-4">
            {this.state.error?.message || "An unexpected error occurred"}
          </p>
          <Button onClick={() => window.location.reload()}>
            Reload Page
          </Button>
        </div>
      )
    }

    return this.props.children
  }
}
```

### WebSocket Integration

#### Custom WebSocket Hook

PyBase uses a custom `useWebSocket` hook for real-time communication with automatic reconnection and message queuing.

```typescript
// hooks/useWebSocket.ts
import { useEffect, useRef, useState, useCallback, useMemo } from 'react'

type WebSocketStatus = 'connecting' | 'connected' | 'disconnected' | 'error'

interface RecordFieldValue {
  field_id: string
  value: unknown
}

interface WebSocketMessage {
  event_type: string
  data: Record<RecordFieldValue>
}

interface UseWebSocketOptions {
  url: string
  token?: string
  onMessage?: (message: WebSocketMessage) => void
  reconnectInterval?: number
}

const DEFAULT_RECONNECT_INTERVAL = 3000

/**
 * Custom hook for WebSocket connections with automatic reconnection.
 * Features:
 * - Automatic reconnection with exponential backoff
 * - Message queuing when disconnected
 * - Token-based authentication
 * - Type-safe message handling
 */
export const useWebSocket = ({
  url,
  token,
  onMessage,
  reconnectInterval = DEFAULT_RECONNECT_INTERVAL
}: UseWebSocketOptions) => {
  const [status, setStatus] = useState<WebSocketStatus>('disconnected')
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>()
  const messageQueueRef = useRef<WebSocketMessage[]>([])

  const connect = useCallback(() => {
    if (!token) {
      console.warn('Cannot connect WebSocket: no token provided')
      return
    }

    // Build URL with token
    const wsUrl = `${url}?token=${token}`

    try {
      const ws = new WebSocket(wsUrl)

      ws.onopen = () => {
        console.log('WebSocket Connected')
        setStatus('connected')

        // Send queued messages
        while (messageQueueRef.current.length > 0) {
          const msg = messageQueueRef.current.shift()
          if (msg) {
            ws.send(JSON.stringify(msg))
          }
        }
      }

      ws.onclose = () => {
        console.log('WebSocket Disconnected')
        setStatus('disconnected')

        // Attempt reconnect with exponential backoff
        const timeout = Math.min(10000, reconnectInterval * 2)
        reconnectTimeoutRef.current = setTimeout(() => {
          console.log('Attempting reconnect (timeout:', timeout / 1000, 's)...')
          connect()
        }, timeout)
      }

      ws.onerror = (error) => {
        console.error('WebSocket Error:', error)
        setStatus('error')
        ws.close()
      }

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data) as WebSocketMessage
          if (onMessage) {
            onMessage(message)
          }
        } catch (e) {
          console.error('Failed to parse WebSocket message:', e)
        }
      }

      wsRef.current = ws

    } catch (e) {
      console.error('Failed to create WebSocket connection', e)
      setStatus('error')
    }
  }, [url, token, onMessage, reconnectInterval])

  useEffect(() => {
    connect()

    return () => {
      if (wsRef.current) {
        wsRef.current.close()
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
    }
  }, [connect])

  const send = useCallback((event_type: string, data: Record<RecordFieldValue>) => {
    const message: WebSocketMessage = { event_type, data }

    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message))
    } else {
      console.warn('Cannot send message: WebSocket is not open, queueing:', message)
      messageQueueRef.current.push(message)
    }
  }, [])

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
    }
    if (wsRef.current) {
      wsRef.current.close()
    }
  }, [])

  return useMemo(() => ({
    status,
    send,
    disconnect,
  }), [status, send, disconnect])
}
```

**WebSocket Hook Features:**
- **Automatic Reconnection**: Exponential backoff strategy (max 10s)
- **Message Queuing**: Messages sent while disconnected are queued and sent on reconnect
- **Token Authentication**: Passes auth token via query parameter
- **Type Safety**: TypeScript interfaces for messages
- **Status Tracking**: `connecting`, `connected`, `disconnected`, `error`
- **Cleanup**: Proper cleanup on unmount

#### Using WebSocket in Components

```typescript
// routes/TableViewPage.tsx
import { useWebSocket } from "@/hooks/useWebSocket"
import { useAuthStore } from "@/features/auth/stores/authStore"
import { useQueryClient } from "@tanstack/react-query"

export default function TableViewPage() {
  const { tableId } = useParams()
  const queryClient = useQueryClient()
  const token = useAuthStore((state) => state.token)

  // WebSocket connection for real-time updates
  const { status, send } = useWebSocket({
    url: 'ws://localhost:8000/api/v1/realtime/ws',
    token: token || undefined,
    reconnectInterval: 3000,

    onMessage: (message) => {
      console.log('WebSocket message received:', message.event_type)

      // Handle different event types
      switch (message.event_type) {
        case 'record.created':
        case 'record.updated':
        case 'record.deleted':
          // Invalidate records query to refetch data
          queryClient.invalidateQueries({
            queryKey: ["tables", tableId, "records"]
          })
          break

        case 'field.created':
        case 'field.updated':
        case 'field.deleted':
          // Invalidate fields query
          queryClient.invalidateQueries({
            queryKey: ["tables", tableId, "fields"]
          })
          break

        case 'presence.user_joined':
        case 'presence.user_left':
          // Update presence state
          // Handle collaborative cursor/selection updates
          break

        default:
          console.log('Unknown event type:', message.event_type)
      }
    },
  })

  // Show connection status in UI
  const connectionStatus = {
    connecting: { color: 'text-yellow-500', text: 'Connecting...' },
    connected: { color: 'text-green-500', text: 'Live' },
    disconnected: { color: 'text-gray-500', text: 'Offline' },
    error: { color: 'text-red-500', text: 'Error' },
  }[status]

  return (
    <div>
      <div className={`flex items-center gap-2 ${connectionStatus.color}`}>
        <div className="w-2 h-2 rounded-full bg-current" />
        <span className="text-sm">{connectionStatus.text}</span>
      </div>

      {/* Rest of table view */}
    </div>
  )
}
```

#### WebSocket Event Broadcasting

```typescript
// Send updates to other clients
const handleCellUpdate = (rowId: string, fieldId: string, value: any) => {
  // Update via API
  updateRecordMutation.mutate({
    recordId: rowId,
    data: { [fieldId]: value },
  })

  // Broadcast to other clients via WebSocket
  send('record.update', {
    field_id: fieldId,
    value: value,
  })
}
```

### Real-Time Sync Patterns

#### Optimistic Updates + WebSocket Sync

Combine optimistic updates with WebSocket synchronization for best UX:

```typescript
const updateRecordMutation = useMutation({
  mutationFn: ({ recordId, data }: { recordId: string; data: any }) =>
    updateRecord(recordId, data),

  // 1. Optimistic update - instant UI feedback
  onMutate: async (variables) => {
    await queryClient.cancelQueries({ queryKey: ["tables", tableId, "records"] })

    const previousRecords = queryClient.getQueryData(["tables", tableId, "records"])

    queryClient.setQueryData(["tables", tableId, "records"], (old: any[]) =>
      old.map((record) =>
        record.id === variables.recordId
          ? { ...record, ...variables.data }
          : record
      )
    )

    return { previousRecords }
  },

  // 2. Rollback on error
  onError: (err, variables, context) => {
    queryClient.setQueryData(
      ["tables", tableId, "records"],
      context?.previousRecords
    )

    toast({
      title: "Update Failed",
      description: "Your changes could not be saved",
      variant: "destructive",
    })
  },

  // 3. WebSocket will trigger refetch for all clients (including this one)
  // No need to invalidate here - let WebSocket handle sync
})

// WebSocket handler will refetch for everyone
onMessage: (msg) => {
  if (msg.event_type === 'record.updated') {
    queryClient.invalidateQueries({ queryKey: ["tables", tableId, "records"] })
  }
}
```

**Benefits:**
- Instant UI feedback (optimistic update)
- Error recovery (rollback on failure)
- Multi-client sync (WebSocket broadcast)
- Eventually consistent across all clients

### Request Retry and Timeout

```typescript
// lib/api.ts - Enhanced with retry and timeout
async function request<T>(
  endpoint: string,
  options: RequestInit = {},
  retries = 1,
  timeout = 30000
): Promise<T> {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), timeout)

  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers,
      signal: controller.signal,
    })

    clearTimeout(timeoutId)

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Request failed' }))

      // Retry on 5xx errors
      if (response.status >= 500 && retries > 0) {
        console.log(`Retrying request (${retries} attempts left)...`)
        await new Promise(resolve => setTimeout(resolve, 1000))
        return request<T>(endpoint, options, retries - 1, timeout)
      }

      throw new APIError(
        response.status,
        error.detail || `HTTP ${response.status}`,
        error.code,
        error.field
      )
    }

    if (response.status === 204) {
      return undefined as T
    }

    return response.json()
  } catch (err) {
    clearTimeout(timeoutId)

    if (err instanceof APIError) {
      throw err
    }

    if (err.name === 'AbortError') {
      throw new APIError(0, 'Request timeout - please try again')
    }

    throw new APIError(0, 'Network error - please check your connection')
  }
}
```

---

## Best Practices

### General Principles

1. **Separate Server and Client State**
   - Use TanStack Query for server data
   - Use Zustand for client-only data
   - Don't duplicate server data in Zustand

2. **Consistent Query Keys**
   ```typescript
   // ✅ GOOD: Hierarchical, predictable
   ["tables", tableId, "records"]
   ["bases", baseId]
   ["workspaces"]

   // ❌ BAD: Flat, unpredictable
   ["tableRecords", tableId]
   ["base-" + baseId]
   ```

3. **Selective Subscriptions**
   ```typescript
   // ✅ GOOD: Only subscribe to what you need
   const setAuth = useAuthStore((state) => state.setAuth)

   // ❌ BAD: Subscribe to entire store
   const authStore = useAuthStore()
   ```

4. **Type Everything**
   ```typescript
   // ✅ GOOD: Full type safety
   const { data: table } = useQuery({
     queryKey: ["tables", tableId],
     queryFn: () => get<Table>(`/tables/${tableId}`),
   })

   // ❌ BAD: No types
   const { data } = useQuery({
     queryKey: ["tables", tableId],
     queryFn: () => get(`/tables/${tableId}`),
   })
   ```

### TanStack Query Best Practices

1. **Use Query Keys Wisely**
   - Include all variables that affect the query
   - Use consistent structure across the app
   - Enable targeted invalidation

2. **Enable/Disable Queries Conditionally**
   ```typescript
   const { data } = useQuery({
     queryKey: ["table", tableId],
     queryFn: () => fetchTable(tableId!),
     enabled: !!tableId,  // Don't run if tableId is undefined
   })
   ```

3. **Handle Loading and Error States**
   ```typescript
   const { data, isLoading, error } = useQuery(...)

   if (isLoading) return <Spinner />
   if (error) return <Error message={error.message} />
   return <DataView data={data} />
   ```

4. **Invalidate Strategically**
   ```typescript
   // After mutation, invalidate affected queries
   onSuccess: () => {
     queryClient.invalidateQueries({ queryKey: ["tables", tableId, "records"] })
   }
   ```

5. **Use Optimistic Updates for Better UX**
   - Update UI immediately
   - Rollback on error
   - Refetch to ensure consistency

### Zustand Best Practices

1. **Keep Stores Focused**
   - One store per domain (auth, theme, UI preferences)
   - Don't create a single giant store

2. **Use Selectors**
   ```typescript
   // ✅ GOOD: Component only re-renders when setAuth changes
   const setAuth = useAuthStore((state) => state.setAuth)

   // ❌ BAD: Component re-renders on any auth state change
   const { setAuth } = useAuthStore()
   ```

3. **Persist Carefully**
   - Only persist what's necessary (token, preferences)
   - Don't persist sensitive data without encryption
   - Handle hydration errors gracefully

4. **Actions Over Direct Mutation**
   ```typescript
   // ✅ GOOD: Use action
   const { logout } = useAuthStore()
   logout()

   // ❌ BAD: Direct setState (outside components)
   useAuthStore.setState({ user: null, token: null })
   ```

---

## Anti-Patterns to Avoid

### ❌ Don't Duplicate Server State in Zustand

```typescript
// ❌ BAD: Storing API data in Zustand
const useDataStore = create((set) => ({
  tables: [],
  setTables: (tables) => set({ tables }),
}))

// Fetch data and store in Zustand
const data = await fetchTables()
setTables(data)

// ✅ GOOD: Use TanStack Query for server data
const { data: tables } = useQuery({
  queryKey: ["tables"],
  queryFn: fetchTables,
})
```

### ❌ Don't Use useState for Server Data

```typescript
// ❌ BAD: Managing server data with useState
const [tables, setTables] = useState([])
const [loading, setLoading] = useState(false)

useEffect(() => {
  setLoading(true)
  fetchTables().then(data => {
    setTables(data)
    setLoading(false)
  })
}, [])

// ✅ GOOD: Use TanStack Query
const { data: tables, isLoading } = useQuery({
  queryKey: ["tables"],
  queryFn: fetchTables,
})
```

### ❌ Don't Over-Invalidate

```typescript
// ❌ BAD: Invalidating everything
onSuccess: () => {
  queryClient.invalidateQueries()  // Refetches ALL queries!
}

// ✅ GOOD: Targeted invalidation
onSuccess: () => {
  queryClient.invalidateQueries({ queryKey: ["tables", tableId, "records"] })
}
```

### ❌ Don't Ignore Error Handling

```typescript
// ❌ BAD: No error handling
const { data } = useQuery({ queryKey: ["data"], queryFn: fetchData })
return <div>{data.value}</div>  // Crashes if error occurs

// ✅ GOOD: Handle all states
const { data, isLoading, error } = useQuery({
  queryKey: ["data"],
  queryFn: fetchData
})

if (isLoading) return <Spinner />
if (error) return <ErrorMessage error={error} />
if (!data) return null

return <div>{data.value}</div>
```

### ❌ Don't Forget Query Keys

```typescript
// ❌ BAD: Static query key for dynamic data
const { data } = useQuery({
  queryKey: ["table"],  // Same key for all tables!
  queryFn: () => fetchTable(tableId),
})

// ✅ GOOD: Include parameters in query key
const { data } = useQuery({
  queryKey: ["table", tableId],  // Unique key per table
  queryFn: () => fetchTable(tableId),
})
```

---

## Summary

### Quick Reference

| Task | Solution | Example |
|------|----------|---------|
| Fetch data from API | `useQuery` | `useQuery({ queryKey: ["tables"], queryFn: fetchTables })` |
| Create/update/delete | `useMutation` | `useMutation({ mutationFn: createRecord })` |
| Store auth state | Zustand | `useAuthStore((s) => s.user)` |
| Store UI preferences | Zustand + persist | `usePreferencesStore((s) => s.theme)` |
| Invalidate after mutation | `queryClient.invalidateQueries` | `queryClient.invalidateQueries({ queryKey: ["tables"] })` |
| Real-time sync | WebSocket + invalidate | `onMessage: () => queryClient.invalidateQueries(...)` |

### Key Takeaways

1. **TanStack Query** = Server state (API data, caching, sync)
2. **Zustand** = Client state (auth, UI, preferences)
3. **Never duplicate** server data in Zustand
4. **Use selectors** to prevent unnecessary re-renders
5. **Type everything** for safety and developer experience
6. **Invalidate strategically** after mutations
7. **Handle loading and errors** for better UX

---

*For more patterns and examples, see:*
- [Frontend Architecture](./frontend-architecture.md)
- [Component Patterns](./frontend-component-patterns.md)
- [TanStack Query Docs](https://tanstack.com/query/latest)
- [Zustand Docs](https://docs.pmnd.rs/zustand)
