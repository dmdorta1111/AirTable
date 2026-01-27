import { create } from "zustand"
import type { TrashItem } from "@/types"
import * as trashApi from "../api/trashApi"

interface TrashState {
  items: TrashItem[]
  total: number
  page: number
  pageSize: number
  isLoading: boolean
  error: string | null
  fetchTrash: (params?: { table_id?: string; page?: number; page_size?: number }) => Promise<void>
  restoreRecord: (recordId: string) => Promise<void>
  batchRestoreRecords: (recordIds: string[]) => Promise<void>
  permanentDeleteRecord: (recordId: string) => Promise<void>
  batchPermanentDeleteRecords: (recordIds: string[]) => Promise<void>
  clearError: () => void
}

export const useTrashStore = create<TrashState>((set) => ({
  items: [],
  total: 0,
  page: 1,
  pageSize: 20,
  isLoading: false,
  error: null,

  fetchTrash: async (params) => {
    set({ isLoading: true, error: null })
    try {
      const response = await trashApi.listTrash(params)
      set({
        items: response.items,
        total: response.total,
        page: response.page,
        pageSize: response.page_size,
        isLoading: false,
      })
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Failed to fetch trash items"
      set({ error: errorMessage, isLoading: false })
    }
  },

  restoreRecord: async (recordId) => {
    set({ isLoading: true, error: null })
    try {
      await trashApi.restoreRecord(recordId)
      // Remove the restored item from the list
      set((state) => ({
        items: state.items.filter((item) => item.id !== recordId),
        total: state.total - 1,
        isLoading: false,
      }))
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Failed to restore record"
      set({ error: errorMessage, isLoading: false })
      throw error
    }
  },

  batchRestoreRecords: async (recordIds) => {
    set({ isLoading: true, error: null })
    try {
      const response = await trashApi.batchRestoreRecords(recordIds)
      // Remove successfully restored items from the list
      const restoredIds = response.results
        .filter((result) => result.success)
        .map((result) => result.record_id)
      set((state) => ({
        items: state.items.filter((item) => !restoredIds.includes(item.id)),
        total: state.total - restoredIds.length,
        isLoading: false,
      }))
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Failed to batch restore records"
      set({ error: errorMessage, isLoading: false })
      throw error
    }
  },

  permanentDeleteRecord: async (recordId) => {
    set({ isLoading: true, error: null })
    try {
      await trashApi.permanentDeleteRecord(recordId)
      // Remove the permanently deleted item from the list
      set((state) => ({
        items: state.items.filter((item) => item.id !== recordId),
        total: state.total - 1,
        isLoading: false,
      }))
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Failed to permanently delete record"
      set({ error: errorMessage, isLoading: false })
      throw error
    }
  },

  batchPermanentDeleteRecords: async (recordIds) => {
    set({ isLoading: true, error: null })
    try {
      const response = await trashApi.batchPermanentDeleteRecords(recordIds)
      // Remove successfully deleted items from the list
      const deletedIds = response.results
        .filter((result) => result.success)
        .map((result) => result.record_id)
      set((state) => ({
        items: state.items.filter((item) => !deletedIds.includes(item.id)),
        total: state.total - deletedIds.length,
        isLoading: false,
      }))
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Failed to batch permanently delete records"
      set({ error: errorMessage, isLoading: false })
      throw error
    }
  },

  clearError: () => {
    set({ error: null })
  },
}))
