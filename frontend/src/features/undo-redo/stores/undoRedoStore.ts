import { create } from "zustand"
import type { OperationLogResponse } from "@/features/undo-redo/api/undoRedoApi"

const STORAGE_KEY = "undo_redo_operations"
const STORAGE_TIMESTAMP_KEY = "undo_redo_timestamp"
const MAX_OPERATIONS = 100
const STORAGE_EXPIRY_MS = 24 * 60 * 60 * 1000 // 24 hours

interface UndoRedoState {
  operations: OperationLogResponse[]
  currentIndex: number
  canUndo: boolean
  canRedo: boolean
  setOperations: (operations: OperationLogResponse[]) => void
  addOperation: (operation: OperationLogResponse) => void
  undo: () => OperationLogResponse | null
  redo: () => OperationLogResponse | null
  clear: () => void
  loadFromStorage: () => void
}

/**
 * Zustand store for managing undo/redo state.
 *
 * Provides:
 * - Operations stack (limited to MAX_OPERATIONS)
 * - Current position in stack (for undo/redo navigation)
 * - canUndo/canRedo flags
 * - localStorage persistence (24 hour expiry)
 *
 * @example
 * ```ts
 * const { operations, canUndo, canRedo, undo, redo } = useUndoRedoStore()
 *
 * // Undo last operation
 * if (canUndo) {
 *   const undone = undo()
 *   console.log(`Undone: ${undone?.operation_type}`)
 * }
 * ```
 */
export const useUndoRedoStore = create<UndoRedoState>((set, get) => ({
  operations: [],
  currentIndex: -1,
  canUndo: false,
  canRedo: false,

  setOperations: (operations: OperationLogResponse[]) => {
    const limitedOps = operations.slice(-MAX_OPERATIONS)
    const currentIndex = limitedOps.length - 1

    set({
      operations: limitedOps,
      currentIndex,
      canUndo: currentIndex > 0,
      canRedo: false,
    })

    saveToStorage(limitedOps)
  },

  addOperation: (operation: OperationLogResponse) => {
    const { operations, currentIndex } = get()

    // Remove any operations after current index (they're no longer valid)
    const newOperations = operations.slice(0, currentIndex + 1)

    // Add new operation
    newOperations.push(operation)

    // Limit to MAX_OPERATIONS
    const limitedOps = newOperations.slice(-MAX_OPERATIONS)
    const newCurrentIndex = limitedOps.length - 1

    set({
      operations: limitedOps,
      currentIndex: newCurrentIndex,
      canUndo: newCurrentIndex > 0,
      canRedo: false,
    })

    saveToStorage(limitedOps)
  },

  undo: () => {
    const { operations, currentIndex } = get()

    if (currentIndex < 0) {
      return null
    }

    const operation = operations[currentIndex]
    const newIndex = currentIndex - 1

    set({
      currentIndex: newIndex,
      canUndo: newIndex > 0,
      canRedo: true,
    })

    return operation
  },

  redo: () => {
    const { operations, currentIndex } = get()

    if (currentIndex >= operations.length - 1) {
      return null
    }

    const newIndex = currentIndex + 1
    const operation = operations[newIndex]

    set({
      currentIndex: newIndex,
      canUndo: true,
      canRedo: newIndex < operations.length - 1,
    })

    return operation
  },

  clear: () => {
    set({
      operations: [],
      currentIndex: -1,
      canUndo: false,
      canRedo: false,
    })

    localStorage.removeItem(STORAGE_KEY)
    localStorage.removeItem(STORAGE_TIMESTAMP_KEY)
  },

  loadFromStorage: () => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY)
      const timestamp = localStorage.getItem(STORAGE_TIMESTAMP_KEY)

      if (!stored || !timestamp) {
        return
      }

      // Check expiry
      const storedTime = parseInt(timestamp, 10)
      const now = Date.now()

      if (now - storedTime > STORAGE_EXPIRY_MS) {
        // Expired - clear storage
        get().clear()
        return
      }

      // Parse and set state
      const operations: OperationLogResponse[] = JSON.parse(stored)
      const limitedOps = operations.slice(-MAX_OPERATIONS)
      const currentIndex = limitedOps.length - 1

      set({
        operations: limitedOps,
        currentIndex,
        canUndo: currentIndex > 0,
        canRedo: false,
      })
    } catch (error) {
      // Invalid data in storage - clear it
      console.error("Failed to load operations from storage:", error)
      get().clear()
    }
  },
}))

/**
 * Save operations to localStorage with timestamp.
 */
function saveToStorage(operations: OperationLogResponse[]): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(operations))
    localStorage.setItem(STORAGE_TIMESTAMP_KEY, Date.now().toString())
  } catch (error) {
    console.error("Failed to save operations to storage:", error)
  }
}

// Initialize store from localStorage on module load
useUndoRedoStore.getState().loadFromStorage()
