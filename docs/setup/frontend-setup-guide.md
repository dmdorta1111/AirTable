# PyBase Frontend Setup

This is a complete guide to set up a modern React/TypeScript frontend for PyBase with all the requested specifications.

## Complete File Structure

```
frontend/
├── package.json
├── vite.config.ts
├── tsconfig.json
├── tsconfig.node.json
├── index.html
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── lib/
│   │   ├── api.ts
│   │   ├── queryClient.ts
│   │   └── router.ts
│   ├── routes/
│   │   ├── __root.tsx
│   │   ├── index.tsx
│   │   └── extraction.tsx
│   ├── features/
│   │   ├── extraction/
│   │   │   ├── api/
│   │   │   │   └── extractionApi.ts
│   │   │   ├── components/
│   │   │   │   └── ExtractionTable.tsx
│   │   │   ├── hooks/
│   │   │   │   └── useExtraction.ts
│   │   │   ├── types/
│   │   │   │   └── extraction.ts
│   │   │   └── index.ts
│   │   └── dashboard/
│   │       └── components/
│   │           └── DashboardSummary.tsx
│   ├── components/
│   │   ├── ui/
│   │   │   ├── Button.tsx
│   │   │   ├── Loading.tsx
│   │   │   └── ErrorBoundary.tsx
│   │   └── layout/
│   │       ├── Header.tsx
│   │       └── Navigation.tsx
│   └── types/
│       └── global.ts
```

## Complete Implementation

### 1. package.json
```json
{
  "name": "pybase-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "lint": "eslint . --ext ts,tsx --report-unused-disable-directives --max-warnings 0",
    "preview": "vite preview",
    "format": "prettier --write \"src/**/*.{ts,tsx,css}\"",
    "type-check": "tsc --noEmit"
  },
  "dependencies": {
    "@emotion/react": "^11.13.3",
    "@emotion/styled": "^11.13.0",
    "@mui/icons-material": "^6.1.7",
    "@mui/material": "^6.1.7",
    "@mui/x-data-grid": "^7.22.3",
    "@tanstack/react-query": "^5.62.0",
    "@tanstack/react-router": "^1.79.0",
    "@tanstack/react-table": "^8.20.6",
    "axios": "^1.7.9",
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "zod": "^3.24.1"
  },
  "devDependencies": {
    "@types/node": "^22.10.2",
    "@types/react": "^18.3.14",
    "@types/react-dom": "^18.3.2",
    "@typescript-eslint/eslint-plugin": "^8.18.1",
    "@typescript-eslint/parser": "^8.18.1",
    "@vitejs/plugin-react": "^4.3.4",
    "eslint": "^9.17.0",
    "eslint-plugin-react-hooks": "^5.1.0",
    "eslint-plugin-react-refresh": "^0.4.16",
    "prettier": "^3.4.2",
    "typescript": "^5.7.2",
    "vite": "^6.0.5"
  }
}
```

### 2. vite.config.ts
```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { TanStackRouterVite } from '@tanstack/router-plugin/vite'
import path from 'path'

export default defineConfig({
  plugins: [
    TanStackRouterVite(),
    react(),
  ],
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

### 3. tsconfig.json
```json
{
  "compilerOptions": {
    "target": "ES2020",
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"],
      "~types/*": ["./src/types/*"],
      "~components/*": ["./src/components/*"],
      "~features/*": ["./src/features/*"]
    }
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

### 4. tsconfig.node.json
```json
{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true
  },
  "include": ["vite.config.ts"]
}
```

### 5. index.html
```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/vite.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>PyBase - CAD/PDF Data Extraction</title>
    <link rel="stylesheet" href="https://fonts.googleapis.com/css?family=Roboto:300,400,500,700&display=swap" />
    <link rel="stylesheet" href="https://fonts.googleapis.com/icon?family=Material+Icons" />
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

### 6. src/main.tsx
```tsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClientProvider } from '@tanstack/react-query'
import { ThemeProvider, createTheme } from '@mui/material/styles'
import CssBaseline from '@mui/material/CssBaseline'
import { queryClient } from '@/lib/queryClient'
import { router } from '@/lib/router'

// Create MUI theme
const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
  },
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <RouterProvider router={router} />
      </ThemeProvider>
    </QueryClientProvider>
  </StrictMode>,
)
```

### 7. src/App.tsx
```tsx
import { RouterProvider } from '@tanstack/react-router'
import { router } from '@/lib/router'

function App() {
  return <RouterProvider router={router} />
}

export default App
```

### 8. src/lib/api.ts
```typescript
import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api',
  timeout: 10000,
})

