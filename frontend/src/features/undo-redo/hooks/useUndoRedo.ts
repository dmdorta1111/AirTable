import { useEffect, useCallback } from "react"
import { useUndoRedoStore } from "@/features/undo-redo/stores/undoRedoStore"
import { getOperations, undoOperation, redoOperation } from "@/features/undo-redo/api/undoRedoApi"
import type { OperationLogResponse } from "@/features/undo-redo/api/undoRedoApi"

/**
 * Custom hook for managing undo/redo functionality.
 *
 * Provides undo/redo operations with automatic API synchronization
 * and fetches the user's operation history on mount.
 *
 * @example
 * ```tsx
 * function MyComponent() {
 *   const { undo, redo, canUndo, canRedo, isLoading } = useUndoRedo()
 *
 *   return (
 *     <div>
 *       <button onClick={undo} disabled={!canUndo}>Undo</button>
 *       <button onClick={redo} disabled={!canRedo}>Redo</button>
 *     </div>
 *   )
 * }
 * ```
 */
export const useUndoRedo = () => {
  const { operations, canUndo, canRedo, setOperations, undo: storeUndo, redo: storeRedo } =
    useUndoRedoStore()

  /**
   * Fetches operations from the API and updates the store.
   * Called automatically on mount.
   */
  const fetchOperations = useCallback(async () => {
    try {
      const response = await getOperations({ page_size: 100 })
      setOperations(response.items)
    } catch (error) {
      console.error("Failed to fetch operations:", error)
    }
  }, [setOperations])

  /**
   * Undoes the last operation via API and updates local store.
   */
  const undo = useCallback(async () => {
    const operationToUndo = storeUndo()
    if (!operationToUndo) {
      return null
    }

    try {
      const result = await undoOperation({ operation_id: operationToUndo.id })
      return result
    } catch (error) {
      console.error("Failed to undo operation:", error)
      // Revert the store state on error
      storeRedo()
      throw error
    }
  }, [storeUndo, storeRedo])

  /**
   * Redoes the next operation via API and updates local store.
   */
  const redo = useCallback(async () => {
    const operationToRedo = storeRedo()
    if (!operationToRedo) {
      return null
    }

    try {
      const result = await redoOperation({ operation_id: operationToRedo.id })
      return result
    } catch (error) {
      console.error("Failed to redo operation:", error)
      // Revert the store state on error
      storeUndo()
      throw error
    }
  }, [storeRedo, storeUndo])

  // Fetch operations on mount
  useEffect(() => {
    fetchOperations()
  }, [fetchOperations])

  return {
    operations,
    canUndo,
    canRedo,
    undo,
    redo,
    fetchOperations,
  }
}
