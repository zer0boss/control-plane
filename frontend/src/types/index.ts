/**
 * API Types for OpenClaw Control Plane
 */

export type AuthType = 'token' | 'password' | 'mtls';

export interface InstanceCredentials {
  auth_type: AuthType;
  token?: string;
  password?: string;
  cert_path?: string;
  key_path?: string;
  ca_path?: string;
}

export interface Instance {
  id: string;
  name: string;
  host: string;
  port: number;
  channel_id: string;
  credentials?: InstanceCredentials;
  status: 'connected' | 'disconnected' | 'error' | 'connecting';
  status_message?: string;
  health: {
    latency_ms?: number;
    last_ping?: string;
    reconnect_count: number;
    message_count: number;
  };
  created_at: string;
  updated_at: string;
  last_connected_at?: string;
  last_error_at?: string;
}

export interface InstanceCreate {
  name: string;
  host: string;
  port: number;
  channel_id?: string;
  credentials?: InstanceCredentials;
}

export interface InstanceUpdate {
  name?: string;
  host?: string;
  port?: number;
  credentials?: InstanceCredentials;
  channel_id?: string;
}

export interface InstanceList {
  items: Instance[];
  total: number;
}

export interface InstanceHealth {
  status: string;
  latency_ms: number;
  message_count: number;
  error_count: number;
}

export interface Session {
  id: string;
  instance_id: string;
  target: string;
  context: Record<string, unknown>;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  last_message_at?: string;
}

export interface SessionCreate {
  instance_id: string;
  target: string;
  context?: Record<string, unknown>;
}

export interface SessionList {
  items: Session[];
  total: number;
}

export type MessageRole = 'user' | 'assistant' | 'system';

export interface Message {
  id: string;
  session_id: string;
  role: MessageRole;
  content: string;
  metadata?: Record<string, unknown>;
  latency_ms?: number;
  created_at: string;
}

export interface MessageSend {
  content: string;
}

export interface MessageList {
  items: Message[];
  total: number;
}

export interface HealthCheck {
  status: string;
  version: string;
}

export interface AppInfo {
  name: string;
  version: string;
  docs: string;
}

export interface WebSocketEvent {
  type: 'message' | 'status' | 'error' | 'connected' | 'disconnected';
  session_id: string;
  data: unknown;
  timestamp: string;
}
