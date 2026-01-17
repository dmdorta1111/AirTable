import { useEffect, useCallback } from 'react'

export interface KeyboardShortcut {
  key: string
  ctrlKey?: boolean
  shiftKey?: boolean
  altKey?: boolean
  metaKey?: boolean
  description: string
  callback: () => void
  disabled?: boolean
}

interface UseKeyboardShortcutsOptions {
  shortcuts: KeyboardShortcut[]
  enabled?: boolean
}

export function useKeyboardShortcuts({ shortcuts, enabled = true }: UseKeyboardShortcutsOptions) {
  useEffect(() => {
    if (!enabled) return

    const handleKeyDown = (event: KeyboardEvent) => {
      const pressedKey = event.key.toLowerCase()

      shortcuts.forEach(shortcut => {
        // Check if all modifiers match
        const ctrlMatches = !shortcut.ctrlKey || (event.ctrlKey === shortcut.ctrlKey)
        const shiftMatches = !shortcut.shiftKey || (event.shiftKey === shortcut.shiftKey)
        const altMatches = !shortcut.altKey || (event.altKey === shortcut.altKey)
        const metaMatches = !shortcut.metaKey || (event.metaKey === shortcut.metaKey)

        // Check if key matches and all modifiers match
        const keyMatches = pressedKey === shortcut.key.toLowerCase()

        if (keyMatches && ctrlMatches && shiftMatches && altMatches && metaMatches) {
          event.preventDefault()
          event.stopPropagation()

          if (!shortcut.disabled) {
            shortcut.callback()
          }
        }
      })
    }

    document.addEventListener('keydown', handleKeyDown)

    return () => {
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [shortcuts, enabled])

  return {}
}
