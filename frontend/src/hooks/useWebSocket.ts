import { useEffect, useRef, useState, useCallback, useMemo } from 'react';
import type { RecordFieldValue } from '@/types';

type WebSocketStatus = 'connecting' | 'connected' | 'disconnected' | 'error';

interface WebSocketMessage {
  event_type: string;
  data: { [key: string]: RecordFieldValue };
}

interface UseWebSocketOptions {
  url: string;
  token?: string;
  onMessage?: (message: WebSocketMessage) => void;
  reconnectInterval?: number;
}

const DEFAULT_RECONNECT_INTERVAL = 3000;

/**
 * Custom hook for WebSocket connections with automatic reconnection.
 * @returns Object with status and send method
 */
export const useWebSocket = ({
  url,
  token,
  onMessage,
  reconnectInterval = DEFAULT_RECONNECT_INTERVAL
}: UseWebSocketOptions) => {
  const [status, setStatus] = useState<WebSocketStatus>('disconnected');
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>();
  const messageQueueRef = useRef<WebSocketMessage[]>([]);

  const connect = useCallback(() => {
    if (!token) {
      console.warn('Cannot connect WebSocket: no token provided');
      return;
    }

    // Build URL with token
    const wsUrl = `${url}?token=${token}`;
    
    try {
      const ws = new WebSocket(wsUrl);
      
      ws.onopen = () => {
        setStatus('connected');

        // Send queued messages
        while (messageQueueRef.current.length > 0) {
          const msg = messageQueueRef.current.shift();
          ws.send(JSON.stringify(msg));
        }
      };

      ws.onclose = () => {
        setStatus('disconnected');
        // Attempt reconnect with backoff
        const timeout = Math.min(10000, reconnectInterval * 2);
        reconnectTimeoutRef.current = setTimeout(() => {
          connect();
        }, timeout);
      };

      ws.onerror = (error) => {
        console.error('WebSocket Error:', error);
        setStatus('error');
        ws.close();
      };

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data) as WebSocketMessage;
          if (onMessage) {
            onMessage(message);
          }
        } catch (e) {
          console.error('Failed to parse WebSocket message:', e);
        }
      };

      wsRef.current = ws;

    } catch (e) {
      console.error('Failed to create WebSocket connection', e);
      setStatus('error');
    }
  }, [url, token, onMessage, reconnectInterval]);

  useEffect(() => {
    connect();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [connect]);

  const send = useCallback((event_type: string, data: { [key: string]: RecordFieldValue }) => {
    const message: WebSocketMessage = { event_type, data };
    
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    } else {
      console.warn('Cannot send message: WebSocket is not open, queueing:', message);
      messageQueueRef.current.push(message);
    }
  }, []);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    if (wsRef.current) {
      wsRef.current.close();
    }
  }, []);

  return useMemo(() => ({
    status,
    send,
    disconnect,
  }), [status, send, disconnect]);
};
