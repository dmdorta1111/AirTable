# Design Guidelines

## Frontend Overview
The PyBase frontend is built with React 18, TypeScript, and Vite. It aims to provide a responsive, intuitive, and high-performance interface for managing complex technical data.

## Visual Language
- **Colors**: Professional and clean. Primary color: Blue (`#3b82f6`).
- **Typography**: Sans-serif (Inter or similar). Readable at small sizes for data-heavy grids.
- **Icons**: Lucide React for consistent, scalable iconography.

## Component Architecture
- **Framework**: React with Functional Components and Hooks.
- **UI Components**: `shadcn/ui` (built on Radix UI and Tailwind CSS).
- **Layout**: Bento-grid inspired layouts for dashboards.
- **Data Grids**: Virtualized scrolling (e.g., `react-virtual`) for handling large datasets.

## State Management
- **Server State**: `TanStack Query` for data fetching, caching, and synchronization.
- **Client State**: `Zustand` for lightweight global state (e.g., UI preferences).
- **Forms**: `react-hook-form` for efficient form handling and validation.

## UI/UX Principles

### 1. Data-First Design
The interface should prioritize data visibility. Use clear headings, consistent spacing, and scannable grids.

### 2. Contextual Actions
Provide actions where they are needed (e.g., right-click menus on grid cells, hover actions on records).

### 3. Real-time Feedback
Show immediate feedback for user actions. Use optimistic updates via React Query to make the UI feel instantaneous. Display presence indicators for other active users.

### 4. Accessibility (A11y)
- Use semantic HTML.
- Ensure proper keyboard navigation.
- Maintain high contrast for readability.
- Support screen readers through ARIA labels.

## Implementation Patterns

### View Components
Each view type (Grid, Kanban, etc.) should be encapsulated in its own directory within `src/frontend/components/views/`.

### Field Renderers
Create specialized components for rendering different field types (e.g., `DimensionRenderer`, `GdtRenderer`).

### Performance
- Lazy load routes and large components.
- Memoize expensive calculations.
- Use `react-window` or `react-virtual` for lists with > 50 items.
