import { useState } from "react"
import { Checkbox } from "@/components/ui/checkbox"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { useTrashStore } from "../stores/trashStore"
import { formatDistanceToNow } from "date-fns"

interface TrashItemProps {
  item: {
    id: string
    table_id: string
    data: { [key: string]: unknown }
    deleted_at: string
    deleted_by_id: string | null
    created_at: string
    updated_at: string
    row_height: number
  }
  isSelected?: boolean
  onSelectionChange?: (itemId: string, selected: boolean) => void
  showCheckbox?: boolean
}

export default function TrashItem({
  item,
  isSelected = false,
  onSelectionChange,
  showCheckbox = true,
}: TrashItemProps) {
  const restoreRecord = useTrashStore((state) => state.restoreRecord)
  const permanentDeleteRecord = useTrashStore((state) => state.permanentDeleteRecord)
  const [loading, setLoading] = useState<"restore" | "delete" | null>(null)
  const [error, setError] = useState("")

  const handleRestore = async () => {
    setError("")
    setLoading("restore")
    try {
      await restoreRecord(item.id)
    } catch (err: any) {
      setError(err.message || "Failed to restore record")
    } finally {
      setLoading(null)
    }
  }

  const handlePermanentDelete = async () => {
    setError("")
    setLoading("delete")
    try {
      await permanentDeleteRecord(item.id)
    } catch (err: any) {
      setError(err.message || "Failed to permanently delete record")
    } finally {
      setLoading(null)
    }
  }

  const handleSelectionChange = (checked: boolean) => {
    if (onSelectionChange) {
      onSelectionChange(item.id, checked)
    }
  }

  // Get a display name from the record data
  const getDisplayName = () => {
    if (item.data.name && typeof item.data.name === "string") {
      return item.data.name
    }
    if (item.data.title && typeof item.data.title === "string") {
      return item.data.title
    }
    return `Record ${item.id.slice(0, 8)}`
  }

  const timeAgo = formatDistanceToNow(new Date(item.deleted_at), { addSuffix: true })

  return (
    <Card className="p-4">
      <div className="flex items-start gap-3">
        {showCheckbox && (
          <Checkbox
            checked={isSelected}
            onCheckedChange={handleSelectionChange}
            className="mt-1"
            disabled={loading !== null}
          />
        )}

        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2 mb-2">
            <h3 className="font-medium truncate">{getDisplayName()}</h3>
            <Badge variant="secondary" className="shrink-0">
              {item.table_id.slice(0, 8)}
            </Badge>
          </div>

          <div className="text-sm text-muted-foreground mb-3">
            <div>Deleted {timeAgo}</div>
            {item.deleted_by_id && (
              <div>By {item.deleted_by_id.slice(0, 8)}</div>
            )}
          </div>

          {error && (
            <div className="text-sm text-destructive mb-3">{error}</div>
          )}

          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant="outline"
              onClick={handleRestore}
              disabled={loading !== null}
            >
              {loading === "restore" ? "Restoring..." : "Restore"}
            </Button>

            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  size="sm"
                  variant="ghost"
                  disabled={loading !== null}
                >
                  More
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem
                  onClick={handlePermanentDelete}
                  className="text-destructive focus:text-destructive"
                  disabled={loading !== null}
                >
                  {loading === "delete" ? "Deleting..." : "Delete Permanently"}
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </div>
    </Card>
  )
}
