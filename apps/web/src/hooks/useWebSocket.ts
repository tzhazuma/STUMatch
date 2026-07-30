import { useCallback, useEffect, useRef, useState } from 'react';
import { useAuthStore } from '@/store/authStore';
import type { Message } from '@/types';

export type WSEventType = 'send_message' | 'message_read' | 'typing';

export interface WSEvent {
  type: WSEventType;
  payload: Record<string, unknown>;
}

export interface UseWebSocketOptions {
  /** Called with every parsed inbound frame (after internal state is updated). */
  onMessage?: (data: Record<string, unknown>) => void;
}

export function useWebSocket(options: UseWebSocketOptions = {}) {
  const { access_token } = useAuthStore();
  const ws = useRef<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [lastEvent, setLastEvent] = useState<Record<string, unknown> | null>(null);
  const reconnectTimer = useRef<number | null>(null);
  // Keep the latest callback without forcing a reconnect when it changes.
  const onMessageRef = useRef(options.onMessage);
  onMessageRef.current = options.onMessage;

  const connect = useCallback(() => {
    if (!access_token || ws.current?.readyState === WebSocket.OPEN) return;

    // Host-agnostic WS: absolute envBase → derive ws(s); empty → follow page origin
    const envBase = import.meta.env.VITE_API_BASE_URL;
    let wsBase: string;
    if (envBase && /^https?:\/\//.test(envBase)) {
      wsBase = envBase.replace(/^http/, 'ws');
    } else {
      const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
      wsBase = `${proto}//${location.host}`;
    }
    const socket = new WebSocket(`${wsBase}/ws/chat?token=${access_token}`);

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
        const data = JSON.parse(event.data) as Record<string, unknown>;
        setLastEvent(data);
        // Backend broadcasts new messages as { type, conversation_id, message: {...} }.
        // Older/other frames may use `payload`. Accept both.
        const msg = (data.message ?? data.payload) as Message | undefined;
        if (data.type === 'new_message' && msg) {
          setMessages((prev) => [...prev, msg]);
        }
        onMessageRef.current?.(data);
      } catch {
        // ignore malformed frames
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
      return true;
    }
    return false;
  }, []);

  useEffect(() => {
    connect();
    return () => disconnect();
  }, [connect, disconnect]);

  return { connected, messages, send, lastEvent, connect, disconnect };
}
