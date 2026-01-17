import { useEffect, useRef, useCallback, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useAuthStore } from '@/stores/auth'

// WebSocket event types from backend
export type WebSocketEventType =
  | 'record_created'
  | 'record_updated'
  | 'record_deleted'
  | 'field_created'
  | 'field_updated'
  | 'field_deleted'
  | 'user_joined'
  | 'user_left'
  | 'cell_focus'
  | 'cell_blur'
  | 'cursor_move'
  | 'presence_sync'
  | 'error'

export interface WebSocketMessage {
  type: WebSocketEventType
  payload: unknown
  timestamp: string
  user_id?: string
}

export interface RecordEventPayload {
  record_id: string
  table_id: string
  fields?: { [key: string]: unknown }
}

export interface FieldEventPayload {
  field_id: string
  table_id: string
  name?: string
  type?: string
}

export interface UserPresence {
  user_id: string
  user_name: string
  avatar_url?: string
  color: string
  joined_at: string
}

export interface CellFocusPayload {
  user_id: string
  user_name: string
  color: string
  record_id: string
  field_id: string
}

export interface CursorMovePayload {
  user_id: string
  user_name: string
  color: string
  x: number
  y: number
}

interface UseWebSocketOptions {
  tableId: string
  onMessage?: (message: WebSocketMessage) => void
  onConnected?: () => void
  onDisconnected?: () => void
  onError?: (error: Event) => void
  autoReconnect?: boolean
  reconnectInterval?: number
  maxReconnectAttempts?: number
}

interface UseWebSocketReturn {
  isConnected: boolean
  presence: UserPresence[]
  cellFocus: Map<string, CellFocusPayload>
  cursors: Map<string, CursorMovePayload>
  sendMessage: (type: string, payload: unknown) => void
  focusCell: (recordId: string, fieldId: string) => void
  blurCell: () => void
  moveCursor: (x: number, y: number) => void
  disconnect: () => void
  reconnect: () => void
}

