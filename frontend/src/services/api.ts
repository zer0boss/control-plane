import axios, { AxiosError } from 'axios';
import type {
  Instance,
  InstanceCreate,
  InstanceUpdate,
  InstanceList,
  InstanceHealth,
  Session,
  SessionCreate,
  SessionList,
  Message,
  MessageSend,
  MessageList,
  HealthCheck,
  AppInfo,
  Task,
  TaskCreate,
  TaskUpdate,
  TaskList,
  TaskAssignManager,
  SubTask,
  SubTaskCreate,
  SubTaskUpdate,
  SubTaskList,
  TaskProgressList,
  TaskStatus,
  TaskPriority,
  Meeting,
  MeetingCreate,
  MeetingUpdate,
  MeetingList,
  MeetingParticipant,
  ParticipantCreate,
  ParticipantUpdate,
  ParticipantList,
  ParticipantsReorder,
  MeetingMessage,
  MeetingMessageList,
  MeetingMessageCreate,
  MeetingRound,
  MeetingRoundList,
  MeetingRoundCreate,
  MeetingTranscript,
  SpeakInvitation,
  NextSpeakerRequest,
  DirectMessageRequest,
  MeetingStatus,
  PromptTemplate,
  PromptTemplateCreate,
  PromptTemplateUpdate,
  PromptTemplateList,
} from '@/types';

// 如果不是通过 Vite 代理（端口 3000），直接连接到后端
const isDevProxy = typeof window !== 'undefined' && window.location.port === '3000';
const API_BASE_URL = isDevProxy ? '/api/v1' : 'http://localhost:8001/api/v1';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Error handler
const handleError = (error: AxiosError) => {
  if (error.response) {
    const data = error.response.data as { detail?: string };
    throw new Error(data.detail || `HTTP ${error.response.status}`);
  }
  throw error;
};

// Instance API
export const instanceApi = {
  list: async (): Promise<InstanceList> => {
    try {
      const response = await apiClient.get<InstanceList>('/instances');
      return response.data;
    } catch (error) {
      return handleError(error as AxiosError);
    }
  },

  get: async (id: string): Promise<Instance> => {
    try {
      const response = await apiClient.get<Instance>(`/instances/${id}`);
      return response.data;
    } catch (error) {
      return handleError(error as AxiosError);
    }
  },

  create: async (data: InstanceCreate): Promise<Instance> => {
    try {
      const response = await apiClient.post<Instance>('/instances', data);
      return response.data;
    } catch (error) {
      return handleError(error as AxiosError);
    }
  },

  update: async (id: string, data: InstanceUpdate): Promise<Instance> => {
    try {
      const response = await apiClient.patch<Instance>(`/instances/${id}`, data);
      return response.data;
    } catch (error) {
      return handleError(error as AxiosError);
    }
  },

  delete: async (id: string): Promise<void> => {
    try {
      await apiClient.delete(`/instances/${id}`);
    } catch (error) {
      return handleError(error as AxiosError);
    }
  },

  connect: async (id: string): Promise<{ success: boolean; status: string; message?: string }> => {
    try {
      const response = await apiClient.post(`/instances/${id}/connect`);
      return response.data;
    } catch (error) {
      return handleError(error as AxiosError);
    }
  },

  disconnect: async (id: string): Promise<{ success: boolean; status: string }> => {
    try {
      const response = await apiClient.post(`/instances/${id}/disconnect`);
      return response.data;
    } catch (error) {
      return handleError(error as AxiosError);
    }
  },

  getHealth: async (id: string): Promise<InstanceHealth> => {
    try {
      const response = await apiClient.get<InstanceHealth>(`/instances/${id}/health`);
      return response.data;
    } catch (error) {
      return handleError(error as AxiosError);
    }
  },
};

