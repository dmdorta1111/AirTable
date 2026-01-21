# Frontend Architecture

## Architectural Overview
PyBase frontend follows a feature-based architecture with centralized state management, optimized for real-time collaboration and complex data visualization. Built with React 18 and TypeScript, it emphasizes type safety, component reusability, and developer experience.

## Technology Stack

### Core Framework
- **React**: 18.3.1 with React Router DOM for navigation
- **TypeScript**: 5.2.2 with strict mode enabled
- **Vite**: 5.1.6 for fast development and optimized production builds
- **Build Tool**: ESLint with TypeScript support, strict linting rules

### State Management
- **Zustand**: 4.5.2 for client state (auth, UI state)
- **TanStack Query**: 5.28.0 for server state management and caching
- **Recoil**: 0.7.7 for atomic state management (alternative to Zustand)

### UI & Styling
- **Tailwind CSS**: 3.4.1 utility-first CSS framework
- **shadcn/ui**: Radix UI-based component library
- **Radix UI**: Headless UI primitives for accessibility
- **Lucide React**: 0.363.0 icon library
- **class-variance-authority**: 0.7.0 for component variant management
- **tailwind-merge**: 2.6.0 for conflict-free className merging

### Data Handling
- **TanStack Table**: 8.13.0 for advanced table/grid functionality
- **React Hook Form**: 7.51.0 with Zod validation
- **date-fns**: 3.6.0 for date manipulation
- **Zod**: 3.22.4 for runtime type validation
- **Axios**: 1.13.2 for HTTP requests

### Specialized Features
- **@dnd-kit**: 6.1.0+ for drag-and-drop functionality (Kanban, reordering)
- **Recharts**: 2.12.2 for data visualization
- **WebSocket API**: Native browser WebSocket for real-time updates

### Testing
- **Vitest**: 1.4.0 for unit and integration testing
- **Playwright**: 1.42.1 for end-to-end testing

## Feature-Based Architecture

The frontend is organized by feature domains rather than technical layers, promoting modularity and scalability:

```
frontend/src/
├── features/               # Feature modules (domain-driven)
│   └── auth/              # Authentication feature
│       ├── api/           # API calls specific to auth
│       │   └── authApi.ts
│       ├── components/    # Auth-specific components
│       │   ├── LoginForm.tsx
│       │   └── RegisterForm.tsx
│       └── stores/        # Auth state management
│           └── authStore.ts
│
├── components/            # Shared/generic components
│   ├── ui/               # shadcn/ui components (button, input, etc.)
│   ├── layout/           # Layout components (Header, Sidebar)
│   ├── fields/           # Field type editors (TextCellEditor, etc.)
│   └── views/            # View implementations (GridView, Kanban, etc.)
│
├── common/               # Cross-cutting concerns
│   └── search/          # Global search functionality
│
├── hooks/               # Shared React hooks
│   └── useWebSocket.ts # WebSocket connection management
│
├── routes/              # Page-level components
│   ├── DashboardPage.tsx
│   ├── TableViewPage.tsx
│   └── LoginPage.tsx
│
├── types/               # TypeScript type definitions
│   └── index.ts        # Shared types (User, Base, Table, etc.)
│
├── lib/                # Utility libraries (queryClient, router)
├── utils/              # Helper functions
├── App.tsx             # Root component
└── main.tsx            # Application entry point
```

## State Management Patterns

### 1. Server State (TanStack Query)
Used for API data fetching, caching, and synchronization:

```typescript
// Example: Fetching and caching table data
const { data, isLoading, error } = useQuery({
  queryKey: ['table', tableId],
  queryFn: () => fetchTable(tableId)
})
```

**Key Features:**
- Automatic caching and background refetching
- Optimistic updates for better UX
- Request deduplication
- Integrated with WebSocket for real-time invalidation

### 2. Client State (Zustand)
Used for UI state and client-side data (e.g., authentication):

```typescript
// features/auth/stores/authStore.ts
interface AuthState {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  setAuth: (user: User, token: string) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: null,
  isAuthenticated: false,
  setAuth: (user, token) => {
    localStorage.setItem("access_token", token)
    set({ user, token, isAuthenticated: true })
  },
  logout: () => {
    localStorage.removeItem("access_token")
    set({ user: null, token: null, isAuthenticated: false })
  }
}))
```

**Benefits:**
- Minimal boilerplate
- Simple API with hooks
- Persists to localStorage where needed
- No provider wrapping required

## Component Patterns

### 1. Feature-Scoped Components
Components are organized within feature directories with their related logic:

```typescript
// features/auth/components/LoginForm.tsx
export default function LoginForm() {
  const setAuth = useAuthStore((state) => state.setAuth)
  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    const response = await login({ email, password })
    setAuth(response.user, response.access_token)
    navigate("/dashboard")
  }

  return <Card>...</Card>
}
```