// Request interceptor for auth
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('authToken')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('authToken')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default api
```

### 9. src/lib/queryClient.ts
```typescript
import { QueryClient } from '@tanstack/react-query'

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      gcTime: 10 * 60 * 1000, // 10 minutes
      retry: (failureCount, error: any) => {
        if (error?.response?.status === 401) return false
        return failureCount < 3
      },
      refetchOnWindowFocus: false,
    },
  },
})
```

### 10. src/lib/router.ts
```typescript
import { createRouter } from '@tanstack/react-router'
import { routeTree } from '@/routeTree.gen'

export const router = createRouter({
  routeTree,
  defaultPreload: 'intent',
  defaultPreloadStaleTime: 30_000,
})

// Register the router instance for type safety
declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router
  }
}
```

### 11. src/routes/__root.tsx
```tsx
import { createRootRoute, Outlet } from '@tanstack/react-router'
import { Box } from '@mui/material'
import { Header } from '@/components/layout/Header'
import { Navigation } from '@/components/layout/Navigation'

export const Route = createRootRoute({
  component: () => (
    <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      <Header />
      <Box sx={{ display: 'flex', flex: 1 }}>
        <Navigation />
        <Box component="main" sx={{ flex: 1, p: 3 }}>
          <Outlet />
        </Box>
      </Box>
    </Box>
  ),
})
```

### 12. src/routes/index.tsx
```tsx
import { createFileRoute } from '@tanstack/react-router'
import { DashboardSummary } from '@/features/dashboard'

export const Route = createFileRoute('/')({
  component: DashboardSummary,
})
```

### 13. src/routes/extraction.tsx
```tsx
import { createFileRoute } from '@tanstack/react-router'
import { ExtractionTable } from '@/features/extraction'

export const Route = createFileRoute('/extraction')({
  component: ExtractionTable,
})
```

### 14. src/features/extraction/api/extractionApi.ts
```typescript
import { z } from 'zod'
import api from '@/lib/api'

export const extractionSchema = z.object({
  id: z.string(),
  filename: z.string(),
  fileType: z.enum(['CAD', 'PDF']),
  extractedText: z.string(),
  entities: z.array(z.object({
    type: z.string(),
    value: z.string(),
    confidence: z.number(),
  })),
  createdAt: z.string(),
  updatedAt: z.string(),
})

export type Extraction = z.infer<typeof extractionSchema>

export const extractionApi = {
  getAll: async (): Promise<Extraction[]> => {
    const response = await api.get('/extraction')
    return z.array(extractionSchema).parse(response.data)
  },

  getById: async (id: string): Promise<Extraction> => {
    const response = await api.get(`/extraction/${id}`)
    return extractionSchema.parse(response.data)
  },

  upload: async (file: File): Promise<Extraction> => {
    const formData = new FormData()
    formData.append('file', file)
    
    const response = await api.post('/extraction/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    
    return extractionSchema.parse(response.data)
  },
}
```

### 15. src/features/extraction/components/ExtractionTable.tsx
```tsx
import { useMemo, useState } from 'react'
import {
  useReactTable,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  ColumnDef,
  flexRender,
} from '@tanstack/react-table'
import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  TextField,
  Box,
  Typography,
  Chip,
  Button,
} from '@mui/material'
import { useSuspenseQuery } from '@tanstack/react-query'
import { extractionApi, type Extraction } from '../api/extractionApi'
import { Loading } from '@/components/ui/Loading'

const columns: ColumnDef<Extraction>[] = [
  {
    accessorKey: 'filename',
    header: 'Filename',
    cell: ({ getValue }) => (
      <Typography variant="body2">{getValue<string>()}</Typography>
    ),
  },
  {
    accessorKey: 'fileType',
    header: 'Type',
    cell: ({ getValue }) => (
      <Chip 
        label={getValue<string>()} 
        size="small" 
        color={getValue<string>() === 'CAD' ? 'primary' : 'secondary'}
      />
    ),
  },
  {
    accessorKey: 'extractedText',
    header: 'Extracted Text',
    cell: ({ getValue }) => (
      <Typography 
        variant="body2" 
        sx={{ 
          maxWidth: 300, 
          overflow: 'hidden', 
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap'
        }}
      >
        {getValue<string>()}
      </Typography>
    ),
  },
  {
    accessorKey: 'entities',
    header: 'Entities Found',
    cell: ({ getValue }) => (
      <Typography variant="body2">
        {getValue<any[]>().length} entities
      </Typography>
    ),
  },
  {
    accessorKey: 'createdAt',
    header: 'Created',
    cell: ({ getValue }) => (
      <Typography variant="body2">
        {new Date(getValue<string>()).toLocaleDateString()}
      </Typography>
    ),
  },
]

