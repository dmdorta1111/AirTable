# Frontend Component Patterns

## Overview

PyBase frontend follows a structured component organization pattern that emphasizes reusability, accessibility, type safety, and maintainability. This document details the component patterns used throughout the application and provides guidelines for creating new components.

## Related Documentation

For broader context and related topics, see:
- **[Frontend Architecture](./frontend-architecture.md)** - Overall frontend architecture, tech stack, and design decisions
- **[State Management](./frontend-state-management.md)** - TanStack Query and Zustand patterns used within components
- **[Code Standards](./code-standards.md)** - Project-wide coding standards

## Table of Contents
- [Component Organization](#component-organization)
- [Feature-Based Organization](#feature-based-organization)
- [UI Component Pattern (Radix + Tailwind)](#ui-component-pattern-radix--tailwind)
- [Field Editor Components](#field-editor-components)
- [View Components](#view-components)
- [Layout Components](#layout-components)
- [Component Composition Patterns](#component-composition-patterns)
- [Best Practices](#best-practices)

---

## Component Organization

Components are organized into four main categories, each serving a specific purpose:

```
frontend/src/components/
├── ui/                    # Reusable UI primitives (shadcn/ui)
│   ├── button.tsx
│   ├── input.tsx
│   ├── card.tsx
│   ├── select.tsx
│   ├── table.tsx
│   ├── checkbox.tsx
│   ├── badge.tsx
│   ├── label.tsx
│   ├── tooltip.tsx
│   └── dropdown-menu.tsx
│
├── fields/                # Field type cell editors
│   ├── TextCellEditor.tsx
│   ├── NumberCellEditor.tsx
│   ├── DateCellEditor.tsx
│   ├── SelectCellEditor.tsx
│   ├── CheckboxCellEditor.tsx
│   ├── LinkCellEditor.tsx
│   └── AttachmentCellEditor.tsx
│
├── views/                 # View type implementations
│   ├── GridView.tsx
│   ├── KanbanView.tsx
│   ├── CalendarView.tsx
│   ├── GalleryView.tsx
│   ├── FormView.tsx
│   ├── GanttView.tsx
│   └── TimelineView.tsx
│
└── layout/               # Application layout components
    ├── MainLayout.tsx
    ├── Header.tsx
    └── Sidebar.tsx
```

### Component Category Guidelines

| Category | Purpose | When to Use |
|----------|---------|-------------|
| **ui/** | Atomic, reusable UI primitives | Building blocks for all other components |
| **fields/** | Data type-specific cell editors | Inline editing in grid views |
| **views/** | Complex data visualization patterns | Table view type implementations |
| **layout/** | Page structure and navigation | Application shell components |

---

## Feature-Based Organization

### Pattern Overview

Beyond component categorization, PyBase organizes code by **feature modules**. Each feature encapsulates all code related to a specific domain (e.g., authentication, tables, records) in a self-contained directory structure.

This pattern promotes:
- **Colocation:** Related code lives together
- **Modularity:** Features can be developed/tested independently
- **Scalability:** Easy to add new features without cluttering shared directories
- **Clarity:** Clear ownership and boundaries between features

### Feature Module Structure

Features are organized in `frontend/src/features/` with a consistent internal structure:

```
frontend/src/features/
└── auth/                    # Feature: Authentication
    ├── api/                # API layer - backend communication
    │   └── authApi.ts      # API functions (login, register, logout)
    ├── components/         # UI components specific to this feature
    │   └── LoginForm.tsx   # Login form component
    └── stores/             # State management (Zustand stores)
        └── authStore.ts    # Authentication state and actions
```

**Each subdirectory serves a specific purpose:**

| Directory | Purpose | What Goes Here |
|-----------|---------|----------------|
| **api/** | Backend integration | API calls, request/response handlers, type definitions |
| **components/** | Feature UI | React components used exclusively by this feature |
| **stores/** | State management | Zustand stores for feature-specific state |

### API Layer Pattern (`api/`)

The API layer handles all backend communication for a feature. Functions are thin wrappers around the shared API client.

**Pattern:**
```typescript
import { post, get } from "@/lib/api"
import type { RequestType, ResponseType } from "@/types"

export async function operationName(data: RequestType): Promise<ResponseType> {
  return post<ResponseType>("/endpoint", data)
}
```

**Example: `features/auth/api/authApi.ts`**
```typescript
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

**Key Characteristics:**
- **Named exports:** Each API function is a named export
- **Type-safe:** Uses TypeScript generics for request/response types
- **Thin wrappers:** Delegates to shared API client (`@/lib/api`)
- **Async/await:** All functions return Promises
- **No business logic:** Pure API calls only

### Component Layer Pattern (`components/`)

Feature components are UI elements specific to a feature. They integrate with the feature's API and state layers.

**Example: `features/auth/components/LoginForm.tsx`**
```typescript
import { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { login } from "../api/authApi"
import { useAuthStore } from "../stores/authStore"

export default function LoginForm() {
  const navigate = useNavigate()
  const setAuth = useAuthStore((state) => state.setAuth)
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError("")
    setLoading(true)

    try {
      const response = await login({ email, password })
      setAuth(response.user, response.access_token)
      navigate("/dashboard")
    } catch (err: any) {
      setError(err.response?.data?.detail || "Login failed")
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card className="w-full max-w-md">
      <CardHeader>
        <CardTitle>Login to PyBase</CardTitle>
        <CardDescription>Enter your credentials to access your workspace</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              disabled={loading}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="password">Password</Label>
            <Input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              disabled={loading}
            />
          </div>
          {error && <div className="text-sm text-destructive">{error}</div>}
          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? "Logging in..." : "Login"}
          </Button>
        </form>
      </CardContent>
    </Card>
  )
}
```

**Key Characteristics:**
- **Relative imports:** Uses `../api/` and `../stores/` for feature code
- **Absolute imports:** Uses `@/components/ui/` for shared UI primitives
- **State integration:** Consumes Zustand stores from feature's `stores/`
- **API integration:** Calls API functions from feature's `api/`
- **Error handling:** Manages loading, error, and success states
- **Default export:** Components use default exports

### State Layer Pattern (`stores/`)

Feature stores manage client-side state using Zustand. State includes derived data, actions, and persistence logic.

**Example: `features/auth/stores/authStore.ts`**
```typescript
import { create } from "zustand"
import type { User } from "@/types"

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

// Initialize auth state from localStorage
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

**Key Characteristics:**
- **Named export:** Store hook exported as `use[Feature]Store`
- **TypeScript interface:** Explicit state shape with types
- **Actions included:** State mutations defined in store (not separate)
- **Persistence:** Handles localStorage sync when needed
- **Initialization:** Hydrates state from localStorage on load
- **Zustand pattern:** Uses `create()` with functional setState

### When to Create a Feature Module

Create a new feature module when:

1. **Domain-specific logic:** Code serves a distinct business domain
2. **Multiple files:** Feature requires API, components, and/or state
3. **Reusable across routes:** Feature used in multiple pages
4. **Independent state:** Feature manages its own state separate from global state

**Examples of features:**
- `auth/` - User authentication and session management
- `tables/` - Table CRUD operations and metadata
- `records/` - Record operations and inline editing
- `views/` - View configuration and switching
- `fields/` - Field type definitions and editors

**Don't create a feature module for:**
- Single-purpose components (put in `components/`)
- Shared utilities (put in `lib/`)
- Page-specific code (put in `pages/`)
- Global state (put in `stores/`)

### Feature Module Checklist

When creating a new feature module:

- [ ] Create feature directory in `src/features/[feature-name]/`
- [ ] Add `api/` subdirectory for backend integration
- [ ] Add `components/` subdirectory for feature UI
- [ ] Add `stores/` subdirectory if feature needs state
- [ ] Use relative imports within feature (`../api/`, `../stores/`)
- [ ] Use absolute imports for shared code (`@/components/ui/`, `@/lib/`)
- [ ] Export API functions as named exports
- [ ] Export components as default exports
- [ ] Export stores as `use[Feature]Store` hooks
- [ ] Add TypeScript types for all API and state interfaces
- [ ] Document feature purpose in directory README (optional)

### Feature Integration Example

**Route definition using feature components:**
```typescript
// src/App.tsx
import LoginForm from "@/features/auth/components/LoginForm"

const router = createBrowserRouter([
  {
    path: "/login",
    element: <LoginForm />,
  },
])
```

**Using feature state in other components:**
```typescript
// src/components/layout/Header.tsx
import { useAuthStore } from "@/features/auth/stores/authStore"
import { logout } from "@/features/auth/api/authApi"

export default function Header() {
  const user = useAuthStore((state) => state.user)
  const logoutUser = useAuthStore((state) => state.logout)

  const handleLogout = async () => {
    await logout()
    logoutUser()
  }

  return <header>{user?.name} <button onClick={handleLogout}>Logout</button></header>
}
```

---

## UI Component Pattern (Radix + Tailwind)

### Pattern Overview

UI components follow the **shadcn/ui** pattern: Radix UI primitives wrapped with Tailwind CSS styling, using `class-variance-authority` (CVA) for variant management.

**Key Technologies:**
- **Radix UI**: Headless, accessible UI primitives
- **Tailwind CSS**: Utility-first styling
- **CVA**: Type-safe component variants
- **clsx + tailwind-merge**: Conflict-free className composition

### Core Utilities

#### `cn()` Function
All UI components use the `cn()` utility for className merging:

```typescript
import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
```

**Purpose:**
- Merge multiple className strings
- Resolve Tailwind class conflicts (e.g., `px-2` overrides `px-4`)
- Conditional class application

### Pattern Template

```typescript
import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "./button"

const componentVariants = cva(
  "base-classes-here", // Base classes applied to all variants
  {
    variants: {
      variant: {
        default: "variant-specific-classes",
        secondary: "variant-specific-classes",
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-9 px-3",
        lg: "h-11 px-8",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

export interface ComponentProps
  extends React.HTMLAttributes<HTMLElement>,
    VariantProps<typeof componentVariants> {
  asChild?: boolean // Optional Radix Slot pattern
}

const Component = React.forwardRef<HTMLElement, ComponentProps>(
  ({ className, variant, size, ...props }, ref) => {
    return (
      <element
        className={cn(componentVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    )
  }
)
Component.displayName = "Component"

export { Component, componentVariants }
```

### Example: Button Component

```typescript
import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "./button"

const buttonVariants = cva(
  "inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground hover:bg-primary/90",
        destructive: "bg-destructive text-destructive-foreground hover:bg-destructive/90",
        outline: "border border-input bg-background hover:bg-accent hover:text-accent-foreground",
        secondary: "bg-secondary text-secondary-foreground hover:bg-secondary/80",
        ghost: "hover:bg-accent hover:text-accent-foreground",
        link: "text-primary underline-offset-4 hover:underline",
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-9 rounded-md px-3",
        lg: "h-11 rounded-md px-8",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button"
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    )
  }
)
Button.displayName = "Button"

export { Button, buttonVariants }
```

**Usage:**
```typescript
<Button variant="destructive" size="lg">Delete</Button>
<Button variant="outline" asChild>
  <Link to="/settings">Settings</Link>
</Button>
```

### Example: Composite Component (Card)

Components with multiple sub-components export all parts:

```typescript
import * as React from "react"
import { cn } from "./button"

const Card = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn("rounded-lg border bg-card text-card-foreground shadow-sm", className)}
      {...props}
    />
  )
)
Card.displayName = "Card"

const CardHeader = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn("flex flex-col space-y-1.5 p-6", className)} {...props} />
  )
)
CardHeader.displayName = "CardHeader"

const CardTitle = React.forwardRef<HTMLParagraphElement, React.HTMLAttributes<HTMLHeadingElement>>(
  ({ className, ...props }, ref) => (
    <h3
      ref={ref}
      className={cn("text-2xl font-semibold leading-none tracking-tight", className)}
      {...props}
    />
  )
)
CardTitle.displayName = "CardTitle"

const CardContent = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn("p-6 pt-0", className)} {...props} />
  )
)
CardContent.displayName = "CardContent"

export { Card, CardHeader, CardTitle, CardContent }
```

**Usage:**
```typescript
<Card>
  <CardHeader>
    <CardTitle>User Profile</CardTitle>
  </CardHeader>
  <CardContent>
    <p>User details here...</p>
  </CardContent>
</Card>
```

### Example: Radix UI Integration (Select)

Wrapping Radix UI primitives with Tailwind styling:

```typescript
import * as React from "react"
import * as SelectPrimitive from "@radix-ui/react-select"
import { Check, ChevronDown } from "lucide-react"
import { cn } from "./button"

const Select = SelectPrimitive.Root
const SelectGroup = SelectPrimitive.Group
const SelectValue = SelectPrimitive.Value

const SelectTrigger = React.forwardRef<
  React.ElementRef<typeof SelectPrimitive.Trigger>,
  React.ComponentPropsWithoutRef<typeof SelectPrimitive.Trigger>
>(({ className, children, ...props }, ref) => (
  <SelectPrimitive.Trigger
    ref={ref}
    className={cn(
      "flex h-10 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50",
      className
    )}
    {...props}
  >
    {children}
    <SelectPrimitive.Icon asChild>
      <ChevronDown className="h-4 w-4 opacity-50" />
    </SelectPrimitive.Icon>
  </SelectPrimitive.Trigger>
))
SelectTrigger.displayName = SelectPrimitive.Trigger.displayName

const SelectItem = React.forwardRef<
  React.ElementRef<typeof SelectPrimitive.Item>,
  React.ComponentPropsWithoutRef<typeof SelectPrimitive.Item>
>(({ className, children, ...props }, ref) => (
  <SelectPrimitive.Item
    ref={ref}
    className={cn(
      "relative flex w-full cursor-default select-none items-center rounded-sm py-1.5 pl-8 pr-2 text-sm outline-none focus:bg-accent focus:text-accent-foreground data-[disabled]:pointer-events-none data-[disabled]:opacity-50",
      className
    )}
    {...props}
  >
    <span className="absolute left-2 flex h-3.5 w-3.5 items-center justify-center">
      <SelectPrimitive.ItemIndicator>
        <Check className="h-4 w-4" />
      </SelectPrimitive.ItemIndicator>
    </span>
    <SelectPrimitive.ItemText>{children}</SelectPrimitive.ItemText>
  </SelectPrimitive.Item>
))
SelectItem.displayName = SelectPrimitive.Item.displayName

export { Select, SelectGroup, SelectValue, SelectTrigger, SelectItem }
```

**Usage:**
```typescript
<Select>
  <SelectTrigger>
    <SelectValue placeholder="Select a status" />
  </SelectTrigger>
  <SelectContent>
    <SelectItem value="todo">To Do</SelectItem>
    <SelectItem value="in-progress">In Progress</SelectItem>
    <SelectItem value="done">Done</SelectItem>
  </SelectContent>
</Select>
```

### UI Component Checklist

When creating new UI components:

- [ ] Use `React.forwardRef` for ref forwarding
- [ ] Set `displayName` for debugging
- [ ] Implement CVA variants for common variations
- [ ] Use `cn()` for className merging
- [ ] Extend native HTML element props
- [ ] Add TypeScript interfaces with proper generics
- [ ] Include accessibility attributes from Radix
- [ ] Export both component and variants (if using CVA)

---

## Field Editor Components

### Pattern Overview

Field editors are specialized components for inline cell editing in GridView. Each field type has a dedicated editor component that handles:
- Auto-focus on mount
- Value validation and transformation
- Blur event handling for commit
- Type-specific UI rendering

### Common Interface Pattern

All field editors implement a consistent interface:

```typescript
interface FieldEditorProps<T> {
  value: T                        // Current cell value
  onChange: (value: T) => void    // Value change handler
  onBlur?: () => void             // Commit handler (exit edit mode)
  autoFocus?: boolean             // Auto-focus on mount (default: true)
}
```

### Implementation Pattern Template

```typescript
import React, { useEffect, useRef } from 'react';
import { Input } from '@/components/ui/input';

interface FieldEditorProps {
  value: ValueType;
  onChange: (value: ValueType) => void;
  onBlur?: () => void;
  autoFocus?: boolean;
}

export const FieldEditor: React.FC<FieldEditorProps> = ({
  value,
  onChange,
  onBlur,
  autoFocus = true,
}) => {
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-focus on mount
  useEffect(() => {
    if (autoFocus && inputRef.current) {
      inputRef.current.focus();
    }
  }, [autoFocus]);

  // Optional: Value transformation/validation
  const handleChange = (newValue: ValueType) => {
    // Validate or transform value
    onChange(newValue);
  };

  return (
    <Input
      ref={inputRef}
      value={value || ''}
      onChange={(e) => handleChange(e.target.value)}
      onBlur={onBlur}
      className="h-full w-full border-none rounded-none focus-visible:ring-0 px-2 bg-background"
    />
  );
};
```

### Implemented Field Editors

#### 1. TextCellEditor

**Purpose:** Edit text and long_text fields

```typescript
import React, { useEffect, useRef } from 'react';
import { Input } from '@/components/ui/input';

interface TextCellEditorProps {
  value: string;
  onChange: (value: string) => void;
  onBlur?: () => void;
  autoFocus?: boolean;
}

export const TextCellEditor: React.FC<TextCellEditorProps> = ({
  value,
  onChange,
  onBlur,
  autoFocus = true,
}) => {
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (autoFocus && inputRef.current) {
      inputRef.current.focus();
    }
  }, [autoFocus]);

  return (
    <Input
      ref={inputRef}
      value={value || ''}
      onChange={(e) => onChange(e.target.value)}
      onBlur={onBlur}
      className="h-full w-full border-none rounded-none focus-visible:ring-0 px-2 bg-background"
    />
  );
};
```

**Key Features:**
- Simple text input with no validation
- Handles empty/null values gracefully
- Removes border/ring for inline editing appearance

#### 2. NumberCellEditor

**Purpose:** Edit number, currency, and percent fields

```typescript
import React, { useEffect, useRef } from 'react';
import { Input } from '@/components/ui/input';

interface NumberCellEditorProps {
  value: number | string;
  onChange: (value: number | string) => void;
  onBlur?: () => void;
  autoFocus?: boolean;
}

export const NumberCellEditor: React.FC<NumberCellEditorProps> = ({
  value,
  onChange,
  onBlur,
  autoFocus = true,
}) => {
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (autoFocus && inputRef.current) {
      inputRef.current.focus();
    }
  }, [autoFocus]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    // Allow empty string or valid number input
    if (val === '' || !isNaN(Number(val))) {
      onChange(val === '' ? '' : Number(val));
    }
  };

  return (
    <Input
      ref={inputRef}
      type="number"
      value={value ?? ''}
      onChange={handleChange}
      onBlur={onBlur}
      className="h-full w-full border-none rounded-none focus-visible:ring-0 px-2 bg-background text-right"
    />
  );
};
```

**Key Features:**
- Validates numeric input
- Allows empty string for deletion
- Right-aligned text (common for numbers)
- Converts to Number type on change

#### 3. CheckboxCellEditor

**Purpose:** Edit boolean/checkbox fields

```typescript
import React, { useEffect, useRef } from 'react';
import { Checkbox } from '@/components/ui/checkbox';

interface CheckboxCellEditorProps {
  value: boolean;
  onChange: (value: boolean) => void;
  onBlur?: () => void;
  autoFocus?: boolean;
}

export const CheckboxCellEditor: React.FC<CheckboxCellEditorProps> = ({
  value,
  onChange,
  onBlur,
  autoFocus = true,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (autoFocus && containerRef.current) {
      containerRef.current.focus();
    }
  }, [autoFocus]);

  return (
    <div
      ref={containerRef}
      className="h-full w-full flex items-center justify-center bg-background focus:outline-none"
      tabIndex={0}
      onBlur={onBlur}
      onClick={() => onChange(!value)}
      onKeyDown={(e) => {
        if (e.key === ' ' || e.key === 'Enter') {
          e.preventDefault();
          onChange(!value);
        }
      }}
    >
      <Checkbox
        checked={value}
        onCheckedChange={(checked) => onChange(checked === true)}
      />
    </div>
  );
};
```

**Key Features:**
- Toggle on click or keyboard (Space/Enter)
- Centered in cell
- Keyboard accessible
- Immediate toggle (no separate edit mode needed)

#### 4. DateCellEditor

**Purpose:** Edit date and datetime fields

```typescript
import React, { useEffect, useRef } from 'react';
import { Input } from '@/components/ui/input';

interface DateCellEditorProps {
  value: string; // ISO date string
  onChange: (value: string) => void;
  onBlur?: () => void;
  autoFocus?: boolean;
}

export const DateCellEditor: React.FC<DateCellEditorProps> = ({
  value,
  onChange,
  onBlur,
  autoFocus = true,
}) => {
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (autoFocus && inputRef.current) {
      inputRef.current.focus();
    }
  }, [autoFocus]);

  return (
    <Input
      ref={inputRef}
      type="date"
      value={value || ''}
      onChange={(e) => onChange(e.target.value)}
      onBlur={onBlur}
      className="h-full w-full border-none rounded-none focus-visible:ring-0 px-2 bg-background"
    />
  );
};
```

**Key Features:**
- Native date picker
- ISO date string format
- Browser-native validation

#### 5. SelectCellEditor

**Purpose:** Edit single_select and multi_select fields

```typescript
import React, { useEffect, useRef } from 'react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

interface SelectCellEditorProps {
  value: string;
  options: string[];
  onChange: (value: string) => void;
  onBlur?: () => void;
  autoFocus?: boolean;
}

export const SelectCellEditor: React.FC<SelectCellEditorProps> = ({
  value,
  options,
  onChange,
  onBlur,
  autoFocus = true,
}) => {
  return (
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger className="h-full w-full border-none rounded-none focus-visible:ring-0 px-2 bg-background">
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {options.map((option) => (
          <SelectItem key={option} value={option}>
            {option}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
};
```

**Key Features:**
- Dropdown selection from predefined options
- Radix UI Select for accessibility
- Options passed via props

#### 6. LinkCellEditor

**Purpose:** Edit linked_record fields

```typescript
import React from 'react';

interface LinkCellEditorProps {
  value: any;
  onChange: (value: any) => void;
  onBlur?: () => void;
  autoFocus?: boolean;
}

export const LinkCellEditor: React.FC<LinkCellEditorProps> = ({
  value,
  onChange,
  onBlur,
}) => {
  // Simplified implementation - would show record picker modal
  return (
    <div className="h-full w-full flex items-center px-2 bg-background">
      <button
        className="text-xs text-primary hover:underline"
        onClick={() => {
          // Open record picker modal
        }}
      >
        {Array.isArray(value) ? `${value.length} linked records` : 'Link records...'}
      </button>
    </div>
  );
};
```

**Key Features:**
- Opens modal for record selection
- Displays count of linked records
- Complex interaction pattern

#### 7. AttachmentCellEditor

**Purpose:** Edit attachment fields (file uploads)

```typescript
import React, { useRef } from 'react';

interface AttachmentCellEditorProps {
  value: any[];
  onChange: (value: any[]) => void;
  onBlur?: () => void;
  autoFocus?: boolean;
}

export const AttachmentCellEditor: React.FC<AttachmentCellEditorProps> = ({
  value,
  onChange,
  onBlur,
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    // Upload files and add to value array
    onChange([...value, ...files]);
  };

  return (
    <div className="h-full w-full flex items-center px-2 bg-background">
      <input
        ref={fileInputRef}
        type="file"
        multiple
        className="hidden"
        onChange={handleFileChange}
      />
      <button
        className="text-xs text-primary hover:underline"
        onClick={() => fileInputRef.current?.click()}
      >
        {Array.isArray(value) && value.length > 0
          ? `${value.length} files`
          : 'Add files...'}
      </button>
    </div>
  );
};
```

**Key Features:**
- Hidden file input with custom trigger
- Multiple file upload support
- Display file count

### Field Editor Integration Pattern

Field editors are used in GridView via the `EditableCell` component:

```typescript
const EditableCell = ({ getValue, row, column, table }: CellContext<any, any>) => {
  const initialValue = getValue();
  const [value, setValue] = useState(initialValue);
  const [isEditing, setIsEditing] = useState(false);

  const fieldType = (column.columnDef.meta as any)?.type || 'text';
  const fieldOptions = (column.columnDef.meta as any)?.options || {};

  const onBlur = () => {
    setIsEditing(false);
    // Update cell value
    const columnMeta = column.columnDef.meta as Record<string, unknown> | undefined;
    if (columnMeta && columnMeta.updateData) {
      (columnMeta.updateData as Function)(row.original.id, column.id, value);
    }
  };

  if (isEditing) {
    switch (fieldType) {
      case 'number':
        return <NumberCellEditor value={value} onChange={setValue} onBlur={onBlur} />;
      case 'date':
        return <DateCellEditor value={value} onChange={setValue} onBlur={onBlur} />;
      case 'select':
        return <SelectCellEditor value={value} options={fieldOptions.choices} onChange={setValue} onBlur={onBlur} />;
      case 'checkbox':
        return <CheckboxCellEditor value={value} onChange={setValue} onBlur={onBlur} />;
      case 'text':
      default:
        return <TextCellEditor value={value} onChange={setValue} onBlur={onBlur} />;
    }
  }

  // Display mode
  return (
    <div
      className="h-full w-full min-h-[32px] flex items-center px-2 cursor-pointer hover:bg-muted/50"
      onClick={() => setIsEditing(true)}
    >
      {renderCellContent(value, fieldType)}
    </div>
  );
};
```

### Field Editor Checklist

When creating new field editors:

- [ ] Implement consistent `FieldEditorProps<T>` interface
- [ ] Use `useRef` for auto-focus
- [ ] Handle `onBlur` to commit changes
- [ ] Validate/transform input appropriately
- [ ] Handle null/undefined values gracefully
- [ ] Use appropriate UI component from `components/ui/`
- [ ] Remove borders/rings for inline appearance
- [ ] Add keyboard accessibility (if applicable)

---

## View Components

### Pattern Overview

View components are complex data visualization patterns that render records in different layouts (Grid, Kanban, Calendar, etc.). They:
- Accept standardized props (`data`, `fields`, callbacks)
- Handle their own internal state and layout logic
- Integrate with TanStack Table (for GridView)
- Provide interactive features (editing, drag-and-drop, etc.)

### Common Interface Pattern

```typescript
interface ViewProps {
  data: RecordData[];           // Array of records to display
  fields: Field[];              // Field definitions
  onCellUpdate?: (rowId: string, fieldId: string, value: unknown) => void;
  onRowAdd?: () => void;        // Optional row creation
  onRecordClick?: (record: RecordData) => void;
}
```

### Implemented View Components

#### 1. GridView

**Purpose:** Spreadsheet-like table with inline editing

**Technology:** TanStack Table v8 with custom cell editors

```typescript
import React, { useState } from 'react';
import { useReactTable, getCoreRowModel, flexRender, ColumnDef } from '@tanstack/react-table';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { TextCellEditor } from '../fields/TextCellEditor';
// ... other field editors

interface GridViewProps {
  data: RecordData[];
  fields: Field[];
  onCellUpdate: (rowId: string, fieldId: string, value: unknown) => void;
  onRowAdd?: () => void;
}

export const GridView: React.FC<GridViewProps> = ({ data, fields, onCellUpdate, onRowAdd }) => {
  // Generate columns from fields
  const columns = React.useMemo<ColumnDef<any>[]>(() => {
    return fields.map((field) => ({
      accessorKey: field.name,
      id: field.id || field.name,
      header: field.name,
      cell: EditableCell, // Custom editable cell component
      meta: {
        type: field.type,
        options: field.options,
      },
    }));
  }, [fields]);

  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
    meta: {
      updateData: (rowId: string, columnId: string, value: any) => {
        onCellUpdate(rowId, columnId, value);
      },
    },
  });

  return (
    <div className="w-full border rounded-md overflow-hidden bg-background shadow-sm">
      <Table>
        <TableHeader>
          {table.getHeaderGroups().map((headerGroup) => (
            <TableRow key={headerGroup.id}>
              <TableHead className="w-[50px] text-center bg-muted/50">#</TableHead>
              {headerGroup.headers.map((header) => (
                <TableHead key={header.id} className="min-w-[150px] border-l bg-muted/50">
                  {flexRender(header.column.columnDef.header, header.getContext())}
                </TableHead>
              ))}
            </TableRow>
          ))}
        </TableHeader>
        <TableBody>
          {table.getRowModel().rows.map((row, index) => (
            <TableRow key={row.id}>
              <TableCell className="text-center text-muted-foreground text-xs bg-muted/20">
                {index + 1}
              </TableCell>
              {row.getVisibleCells().map((cell) => (
                <TableCell key={cell.id} className="p-0 border-l h-10 relative">
                  {flexRender(cell.column.columnDef.cell, cell.getContext())}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
      {onRowAdd && (
        <div className="border-t p-2 bg-muted/10">
          <button onClick={onRowAdd} className="text-sm text-muted-foreground hover:text-primary">
            + Add Row
          </button>
        </div>
      )}
    </div>
  );
};
```

**Key Features:**
- TanStack Table for column management
- Custom `EditableCell` component with field editor switching
- Row numbering in first column
- Inline "Add Row" button
- Column metadata for field types

#### 2. KanbanView

**Purpose:** Card-based task board grouped by select field

**Technology:** Card components with drag-and-drop (future: @dnd-kit)

```typescript
import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface KanbanViewProps {
  data: any[];
  fields: any[];
}

export const KanbanView: React.FC<KanbanViewProps> = ({ data, fields }) => {
  // Find first select field for grouping
  const groupByField = fields.find(f => f.type === 'select' || f.type === 'singleSelect');

  if (!groupByField) {
    return (
      <div className="p-4 text-muted-foreground">
        Please add a Single Select field to use Kanban view.
      </div>
    );
  }

  // Group data by select field value
  const options = groupByField.options?.choices || [];
  const groupedData: Record<string, any[]> = {};

  options.forEach((opt: any) => {
    groupedData[opt.name || opt] = [];
  });
  groupedData['Unassigned'] = [];

  data.forEach(item => {
    const val = item[groupByField.name];
    if (val && groupedData[val]) {
      groupedData[val].push(item);
    } else {
      groupedData['Unassigned'].push(item);
    }
  });

  return (
    <div className="flex h-full overflow-x-auto gap-4 p-4 bg-muted/10">
      {Object.entries(groupedData).map(([groupName, items]) => (
        <div key={groupName} className="min-w-[280px] w-[280px] flex flex-col gap-3">
          <div className="flex items-center justify-between px-2">
            <span className="font-semibold text-sm uppercase text-muted-foreground">
              {groupName} <span className="ml-1 text-xs opacity-70">({items.length})</span>
            </span>
          </div>
          <div className="flex-1 flex flex-col gap-2 overflow-y-auto pb-4">
            {items.map(item => (
              <Card key={item.id} className="cursor-pointer hover:shadow-md transition-shadow">
                <CardHeader className="p-3 pb-0">
                  <CardTitle className="text-sm font-medium">
                    {item[fields[0].name] || 'Untitled'}
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-3 text-xs text-muted-foreground">
                  {fields.slice(1, 4).map(field => (
                    <div key={field.id} className="truncate">
                      <span className="opacity-70 mr-1">{field.name}:</span>
                      {String(item[field.name] || '-')}
                    </div>
                  ))}
                </CardContent>
              </Card>
            ))}
            <button className="w-full py-2 text-xs text-muted-foreground border border-dashed rounded-md hover:bg-background">
              + New Record
            </button>
          </div>
        </div>
      ))}
    </div>
  );
};
```

**Key Features:**
- Auto-groups by first select field
- Vertical columns with horizontal scroll
- Card-based record display
- Shows first 3 fields in card preview
- Graceful handling of missing select field

#### 3. FormView

**Purpose:** Single-record form for data entry

**Technology:** Card layout with form inputs

```typescript
import React from 'react';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

interface FormViewProps {
  fields: any[];
  onSubmit?: (data: any) => void;
}

export const FormView: React.FC<FormViewProps> = ({ fields, onSubmit }) => {
  return (
    <div className="max-w-2xl mx-auto py-8 px-4">
      <div className="bg-primary h-32 rounded-t-lg mb-[-40px]"></div>
      <Card className="shadow-lg relative z-10">
        <CardHeader className="text-center pt-8">
          <CardTitle className="text-3xl">Submit a Record</CardTitle>
          <CardDescription>Fill out the form below to add a new record to the table.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6 pt-6">
          {fields.map(field => (
            <div key={field.id} className="space-y-2">
              <Label htmlFor={field.id} className="text-base">
                {field.name}
                {field.required && <span className="text-red-500 ml-1">*</span>}
              </Label>
              {field.description && (
                <p className="text-xs text-muted-foreground">{field.description}</p>
              )}

              {/* Input based on field type */}
              {field.type === 'longText' ? (
                <textarea className="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm" />
              ) : field.type === 'select' ? (
                <select className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm">
                  <option value="">Select an option...</option>
                  {field.options?.choices?.map((c: any) => (
                    <option key={c.name || c} value={c.name || c}>{c.name || c}</option>
                  ))}
                </select>
              ) : (
                <Input
                  id={field.id}
                  type={field.type === 'number' ? 'number' : field.type === 'date' ? 'date' : 'text'}
                  placeholder="Your answer"
                />
              )}
            </div>
          ))}

          <div className="pt-4 flex justify-center">
            <Button size="lg" className="w-full md:w-auto px-8" onClick={() => onSubmit && onSubmit({})}>
              Submit Form
            </Button>
          </div>
        </CardContent>
      </Card>
      <div className="text-center mt-6 text-xs text-muted-foreground">
        Powered by PyBase
      </div>
    </div>
  );
};
```

**Key Features:**
- Centered, card-based layout
- Decorative header banner
- Required field indicators
- Field descriptions
- Responsive width (max-w-2xl)

### View Component Checklist

When creating new view components:

- [ ] Accept standard `ViewProps` interface
- [ ] Handle empty data gracefully
- [ ] Use memoization for expensive computations
- [ ] Implement responsive design
- [ ] Add loading/error states (if fetching data)
- [ ] Use components from `components/ui/`
- [ ] Document specific props in comments
- [ ] Export as named export

---

## Layout Components

### Pattern Overview

Layout components define the application shell structure. They:
- Provide consistent navigation and structure
- Use React Router's `<Outlet />` for nested routes
- Handle application-wide state (sidebar, header)
- Integrate with authentication

### Implemented Layout Components

#### 1. MainLayout

**Purpose:** Application shell with header, sidebar, and main content area

```typescript
import { Outlet } from "react-router-dom"
import Sidebar from "./Sidebar"
import Header from "./Header"

export default function MainLayout() {
  return (
    <div className="min-h-screen bg-background">
      <Header />
      <div className="flex">
        <Sidebar />
        <main className="flex-1 p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
```

**Key Features:**
- Flexbox layout with fixed sidebar
- Full viewport height
- React Router `<Outlet />` for nested routes
- Padding for main content area

#### 2. Header

**Purpose:** Top navigation bar with branding and user menu

```typescript
export default function Header() {
  return (
    <header className="h-14 border-b bg-card px-6 flex items-center justify-between">
      <div className="flex items-center gap-2">
        <h1 className="text-xl font-bold">PyBase</h1>
      </div>
      <div className="flex items-center gap-4">
        {/* User menu, search, notifications */}
      </div>
    </header>
  )
}
```

**Key Features:**
- Fixed height (h-14)
- Border bottom for separation
- Flexbox for left/right alignment

#### 3. Sidebar

**Purpose:** Navigation sidebar with workspaces and bases

```typescript
import { useEffect, useState } from "react"
import { get } from "@/lib/api"
import type { Workspace, Base } from "@/types"
import { Link } from "react-router-dom"

export default function Sidebar() {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([])
  const [bases, setBases] = useState<Base[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    try {
      setLoading(true)
      const workspacesData = await get<Workspace[]>("/workspaces")
      const basesData = await get<Base[]>("/bases")
      setWorkspaces(workspacesData)
      setBases(basesData)
    } catch (error) {
      console.error("Failed to fetch sidebar data:", error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <aside className="w-64 border-r bg-card min-h-[calc(100vh-3.5rem)] p-4">
      {loading ? (
        <div className="text-sm text-muted-foreground">Loading...</div>
      ) : (
        <nav className="space-y-4">
          <div>
            <h3 className="text-sm font-semibold text-muted-foreground mb-2">Workspaces</h3>
            <ul className="space-y-1">
              {workspaces.map((ws) => (
                <li key={ws.id}>
                  <div className="text-sm font-medium">{ws.name}</div>
                  <ul className="ml-4 mt-2 space-y-1">
                    {bases
                      .filter((b) => b.workspace_id === ws.id)
                      .map((base) => (
                        <li key={base.id}>
                          <Link
                            to={`/bases/${base.id}`}
                            className="text-sm text-muted-foreground hover:text-primary block py-1"
                          >
                            📄 {base.name}
                          </Link>
                        </li>
                      ))}
                  </ul>
                </li>
              ))}
            </ul>
          </div>
        </nav>
      )}
    </aside>
  )
}
```

**Key Features:**
- Fixed width (w-64)
- Fetches navigation data on mount
- Nested workspace/base hierarchy
- Loading state
- React Router `<Link>` for navigation

### Layout Component Checklist

When creating new layout components:

- [ ] Use semantic HTML (`<header>`, `<aside>`, `<main>`)
- [ ] Implement responsive design
- [ ] Use React Router `<Outlet />` for nested routes
- [ ] Handle loading states
- [ ] Use consistent spacing/sizing
- [ ] Export as default export

---

## Component Composition Patterns

### 1. Compound Components Pattern

Used for components with multiple sub-parts that share state:

```typescript
// Card is compound component with Header, Title, Content, Footer
<Card>
  <CardHeader>
    <CardTitle>User Profile</CardTitle>
    <CardDescription>Manage your account</CardDescription>
  </CardHeader>
  <CardContent>
    <UserForm />
  </CardContent>
  <CardFooter>
    <Button>Save</Button>
  </CardFooter>
</Card>
```

**Benefits:**
- Flexible composition
- Shared styling context
- Clear component hierarchy

### 2. Render Props Pattern

Used for custom rendering logic:

```typescript
// TanStack Table cell customization
const columns: ColumnDef<Record>[] = [
  {
    accessorKey: "name",
    header: "Name",
    cell: ({ getValue, row }) => {
      // Custom cell rendering
      return <strong>{getValue()}</strong>
    }
  }
]
```

### 3. Slot Pattern (Radix UI)

Used for polymorphic components that can render as different elements:

```typescript
// Button can render as a link
<Button asChild>
  <Link to="/settings">Settings</Link>
</Button>
```

**Implementation:**
```typescript
const Comp = asChild ? Slot : "button"
return <Comp {...props} />
```

### 4. Controller Pattern

Used for form inputs with React Hook Form:

```typescript
<Controller
  name="email"
  control={control}
  render={({ field }) => (
    <Input {...field} type="email" />
  )}
/>
```

### 5. Provider Pattern

Used for context-based state sharing:

```typescript
// QueryClient provider for TanStack Query
<QueryClientProvider client={queryClient}>
  <RouterProvider router={router} />
</QueryClientProvider>

// Zustand (no provider needed)
const user = useAuthStore((state) => state.user)
```

---

## Best Practices

### TypeScript Guidelines

1. **Always define prop interfaces:**
   ```typescript
   interface ComponentProps {
     data: RecordData[]
     onUpdate: (id: string, value: unknown) => void
   }
   ```

2. **Use type inference for generics:**
   ```typescript
   const [value, setValue] = useState<string>('') // Explicit
   const [value, setValue] = useState('') // Inferred (prefer this)
   ```

3. **Extend native props:**
   ```typescript
   interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
     variant?: 'default' | 'outline'
   }
   ```

4. **Use discriminated unions for variant types:**
   ```typescript
   type Field =
     | { type: 'text'; value: string }
     | { type: 'number'; value: number }
     | { type: 'date'; value: Date }
   ```

### Component Design Guidelines

1. **Single Responsibility:** Each component should do one thing well
2. **Composability:** Prefer small, composable components over monoliths
3. **Accessibility:** Use semantic HTML and ARIA attributes
4. **Performance:** Memoize expensive computations and callbacks
5. **Error Boundaries:** Wrap complex components in error boundaries
6. **Loading States:** Always show loading/error states for async operations

### Styling Guidelines

1. **Use Tailwind utilities:** Prefer `className` over inline styles
2. **Use design tokens:** Use CSS variables (e.g., `bg-background`, `text-primary`)
3. **Use `cn()` for merging:** Always use `cn()` for className composition
4. **Responsive design:** Use Tailwind responsive prefixes (`md:`, `lg:`)
5. **Dark mode:** Use semantic color tokens that support dark mode

### File Organization Guidelines

1. **One component per file** (except compound components)
2. **Colocate styles** (use Tailwind classes in component file)
3. **Group related components** (e.g., all field editors in `fields/`)
4. **Use index files sparingly** (prefer named imports)

### Naming Conventions

1. **Components:** PascalCase (e.g., `GridView`, `TextCellEditor`)
2. **Files:** Match component name (e.g., `GridView.tsx`)
3. **Props interfaces:** `ComponentNameProps` (e.g., `GridViewProps`)
4. **Hooks:** `useCamelCase` (e.g., `useWebSocket`)
5. **Utilities:** camelCase (e.g., `cn`, `formatDate`)

### Testing Guidelines

1. **Test user interactions** (clicks, keyboard, form submission)
2. **Test accessibility** (ARIA attributes, keyboard navigation)
3. **Test error states** (loading, error, empty data)
4. **Test edge cases** (null values, empty arrays, invalid data)
5. **Use Testing Library** (prefer user-centric queries)

---

## Conclusion

PyBase frontend component architecture emphasizes:

- **Consistency:** All components follow established patterns
- **Reusability:** UI primitives can be composed into complex features
- **Type Safety:** Full TypeScript coverage with strict mode
- **Accessibility:** Radix UI ensures WCAG compliance
- **Developer Experience:** Clear patterns reduce cognitive load

When creating new components, refer to this document and follow existing patterns. For questions or clarifications, consult the existing codebase or team documentation.

---

**Related Documentation:**
- [Frontend Architecture](./frontend-architecture.md) - Overall architecture and tech stack
- [State Management Patterns](./frontend-state-management.md) - Zustand and TanStack Query usage (to be created)
- [API Integration Patterns](./api.md) - Backend API integration

**Last Updated:** 2026-01-21