### 2. Reusable UI Components (shadcn/ui)
Atomic, accessible components from shadcn/ui library:

```typescript
// components/ui/button.tsx
import { cva, type VariantProps } from "class-variance-authority"

const buttonVariants = cva(
  "inline-flex items-center justify-center rounded-md text-sm font-medium",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground hover:bg-primary/90",
        destructive: "bg-destructive text-destructive-foreground",
        outline: "border border-input bg-background hover:bg-accent",
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-9 rounded-md px-3",
        lg: "h-11 rounded-md px-8",
      }
    }
  }
)
```

### 3. Field Editors Pattern
Specialized components for editing different field types:

```typescript
// components/fields/TextCellEditor.tsx
interface TextCellEditorProps {
  value: string
  onChange: (value: string) => void
  onBlur: () => void
}

export const TextCellEditor: React.FC<TextCellEditorProps> = ({
  value,
  onChange,
  onBlur
}) => {
  return (
    <Input
      value={value}
      onChange={(e) => onChange(e.target.value)}
      onBlur={onBlur}
      autoFocus
    />
  )
}
```

**Field Types Implemented:**
- TextCellEditor (text, long_text)
- NumberCellEditor (number, currency, percent)
- DateCellEditor (date, datetime)
- SelectCellEditor (single_select, multi_select)
- CheckboxCellEditor (checkbox, boolean)
- LinkCellEditor (linked_record)
- AttachmentCellEditor (file attachments)

### 4. View Components Pattern
Complex view implementations using TanStack Table:

```typescript
// components/views/GridView.tsx
export const GridView: React.FC<GridViewProps> = ({
  data,
  fields,
  onCellUpdate
}) => {
  // Generate columns from field definitions
  const columns = React.useMemo<ColumnDef<any>[]>(() => {
    return fields.map((field) => ({
      accessorKey: field.name,
      id: field.id,
      header: field.name,
      cell: EditableCell,
      meta: {
        type: field.type,
        options: field.options,
      },
    }))
  }, [fields])

  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
    meta: {
      updateData: onCellUpdate
    }
  })

  return <Table>...</Table>
}
```

**View Types Implemented:**
- GridView: Spreadsheet-like table with inline editing
- KanbanView: Card-based task board with drag-and-drop
- CalendarView: Date-based event calendar
- GalleryView: Image/card gallery layout
- FormView: Single-record form view
- GanttView: Project timeline visualization
- TimelineView: Chronological event display

## API Integration Patterns

### 1. Feature-Based API Modules
API functions are colocated with features:

```typescript
// features/auth/api/authApi.ts
import { post } from "@/lib/api"

export async function login(data: LoginRequest): Promise<LoginResponse> {
  return post<LoginResponse>("/auth/login", data)
}

export async function register(data: RegisterRequest): Promise<LoginResponse> {
  return post<LoginResponse>("/auth/register", data)
}
```

### 2. Type-Safe API Client
Axios-based client with TypeScript generics:

```typescript
// lib/api.ts (inferred pattern)
export async function post<T>(endpoint: string, data: any): Promise<T> {
  const response = await axios.post(endpoint, data)
  return response.data
}
```

### 3. TanStack Query Integration
API calls wrapped in React Query hooks for caching and state management:

```typescript
const { data: user, isLoading } = useQuery({
  queryKey: ['currentUser'],
  queryFn: () => getCurrentUser(),
  staleTime: 5 * 60 * 1000 // 5 minutes
})
```

## Real-time Communication

### WebSocket Hook Pattern
Custom hook for WebSocket management with automatic reconnection:

```typescript
// hooks/useWebSocket.ts
export const useWebSocket = ({
  url,
  token,
  onMessage,
  reconnectInterval = 3000
}: UseWebSocketOptions) => {
  const [status, setStatus] = useState<WebSocketStatus>('disconnected')
  const wsRef = useRef<WebSocket | null>(null)

  const connect = useCallback(() => {
    const wsUrl = `${url}?token=${token}`
    const ws = new WebSocket(wsUrl)

    ws.onopen = () => setStatus('connected')
    ws.onclose = () => {
      setStatus('disconnected')
      setTimeout(connect, reconnectInterval)
    }
    ws.onmessage = (event) => {
      const message = JSON.parse(event.data)
      onMessage?.(message)
    }

    wsRef.current = ws
  }, [url, token, onMessage, reconnectInterval])

  return { status, send, disconnect }
}
```

**Real-time Features:**
- Record updates broadcast to all connected clients
- Optimistic UI updates with server reconciliation
- Automatic reconnection with exponential backoff
- Message queuing during disconnection

## Build Configuration