// Session API
export const sessionApi = {
  list: async (instanceId?: string): Promise<SessionList> => {
    try {
      const params = instanceId ? { instance_id: instanceId } : undefined;
      const response = await apiClient.get<SessionList>('/sessions', { params });
      return response.data;
    } catch (error) {
      return handleError(error as AxiosError);
    }
  },

  get: async (id: string): Promise<Session> => {
    try {
      const response = await apiClient.get<Session>(`/sessions/${id}`);
      return response.data;
    } catch (error) {
      return handleError(error as AxiosError);
    }
  },

  create: async (data: SessionCreate): Promise<Session> => {
    try {
      const response = await apiClient.post<Session>('/sessions', data);
      return response.data;
    } catch (error) {
      return handleError(error as AxiosError);
    }
  },

  delete: async (id: string): Promise<void> => {
    try {
      await apiClient.delete(`/sessions/${id}`);
    } catch (error) {
      return handleError(error as AxiosError);
    }
  },

  close: async (id: string): Promise<{ success: boolean; status: string }> => {
    try {
      const response = await apiClient.post(`/sessions/${id}/close`);
      return response.data;
    } catch (error) {
      return handleError(error as AxiosError);
    }
  },

  getMessages: async (sessionId: string, limit = 100, offset = 0): Promise<MessageList> => {
    try {
      const response = await apiClient.get<MessageList>(`/sessions/${sessionId}/messages`, {
        params: { limit, offset },
      });
      return response.data;
    } catch (error) {
      return handleError(error as AxiosError);
    }
  },

  sendMessage: async (sessionId: string, data: MessageSend): Promise<Message> => {
    try {
      const response = await apiClient.post<Message>(`/sessions/${sessionId}/messages`, data);
      return response.data;
    } catch (error) {
      return handleError(error as AxiosError);
    }
  },
};

// System API
export const systemApi = {
  health: async (): Promise<HealthCheck> => {
    try {
      const response = await axios.get<HealthCheck>('/health');
      return response.data;
    } catch (error) {
      return handleError(error as AxiosError);
    }
  },

  info: async (): Promise<AppInfo> => {
    try {
      const response = await axios.get<AppInfo>('/');
      return response.data;
    } catch (error) {
      return handleError(error as AxiosError);
    }
  },
};