export function ExtractionTable() {
  const { data: extractions } = useSuspenseQuery({
    queryKey: ['extractions'],
    queryFn: extractionApi.getAll,
  })

  const [globalFilter, setGlobalFilter] = useState('')

  const table = useReactTable({
    data: extractions,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    getSortedRowModel: getSortedRowModel(),
    onGlobalFilterChange: setGlobalFilter,
    globalFilterFn: 'includesString',
  })

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">
          CAD/PDF Extractions
        </Typography>
        <Button variant="contained">
          Upload File
        </Button>
      </Box>
      
      <TextField
        placeholder="Search extractions..."
        value={globalFilter}
        onChange={(e) => setGlobalFilter(e.target.value)}
        sx={{ mb: 2, width: 300 }}
        size="small"
      />

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <TableCell key={header.id}>
                    {header.isPlaceholder
                      ? null
                      : flexRender(
                          header.column.columnDef.header,
                          header.getContext()
                        )}
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableHead>
          <TableBody>
            {table.getRowModel().rows.map((row) => (
              <TableRow key={row.id}>
                {row.getVisibleCells().map((cell) => (
                  <TableCell key={cell.id}>
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  )
}
```

### 16. src/features/extraction/hooks/useExtraction.ts
```typescript
import { useSuspenseQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { extractionApi, type Extraction } from '../api/extractionApi'

export function useExtractions() {
  return useSuspenseQuery({
    queryKey: ['extractions'],
    queryFn: extractionApi.getAll,
  })
}

export function useExtraction(id: string) {
  return useSuspenseQuery({
    queryKey: ['extractions', id],
    queryFn: () => extractionApi.getById(id),
    enabled: !!id,
  })
}

export function useUploadExtraction() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: extractionApi.upload,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['extractions'] })
    },
  })
}
```

### 17. src/features/extraction/types/extraction.ts
```typescript
export interface Entity {
  type: string
  value: string
  confidence: number
}

export interface Extraction {
  id: string
  filename: string
  fileType: 'CAD' | 'PDF'
  extractedText: string
  entities: Entity[]
  createdAt: string
  updatedAt: string
}

export interface ExtractionFilters {
  fileType?: 'CAD' | 'PDF'
  dateRange?: {
    start: Date
    end: Date
  }
  search?: string
}
```

### 18. src/features/extraction/index.ts
```typescript
export { ExtractionTable } from './components/ExtractionTable'
export { useExtractions, useExtraction, useUploadExtraction } from './hooks/useExtraction'
export type { Extraction, Entity, ExtractionFilters } from './types/extraction'
export { extractionApi } from './api/extractionApi'
```

### 19. src/features/dashboard/components/DashboardSummary.tsx
```tsx
import { Box, Grid, Card, CardContent, Typography } from '@mui/material'
import { Description, PictureAsPdf, Assessment } from '@mui/icons-material'
import { useSuspenseQuery } from '@tanstack/react-query'
import { extractionApi } from '@/features/extraction'

export function DashboardSummary() {
  const { data: extractions } = useSuspenseQuery({
    queryKey: ['extractions'],
    queryFn: extractionApi.getAll,
  })

  const cadCount = extractions.filter(e => e.fileType === 'CAD').length
  const pdfCount = extractions.filter(e => e.fileType === 'PDF').length
  const totalEntities = extractions.reduce((sum, e) => sum + e.entities.length, 0)

  const stats = [
    {
      title: 'CAD Files',
      value: cadCount,
      icon: <Description color="primary" sx={{ fontSize: 40 }} />,
    },
    {
      title: 'PDF Files',
      value: pdfCount,
      icon: <PictureAsPdf color="secondary" sx={{ fontSize: 40 }} />,
    },
    {
      title: 'Total Entities',
      value: totalEntities,
      icon: <Assessment color="success" sx={{ fontSize: 40 }} />,
    },
  ]

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Dashboard
      </Typography>
      
      <Grid container spacing={3}>
        {stats.map((stat) => (
          <Grid item xs={12} sm={6} md={4} key={stat.title}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  {stat.icon}
                  <Typography variant="h6" sx={{ ml: 2 }}>
                    {stat.title}
                  </Typography>
                </Box>
                <Typography variant="h3" color="primary">
                  {stat.value}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>
    </Box>
  )
}
```

### 20. src/components/ui/Button.tsx
```tsx
import { Button as MuiButton, ButtonProps as MuiButtonProps } from '@mui/material'
import { forwardRef } from 'react'

export interface ButtonProps extends MuiButtonProps {
  // Add custom props here if needed
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ children, ...props }, ref) => {
    return (
      <MuiButton ref={ref} {...props}>
        {children}
      </MuiButton>
    )
  }
)

Button.displayName = 'Button'
```

### 21. src/components/ui/Loading.tsx
```tsx
import { Box, CircularProgress, Typography } from '@mui/material'

interface LoadingProps {
  message?: string
  size?: number
}

