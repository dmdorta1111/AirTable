import { useEffect, useState } from "react"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { useTrashStore } from "../stores/trashStore"
import TrashItem from "./TrashItem"

export default function TrashBin({ tableId }: { tableId?: string }) {
  const { items, total, page, pageSize, isLoading, error, fetchTrash, batchRestoreRecords, batchPermanentDeleteRecords, clearError } = useTrashStore()

  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [bulkActionLoading, setBulkActionLoading] = useState<"restore" | "delete" | null>(null)
  const [showDeleteDialog, setShowDeleteDialog] = useState(false)
  const [bulkError, setBulkError] = useState("")

  useEffect(() => {
    fetchTrash({ table_id: tableId, page, page_size: pageSize })
  }, [tableId, page, pageSize])

  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      setSelectedIds(new Set(items.map((item) => item.id)))
    } else {
      setSelectedIds(new Set())
    }
  }

  const handleItemSelectionChange = (itemId: string, selected: boolean) => {
    setSelectedIds((prev) => {
      const newSet = new Set(prev)
      if (selected) {
        newSet.add(itemId)
      } else {
        newSet.delete(itemId)
      }
      return newSet
    })
  }

  const isAllSelected = items.length > 0 && selectedIds.size === items.length
  const isSomeSelected = selectedIds.size > 0

  const handleBulkRestore = async () => {
    if (selectedIds.size === 0) return

    setBulkActionLoading("restore")
    setBulkError("")
    clearError()

    try {
      await batchRestoreRecords(Array.from(selectedIds))
      setSelectedIds(new Set())
    } catch (err: any) {
      setBulkError(err.message || "Failed to restore some records")
    } finally {
      setBulkActionLoading(null)
    }
  }

  const handleBulkDelete = async () => {
    if (selectedIds.size === 0) return

    setBulkActionLoading("delete")
    setBulkError("")
    clearError()
    setShowDeleteDialog(false)

    try {
      await batchPermanentDeleteRecords(Array.from(selectedIds))
      setSelectedIds(new Set())
    } catch (err: any) {
      setBulkError(err.message || "Failed to permanently delete some records")
    } finally {
      setBulkActionLoading(null)
    }
  }

  const handlePageChange = (newPage: number) => {
    if (newPage >= 1 && newPage <= Math.ceil(total / pageSize)) {
      fetchTrash({ table_id: tableId, page: newPage, page_size: pageSize })
    }
  }

  const totalPages = Math.ceil(total / pageSize)

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle>Trash Bin</CardTitle>
        <CardDescription>
          {total === 0
            ? "No deleted records"
            : `${total} deleted record${total !== 1 ? "s" : ""}`}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Bulk Actions Bar */}
        {items.length > 0 && (
          <div className="flex items-center justify-between p-3 bg-muted rounded-lg">
            <div className="flex items-center gap-2">
              <Checkbox
                checked={isAllSelected}
                onCheckedChange={handleSelectAll}
                disabled={isLoading || bulkActionLoading !== null}
                aria-label="Select all"
              />
              <span className="text-sm text-muted-foreground">
                {selectedIds.size > 0
                  ? `${selectedIds.size} selected`
                  : "Select all"}
              </span>
            </div>

            {isSomeSelected && (
              <div className="flex items-center gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={handleBulkRestore}
                  disabled={bulkActionLoading !== null}
                >
                  {bulkActionLoading === "restore" ? "Restoring..." : "Restore Selected"}
                </Button>

                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={bulkActionLoading !== null}
                    >
                      Bulk Actions
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem
                      onClick={() => setShowDeleteDialog(true)}
                      className="text-destructive focus:text-destructive"
                      disabled={bulkActionLoading !== null}
                    >
                      {bulkActionLoading === "delete" ? "Deleting..." : "Delete Permanently"}
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            )}
          </div>
        )}

        {/* Error Display */}
        {(error || bulkError) && (
          <div className="text-sm text-destructive p-3 bg-destructive/10 rounded-lg">
            {error || bulkError}
          </div>
        )}

        {/* Trash Items List */}
        {isLoading ? (
          <div className="text-center py-8 text-muted-foreground">
            Loading trash items...
          </div>
        ) : items.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            {total === 0
              ? "Trash bin is empty"
              : "No items on this page"}
          </div>
        ) : (
          <div className="space-y-3">
            {items.map((item) => (
              <TrashItem
                key={item.id}
                item={item}
                isSelected={selectedIds.has(item.id)}
                onSelectionChange={handleItemSelectionChange}
                showCheckbox
              />
            ))}
          </div>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between pt-4 border-t">
            <div className="text-sm text-muted-foreground">
              Page {page} of {totalPages}
            </div>
            <div className="flex items-center gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={() => handlePageChange(page - 1)}
                disabled={page === 1 || isLoading || bulkActionLoading !== null}
              >
                Previous
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() => handlePageChange(page + 1)}
                disabled={page === totalPages || isLoading || bulkActionLoading !== null}
              >
                Next
              </Button>
            </div>
          </div>
        )}

        {/* Confirmation Dialog */}
        <Dialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Delete Permanently?</DialogTitle>
              <DialogDescription>
                Are you sure you want to permanently delete {selectedIds.size} record{selectedIds.size !== 1 ? "s" : ""}?
                This action cannot be undone.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => setShowDeleteDialog(false)}
                disabled={bulkActionLoading !== null}
              >
                Cancel
              </Button>
              <Button
                variant="destructive"
                onClick={handleBulkDelete}
                disabled={bulkActionLoading !== null}
              >
                {bulkActionLoading === "delete" ? "Deleting..." : "Delete Permanently"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </CardContent>
    </Card>
  )
}