// Task API
export const taskApi = {
  list: async (params?: {
    status?: TaskStatus;
    priority?: TaskPriority;
    manager_instance_id?: string;
    limit?: number;
    offset?: number;
  }): Promise<TaskList> => {
    try {
      const response = await apiClient.get<TaskList>('/tasks', { params });
      return response.data;
    } catch (error) {
      return handleError(error as AxiosError);
    }
  },

  get: async (id: string): Promise<Task> => {
    try {
      const response = await apiClient.get<Task>(`/tasks/${id}`);
      return response.data;
    } catch (error) {
      return handleError(error as AxiosError);
    }
  },

  create: async (data: TaskCreate): Promise<Task> => {
    try {
      const response = await apiClient.post<Task>('/tasks', data);
      return response.data;
    } catch (error) {
      return handleError(error as AxiosError);
    }
  },

  update: async (id: string, data: TaskUpdate): Promise<Task> => {
    try {
      const response = await apiClient.patch<Task>(`/tasks/${id}`, data);
      return response.data;
    } catch (error) {
      return handleError(error as AxiosError);
    }
  },

  delete: async (id: string): Promise<void> => {
    try {
      await apiClient.delete(`/tasks/${id}`);
    } catch (error) {
      return handleError(error as AxiosError);
    }
  },

  publish: async (id: string): Promise<Task> => {
    try {
      const response = await apiClient.post<Task>(`/tasks/${id}/publish`);
      return response.data;
    } catch (error) {
      return handleError(error as AxiosError);
    }
  },

  assignManager: async (id: string, data: TaskAssignManager): Promise<Task> => {
    try {
      const response = await apiClient.post<Task>(`/tasks/${id}/assign-manager`, data);
      return response.data;
    } catch (error) {
      return handleError(error as AxiosError);
    }
  },

  analyze: async (id: string): Promise<Task> => {
    try {
      const response = await apiClient.post<Task>(`/tasks/${id}/analyze`);
      return response.data;
    } catch (error) {
      return handleError(error as AxiosError);
    }
  },

  confirm: async (id: string): Promise<Task> => {
    try {
      const response = await apiClient.post<Task>(`/tasks/${id}/confirm`, { confirmed: true });
      return response.data;
    } catch (error) {
      return handleError(error as AxiosError);
    }
  },

  start: async (id: string): Promise<Task> => {
    try {
      const response = await apiClient.post<Task>(`/tasks/${id}/start`);
      return response.data;
    } catch (error) {
      return handleError(error as AxiosError);
    }
  },

  complete: async (id: string, result?: string, summary?: string): Promise<Task> => {
    try {
      const params = new URLSearchParams();
      if (result) params.append('result', result);
      if (summary) params.append('summary', summary);
      const response = await apiClient.post<Task>(`/tasks/${id}/complete?${params.toString()}`);
      return response.data;
    } catch (error) {
      return handleError(error as AxiosError);
    }
  },

  fail: async (id: string, errorMessage?: string): Promise<Task> => {
    try {
      const params = errorMessage ? `?error_message=${encodeURIComponent(errorMessage)}` : '';
      const response = await apiClient.post<Task>(`/tasks/${id}/fail${params}`);
      return response.data;
    } catch (error) {
      return handleError(error as AxiosError);
    }
  },

  getSubtasks: async (id: string): Promise<SubTaskList> => {
    try {
      const response = await apiClient.get<SubTaskList>(`/tasks/${id}/subtasks`);
      return response.data;
    } catch (error) {
      return handleError(error as AxiosError);
    }
  },

  createSubtask: async (taskId: string, data: SubTaskCreate): Promise<SubTask> => {
    try {
      const response = await apiClient.post<SubTask>(`/tasks/${taskId}/subtasks`, data);
      return response.data;
    } catch (error) {
      return handleError(error as AxiosError);
    }
  },

  getProgress: async (id: string, limit = 100, offset = 0): Promise<TaskProgressList> => {
    try {
      const response = await apiClient.get<TaskProgressList>(`/tasks/${id}/progress`, {
        params: { limit, offset },
      });
      return response.data;
    } catch (error) {
      return handleError(error as AxiosError);
    }
  },

  getProgressPercent: async (id: string): Promise<{ task_id: string; progress_percent: number }> => {
    try {
      const response = await apiClient.get<{ task_id: string; progress_percent: number }>(
        `/tasks/${id}/progress/percent`
      );
      return response.data;
    } catch (error) {
      return handleError(error as AxiosError);
    }
  },
};

// SubTask API
export const subtaskApi = {
  get: async (id: string): Promise<SubTask> => {
    try {
      const response = await apiClient.get<SubTask>(`/tasks/subtasks/${id}`);
      return response.data;
    } catch (error) {
      return handleError(error as AxiosError);
    }
  },

  update: async (id: string, data: SubTaskUpdate): Promise<SubTask> => {
    try {
      const response = await apiClient.patch<SubTask>(`/tasks/subtasks/${id}`, data);
      return response.data;
    } catch (error) {
      return handleError(error as AxiosError);
    }
  },

  delete: async (id: string): Promise<void> => {
    try {
      await apiClient.delete(`/tasks/subtasks/${id}`);
    } catch (error) {
      return handleError(error as AxiosError);
    }
  },

  assign: async (id: string, executorInstanceId: string): Promise<SubTask> => {
    try {
      const response = await apiClient.post<SubTask>(
        `/tasks/subtasks/${id}/assign?executor_instance_id=${executorInstanceId}`
      );
      return response.data;
    } catch (error) {
      return handleError(error as AxiosError);
    }
  },

  start: async (id: string): Promise<SubTask> => {
    try {
      const response = await apiClient.post<SubTask>(`/tasks/subtasks/${id}/start`);
      return response.data;
    } catch (error) {
      return handleError(error as AxiosError);
    }
  },

  complete: async (id: string, result?: string): Promise<SubTask> => {
    try {
      const params = result ? `?result=${encodeURIComponent(result)}` : '';
      const response = await apiClient.post<SubTask>(`/tasks/subtasks/${id}/complete${params}`);
      return response.data;
    } catch (error) {
      return handleError(error as AxiosError);
    }
  },

  fail: async (id: string, errorMessage: string): Promise<SubTask> => {
    try {
      const response = await apiClient.post<SubTask>(
        `/tasks/subtasks/${id}/fail?error_message=${encodeURIComponent(errorMessage)}`
      );
      return response.data;
    } catch (error) {
      return handleError(error as AxiosError);
    }
  },
};

