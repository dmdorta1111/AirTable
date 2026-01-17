import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card'
import { Plus, Database, Loader2 } from 'lucide-react'
import type { Base } from '@/types'

export default function DashboardPage() {
  const { data: bases, isLoading } = useQuery({
    queryKey: ['bases'],
    queryFn: async () => {
      const response = await api.get<{ items: Base[] }>('/bases')
      return response.data.items
    },
  })

  return (
    <div className="flex-1">
      {/* Header */}
      <header className="border-b bg-card">
        <div className="px-6 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">Dashboard</h1>
            <p className="text-muted-foreground">
              Manage your bases and workspaces
            </p>
          </div>
          <Button>
            <Plus className="h-4 w-4 mr-2" />
            New Base
          </Button>
        </div>
      </header>

      {/* Content */}
      <div className="p-6">
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : bases && bases.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {bases.map((base) => (
              <Link key={base.id} to={`/base/${base.id}`}>
                <Card className="hover:shadow-md transition-shadow cursor-pointer">
                  <CardHeader>
                    <div className="flex items-center gap-3">
                      <div
                        className="h-10 w-10 rounded-lg flex items-center justify-center"
                        style={{ backgroundColor: base.color || '#6366f1' }}
                      >
                        <Database className="h-5 w-5 text-white" />
                      </div>
                      <div>
                        <CardTitle className="text-base">{base.name}</CardTitle>
                        {base.description && (
                          <CardDescription className="line-clamp-1">
                            {base.description}
                          </CardDescription>
                        )}
                      </div>
                    </div>
                  </CardHeader>
                </Card>
              </Link>
            ))}
          </div>
        ) : (
          <Card className="max-w-md mx-auto">
            <CardContent className="pt-6 text-center">
              <Database className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <h3 className="font-semibold mb-2">No bases yet</h3>
              <p className="text-muted-foreground text-sm mb-4">
                Create your first base to get started
              </p>
              <Button>
                <Plus className="h-4 w-4 mr-2" />
                Create Base
              </Button>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}