export function useWebSocket({
  tableId,
  onMessage,
  onConnected,
  onDisconnected,
  onError,
  autoReconnect = true,
  reconnectInterval = 3000,
  maxReconnectAttempts = 5,
}: UseWebSocketOptions): UseWebSocketReturn {
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectAttempts = useRef(0)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  const queryClient = useQueryClient()
  const { accessToken } = useAuthStore()

  const [isConnected, setIsConnected] = useState(false)
  const [presence, setPresence] = useState<UserPresence[]>([])
  const [cellFocus, setCellFocus] = useState<Map<string, CellFocusPayload>>(new Map())
  const [cursors, setCursors] = useState<Map<string, CursorMovePayload>>(new Map())

  // Build WebSocket URL
  const getWebSocketUrl = useCallback(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    return `${protocol}//${host}/api/v1/ws/${tableId}?token=${accessToken}`
  }, [tableId, accessToken])

  // Handle incoming messages
  const handleMessage = useCallback((event: MessageEvent) => {
    try {
      const message: WebSocketMessage = JSON.parse(event.data)
      
      // Handle different event types
      switch (message.type) {
        case 'record_created':
        case 'record_updated':
        case 'record_deleted':
          // Invalidate records query to refetch
          queryClient.invalidateQueries({ queryKey: ['records', tableId] })
          break

        case 'field_created':
        case 'field_updated':
        case 'field_deleted':
          // Invalidate fields query to refetch
          queryClient.invalidateQueries({ queryKey: ['fields', tableId] })
          break

        case 'user_joined': {
          const user = message.payload as UserPresence
          setPresence(prev => [...prev.filter(p => p.user_id !== user.user_id), user])
          break
        }

        case 'user_left': {
          const payload = message.payload as { user_id: string }
          setPresence(prev => prev.filter(p => p.user_id !== payload.user_id))
          // Clear their cell focus and cursor
          setCellFocus(prev => {
            const next = new Map(prev)
            next.delete(payload.user_id)
            return next
          })
          setCursors(prev => {
            const next = new Map(prev)
            next.delete(payload.user_id)
            return next
          })
          break
        }

        case 'presence_sync': {
          const users = message.payload as UserPresence[]
          setPresence(users)
          break
        }

        case 'cell_focus': {
          const focus = message.payload as CellFocusPayload
          setCellFocus(prev => {
            const next = new Map(prev)
            next.set(focus.user_id, focus)
            return next
          })
          break
        }

        case 'cell_blur': {
          const payload = message.payload as { user_id: string }
          setCellFocus(prev => {
            const next = new Map(prev)
            next.delete(payload.user_id)
            return next
          })
          break
        }

        case 'cursor_move': {
          const cursor = message.payload as CursorMovePayload
          setCursors(prev => {
            const next = new Map(prev)
            next.set(cursor.user_id, cursor)
            return next
          })
          break
        }

        case 'error':
          console.error('WebSocket error from server:', message.payload)
          break
      }

      // Call custom message handler
      onMessage?.(message)
    } catch (error) {
      console.error('Failed to parse WebSocket message:', error)
    }
  }, [queryClient, tableId, onMessage])

  // Connect to WebSocket
  const connect = useCallback(() => {
    if (!tableId || !accessToken) return

    // Close existing connection
    if (wsRef.current) {
      wsRef.current.close()
    }

    const url = getWebSocketUrl()
    const ws = new WebSocket(url)

    ws.onopen = () => {
      console.log('WebSocket connected')
      setIsConnected(true)
      reconnectAttempts.current = 0
      onConnected?.()
    }

    ws.onclose = (event) => {
      console.log('WebSocket disconnected', event.code, event.reason)
      setIsConnected(false)
      setPresence([])
      setCellFocus(new Map())
      setCursors(new Map())
      onDisconnected?.()

      // Auto reconnect if not intentionally closed
      if (autoReconnect && event.code !== 1000 && reconnectAttempts.current < maxReconnectAttempts) {
        reconnectTimeoutRef.current = setTimeout(() => {
          reconnectAttempts.current++
          console.log(`Reconnecting (attempt ${reconnectAttempts.current}/${maxReconnectAttempts})...`)
          connect()
        }, reconnectInterval)
      }
    }

    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
      onError?.(error)
    }

    ws.onmessage = handleMessage

    wsRef.current = ws
  }, [tableId, accessToken, getWebSocketUrl, handleMessage, onConnected, onDisconnected, onError, autoReconnect, reconnectInterval, maxReconnectAttempts])

  // Disconnect from WebSocket
  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
    }
    if (wsRef.current) {
      wsRef.current.close(1000, 'User initiated disconnect')
      wsRef.current = null
    }
  }, [])

  // Reconnect manually
  const reconnect = useCallback(() => {
    disconnect()
    reconnectAttempts.current = 0
    connect()
  }, [connect, disconnect])

  // Send message
  const sendMessage = useCallback((type: string, payload: unknown) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type, payload, timestamp: new Date().toISOString() }))
    }
  }, [])

  // Focus cell
  const focusCell = useCallback((recordId: string, fieldId: string) => {
    sendMessage('cell_focus', { record_id: recordId, field_id: fieldId })
  }, [sendMessage])

  // Blur cell
  const blurCell = useCallback(() => {
    sendMessage('cell_blur', {})
  }, [sendMessage])

  // Move cursor
  const moveCursor = useCallback((x: number, y: number) => {
    sendMessage('cursor_move', { x, y })
  }, [sendMessage])

  // Connect on mount, disconnect on unmount
  useEffect(() => {
    connect()
    return () => {
      disconnect()
    }
  }, [connect, disconnect])

  return {
    isConnected,
    presence,
    cellFocus,
    cursors,
    sendMessage,
    focusCell,
    blurCell,
    moveCursor,
    disconnect,
    reconnect,
  }
}

// Presence indicator component helper
export function getPresenceColor(index: number): string {
  const colors = [
    '#ef4444', // red
    '#f97316', // orange
    '#eab308', // yellow
    '#22c55e', // green
    '#06b6d4', // cyan
    '#3b82f6', // blue
    '#8b5cf6', // violet
    '#ec4899', // pink
  ]
  return colors[index % colors.length]
}
