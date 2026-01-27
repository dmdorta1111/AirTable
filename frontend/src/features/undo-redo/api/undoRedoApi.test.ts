import { describe, it, expect, vi, beforeEach } from "vitest"
import { getOperations, undoOperation, redoOperation } from "./undoRedoApi"
import { get, post } from "@/lib/api"

// Mock the API functions
vi.mock("@/lib/api", () => ({
  get: vi.fn(),
  post: vi.fn(),
}))

describe("undoRedoApi", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe("getOperations", () => {
    it("should fetch operations without parameters", async () => {
      const mockResponse = {
        items: [
          {
            id: "op-1",
            user_id: "user-1",
            operation_type: "create",
            entity_type: "record",
            entity_id: "record-1",
            before_data: null,
            after_data: { name: "Test" },
            created_at: "2024-01-01T00:00:00Z",
            updated_at: "2024-01-01T00:00:00Z",
          },
        ],
        total: 1,
        page: 1,
        page_size: 20,
      }

      vi.mocked(get).mockResolvedValue(mockResponse)

      const result = await getOperations()

      expect(get).toHaveBeenCalledWith("/api/v1/undo-redo/operations")
      expect(result).toEqual(mockResponse)
    })

    it("should fetch operations with pagination parameters", async () => {
      const mockResponse = {
        items: [],
        total: 0,
        page: 2,
        page_size: 50,
      }

      vi.mocked(get).mockResolvedValue(mockResponse)

      await getOperations({ page: 2, page_size: 50 })

      expect(get).toHaveBeenCalledWith("/api/v1/undo-redo/operations?page=2&page_size=50")
    })

    it("should fetch operations with filter parameters", async () => {
      const mockResponse = {
        items: [],
        total: 0,
        page: 1,
        page_size: 20,
      }

      vi.mocked(get).mockResolvedValue(mockResponse)

      await getOperations({
        operation_type: "update",
        entity_type: "record",
      })

      expect(get).toHaveBeenCalledWith("/api/v1/undo-redo/operations?operation_type=update&entity_type=record")
    })

    it("should fetch operations with all parameters", async () => {
      const mockResponse = {
        items: [],
        total: 0,
        page: 1,
        page_size: 20,
      }

      vi.mocked(get).mockResolvedValue(mockResponse)

      await getOperations({
        page: 1,
        page_size: 20,
        operation_type: "delete",
        entity_type: "field",
      })

      expect(get).toHaveBeenCalledWith(
        "/api/v1/undo-redo/operations?page=1&page_size=20&operation_type=delete&entity_type=field"
      )
    })
  })

  describe("undoOperation", () => {
    it("should undo an operation", async () => {
      const mockResponse = {
        id: "op-1",
        user_id: "user-1",
        operation_type: "create",
        entity_type: "record",
        entity_id: "record-1",
        before_data: null,
        after_data: { name: "Test" },
        created_at: "2024-01-01T00:00:00Z",
        updated_at: "2024-01-01T00:00:00Z",
      }

      vi.mocked(post).mockResolvedValue(mockResponse)

      const request = { operation_id: "op-1" }
      const result = await undoOperation(request)

      expect(post).toHaveBeenCalledWith("/api/v1/undo-redo/undo", request)
      expect(result).toEqual(mockResponse)
    })

    it("should pass operation_id in request body", async () => {
      const mockResponse = {
        id: "op-2",
        user_id: "user-1",
        operation_type: "update",
        entity_type: "record",
        entity_id: "record-1",
        before_data: { name: "Old" },
        after_data: { name: "New" },
        created_at: "2024-01-01T00:00:00Z",
        updated_at: "2024-01-01T00:00:00Z",
      }

      vi.mocked(post).mockResolvedValue(mockResponse)

      const request = { operation_id: "op-2" }
      await undoOperation(request)

      expect(post).toHaveBeenCalledWith("/api/v1/undo-redo/undo", request)
    })
  })

  describe("redoOperation", () => {
    it("should redo an operation", async () => {
      const mockResponse = {
        id: "op-1",
        user_id: "user-1",
        operation_type: "create",
        entity_type: "record",
        entity_id: "record-1",
        before_data: null,
        after_data: { name: "Test" },
        created_at: "2024-01-01T00:00:00Z",
        updated_at: "2024-01-01T00:00:00Z",
      }

      vi.mocked(post).mockResolvedValue(mockResponse)

      const request = { operation_id: "op-1" }
      const result = await redoOperation(request)

      expect(post).toHaveBeenCalledWith("/api/v1/undo-redo/redo", request)
      expect(result).toEqual(mockResponse)
    })

    it("should pass operation_id in request body", async () => {
      const mockResponse = {
        id: "op-3",
        user_id: "user-1",
        operation_type: "delete",
        entity_type: "record",
        entity_id: "record-1",
        before_data: { name: "Test" },
        after_data: null,
        created_at: "2024-01-01T00:00:00Z",
        updated_at: "2024-01-01T00:00:00Z",
      }

      vi.mocked(post).mockResolvedValue(mockResponse)

      const request = { operation_id: "op-3" }
      await redoOperation(request)

      expect(post).toHaveBeenCalledWith("/api/v1/undo-redo/redo", request)
    })
  })
})