// Meeting API
export const meetingApi = {
  list: async (params?: {
    status?: MeetingStatus;
    limit?: number;
    offset?: number;
  }): Promise<MeetingList> => {
    try {
      const response = await apiClient.get<MeetingList>('/meetings', { params });
      return response.data;
    } catch (error) {
      return handleError(error as AxiosError);
    }
  },

  get: async (id: string): Promise<Meeting> => {
    try {
      const response = await apiClient.get<Meeting>(`/meetings/${id}`);
      return response.data;
    } catch (error) {
      return handleError(error as AxiosError);
    }
  },

  create: async (data: MeetingCreate): Promise<Meeting> => {
    try {
      const response = await apiClient.post<Meeting>('/meetings', data);
      return response.data;
    } catch (error) {
      return handleError(error as AxiosError);
    }
  },

  update: async (id: string, data: MeetingUpdate): Promise<Meeting> => {
    try {
      const response = await apiClient.patch<Meeting>(`/meetings/${id}`, data);
      return response.data;
    } catch (error) {
      return handleError(error as AxiosError);
    }
  },

  delete: async (id: string): Promise<void> => {
    try {
      await apiClient.delete(`/meetings/${id}`);
    } catch (error) {
      return handleError(error as AxiosError);
    }
  },

  // Lifecycle
  setReady: async (id: string): Promise<Meeting> => {
    try {
      const response = await apiClient.post<Meeting>(`/meetings/${id}/ready`);
      return response.data;
    } catch (error) {
      return handleError(error as AxiosError);
    }
  },

  start: async (id: string): Promise<Meeting> => {
    try {
      const response = await apiClient.post<Meeting>(`/meetings/${id}/start`);
      return response.data;
    } catch (error) {
      return handleError(error as AxiosError);
    }
  },

  pause: async (id: string): Promise<Meeting> => {
    try {
      const response = await apiClient.post<Meeting>(`/meetings/${id}/pause`);
      return response.data;
    } catch (error) {
      return handleError(error as AxiosError);
    }
  },

  resume: async (id: string): Promise<Meeting> => {
    try {
      const response = await apiClient.post<Meeting>(`/meetings/${id}/resume`);
      return response.data;
    } catch (error) {
      return handleError(error as AxiosError);
    }
  },

  end: async (id: string): Promise<Meeting> => {
    try {
      const response = await apiClient.post<Meeting>(`/meetings/${id}/end`);
      return response.data;
    } catch (error) {
      return handleError(error as AxiosError);
    }
  },

  cancel: async (id: string): Promise<Meeting> => {
    try {
      const response = await apiClient.post<Meeting>(`/meetings/${id}/cancel`);
      return response.data;
    } catch (error) {
      return handleError(error as AxiosError);
    }
  },

  // Participants
  getParticipants: async (id: string): Promise<ParticipantList> => {
    try {
      const response = await apiClient.get<ParticipantList>(`/meetings/${id}/participants`);
      return response.data;
    } catch (error) {
      return handleError(error as AxiosError);
    }
  },

  addParticipant: async (meetingId: string, data: ParticipantCreate): Promise<MeetingParticipant> => {
    try {
      const response = await apiClient.post<MeetingParticipant>(`/meetings/${meetingId}/participants`, data);
      return response.data;
    } catch (error) {
      return handleError(error as AxiosError);
    }
  },

  updateParticipant: async (participantId: string, data: ParticipantUpdate): Promise<MeetingParticipant> => {
    try {
      const response = await apiClient.patch<MeetingParticipant>(`/meetings/participants/${participantId}`, data);
      return response.data;
    } catch (error) {
      return handleError(error as AxiosError);
    }
  },

  removeParticipant: async (participantId: string): Promise<void> => {
    try {
      await apiClient.delete(`/meetings/participants/${participantId}`);
    } catch (error) {
      return handleError(error as AxiosError);
    }
  },

  reorderParticipants: async (meetingId: string, data: ParticipantsReorder): Promise<ParticipantList> => {
    try {
      const response = await apiClient.post<ParticipantList>(`/meetings/${meetingId}/participants/reorder`, data);
      return response.data;
    } catch (error) {
      return handleError(error as AxiosError);
    }
  },

  // Rounds
  getRounds: async (id: string): Promise<MeetingRoundList> => {
    try {
      const response = await apiClient.get<MeetingRoundList>(`/meetings/${id}/rounds`);
      return response.data;
    } catch (error) {
      return handleError(error as AxiosError);
    }
  },

  startNextRound: async (id: string, data?: MeetingRoundCreate): Promise<MeetingRound> => {
    try {
      const response = await apiClient.post<MeetingRound>(`/meetings/${id}/rounds`, data || {});
      return response.data;
    } catch (error) {
      return handleError(error as AxiosError);
    }
  },

  completeRound: async (roundId: string): Promise<MeetingRound> => {
    try {
      const response = await apiClient.post<MeetingRound>(`/meetings/rounds/${roundId}/complete`);
      return response.data;
    } catch (error) {
      return handleError(error as AxiosError);
    }
  },

  // Messages
  getMessages: async (id: string, roundNumber?: number, limit = 100): Promise<MeetingMessageList> => {
    try {
      const params: Record<string, unknown> = { limit };
      if (roundNumber !== undefined) params.round_number = roundNumber;
      const response = await apiClient.get<MeetingMessageList>(`/meetings/${id}/messages`, { params });
      return response.data;
    } catch (error) {
      return handleError(error as AxiosError);
    }
  },

  sendMessage: async (meetingId: string, participantId: string, data: MeetingMessageCreate): Promise<MeetingMessage> => {
    try {
      const response = await apiClient.post<MeetingMessage>(
        `/meetings/${meetingId}/messages?participant_id=${participantId}`,
        data
      );
      return response.data;
    } catch (error) {
      return handleError(error as AxiosError);
    }
  },

  inviteSpeak: async (meetingId: string, participantId: string): Promise<{ success: boolean; participant_id: string }> => {
    try {
      const response = await apiClient.post<{ success: boolean; participant_id: string }>(
        `/meetings/${meetingId}/invite-speak`,
        { participant_id: participantId } as SpeakInvitation
      );
      return response.data;
    } catch (error) {
      return handleError(error as AxiosError);
    }
  },

  setNextSpeaker: async (meetingId: string, participantId: string): Promise<{ success: boolean; next_speaker: string }> => {
    try {
      const response = await apiClient.post<{ success: boolean; next_speaker: string }>(
        `/meetings/${meetingId}/next-speaker`,
        { participant_id: participantId } as NextSpeakerRequest
      );
      return response.data;
    } catch (error) {
      return handleError(error as AxiosError);
    }
  },

  sendDirectMessage: async (meetingId: string, data: DirectMessageRequest): Promise<{ success: boolean; message: string }> => {
    try {
      const response = await apiClient.post<{ success: boolean; message: string }>(
        `/meetings/${meetingId}/direct-message`,
        data
      );
      return response.data;
    } catch (error) {
      return handleError(error as AxiosError);
    }
  },

  // Summary & Transcript
  summarize: async (id: string): Promise<{ success: boolean; message: string }> => {
    try {
      const response = await apiClient.post<{ success: boolean; message: string }>(`/meetings/${id}/summarize`);
      return response.data;
    } catch (error) {
      return handleError(error as AxiosError);
    }
  },

  getTranscript: async (id: string): Promise<MeetingTranscript> => {
    try {
      const response = await apiClient.get<MeetingTranscript>(`/meetings/${id}/transcript`);
      return response.data;
    } catch (error) {
      return handleError(error as AxiosError);
    }
  },

  // Flow Control
  skipSpeaker: async (meetingId: string): Promise<{ success: boolean }> => {
    try {
      const response = await apiClient.post<{ success: boolean }>(`/meetings/${meetingId}/skip-speaker`);
      return response.data;
    } catch (error) {
      return handleError(error as AxiosError);
    }
  },

  overrideSpeaker: async (meetingId: string, participantId: string): Promise<{ success: boolean; participant_id: string }> => {
    try {
      const response = await apiClient.post<{ success: boolean; participant_id: string }>(
        `/meetings/${meetingId}/override-speaker?participant_id=${participantId}`
      );
      return response.data;
    } catch (error) {
      return handleError(error as AxiosError);
    }
  },

  forceNextRound: async (meetingId: string): Promise<{ success: boolean }> => {
    try {
      const response = await apiClient.post<{ success: boolean }>(`/meetings/${meetingId}/force-next-round`);
      return response.data;
    } catch (error) {
      return handleError(error as AxiosError);
    }
  },

  submitSummary: async (meetingId: string, roundNumber: number, content: string): Promise<{ success: boolean }> => {
    try {
      const response = await apiClient.post<{ success: boolean }>(
        `/meetings/${meetingId}/submit-summary?round_number=${roundNumber}&content=${encodeURIComponent(content)}`
      );
      return response.data;
    } catch (error) {
      return handleError(error as AxiosError);
    }
  },

  toggleAutoProceed: async (meetingId: string): Promise<{ success: boolean; auto_proceed: boolean }> => {
    try {
      const response = await apiClient.post<{ success: boolean; auto_proceed: boolean }>(
        `/meetings/${meetingId}/toggle-auto-proceed`
      );
      return response.data;
    } catch (error) {
      return handleError(error as AxiosError);
    }
  },

  getSpeakerContext: async (meetingId: string, participantId: string): Promise<Record<string, unknown>> => {
    try {
      const response = await apiClient.get<Record<string, unknown>>(
        `/meetings/${meetingId}/context?participant_id=${participantId}`
      );
      return response.data;
    } catch (error) {
      return handleError(error as AxiosError);
    }
  },
};

