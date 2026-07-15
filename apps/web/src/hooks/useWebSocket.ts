import { useCallback, useEffect, useRef, useState } from 'react';
import { useAuthStore } from '@/store/authStore';
import type { Message } from '@/types';

export type WSEventType = 'send_message' | 'message_read' | 'typing';

export interface WSEvent {
  type: WSEventType;
  payload: Record<string, unknown>;
}

export function useWebSocket() {
  const { access_token } = useAuthStore();
  const ws = useRef<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [lastEvent, setLastEvent] = useState<Record<string, unknown> | null>(null);
  const reconnectTimer = useRef<number | null>(null);

  const connect = useCallback(() => {
    if (!access_token || ws.current?.readyState === WebSocket.OPEN) return;

    const baseURL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
    const wsUrl = baseURL.replace(/^http/, 'ws');
    const socket = new WebSocket(`${wsUrl}/ws/chat?token=${access_token}`);

    socket.onopen = () => setConnected(true);
    socket.onclose = () => {
      setConnected(false);
      if (!reconnectTimer.current) {
        reconnectTimer.current = window.setTimeout(() => {
          reconnectTimer.current = null;
          connect();
        }, 3000);
      }
    };
    socket.onerror = (e) => console.error('WebSocket error', e);
    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setLastEvent(data);
        if (data.type === 'new_message' && data.payload) {
          setMessages((prev) => [...prev, data.payload as Message]);
        }
      } catch {
        // ignore
      }
    };

    ws.current = socket;
  }, [access_token]);

  const disconnect = useCallback(() => {
    if (reconnectTimer.current) {
      clearTimeout(reconnectTimer.current);
      reconnectTimer.current = null;
    }
    ws.current?.close();
    ws.current = null;
  }, []);

  const send = useCallback((event: WSEvent) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(event));
    }
  }, []);

  useEffect(() => {
    connect();
    return () => disconnect();
  }, [connect, disconnect]);

  return { connected, messages, send, lastEvent, connect, disconnect };
}
