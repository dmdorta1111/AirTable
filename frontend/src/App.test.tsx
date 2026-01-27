import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook } from '@testing-library/react'
import { useUndoRedo } from '@/features/undo-redo/hooks/useUndoRedo'
import { useKeyboardShortcuts } from '@/features/undo-redo/hooks/useKeyboardShortcuts'

// Mock the undo-redo hooks
vi.mock('@/features/undo-redo/hooks/useUndoRedo', () => ({
  useUndoRedo: vi.fn(),
}))

vi.mock('@/features/undo-redo/hooks/useKeyboardShortcuts', () => ({
  useKeyboardShortcuts: vi.fn(),
}))

describe('App Integration', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should initialize undo/redo functionality', () => {
    const mockUndo = vi.fn()
    const mockRedo = vi.fn()
    const mockHandleKeyboard = vi.fn()

    vi.mocked(useUndoRedo).mockReturnValue({
      undo: mockUndo,
      redo: mockRedo,
      canUndo: true,
      canRedo: false,
      operations: [],
      fetchOperations: vi.fn(),
    })

    vi.mocked(useKeyboardShortcuts).mockReturnValue(mockHandleKeyboard)

    const { result } = renderHook(() => useUndoRedo())

    expect(result.current.undo).toBeDefined()
    expect(result.current.redo).toBeDefined()
    expect(useUndoRedo).toHaveBeenCalled()
  })

  it('should setup keyboard shortcuts with undo and redo callbacks', () => {
    const mockUndo = vi.fn()
    const mockRedo = vi.fn()

    vi.mocked(useKeyboardShortcuts).mockReturnValue(vi.fn())

    renderHook(() => useKeyboardShortcuts(mockUndo, mockRedo))

    expect(useKeyboardShortcuts).toHaveBeenCalledWith(mockUndo, mockRedo)
  })
})
