import { io, Socket } from 'socket.io-client';
import type { WebSocketEvent } from '@/types';

type EventCallback = (event: WebSocketEvent) => void;

class WebSocketService {
  private socket: Socket | null = null;
  private callbacks: Map<string, Set<EventCallback>> = new Map();
  private currentSessionId: string | null = null;

  connect() {
    if (this.socket?.connected) return;

    this.socket = io('/', {
      transports: ['polling', 'websocket'],  // Allow polling handshake before WebSocket upgrade
      autoConnect: true,
      reconnection: true,
      reconnectionAttempts: 10,
      reconnectionDelay: 1000,
    });

    this.socket.on('connect', () => {
      console.log('WebSocket connected, socket id:', this.socket?.id);
      // Re-join session room if we were in one
      if (this.currentSessionId) {
        this.joinSession(this.currentSessionId);
      }
    });

    this.socket.on('disconnect', (reason) => {
      console.log('WebSocket disconnected, reason:', reason);
    });

    this.socket.on('connect_error', (error) => {
      console.error('WebSocket connect_error:', error.message);
    });

    this.socket.on('error', (error) => {
      console.error('WebSocket error:', error);
    });

    this.socket.on('message', (data: WebSocketEvent) => {
      console.log('WebSocket received message:', data);
      this.triggerCallbacks('message', data);
      if (data.session_id) {
        this.triggerCallbacks(`session:${data.session_id}`, data);
      }
    });

    this.socket.on('status', (data: WebSocketEvent) => {
      this.triggerCallbacks('status', data);
    });
  }

  disconnect() {
    this.socket?.disconnect();
    this.socket = null;
  }

  joinSession(sessionId: string) {
    this.currentSessionId = sessionId;
    if (this.socket?.connected) {
      console.log('Joining session room:', sessionId);
      this.socket.emit('join_session', sessionId);
    }
  }

  leaveSession(sessionId: string) {
    if (this.currentSessionId === sessionId) {
      this.currentSessionId = null;
    }
    if (this.socket?.connected) {
      console.log('Leaving session room:', sessionId);
      this.socket.emit('leave_session', sessionId);
    }
  }

  subscribe(event: string, callback: EventCallback) {
    if (!this.callbacks.has(event)) {
      this.callbacks.set(event, new Set());
    }
    this.callbacks.get(event)!.add(callback);

    // Return unsubscribe function
    return () => {
      this.callbacks.get(event)?.delete(callback);
    };
  }

  private triggerCallbacks(event: string, data: WebSocketEvent) {
    const callbacks = this.callbacks.get(event);
    if (callbacks) {
      callbacks.forEach((cb) => cb(data));
    }
  }

  send(event: string, data: unknown) {
    this.socket?.emit(event, data);
  }

  isConnected(): boolean {
    return this.socket?.connected ?? false;
  }
}

export const wsService = new WebSocketService();
