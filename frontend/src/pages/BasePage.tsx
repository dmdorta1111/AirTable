import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Plus, Table2, Loader2, ChevronLeft } from 'lucide-react'
import type { Base, Table } from '@/types'

export default function BasePage() {
  const { baseId } = useParams<{ baseId: string }>()

  const { data: base, isLoading: baseLoading } = useQuery({
    queryKey: ['base', baseId],
    queryFn: async () => {
      const response = await api.get<Base>(`/bases/${baseId}`)
      return response.data
    },
    enabled: !!baseId,
  })

  const { data: tables, isLoading: tablesLoading } = useQuery({
    queryKey: ['tables', baseId],
    queryFn: async () => {
      const response = await api.get<{ items: Table[] }>(`/tables?base_id=${baseId}`)
      return response.data.items
    },
    enabled: !!baseId,
  })

  const isLoading = baseLoading || tablesLoading

  return (
    <div className="flex-1">
      {/* Header */}
      <header className="border-b bg-card">
        <div className="px-6 py-4">
          <div className="flex items-center gap-2 text-sm text-muted-foreground mb-2">
            <Link to="/dashboard" className="hover:text-foreground">
              <ChevronLeft className="h-4 w-4 inline" />
              Dashboard
            </Link>
          </div>
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold">{base?.name || 'Loading...'}</h1>
              {base?.description && (
                <p className="text-muted-foreground">{base.description}</p>
              )}
            </div>
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              New Table
            </Button>
          </div>
        </div>
      </header>

      {/* Content */}
      <div className="p-6">
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : tables && tables.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {tables.map((table) => (
              <Link key={table.id} to={`/base/${baseId}/table/${table.id}`}>
                <Card className="hover:shadow-md transition-shadow cursor-pointer">
                  <CardHeader>
                    <div className="flex items-center gap-3">
                      <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center">
                        <Table2 className="h-5 w-5 text-primary" />
                      </div>
                      <div>
                        <CardTitle className="text-base">{table.name}</CardTitle>
                        {table.description && (
                          <p className="text-sm text-muted-foreground line-clamp-1">
                            {table.description}
                          </p>
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
              <Table2 className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <h3 className="font-semibold mb-2">No tables yet</h3>
              <p className="text-muted-foreground text-sm mb-4">
                Create your first table to get started
              </p>
              <Button>
                <Plus className="h-4 w-4 mr-2" />
                Create Table
              </Button>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}
