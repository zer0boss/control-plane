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
} from '@/types';

const API_BASE_URL = '/api/v1';

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