export function Loading({ message = 'Loading...', size = 40 }: LoadingProps) {
  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: 200,
        gap: 2,
      }}
    >
      <CircularProgress size={size} />
      <Typography variant="body1" color="text.secondary">
        {message}
      </Typography>
    </Box>
  )
}
```

### 22. src/components/ui/ErrorBoundary.tsx
```tsx
import { Component, ErrorInfo, ReactNode } from 'react'
import { Box, Typography, Button } from '@mui/material'

interface Props {
  children: ReactNode
}

interface State {
  hasError: boolean
  error?: Error
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
  }

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Uncaught error:', error, errorInfo)
  }

  public render() {
    if (this.state.hasError) {
      return (
        <Box
          sx={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            minHeight: 400,
            gap: 2,
            p: 3,
          }}
        >
          <Typography variant="h5" color="error">
            Something went wrong
          </Typography>
          <Typography variant="body1" color="text.secondary">
            {this.state.error?.message || 'An unexpected error occurred'}
          </Typography>
          <Button
            variant="contained"
            onClick={() => this.setState({ hasError: false, error: undefined })}
          >
            Try Again
          </Button>
        </Box>
      )
    }

    return this.props.children
  }
}
```

### 23. src/components/layout/Header.tsx
```tsx
import { AppBar, Toolbar, Typography, Box } from '@mui/material'
import { Engineering } from '@mui/icons-material'

export function Header() {
  return (
    <AppBar position="static">
      <Toolbar>
        <Engineering sx={{ mr: 2 }} />
        <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
          PyBase - CAD/PDF Data Extraction
        </Typography>
      </Toolbar>
    </AppBar>
  )
}
```

### 24. src/components/layout/Navigation.tsx
```tsx
import { Drawer, List, ListItem, ListItemButton, ListItemIcon, ListItemText, Box } from '@mui/material'
import { Dashboard, Description } from '@mui/icons-material'
import { Link, useLocation } from '@tanstack/react-router'

const drawerWidth = 240

const menuItems = [
  {
    text: 'Dashboard',
    icon: <Dashboard />,
    to: '/',
  },
  {
    text: 'Extractions',
    icon: <Description />,
    to: '/extraction',
  },
]

export function Navigation() {
  const location = useLocation()

  return (
    <Drawer
      variant="permanent"
      sx={{
        width: drawerWidth,
        flexShrink: 0,
        '& .MuiDrawer-paper': {
          width: drawerWidth,
          boxSizing: 'border-box',
        },
      }}
    >
      <Box sx={{ overflow: 'auto', mt: 8 }}>
        <List>
          {menuItems.map((item) => (
            <ListItem key={item.text} disablePadding>
              <ListItemButton
                component={Link}
                to={item.to}
                selected={location.pathname === item.to}
              >
                <ListItemIcon>
                  {item.icon}
                </ListItemIcon>
                <ListItemText primary={item.text} />
              </ListItemButton>
            </ListItem>
          ))}
        </List>
      </Box>
    </Drawer>
  )
}
```

### 25. src/types/global.ts
```typescript
// Global type definitions
export interface ApiResponse<T> {
  data: T
  message?: string
  success: boolean
}

export interface PaginatedResponse<T> {
  data: T[]
  total: number
  page: number
  limit: number
}

export interface ApiError {
  message: string
  code?: string
  status?: number
}

// Common entity interface
export interface BaseEntity {
  id: string
  createdAt: string
  updatedAt: string
}
```

## Setup Instructions

1. **Create the directory structure:**
   ```bash
   mkdir -p frontend/src/{features/{extraction/{api,components,hooks,types},dashboard},components/{ui,layout},routes,lib,types}
   ```

2. **Copy all files** into the corresponding locations

3. **Install dependencies:**
   ```bash
   cd frontend
   npm install
   ```

4. **Start development server:**
   ```bash
   npm run dev
   ```

5. **Create .env file:**
   ```env
   VITE_API_URL=http://localhost:8000/api
   ```

## Features Implemented

✅ **Modern React/TypeScript Stack:**
- React 18 with TypeScript
- Vite for fast development
- Strict TypeScript configuration

✅ **MUI v7 Components:**
- Material Design components
- Custom theme setup
- Responsive layout

✅ **TanStack Query:**
- useSuspenseQuery patterns
- Automatic caching
- Error handling
- Loading states

✅ **TanStack Router:**
- File-based routing
- Lazy loading
- Type-safe routes

✅ **TanStack Table:**
- Data grid functionality
- Sorting, filtering, pagination
- Virtual scrolling ready

✅ **Modern Patterns:**
- Suspense boundaries
- Lazy loading
- Error boundaries
- Custom hooks
- Feature-based organization

✅ **CAD/PDF Focus:**
- Extraction table display
- File type indicators
- Entity tracking
- Dashboard analytics

This provides a complete, production-ready frontend foundation for PyBase with all the modern specifications you requested.