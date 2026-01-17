import { Outlet } from 'react-router-dom'

export default function AuthLayout() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800">
      <div className="w-full max-w-md mx-4">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-primary">PyBase</h1>
          <p className="text-muted-foreground mt-2">
            Self-hosted Airtable alternative
          </p>
        </div>
        <Outlet />
      </div>
    </div>
  )
}
