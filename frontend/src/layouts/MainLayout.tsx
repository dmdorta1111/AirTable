import { Outlet, Link, useNavigate } from 'react-router-dom'
import { useState } from 'react'
import { useAuthStore } from '@/stores/auth'
import { Button } from '@/components/ui/button'
import {
  LayoutGrid,
  Database,
  Settings,
  LogOut,
  Plus,
  ChevronDown,
  Bell,
} from 'lucide-react'
import NotificationCenter from '@/components/modals/NotificationCenter'

export default function MainLayout() {
  const { user, logout } = useAuthStore()
  const navigate = useNavigate()
  const [notificationsOpen, setNotificationsOpen] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(false)

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div className="min-h-screen flex">
       {/* Sidebar - Desktop */}
      <aside className="w-64 border-r bg-card flex-col hidden md:flex">
      {/* Sidebar - Mobile */}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-30 w-64 bg-card border-r flex-col transition-transform md:hidden",
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
          {/* Logo */}
          <div className="p-4 border-b">
            <Link to="/dashboard" className="flex items-center gap-2">
              <Database className="h-6 w-6 text-primary" />
              <span className="font-bold text-lg">PyBase</span>
            </Link>
          </div>

        {/* Navigation */}
        <nav className="flex-1 p-4 space-y-1">
          <Link
            to="/dashboard"
            className="flex items-center gap-2 px-3 py-2 rounded-md hover:bg-accent text-sm font-medium"
          >
            <LayoutGrid className="h-4 w-4" />
            Dashboard
          </Link>
          
          {/* Workspaces section */}
          <div className="pt-4">
            <div className="flex items-center justify-between px-3 py-2">
              <span className="text-xs font-semibold text-muted-foreground uppercase">
                Workspaces
              </span>
              <Button variant="ghost" size="icon" className="h-6 w-6">
                <Plus className="h-4 w-4" />
              </Button>
            </div>
            
            {/* Placeholder workspace items */}
            <div className="space-y-1">
              <button className="w-full flex items-center gap-2 px-3 py-2 rounded-md hover:bg-accent text-sm text-left">
                <ChevronDown className="h-4 w-4" />
                <span>My Workspace</span>
              </button>
            </div>
          </div>
        </nav>

         {/* User section */}
        <div className="p-4 border-t">
          <div className="flex items-center gap-3">
            <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center">
              <span className="text-sm font-medium text-primary">
                {user?.name?.charAt(0).toUpperCase() || 'U'}
              </span>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">{user?.name}</p>
              <p className="text-xs text-muted-foreground truncate">
                {user?.email}
              </p>
            </div>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setNotificationsOpen(true)}
              className="h-8 w-8"
            >
              <Bell className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              onClick={handleLogout}
              className="h-8 w-8"
            >
              <LogOut className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </aside>

       {/* Mobile Navigation Toggle */}
      <button
        onClick={() => setSidebarOpen(!sidebarOpen)}
        className="md:hidden fixed top-4 left-4 z-50 p-2 rounded-md bg-card border hover:bg-accent"
      >
        <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
        </svg>
      </button>

      {/* Mobile Sidebar Overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Main content */}
      <main className="flex-1 flex flex-col min-h-screen">
        <Outlet />
      </main>

      {/* Notification Center */}
      <NotificationCenter onClose={() => setNotificationsOpen(false)} />
    </div>
  )
}
