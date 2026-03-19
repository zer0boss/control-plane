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


// ============================================================================
// Task Types
// ============================================================================

export type TaskStatus =
  | 'draft'
  | 'published'
  | 'assigned'
  | 'analyzing'
  | 'decomposed'
  | 'in_progress'
  | 'completed'
  | 'failed';

export type TaskPriority = 'low' | 'medium' | 'high' | 'urgent';

export interface Task {
  id: string;
  title: string;
  description?: string;
  status: TaskStatus;
  priority: TaskPriority;
  manager_instance_id?: string;
  tags: string[];
  extra_data: Record<string, unknown>;
  result?: string;
  summary?: string;
  deadline?: string;
  started_at?: string;
  completed_at?: string;
  created_at: string;
  updated_at: string;
}

export interface TaskCreate {
  title: string;
  description?: string;
  priority?: TaskPriority;
  tags?: string[];
  extra_data?: Record<string, unknown>;
  deadline?: string;
}

export interface TaskUpdate {
  title?: string;
  description?: string;
  priority?: TaskPriority;
  tags?: string[];
  extra_data?: Record<string, unknown>;
  deadline?: string;
  status?: TaskStatus;
}

export interface TaskList {
  items: Task[];
  total: number;
}

export interface TaskAssignManager {
  manager_instance_id: string;
}


// ============================================================================
// SubTask Types
// ============================================================================

export type SubTaskStatus =
  | 'pending'
  | 'assigned'
  | 'in_progress'
  | 'completed'
  | 'failed';

export interface SubTask {
  id: string;
  task_id: string;
  title: string;
  description?: string;
  status: SubTaskStatus;
  executor_instance_id?: string;
  order: number;
  dependencies: string[];
  result?: string;
  error_message?: string;
  created_at: string;
  updated_at: string;
}

export interface SubTaskCreate {
  title: string;
  description?: string;
  order?: number;
  dependencies?: string[];
}

export interface SubTaskUpdate {
  title?: string;
  description?: string;
  status?: SubTaskStatus;
  executor_instance_id?: string;
  order?: number;
  dependencies?: string[];
  result?: string;
  error_message?: string;
}

export interface SubTaskList {
  items: SubTask[];
  total: number;
}


// ============================================================================
// Task Progress Types
// ============================================================================

export type TaskProgressEventType =
  | 'created'
  | 'published'
  | 'assigned'
  | 'analyzing'
  | 'decomposed'
  | 'started'
  | 'progress'
  | 'completed'
  | 'failed'
  | 'subtask_created'
  | 'subtask_assigned'
  | 'subtask_started'
  | 'subtask_completed'
  | 'subtask_failed';

export interface TaskProgress {
  id: string;
  task_id: string;
  subtask_id?: string;
  event_type: TaskProgressEventType;
  message?: string;
  progress_percent: number;
  created_at: string;
}

export interface TaskProgressList {
  items: TaskProgress[];
  total: number;
}


// ============================================================================
// Meeting Types
// ============================================================================

export type MeetingStatus =
  | 'draft'
  | 'ready'
  | 'in_progress'
  | 'paused'
  | 'completed'
  | 'cancelled';

export type MeetingType =
  | 'brainstorm'
  | 'expert_discussion'
  | 'decision_making'
  | 'problem_solving'
  | 'review';

export type ParticipantRole = 'host' | 'expert' | 'participant' | 'observer';

export type MeetingRoundStatus = 'pending' | 'in_progress' | 'completed';

export interface Meeting {
  id: string;
  title: string;
  description?: string;
  meeting_type: MeetingType;
  status: MeetingStatus;
  host_instance_id: string;
  max_rounds: number;
  current_round: number;
  summary?: string;
  context: Record<string, unknown>;
  prompt_template_id?: string;
  auto_proceed: boolean;
  current_speaker_id?: string;
  waiting_for_summary: boolean;
  started_at?: string;
  completed_at?: string;
  created_at: string;
  updated_at: string;
}

export interface MeetingCreate {
  title: string;
  description?: string;
  meeting_type?: MeetingType;
  host_instance_id: string;
  max_rounds?: number;
  context?: Record<string, unknown>;
  prompt_template_id?: string;
  auto_proceed?: boolean;
}

