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

## TypeScript Types and Conventions

### TypeScript Configuration

PyBase uses strict TypeScript configuration for maximum type safety and developer experience:

```typescript
// tsconfig.json
{
  "compilerOptions": {
    "target": "ES2020",                    // Modern JavaScript features
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",                    // ESM module system
    "moduleResolution": "bundler",         // Vite-optimized resolution
    "jsx": "react-jsx",                    // Automatic React imports

    // Strict Type Checking
    "strict": true,                        // Enable all strict options
    "noUnusedLocals": true,               // Error on unused variables
    "noUnusedParameters": true,           // Error on unused parameters
    "noFallthroughCasesInSwitch": true,  // Prevent switch fallthrough bugs

    // Module Resolution
    "resolveJsonModule": true,            // Import JSON files
    "allowImportingTsExtensions": true,   // Import .ts files
    "isolatedModules": true,              // Required for Vite
    "skipLibCheck": true,                 // Skip lib type checking
    "noEmit": true,                       // Vite handles compilation

    // Path Aliases (see below)
    "baseUrl": ".",
    "paths": { /* ... */ }
  }
}
```

**Key Configuration Principles:**
- **Strict Mode**: All strict type checking options enabled
- **No Implicit Any**: Every value must have an explicit type
- **Unused Code Detection**: Build fails on unused variables/parameters
- **Modern Target**: ES2020 for optimal browser feature support
- **Vite Integration**: Configuration optimized for Vite bundler

### Path Aliases

TypeScript path aliases provide clean, absolute imports and prevent deeply nested relative paths:

```typescript
// tsconfig.json paths configuration
{
  "baseUrl": ".",
  "paths": {
    // Primary @ alias for src root
    "@/*": ["./src/*"],
    "@/components/*": ["./src/components/*"],
    "@/lib/*": ["./src/lib/*"],
    "@/hooks/*": ["./src/hooks/*"],
    "@/stores/*": ["./src/stores/*"],
    "@/utils/*": ["./src/utils/*"],
    "@/features/*": ["./src/features/*"],
    "@/types/*": ["./src/types/*"],

    // Alternative ~ alias for types and components
    "~/types/*": ["./src/types/*"],
    "~/components/*": ["./src/components/*"],
    "~/features/*": ["./src/features/*"]
  }
}
```

**Usage Examples:**
```typescript
// ❌ Avoid: Relative import hell
import { User } from "../../../types"
import { Button } from "../../components/ui/button"

// ✅ Preferred: Clean absolute imports with aliases
import { User } from "@/types"
import { Button } from "@/components/ui/button"

// ✅ Alternative: ~ alias for types
import type { User, Field } from "~/types"
```

**Alias Conventions:**
- **`@/*`**: Primary alias for all src imports
- **`~/types/*`**: Alternative alias for type imports (improves readability)
- **`~/components/*`**: Alternative alias for shared components
- **Feature imports**: Always use `@/features/...` for clarity

### Type Organization

All shared types are centralized in `src/types/index.ts` for consistency and reusability:

```typescript
// types/index.ts - Single source of truth for application types

// Base mixins for common fields
export interface Id {
  id: string
}

export interface CreatedAt {
  created_at: string
}

export interface UpdatedAt {
  updated_at: string
}

// Domain entities using interface composition
export interface User extends Id, CreatedAt, UpdatedAt {
  email: string
  name?: string
  username?: string
}

export interface Workspace extends Id, CreatedAt, UpdatedAt {
  name: string
  description?: string
  created_by_id: string
}

export interface Base extends Id, CreatedAt, UpdatedAt {
  workspace_id: string
  name: string
  description?: string
  created_by_id: string
}

export interface Table extends Id, CreatedAt, UpdatedAt {
  base_id: string
  name: string
  description?: string
  created_by_id: string
  icon?: string
}

export interface Field extends Id, CreatedAt, UpdatedAt {
  table_id: string
  name: string
  type: FieldType
  options?: FieldOptions
  description?: string
  required?: boolean
}

export interface Record extends Id, CreatedAt, UpdatedAt {
  table_id: string
  values: Record<string, unknown>
}
```

**Type Organization Principles:**
1. **Interface Composition**: Use mixins (Id, CreatedAt, UpdatedAt) for shared fields
2. **Single Export**: All shared types exported from `types/index.ts`
3. **Domain Grouping**: Related types grouped together in file
4. **Feature-Specific Types**: Keep in feature directory if not shared
5. **API Types**: Request/response types defined alongside entity types

### Union Types and Discriminated Unions

TypeScript union types provide type-safe field type handling:

