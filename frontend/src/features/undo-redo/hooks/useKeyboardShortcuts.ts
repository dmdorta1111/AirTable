import { useCallback } from 'react';

/**
 * Custom hook to handle keyboard shortcuts for undo/redo operations.
 * Centralizes the keyboard shortcut logic for Ctrl+Z (undo) and Ctrl+Shift+Z (redo).
 * Prevents default browser behavior to avoid interference with browser's native undo/redo.
 *
 * @param onUndo - Callback function to execute when Ctrl+Z is pressed
 * @param onRedo - Callback function to execute when Ctrl+Shift+Z is pressed
 * @returns A keydown event handler that can be attached to elements
 */
export const useKeyboardShortcuts = (
  onUndo?: () => void,
  onRedo?: () => void
) => {
  return useCallback((e: KeyboardEvent) => {
    // Check for Ctrl+Z (undo) - works on both Windows (Ctrl+Z) and Mac (Cmd+Z)
    if ((e.ctrlKey || e.metaKey) && e.key === 'z' && !e.shiftKey && onUndo) {
      e.preventDefault();
      onUndo();
    }
    // Check for Ctrl+Shift+Z (redo) - works on both Windows (Ctrl+Shift+Z) and Mac (Cmd+Shift+Z)
    else if ((e.ctrlKey || e.metaKey) && e.key === 'z' && e.shiftKey && onRedo) {
      e.preventDefault();
      onRedo();
    }
    // Check for Ctrl+Y (redo - Windows alternative)
    else if ((e.ctrlKey || e.metaKey) && e.key === 'y' && onRedo) {
      e.preventDefault();
      onRedo();
    }
  }, [onUndo, onRedo]);
};