export interface MeetingUpdate {
  title?: string;
  description?: string;
  meeting_type?: MeetingType;
  host_instance_id?: string;
  max_rounds?: number;
  context?: Record<string, unknown>;
  status?: MeetingStatus;
  prompt_template_id?: string;
  auto_proceed?: boolean;
}

export interface MeetingList {
  items: Meeting[];
  total: number;
}

export interface MeetingParticipant {
  id: string;
  meeting_id: string;
  instance_id: string;
  role: ParticipantRole;
  speaking_order: number;
  expertise?: string;
  is_active: boolean;
  last_spoken_at?: string;
  created_at: string;
}

export interface ParticipantCreate {
  instance_id: string;
  role?: ParticipantRole;
  speaking_order?: number;
  expertise?: string;
}

export interface ParticipantUpdate {
  role?: ParticipantRole;
  speaking_order?: number;
  expertise?: string;
  is_active?: boolean;
}

export interface ParticipantList {
  items: MeetingParticipant[];
  total: number;
}

export interface ParticipantsReorder {
  participant_orders: Array<{ id: string; speaking_order: number }>;
}

export interface MeetingMessage {
  id: string;
  meeting_id: string;
  participant_id: string;
  instance_id: string;
  content: string;
  round_number: number;
  speaking_order: number;
  message_type: string;
  extra_data: Record<string, unknown>;
  created_at: string;
}

export interface MeetingMessageList {
  items: MeetingMessage[];
  total: number;
}

export interface MeetingMessageCreate {
  content: string;
  message_type?: string;
}

export interface MeetingRound {
  id: string;
  meeting_id: string;
  round_number: number;
  status: MeetingRoundStatus;
  topic?: string;
  summary?: string;
  summarized_at?: string;
  summarized_by_participant_id?: string;
  started_at?: string;
  completed_at?: string;
  created_at: string;
}

export interface MeetingRoundList {
  items: MeetingRound[];
  total: number;
}

export interface MeetingRoundCreate {
  topic?: string;
}

export interface MeetingTranscript {
  meeting: Meeting;
  participants: MeetingParticipant[];
  messages: MeetingMessage[];
  rounds: MeetingRound[];
}

export interface SpeakInvitation {
  participant_id: string;
}

export interface NextSpeakerRequest {
  participant_id: string;
}

export interface DirectMessageRequest {
  participant_id: string;
  content: string;
}


// ============================================================================
// Socket.IO Event Types
// ============================================================================

export interface MeetingUpdateEvent {
  type: string;
  meeting_id: string;
  data: Record<string, unknown>;
}

export interface MeetingMessageEvent {
  meeting_id: string;
  message: MeetingMessage;
}

export interface ParticipantUpdateEvent {
  type: string;
  meeting_id: string;
  participant_id: string;
  data: Record<string, unknown>;
}

export interface RoundUpdateEvent {
  type: string;
  meeting_id: string;
  round_number: number;
  data: Record<string, unknown>;
}


// ============================================================================
// Prompt Template Types
// ============================================================================

export interface PromptTemplate {
  id: string;
  name: string;
  code: string;
  opening_template: string;
  round_summary_template: string;
  guided_speak_template: string;
  free_speak_template: string;
  closing_summary_template: string;
  participant_speak_template: string;
  max_opening_words: number;
  max_summary_words: number;
  max_speak_words: number;
  is_default: boolean;
  is_system: boolean;
  created_at: string;
  updated_at: string;
}

export interface PromptTemplateCreate {
  name: string;
  code: string;
  opening_template: string;
  round_summary_template: string;
  guided_speak_template: string;
  free_speak_template: string;
  closing_summary_template: string;
  participant_speak_template: string;
  max_opening_words?: number;
  max_summary_words?: number;
  max_speak_words?: number;
}

export interface PromptTemplateUpdate {
  name?: string;
  opening_template?: string;
  round_summary_template?: string;
  guided_speak_template?: string;
  free_speak_template?: string;
  closing_summary_template?: string;
  participant_speak_template?: string;
  max_opening_words?: number;
  max_summary_words?: number;
  max_speak_words?: number;
}

export interface PromptTemplateList {
  items: PromptTemplate[];
  total: number;
}
