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
