import { io, Socket } from 'socket.io-client';
import type { WebSocketEvent } from '@/types';

type EventCallback = (event: WebSocketEvent) => void;

class WebSocketService {
  private socket: Socket | null = null;
  private callbacks: Map<string, Set<EventCallback>> = new Map();
  private currentSessionId: string | null = null;

  connect() {
    if (this.socket?.connected) return;

    // 如果不是通过 Vite 代理（端口 3000），直接连接到后端
    const isDevProxy = window.location.port === '3000';
    const socketUrl = isDevProxy ? '/' : 'http://localhost:8001';

    this.socket = io(socketUrl, {
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

    // Meeting events
    this.socket.on('meeting_update', (data) => {
      console.log('WebSocket received meeting_update:', data);
      this.triggerCallbacks('meeting_update', data);
    });

    this.socket.on('meeting_message', (data) => {
      console.log('WebSocket received meeting_message:', data);
      this.triggerCallbacks('meeting_message', data);
    });

    this.socket.on('participant_update', (data) => {
      console.log('WebSocket received participant_update:', data);
      this.triggerCallbacks('participant_update', data);
    });

    this.socket.on('round_update', (data) => {
      console.log('WebSocket received round_update:', data);
      this.triggerCallbacks('round_update', data);
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

  joinMeeting(meetingId: string) {
    if (this.socket?.connected) {
      console.log('Joining meeting room:', meetingId);
      this.socket.emit('join_meeting', meetingId);
    }
  }

  leaveMeeting(meetingId: string) {
    if (this.socket?.connected) {
      console.log('Leaving meeting room:', meetingId);
      this.socket.emit('leave_meeting', meetingId);
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

  // Alias for subscribe - more intuitive API
  on(event: string, callback: EventCallback) {
    return this.subscribe(event, callback);
  }

  // Unsubscribe from an event
  off(event: string, callback: EventCallback) {
    this.callbacks.get(event)?.delete(callback);
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
