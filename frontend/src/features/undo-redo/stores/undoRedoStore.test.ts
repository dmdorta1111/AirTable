import { describe, it, expect, beforeEach, vi } from "vitest"
import { useUndoRedoStore } from "./undoRedoStore"
import type { OperationLogResponse } from "@/features/undo-redo/api/undoRedoApi"

describe("undoRedoStore", () => {
  beforeEach(() => {
    // Reset store state before each test
    useUndoRedoStore.getState().clear()
    localStorage.clear()
    vi.clearAllMocks()
  })

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

  describe("initial state", () => {
    it("should initialize with empty state", () => {
      const state = useUndoRedoStore.getState()

      expect(state.operations).toEqual([])
      expect(state.currentIndex).toBe(-1)
      expect(state.canUndo).toBe(false)
      expect(state.canRedo).toBe(false)
    })
  })

  describe("setOperations", () => {
    it("should set operations and update flags", () => {
      const { setOperations } = useUndoRedoStore.getState()

      const operations = [
        createMockOperation("op-1", "create"),
        createMockOperation("op-2", "update"),
      ]

      setOperations(operations)

      const state = useUndoRedoStore.getState()
      expect(state.operations).toEqual(operations)
      expect(state.currentIndex).toBe(1)
      expect(state.canUndo).toBe(true)
      expect(state.canRedo).toBe(false)
    })

    it("should limit operations to MAX_OPERATIONS (100)", () => {
      const { setOperations } = useUndoRedoStore.getState()

      // Create 105 operations
      const operations = Array.from({ length: 105 }, (_, i) =>
        createMockOperation(`op-${i}`, "create")
      )

      setOperations(operations)

      const state = useUndoRedoStore.getState()
      expect(state.operations.length).toBe(100)
      expect(state.operations[0].id).toBe("op-5") // First 5 should be removed
      expect(state.operations[99].id).toBe("op-104")
    })

    it("should save to localStorage when setting operations", () => {
      const { setOperations } = useUndoRedoStore.getState()

      const operations = [createMockOperation("op-1", "create")]

      setOperations(operations)

      expect(localStorage.getItem("undo_redo_operations")).toBeTruthy()
      expect(localStorage.getItem("undo_redo_timestamp")).toBeTruthy()
    })
  })

  describe("addOperation", () => {
    it("should add operation and update flags", () => {
      const { addOperation } = useUndoRedoStore.getState()

      const operation = createMockOperation("op-1", "create")
      addOperation(operation)

      const state = useUndoRedoStore.getState()
      expect(state.operations).toEqual([operation])
      expect(state.currentIndex).toBe(0)
      expect(state.canUndo).toBe(false)
      expect(state.canRedo).toBe(false)
    })

    it("should remove operations after current index when adding new operation", () => {
      const { setOperations, addOperation, undo } = useUndoRedoStore.getState()

      // Add 3 operations
      const ops = [
        createMockOperation("op-1", "create"),
        createMockOperation("op-2", "update"),
        createMockOperation("op-3", "update"),
      ]
      setOperations(ops)

      // Undo once (currentIndex goes to 1)
      undo()

      // Add new operation - should remove op-3
      const newOp = createMockOperation("op-4", "create")
      addOperation(newOp)

      const state = useUndoRedoStore.getState()
      expect(state.operations.length).toBe(3)
      expect(state.operations[2].id).toBe("op-4")
      expect(state.currentIndex).toBe(2)
    })

    it("should limit operations to MAX_OPERATIONS when adding", () => {
      const { setOperations, addOperation } = useUndoRedoStore.getState()

      // Set 100 operations (at limit)
      const operations = Array.from({ length: 100 }, (_, i) =>
        createMockOperation(`op-${i}`, "create")
      )
      setOperations(operations)

      // Add one more
      const newOp = createMockOperation("op-100", "create")
      addOperation(newOp)

      const state = useUndoRedoStore.getState()
      expect(state.operations.length).toBe(100)
      expect(state.operations[0].id).toBe("op-1") // First operation removed
      expect(state.operations[99].id).toBe("op-100")
    })
  })

  describe("undo", () => {
    it("should undo last operation and return it", () => {
      const { setOperations, undo } = useUndoRedoStore.getState()

      const operations = [
        createMockOperation("op-1", "create"),
        createMockOperation("op-2", "update"),
      ]
      setOperations(operations)

      const undone = undo()

      expect(undone).toEqual(operations[1])
      const state = useUndoRedoStore.getState()
      expect(state.currentIndex).toBe(0)
      expect(state.canUndo).toBe(false)
      expect(state.canRedo).toBe(true)
    })

    it("should return null when no operations to undo", () => {
      const { undo } = useUndoRedoStore.getState()

      const undone = undo()

      expect(undone).toBeNull()
    })

    it("should update canUndo to false when at beginning", () => {
      const { setOperations, undo } = useUndoRedoStore.getState()

      const operations = [
        createMockOperation("op-1", "create"),
        createMockOperation("op-2", "update"),
      ]
      setOperations(operations)

      undo()
      undo()

      const state = useUndoRedoStore.getState()
      expect(state.canUndo).toBe(false)
      expect(state.canRedo).toBe(true)
    })

    it("should allow multiple undos", () => {
      const { setOperations, undo } = useUndoRedoStore.getState()

      const operations = [
        createMockOperation("op-1", "create"),
        createMockOperation("op-2", "update"),
        createMockOperation("op-3", "update"),
      ]
      setOperations(operations)

      undo()
      undo()

      const state = useUndoRedoStore.getState()
      expect(state.currentIndex).toBe(0)
      expect(state.canUndo).toBe(false)
      expect(state.canRedo).toBe(true)
    })
  })

  describe("redo", () => {
    it("should redo next operation and return it", () => {
      const { setOperations, undo, redo } = useUndoRedoStore.getState()

      const operations = [
        createMockOperation("op-1", "create"),
        createMockOperation("op-2", "update"),
      ]
      setOperations(operations)

      undo() // currentIndex goes to 0
      const redone = redo()

      expect(redone).toEqual(operations[1])
      const state = useUndoRedoStore.getState()
      expect(state.currentIndex).toBe(1)
      expect(state.canUndo).toBe(true)
      expect(state.canRedo).toBe(false)
    })

    it("should return null when no operations to redo", () => {
      const { setOperations, redo } = useUndoRedoStore.getState()

      const operations = [createMockOperation("op-1", "create")]
      setOperations(operations)

      const redone = redo()

      expect(redone).toBeNull()
    })

    it("should update canRedo to false when at end", () => {
      const { setOperations, undo, redo } = useUndoRedoStore.getState()

      const operations = [
        createMockOperation("op-1", "create"),
        createMockOperation("op-2", "update"),
      ]
      setOperations(operations)

      undo()
      redo()

      const state = useUndoRedoStore.getState()
      expect(state.canUndo).toBe(true)
      expect(state.canRedo).toBe(false)
    })
  })

  describe("clear", () => {
    it("should clear all state and localStorage", () => {
      const { setOperations, clear } = useUndoRedoStore.getState()

      const operations = [createMockOperation("op-1", "create")]
      setOperations(operations)

      clear()

      const state = useUndoRedoStore.getState()
      expect(state.operations).toEqual([])
      expect(state.currentIndex).toBe(-1)
      expect(state.canUndo).toBe(false)
      expect(state.canRedo).toBe(false)
      expect(localStorage.getItem("undo_redo_operations")).toBeNull()
      expect(localStorage.getItem("undo_redo_timestamp")).toBeNull()
    })
  })

  describe("localStorage persistence", () => {
    it("should load operations from localStorage on initialization", () => {
      const operations = [
        createMockOperation("op-1", "create"),
        createMockOperation("op-2", "update"),
      ]

      localStorage.setItem("undo_redo_operations", JSON.stringify(operations))
      localStorage.setItem("undo_redo_timestamp", Date.now().toString())

      // Create new store instance to trigger initialization
      const store = useUndoRedoStore.getState()
      store.loadFromStorage()

      const state = useUndoRedoStore.getState()
      expect(state.operations).toEqual(operations)
      expect(state.currentIndex).toBe(1)
      expect(state.canUndo).toBe(true)
    })

    it("should not load expired operations (> 24 hours)", () => {
      const operations = [createMockOperation("op-1", "create")]

      localStorage.setItem("undo_redo_operations", JSON.stringify(operations))
      // Set timestamp to 25 hours ago
      const expiredTime = Date.now() - 25 * 60 * 60 * 1000
      localStorage.setItem("undo_redo_timestamp", expiredTime.toString())

      const store = useUndoRedoStore.getState()
      store.loadFromStorage()

      const state = useUndoRedoStore.getState()
      expect(state.operations).toEqual([])
      expect(localStorage.getItem("undo_redo_operations")).toBeNull()
    })

    it("should handle corrupted localStorage data gracefully", () => {
      localStorage.setItem("undo_redo_operations", "invalid json")
      localStorage.setItem("undo_redo_timestamp", Date.now().toString())

      const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {})

      const store = useUndoRedoStore.getState()
      store.loadFromStorage()

      const state = useUndoRedoStore.getState()
      expect(state.operations).toEqual([])
      expect(consoleSpy).toHaveBeenCalled()

      consoleSpy.mockRestore()
    })

    it("should limit loaded operations to MAX_OPERATIONS", () => {
      const operations = Array.from({ length: 105 }, (_, i) =>
        createMockOperation(`op-${i}`, "create")
      )

      localStorage.setItem("undo_redo_operations", JSON.stringify(operations))
      localStorage.setItem("undo_redo_timestamp", Date.now().toString())

      const store = useUndoRedoStore.getState()
      store.loadFromStorage()

      const state = useUndoRedoStore.getState()
      expect(state.operations.length).toBe(100)
    })
  })

  describe("integration scenarios", () => {
    it("should handle typical undo/redo workflow", () => {
      const { addOperation, undo, redo } = useUndoRedoStore.getState()

      // Create operations
      const op1 = createMockOperation("op-1", "create")
      const op2 = createMockOperation("op-2", "update")
      const op3 = createMockOperation("op-3", "delete")

      addOperation(op1)
      addOperation(op2)
      addOperation(op3)

      let state = useUndoRedoStore.getState()
      expect(state.currentIndex).toBe(2)
      expect(state.canUndo).toBe(true)
      expect(state.canRedo).toBe(false)

      // Undo
      const undone = undo()
      expect(undone?.id).toBe("op-3")

      state = useUndoRedoStore.getState()
      expect(state.currentIndex).toBe(1)
      expect(state.canUndo).toBe(true)
      expect(state.canRedo).toBe(true)

      // Redo
      const redone = redo()
      expect(redone?.id).toBe("op-3")

      state = useUndoRedoStore.getState()
      expect(state.currentIndex).toBe(2)
      expect(state.canUndo).toBe(true)
      expect(state.canRedo).toBe(false)
    })

    it("should reset redo stack when adding new operation after undo", () => {
      const { addOperation, undo, redo } = useUndoRedoStore.getState()

      const op1 = createMockOperation("op-1", "create")
      const op2 = createMockOperation("op-2", "update")
      const op3 = createMockOperation("op-3", "update")

      addOperation(op1)
      addOperation(op2)
      addOperation(op3)

      undo() // Back to op-2

      const op4 = createMockOperation("op-4", "create")
      addOperation(op4) // Should clear op-3 from redo stack

      const state = useUndoRedoStore.getState()
      expect(state.operations.length).toBe(3)
      expect(state.operations[2].id).toBe("op-4")
      expect(state.canRedo).toBe(false)

      const redone = redo()
      expect(redone).toBeNull() // Nothing to redo
    })
  })
})
