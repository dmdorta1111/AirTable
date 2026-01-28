import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import { useUndoRedo } from "./useUndoRedo"
import { useUndoRedoStore } from "@/features/undo-redo/stores/undoRedoStore"
import { getOperations, undoOperation, redoOperation } from "@/features/undo-redo/api/undoRedoApi"
import type { OperationLogResponse } from "@/features/undo-redo/api/undoRedoApi"

// Mock the API functions
vi.mock("@/features/undo-redo/api/undoRedoApi", () => ({
  getOperations: vi.fn(),
  undoOperation: vi.fn(),
  redoOperation: vi.fn(),
}))

describe("useUndoRedo", () => {
  const createMockOperation = (
    id: string,
    type: string
  ): OperationLogResponse => ({
    id,
    user_id: "user-1",
    operation_type: type,
    entity_type: "record",
    entity_id: `record-${id}`,
    before_data: type === "create" ? null : { name: "Old" },
    after_data: type === "delete" ? null : { name: "New" },
    created_at: "2024-01-01T00:00:00Z",
    updated_at: "2024-01-01T00:00:00Z",
  })

  beforeEach(() => {
    vi.clearAllMocks()
    // Reset store state before each test
    useUndoRedoStore.getState().clear()
  })

  describe("initial state", () => {
    it("should initialize with default values", () => {
      vi.mocked(getOperations).mockResolvedValue({
        items: [],
        total: 0,
        page: 1,
        page_size: 100,
      })

      const { result } = renderHook(() => useUndoRedo())

      expect(result.current.canUndo).toBe(false)
      expect(result.current.canRedo).toBe(false)
      expect(result.current.operations).toEqual([])
      expect(typeof result.current.undo).toBe("function")
      expect(typeof result.current.redo).toBe("function")
      expect(typeof result.current.fetchOperations).toBe("function")
    })

    it("should fetch operations on mount", async () => {
      const mockOperations = [
        createMockOperation("op-1", "create"),
        createMockOperation("op-2", "update"),
      ]

      vi.mocked(getOperations).mockResolvedValue({
        items: mockOperations,
        total: 2,
        page: 1,
        page_size: 100,
      })

      const { result } = renderHook(() => useUndoRedo())

      await waitFor(() => {
        expect(getOperations).toHaveBeenCalledWith({ page_size: 100 })
      })

      await waitFor(() => {
        expect(result.current.operations).toEqual(mockOperations)
      })
    })
  })

  describe("undo", () => {
    it("should undo the last operation successfully", async () => {
      const mockOperations = [
        createMockOperation("op-1", "create"),
        createMockOperation("op-2", "update"),
      ]

      vi.mocked(getOperations).mockResolvedValue({
        items: mockOperations,
        total: 2,
        page: 1,
        page_size: 100,
      })

      vi.mocked(undoOperation).mockResolvedValue(mockOperations[1])

      const { result } = renderHook(() => useUndoRedo())

      // Wait for initial fetch
      await waitFor(() => {
        expect(result.current.operations).toEqual(mockOperations)
      })

      // Undo
      const undone = await result.current.undo()

      expect(undone).toEqual(mockOperations[1])
      expect(undoOperation).toHaveBeenCalledWith({ operation_id: "op-2" })
      expect(result.current.canUndo).toBe(false)
      expect(result.current.canRedo).toBe(true)
    })

    it("should return null when no operations to undo", async () => {
      vi.mocked(getOperations).mockResolvedValue({
        items: [],
        total: 0,
        page: 1,
        page_size: 100,
      })

      const { result } = renderHook(() => useUndoRedo())

      await waitFor(() => {
        expect(result.current.operations).toEqual([])
      })

      const undone = await result.current.undo()

      expect(undone).toBeNull()
      expect(undoOperation).not.toHaveBeenCalled()
    })

    it("should revert store state on undo API error", async () => {
      const mockOperations = [
        createMockOperation("op-1", "create"),
        createMockOperation("op-2", "update"),
      ]

      vi.mocked(getOperations).mockResolvedValue({
        items: mockOperations,
        total: 2,
        page: 1,
        page_size: 100,
      })

      const mockError = new Error("API Error")
      vi.mocked(undoOperation).mockRejectedValue(mockError)

      const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {})

      const { result } = renderHook(() => useUndoRedo())

      // Wait for initial fetch
      await waitFor(() => {
        expect(result.current.operations).toEqual(mockOperations)
      })

      // Try to undo - should fail and revert
      await expect(result.current.undo()).rejects.toThrow("API Error")

      // Store state should be reverted (canRedo should be false since we reverted)
      expect(result.current.canRedo).toBe(false)
      expect(consoleSpy).toHaveBeenCalledWith(
        "Failed to undo operation:",
        mockError
      )

      consoleSpy.mockRestore()
    })
  })

  describe("redo", () => {
    it("should redo the next operation successfully", async () => {
      const mockOperations = [
        createMockOperation("op-1", "create"),
        createMockOperation("op-2", "update"),
      ]

      vi.mocked(getOperations).mockResolvedValue({
        items: mockOperations,
        total: 2,
        page: 1,
        page_size: 100,
      })

      vi.mocked(undoOperation).mockResolvedValue(mockOperations[1])
      vi.mocked(redoOperation).mockResolvedValue(mockOperations[1])

      const { result } = renderHook(() => useUndoRedo())

      // Wait for initial fetch
      await waitFor(() => {
        expect(result.current.operations).toEqual(mockOperations)
      })

      // Undo first
      await result.current.undo()

      expect(result.current.canRedo).toBe(true)

      // Redo
      const redone = await result.current.redo()

      expect(redone).toEqual(mockOperations[1])
      expect(redoOperation).toHaveBeenCalledWith({ operation_id: "op-2" })
      expect(result.current.canUndo).toBe(true)
      expect(result.current.canRedo).toBe(false)
    })

    it("should return null when no operations to redo", async () => {
      const mockOperations = [createMockOperation("op-1", "create")]

      vi.mocked(getOperations).mockResolvedValue({
        items: mockOperations,
        total: 1,
        page: 1,
        page_size: 100,
      })

      const { result } = renderHook(() => useUndoRedo())

      await waitFor(() => {
        expect(result.current.operations).toEqual(mockOperations)
      })

      const redone = await result.current.redo()

      expect(redone).toBeNull()
      expect(redoOperation).not.toHaveBeenCalled()
    })

    it("should revert store state on redo API error", async () => {
      const mockOperations = [
        createMockOperation("op-1", "create"),
        createMockOperation("op-2", "update"),
      ]

      vi.mocked(getOperations).mockResolvedValue({
        items: mockOperations,
        total: 2,
        page: 1,
        page_size: 100,
      })

      vi.mocked(undoOperation).mockResolvedValue(mockOperations[1])

      const mockError = new Error("API Error")
      vi.mocked(redoOperation).mockRejectedValue(mockError)

      const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {})

      const { result } = renderHook(() => useUndoRedo())

      // Wait for initial fetch
      await waitFor(() => {
        expect(result.current.operations).toEqual(mockOperations)
      })

      // Undo first
      await result.current.undo()

      // Try to redo - should fail and revert
      await expect(result.current.redo()).rejects.toThrow("API Error")

      // Store state should be reverted (canUndo should be false since we reverted)
      expect(result.current.canUndo).toBe(false)
      expect(consoleSpy).toHaveBeenCalledWith(
        "Failed to redo operation:",
        mockError
      )

      consoleSpy.mockRestore()
    })
  })

  describe("fetchOperations", () => {
    it("should fetch operations and update store", async () => {
      const mockOperations = [
        createMockOperation("op-1", "create"),
        createMockOperation("op-2", "update"),
      ]

      vi.mocked(getOperations).mockResolvedValue({
        items: mockOperations,
        total: 2,
        page: 1,
        page_size: 100,
      })

      const { result } = renderHook(() => useUndoRedo())

      // Wait for automatic fetch on mount
      await waitFor(() => {
        expect(result.current.operations).toEqual(mockOperations)
      })

      expect(getOperations).toHaveBeenCalledWith({ page_size: 100 })
    })

    it("should handle fetch errors gracefully", async () => {
      const mockError = new Error("Network Error")
      vi.mocked(getOperations).mockRejectedValue(mockError)

      const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {})

      const { result } = renderHook(() => useUndoRedo())

      await waitFor(() => {
        expect(getOperations).toHaveBeenCalled()
      })

      expect(consoleSpy).toHaveBeenCalledWith(
        "Failed to fetch operations:",
        mockError
      )
      expect(result.current.operations).toEqual([])

      consoleSpy.mockRestore()
    })
  })

  describe("integration scenarios", () => {
    it("should handle complete undo/redo workflow", async () => {
      const mockOperations = [
        createMockOperation("op-1", "create"),
        createMockOperation("op-2", "update"),
        createMockOperation("op-3", "delete"),
      ]

      vi.mocked(getOperations).mockResolvedValue({
        items: mockOperations,
        total: 3,
        page: 1,
        page_size: 100,
      })

      vi.mocked(undoOperation).mockResolvedValue(mockOperations[2])
      vi.mocked(redoOperation).mockResolvedValue(mockOperations[2])

      const { result } = renderHook(() => useUndoRedo())

      // Wait for initial fetch
      await waitFor(() => {
        expect(result.current.operations).toEqual(mockOperations)
      })

      expect(result.current.canUndo).toBe(true)
      expect(result.current.canRedo).toBe(false)

      // Undo
      const undone = await result.current.undo()
      expect(undone?.id).toBe("op-3")
      expect(result.current.canUndo).toBe(true)
      expect(result.current.canRedo).toBe(true)

      // Redo
      const redone = await result.current.redo()
      expect(redone?.id).toBe("op-3")
      expect(result.current.canUndo).toBe(true)
      expect(result.current.canRedo).toBe(false)
    })
  })
})
