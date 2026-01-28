import { useEffect } from "react"
import { RouterProvider } from "react-router-dom"
import { router } from "@/lib/router"
import { Toaster } from "@/components/ui/toaster"
import { useUndoRedo } from "@/features/undo-redo/hooks/useUndoRedo"
import { useKeyboardShortcuts } from "@/features/undo-redo/hooks/useKeyboardShortcuts"
import { UndoRedoToast } from "@/components/undo-redo/UndoRedoToast"

function App() {
  // Initialize undo/redo functionality
  const { undo, redo } = useUndoRedo()

  // Setup keyboard shortcuts for undo/redo
  const handleKeyboardShortcuts = useKeyboardShortcuts(undo, redo)

  // Attach keyboard event listener at app level
  useEffect(() => {
    window.addEventListener("keydown", handleKeyboardShortcuts)
    return () => {
      window.removeEventListener("keydown", handleKeyboardShortcuts)
    }
  }, [handleKeyboardShortcuts])

  return (
    <>
      <RouterProvider router={router} />
      <Toaster />
      <UndoRedoToast />
    </>
  )
}

export default App