```typescript
// Discriminated union for field types
export type FieldType =
  | "text"
  | "long_text"
  | "number"
  | "checkbox"
  | "single_select"
  | "multi_select"
  | "date"
  | "datetime"
  | "duration"
  | "linked_record"
  | "lookup"
  | "rollup"
  | "formula"
  | "autonumber"
  | "attachment"
  | "url"
  | "email"
  | "phone"
  | "currency"
  | "percent"
  | "rating"
  | "status"

// View type discriminated union
export interface ViewType {
  type: "grid" | "kanban" | "calendar" | "gallery" | "form" | "gantt" | "timeline"
}
```

**Usage Pattern:**
```typescript
// Type narrowing with discriminated unions
function renderFieldEditor(field: Field) {
  switch (field.type) {
    case "text":
    case "long_text":
      return <TextCellEditor {...props} />
    case "number":
    case "currency":
    case "percent":
      return <NumberCellEditor {...props} />
    case "single_select":
    case "multi_select":
      return <SelectCellEditor {...props} />
    // TypeScript ensures all cases handled
  }
}
```

### Type-Safe Field Options Pattern

Field options use discriminated unions for type safety:

```typescript
// Specific option types for each field category
export interface SelectFieldOptions {
  choices?: Array<{ id: string; name: string; color?: string }>
}

export interface NumberFieldOptions {
  precision?: number
  format?: string
  currency?: string
}

export interface DateFieldOptions {
  dateFormat?: string
  timeFormat?: string
  includeTime?: boolean
}

export interface LinkedRecordFieldOptions {
  linkedTableId?: string
  viewIdForRecordSelection?: string
  isReversed?: boolean
}

export interface FormulaFieldOptions {
  formula?: string
  resultType?: "text" | "number" | "date" | "boolean"
}

export interface LookupFieldOptions {
  recordLinkFieldId?: string
  fieldIdInLinkedTable?: string
  rollupFunction?: string
}

// Union type for all field options
export type FieldOptions =
  | SelectFieldOptions
  | NumberFieldOptions
  | DateFieldOptions
  | LinkedRecordFieldOptions
  | FormulaFieldOptions
  | LookupFieldOptions
  | Record<string, unknown>  // Fallback for unknown field types
```

**Type Safety Benefits:**
- **Autocomplete**: IDE suggests correct options based on field type
- **Type Checking**: Prevents invalid option combinations
- **Refactoring**: Type errors highlight breaking changes
- **Documentation**: Types serve as inline documentation

### API Request/Response Types

Request and response types ensure type-safe API integration:

```typescript
// Authentication API types
export interface LoginRequest {
  email: string
  password: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
  user: User
}

export interface RegisterRequest {
  email: string
  password: string
  name?: string
}

export interface RegisterResponse {
  user: User
  access_token: string
}
```

**API Type Conventions:**
- **Suffix**: Request types end with `Request`, responses with `Response`
- **Reuse**: Reference domain types (User, Table, etc.) for consistency
- **Validation**: Pair with Zod schemas for runtime validation
- **Generics**: Use TypeScript generics for reusable API patterns

### Generic Type Patterns

Leverage TypeScript generics for reusable, type-safe code:

```typescript
// Generic API client
async function post<T>(endpoint: string, data: unknown): Promise<T> {
  const response = await axios.post(endpoint, data)
  return response.data
}

// Usage with type inference
const user = await post<User>("/users", userData)  // user: User

// Generic component props
interface CellEditorProps<T> {
  value: T
  onChange: (value: T) => void
  onBlur: () => void
}

// Type-safe cell editor
const TextCellEditor: React.FC<CellEditorProps<string>> = ({ value, onChange }) => {
  // value is guaranteed to be string
}
```

### Type Conventions Summary

**Naming Conventions:**
- **Interfaces**: PascalCase (User, TableField, LoginRequest)
- **Types**: PascalCase for unions (FieldType, ViewType)
- **Enums**: PascalCase with UPPER_CASE values (avoid in favor of union types)

**Import/Export Patterns:**
```typescript
// ✅ Preferred: Import types explicitly
import type { User, Field } from "@/types"
import { useState } from "react"

// ✅ Acceptable: Mixed import with type keyword
import { type User, type Field, createUser } from "@/types"

// ❌ Avoid: Importing types without 'type' keyword (runtime overhead)
import { User, Field } from "@/types"
```

**Optional vs Required Fields:**
- **Required**: Core entity fields (id, name, created_at)
- **Optional**: User-configurable fields (description?, icon?)
- **Nullable**: Use `field: Type | null` for explicit null values
- **Undefined**: Use `field?: Type` for optional/missing values

**Type vs Interface:**
- **Interface**: For object shapes, domain entities (User, Table)
- **Type**: For unions, primitives, complex types (FieldType)
- **Composition**: Interfaces support `extends`, types use intersection `&`

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
