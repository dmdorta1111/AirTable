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
        <nav className="space-y-4 animate-pulse">
          <div>
            {/* Header skeleton */}
            <div className="h-4 bg-muted w-24 rounded mb-2" />

            {/* Workspace skeletons */}
            <ul className="space-y-1">
              {[...Array(3)].map((_, i) => (
                <li key={i}>
                  {/* Workspace name skeleton */}
                  <div className="h-4 bg-muted w-32 rounded" />

                  {/* Nested base skeletons */}
                  <ul className="ml-4 mt-2 space-y-1">
                    {[...Array(2 + (i % 2))].map((_, j) => (
                      <li key={j}>
                        <div className="h-3 bg-muted w-28 rounded py-1" />
                      </li>
                    ))}
                  </ul>
                </li>
              ))}
            </ul>
          </div>
        </nav>
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