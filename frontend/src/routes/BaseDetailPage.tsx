import { useParams } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import { get } from "@/lib/api"
import type { Base, Table } from "@/types"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Link } from "react-router-dom"
import { ArrowLeft, Plus } from "lucide-react"

export default function BaseDetailPage() {
  const { baseId } = useParams<{ baseId: string }>()

  const { data: base } = useQuery({
    queryKey: ["bases", baseId],
    queryFn: () => get<Base>(`/bases/${baseId}`),
    enabled: !!baseId,
  })

  const { data: tables } = useQuery({
    queryKey: ["bases", baseId, "tables"],
    queryFn: () => get<Table[]>(`/bases/${baseId}/tables`),
    enabled: !!baseId,
  })

  if (!base) return <div>Loading...</div>

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Link to="/dashboard">
          <Button variant="ghost" size="icon">
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </Link>
        <div>
          <h1 className="text-3xl font-bold">{base.name}</h1>
          {base.description && (
            <p className="text-muted-foreground">{base.description}</p>
          )}
        </div>
      </div>

      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">Tables</h2>
        <Button>
          <Plus className="mr-2 h-4 w-4" />
          New Table
        </Button>
      </div>

      <div className="grid gap-4">
        {tables?.map((table) => (
          <Link key={table.id} to={`/bases/${baseId}/tables/${table.id}`}>
            <Card className="hover:bg-accent transition-colors cursor-pointer">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="text-lg">{table.name}</CardTitle>
                  <span className="text-2xl">{table.icon || "📊"}</span>
                </div>
                {table.description && <CardDescription>{table.description}</CardDescription>}
              </CardHeader>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  )
}