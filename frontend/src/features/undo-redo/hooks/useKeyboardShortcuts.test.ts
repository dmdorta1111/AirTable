import { describe, it, expect, vi } from "vitest"
import { renderHook } from "@testing-library/react"
import { useKeyboardShortcuts } from "./useKeyboardShortcuts"

describe("useKeyboardShortcuts", () => {
  describe("Ctrl+Z (undo)", () => {
    it("should call onUndo when Ctrl+Z is pressed", () => {
      const onUndo = vi.fn()
      const { result } = renderHook(() => useKeyboardShortcuts(onUndo))

      const event = new KeyboardEvent("keydown", {
        key: "z",
        ctrlKey: true,
        bubbles: true,
      })
      Object.defineProperty(event, "preventDefault", { value: vi.fn() })

      window.dispatchEvent(event)
      result.current(event)

      expect(event.preventDefault).toHaveBeenCalled()
      expect(onUndo).toHaveBeenCalled()
    })

    it("should call onUndo when Cmd+Z is pressed (Mac)", () => {
      const onUndo = vi.fn()
      const { result } = renderHook(() => useKeyboardShortcuts(onUndo))

      const event = new KeyboardEvent("keydown", {
        key: "z",
        metaKey: true,
        bubbles: true,
      })
      Object.defineProperty(event, "preventDefault", { value: vi.fn() })

      result.current(event)

      expect(event.preventDefault).toHaveBeenCalled()
      expect(onUndo).toHaveBeenCalled()
    })

    it("should not call onUndo when Ctrl+Shift+Z is pressed", () => {
      const onUndo = vi.fn()
      const onRedo = vi.fn()
      const { result } = renderHook(() => useKeyboardShortcuts(onUndo, onRedo))

      const event = new KeyboardEvent("keydown", {
        key: "z",
        ctrlKey: true,
        shiftKey: true,
        bubbles: true,
      })
      Object.defineProperty(event, "preventDefault", { value: vi.fn() })

      result.current(event)

      expect(onUndo).not.toHaveBeenCalled()
      expect(onRedo).toHaveBeenCalled()
    })

    it("should not call onUndo when only Z is pressed without Ctrl/Cmd", () => {
      const onUndo = vi.fn()
      const { result } = renderHook(() => useKeyboardShortcuts(onUndo))

      const event = new KeyboardEvent("keydown", {
        key: "z",
        bubbles: true,
      })
      Object.defineProperty(event, "preventDefault", { value: vi.fn() })

      result.current(event)

      expect(event.preventDefault).not.toHaveBeenCalled()
      expect(onUndo).not.toHaveBeenCalled()
    })

    it("should not call onUndo when callback is not provided", () => {
      const { result } = renderHook(() => useKeyboardShortcuts())

      const event = new KeyboardEvent("keydown", {
        key: "z",
        ctrlKey: true,
        bubbles: true,
      })
      Object.defineProperty(event, "preventDefault", { value: vi.fn() })

      result.current(event)

      expect(event.preventDefault).not.toHaveBeenCalled()
    })
  })

  describe("Ctrl+Shift+Z (redo)", () => {
    it("should call onRedo when Ctrl+Shift+Z is pressed", () => {
      const onRedo = vi.fn()
      const { result } = renderHook(() => useKeyboardShortcuts(undefined, onRedo))

      const event = new KeyboardEvent("keydown", {
        key: "z",
        ctrlKey: true,
        shiftKey: true,
        bubbles: true,
      })
      Object.defineProperty(event, "preventDefault", { value: vi.fn() })

      result.current(event)

      expect(event.preventDefault).toHaveBeenCalled()
      expect(onRedo).toHaveBeenCalled()
    })

    it("should call onRedo when Cmd+Shift+Z is pressed (Mac)", () => {
      const onRedo = vi.fn()
      const { result } = renderHook(() => useKeyboardShortcuts(undefined, onRedo))

      const event = new KeyboardEvent("keydown", {
        key: "z",
        metaKey: true,
        shiftKey: true,
        bubbles: true,
      })
      Object.defineProperty(event, "preventDefault", { value: vi.fn() })

      result.current(event)

      expect(event.preventDefault).toHaveBeenCalled()
      expect(onRedo).toHaveBeenCalled()
    })

    it("should not call onRedo when callback is not provided", () => {
      const { result } = renderHook(() => useKeyboardShortcuts())

      const event = new KeyboardEvent("keydown", {
        key: "z",
        ctrlKey: true,
        shiftKey: true,
        bubbles: true,
      })
      Object.defineProperty(event, "preventDefault", { value: vi.fn() })

      result.current(event)

      expect(event.preventDefault).not.toHaveBeenCalled()
    })
  })

  describe("Ctrl+Y (redo - Windows alternative)", () => {
    it("should call onRedo when Ctrl+Y is pressed", () => {
      const onRedo = vi.fn()
      const { result } = renderHook(() => useKeyboardShortcuts(undefined, onRedo))

      const event = new KeyboardEvent("keydown", {
        key: "y",
        ctrlKey: true,
        bubbles: true,
      })
      Object.defineProperty(event, "preventDefault", { value: vi.fn() })

      result.current(event)

      expect(event.preventDefault).toHaveBeenCalled()
      expect(onRedo).toHaveBeenCalled()
    })

    it("should call onRedo when Cmd+Y is pressed (Mac)", () => {
      const onRedo = vi.fn()
      const { result } = renderHook(() => useKeyboardShortcuts(undefined, onRedo))

      const event = new KeyboardEvent("keydown", {
        key: "y",
        metaKey: true,
        bubbles: true,
      })
      Object.defineProperty(event, "preventDefault", { value: vi.fn() })

      result.current(event)

      expect(event.preventDefault).toHaveBeenCalled()
      expect(onRedo).toHaveBeenCalled()
    })
  })

  describe("preventDefault behavior", () => {
    it("should prevent default browser behavior for undo shortcut", () => {
      const onUndo = vi.fn()
      const { result } = renderHook(() => useKeyboardShortcuts(onUndo))

      const event = new KeyboardEvent("keydown", {
        key: "z",
        ctrlKey: true,
        bubbles: true,
        cancelable: true,
      })
      Object.defineProperty(event, "preventDefault", { value: vi.fn() })

      result.current(event)

      expect(event.preventDefault).toHaveBeenCalledTimes(1)
    })

    it("should prevent default browser behavior for redo shortcut", () => {
      const onRedo = vi.fn()
      const { result } = renderHook(() => useKeyboardShortcuts(undefined, onRedo))

      const event = new KeyboardEvent("keydown", {
        key: "z",
        ctrlKey: true,
        shiftKey: true,
        bubbles: true,
        cancelable: true,
      })
      Object.defineProperty(event, "preventDefault", { value: vi.fn() })

      result.current(event)

      expect(event.preventDefault).toHaveBeenCalledTimes(1)
    })

    it("should prevent default browser behavior for Ctrl+Y redo shortcut", () => {
      const onRedo = vi.fn()
      const { result } = renderHook(() => useKeyboardShortcuts(undefined, onRedo))

      const event = new KeyboardEvent("keydown", {
        key: "y",
        ctrlKey: true,
        bubbles: true,
        cancelable: true,
      })
      Object.defineProperty(event, "preventDefault", { value: vi.fn() })

      result.current(event)

      expect(event.preventDefault).toHaveBeenCalledTimes(1)
    })
  })

  describe("other keys", () => {
    it("should not trigger on unrelated key combinations", () => {
      const onUndo = vi.fn()
      const onRedo = vi.fn()
      const { result } = renderHook(() => useKeyboardShortcuts(onUndo, onRedo))

      const event = new KeyboardEvent("keydown", {
        key: "a",
        ctrlKey: true,
        bubbles: true,
      })
      Object.defineProperty(event, "preventDefault", { value: vi.fn() })

      result.current(event)

      expect(event.preventDefault).not.toHaveBeenCalled()
      expect(onUndo).not.toHaveBeenCalled()
      expect(onRedo).not.toHaveBeenCalled()
    })

    it("should not trigger on Ctrl+C (copy)", () => {
      const onUndo = vi.fn()
      const onRedo = vi.fn()
      const { result } = renderHook(() => useKeyboardShortcuts(onUndo, onRedo))

      const event = new KeyboardEvent("keydown", {
        key: "c",
        ctrlKey: true,
        bubbles: true,
      })
      Object.defineProperty(event, "preventDefault", { value: vi.fn() })

      result.current(event)

      expect(event.preventDefault).not.toHaveBeenCalled()
      expect(onUndo).not.toHaveBeenCalled()
      expect(onRedo).not.toHaveBeenCalled()
    })

    it("should not trigger on Ctrl+V (paste)", () => {
      const onUndo = vi.fn()
      const onRedo = vi.fn()
      const { result } = renderHook(() => useKeyboardShortcuts(onUndo, onRedo))

      const event = new KeyboardEvent("keydown", {
        key: "v",
        ctrlKey: true,
        bubbles: true,
      })
      Object.defineProperty(event, "preventDefault", { value: vi.fn() })

      result.current(event)

      expect(event.preventDefault).not.toHaveBeenCalled()
      expect(onUndo).not.toHaveBeenCalled()
      expect(onRedo).not.toHaveBeenCalled()
    })
  })

  describe("callback memoization", () => {
    it("should return stable callback reference", () => {
      const onUndo = vi.fn()
      const onRedo = vi.fn()
      const { result, rerender } = renderHook(() =>
        useKeyboardShortcuts(onUndo, onRedo)
      )

      const firstCallback = result.current
      rerender()
      const secondCallback = result.current

      expect(firstCallback).toBe(secondCallback)
    })
  })
})
