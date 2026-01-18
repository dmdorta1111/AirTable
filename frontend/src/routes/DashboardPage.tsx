import { useQuery } from "@tanstack/react-query"
import { get } from "@/lib/api"
import type { Workspace, Base } from "@/types"
import { Link } from "react-router-dom"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Plus } from "lucide-react"

export default function DashboardPage() {
  const { data: workspaces, isLoading: workspacesLoading } = useQuery({
    queryKey: ["workspaces"],
    queryFn: () => get<Workspace[]>("/workspaces"),
  })

  const { data: bases, isLoading: basesLoading } = useQuery({
    queryKey: ["bases"],
    queryFn: () => get<Base[]>("/bases"),
  })

  if (workspacesLoading || basesLoading) {
    return <div className="flex items-center justify-center h-full">Loading...</div>
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Dashboard</h1>
          <p className="text-muted-foreground">Manage your bases and tables</p>
        </div>
        <Button>
          <Plus className="mr-2 h-4 w-4" />
          New Base
        </Button>
      </div>

      <div className="grid gap-6">
        {workspaces?.map((workspace) => (
          <Card key={workspace.id}>
            <CardHeader>
              <CardTitle>{workspace.name}</CardTitle>
              {workspace.description && (
                <CardDescription>{workspace.description}</CardDescription>
              )}
            </CardHeader>
            <CardContent>
              <div className="grid gap-4">
                {bases
                  ?.filter((b) => b.workspace_id === workspace.id)
                  .map((base) => (
                    <Link key={base.id} to={`/bases/${base.id}`}>
                      <Card className="hover:bg-accent transition-colors cursor-pointer">
                        <CardHeader>
                          <div className="flex items-center justify-between">
                            <CardTitle className="text-lg">{base.name}</CardTitle>
                            <span className="text-sm text-muted-foreground">
                              {base.icon || "📊"}
                            </span>
                          </div>
                          {base.description && <CardDescription>{base.description}</CardDescription>}
                        </CardHeader>
                      </Card>
                    </Link>
                  ))}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}