### Vite Configuration
```typescript
// vite.config.ts
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '~types': path.resolve(__dirname, './src/types'),
      '~components': path.resolve(__dirname, './src/components'),
      '~features': path.resolve(__dirname, './src/features'),
    },
  },
})
```

### TypeScript Configuration
- **Strict Mode**: Enabled for maximum type safety
- **Path Aliases**: `@/` for src root, `~/` for specific directories
- **Target**: ES2020 for modern browser support
- **JSX**: `react-jsx` for automatic React imports

### Tailwind Configuration
- **Dark Mode**: Class-based strategy
- **Theme Extension**: Custom CSS variables for colors
- **Animations**: Radix UI-compatible animations
- **Plugins**: tailwindcss-animate for smooth transitions

## Routing Architecture

### React Router Setup
```typescript
// main.tsx
import { RouterProvider } from "react-router-dom"
import { router } from "@/lib/router"

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  </StrictMode>
)
```

**Route Structure:**
- `/login` - Authentication page
- `/register` - User registration
- `/dashboard` - Main workspace dashboard
- `/base/:baseId` - Base detail view
- `/table/:tableId` - Table view with dynamic view types

## Type System

### Shared Type Definitions
Centralized TypeScript types ensure consistency across the application:

```typescript
// types/index.ts
export interface User extends Id, CreatedAt, UpdatedAt {
  email: string
  name?: string
  username?: string
}

export interface Table extends Id, CreatedAt, UpdatedAt {
  base_id: string
  name: string
  description?: string
  icon?: string
}

export interface Field extends Id, CreatedAt, UpdatedAt {
  table_id: string
  name: string
  type: FieldType
  options?: FieldOptions
  required?: boolean
}

export type FieldType =
  | "text" | "long_text" | "number" | "checkbox"
  | "single_select" | "multi_select"
  | "date" | "datetime" | "duration"
  | "linked_record" | "lookup" | "rollup" | "formula"
  | "autonumber" | "attachment"
  | "url" | "email" | "phone"
  | "currency" | "percent" | "rating" | "status"
```

## Performance Optimizations

### 1. Code Splitting
- Route-based lazy loading with React.lazy()
- Dynamic imports for heavy components (Gantt, Timeline)

### 2. Memoization
- React.useMemo for expensive computations (column generation)
- React.useCallback for stable function references
- React.memo for pure component optimization

### 3. Virtual Scrolling
- Implemented in GridView for large datasets
- TanStack Table's built-in virtualization support

### 4. Optimistic Updates
- Immediate UI updates before server confirmation
- Rollback on failure with TanStack Query mutations

### 5. Request Deduplication
- TanStack Query prevents duplicate API calls
- Shared cache across components

## Development Workflow

### Scripts
```bash
npm run dev        # Start development server (Vite HMR)
npm run build      # TypeScript check + Vite production build
npm run lint       # ESLint with TypeScript rules
npm run preview    # Preview production build
npm test           # Run Vitest unit tests
npm run test:e2e   # Run Playwright E2E tests
```

### Environment Variables
```env
# .env.example
VITE_API_BASE_URL=http://localhost:8000
```

### Linting & Type Checking
- **ESLint**: TypeScript-aware linting with React hooks rules
- **TypeScript**: Strict mode with unused variable detection
- **Pre-commit**: Type checking before builds

## Architecture Decisions

### Why Feature-Based Organization?
- **Scalability**: New features don't create merge conflicts
- **Maintainability**: Related code stays together
- **Developer Experience**: Easy to locate and modify feature code
- **Code Splitting**: Natural boundaries for lazy loading

### Why Zustand + TanStack Query?
- **Zustand**: Lightweight, no boilerplate, perfect for UI state
- **TanStack Query**: Industry-standard server state with caching
- **Separation**: Clear distinction between server and client state
- **Performance**: Automatic optimization and deduplication

### Why shadcn/ui?
- **Ownership**: Components copied to codebase, full customization
- **Accessibility**: Built on Radix UI primitives
- **Consistency**: Unified design system with Tailwind
- **Type Safety**: Full TypeScript support

### Why Vite over CRA/Next.js?
- **Speed**: Instant HMR with native ESM
- **Simplicity**: No framework overhead for SPA
- **Performance**: Optimized production builds with Rollup
- **Developer Experience**: Fast startup, instant feedback

## Future Considerations

### Planned Enhancements
- **React Suspense**: Async component loading
- **Web Workers**: Offload heavy computations (CSV export, formula calculations)
- **Service Workers**: Offline support and caching
- **Storybook**: Component documentation and visual testing
- **Component Catalog**: Searchable component library
- **E2E Test Coverage**: Comprehensive Playwright test suite

### Scalability Roadmap
- **Micro-frontends**: Feature modules as independent apps
- **Module Federation**: Share components across deployments
- **State Persistence**: IndexedDB for offline capability
- **Advanced Caching**: Service worker-based API caching
