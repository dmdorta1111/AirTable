"use client"

import { useEffect, useRef } from "react"
import { useUndoRedoStore } from "@/features/undo-redo/stores/undoRedoStore"
import { useToast } from "@/hooks/use-toast"
import type { OperationLogResponse } from "@/features/undo-redo/api/undoRedoApi"

/**
 * UndoRedoToast component
 *
 * Provides visual feedback when undo/redo operations occur by displaying
 * toast notifications with descriptions of what was undone or redone.
 *
 * This component monitors the undo/redo store and automatically shows toasts
 * when the currentIndex changes (indicating an undo or redo action).
 *
 * @example
 * ```tsx
 * // In your App.tsx or root layout
 * import { UndoRedoToast } from "@/components/undo-redo/UndoRedoToast"
 *
 * function App() {
 *   return (
 *     <>
 *       <YourAppContent />
 *       <UndoRedoToast />
 *     </>
 *   )
 * }
 * ```
 */
export function UndoRedoToast() {
  const { operations, currentIndex } = useUndoRedoStore()
  const { toast } = useToast()
  const lastIndexRef = useRef<number>(-1)
  const lastOperationRef = useRef<OperationLogResponse | null>(null)
  const initializedRef = useRef<boolean>(false)

  useEffect(() => {
    // Initialize on first render - don't show toast
    if (!initializedRef.current) {
      initializedRef.current = true
      lastIndexRef.current = currentIndex
      return
    }

    // Only show toast if the index has changed
    if (currentIndex === lastIndexRef.current) {
      return
    }

    // Determine if this was an undo or redo action
    const isUndo = currentIndex < lastIndexRef.current
    const isRedo = currentIndex > lastIndexRef.current

    // Get the operation to show:
    // - For undo: show the operation we're leaving (at lastIndexRef)
    // - For redo: show the operation we're entering (at currentIndex)
    const operationIndex = isUndo ? lastIndexRef.current : currentIndex
    const operation = operations[operationIndex]

    if (!operation) {
      return
    }

    // Skip if this is the same operation we just showed (prevents duplicates)
    if (lastOperationRef.current?.id === operation.id) {
      return
    }

    // Generate toast message based on operation type and entity type
    const message = getOperationDescription(operation, isUndo ? "undo" : "redo")

    // Show the toast
    toast({
      title: isUndo ? "Undo" : "Redo",
      description: message,
      variant: "default",
    })

    // Update refs
    lastIndexRef.current = currentIndex
    lastOperationRef.current = operation
  }, [currentIndex, operations, toast])

  // This component doesn't render anything - it only shows toasts
  return null
}

/**
 * Generates a human-readable description of an undo/redo operation.
 *
 * @param operation - The operation that was undone or redone
 * @param action - Either "undo" or "redo"
 * @returns A description string for the toast
 *
 * @example
 * ```ts
 * getOperationDescription(
 *   { operation_type: "create", entity_type: "record", ... },
 *   "undo"
 * )
 * // Returns: "Record creation undone"
 * ```
 */
function getOperationDescription(
  operation: OperationLogResponse,
  action: "undo" | "redo"
): string {
  const { operation_type, entity_type } = operation

  // Capitalize operation type
  const opType = operation_type.charAt(0).toUpperCase() + operation_type.slice(1)

  // Capitalize entity type
  const entityType = entity_type.charAt(0).toUpperCase() + entity_type.slice(1)

  // Past tense for undo, present tense for redo
  const actionText = action === "undo" ? "undone" : "redone"

  return `${entityType} ${opType.toLowerCase()} ${actionText}`
}
