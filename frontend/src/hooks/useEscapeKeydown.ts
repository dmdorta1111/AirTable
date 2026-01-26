import { useCallback } from 'react';

/**
 * Custom hook to handle Escape key press for canceling actions.
 * Centralizes the escape key handling logic used across cell editors.
 * 
 * @param onEscape - Callback function to execute when Escape is pressed
 * @returns A keydown event handler that can be attached to elements
 */
export const useEscapeKeydown = (onEscape?: () => void) => {
  return useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Escape' && onEscape) {
      e.preventDefault();
      onEscape();
    }
  }, [onEscape]);
};