// Prompt Template API
export const promptTemplateApi = {
  list: async (): Promise<PromptTemplateList> => {
    try {
      const response = await apiClient.get<PromptTemplateList>('/prompt-templates');
      return response.data;
    } catch (error) {
      return handleError(error as AxiosError);
    }
  },

  get: async (id: string): Promise<PromptTemplate> => {
    try {
      const response = await apiClient.get<PromptTemplate>(`/prompt-templates/${id}`);
      return response.data;
    } catch (error) {
      return handleError(error as AxiosError);
    }
  },

  create: async (data: PromptTemplateCreate): Promise<PromptTemplate> => {
    try {
      const response = await apiClient.post<PromptTemplate>('/prompt-templates', data);
      return response.data;
    } catch (error) {
      return handleError(error as AxiosError);
    }
  },

  update: async (id: string, data: PromptTemplateUpdate): Promise<PromptTemplate> => {
    try {
      const response = await apiClient.patch<PromptTemplate>(`/prompt-templates/${id}`, data);
      return response.data;
    } catch (error) {
      return handleError(error as AxiosError);
    }
  },

  delete: async (id: string): Promise<void> => {
    try {
      await apiClient.delete(`/prompt-templates/${id}`);
    } catch (error) {
      return handleError(error as AxiosError);
    }
  },

  setDefault: async (id: string): Promise<PromptTemplate> => {
    try {
      const response = await apiClient.post<PromptTemplate>(`/prompt-templates/${id}/set-default`);
      return response.data;
    } catch (error) {
      return handleError(error as AxiosError);
    }
  },

  initDefault: async (): Promise<{ success: boolean; template_id: string }> => {
    try {
      const response = await apiClient.post<{ success: boolean; template_id: string }>('/prompt-templates/init-default');
      return response.data;
    } catch (error) {
      return handleError(error as AxiosError);
    }
  },
};
