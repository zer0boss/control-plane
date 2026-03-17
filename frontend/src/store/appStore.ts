import { create } from 'zustand';
import type { Instance, Session, Message } from '@/types';

interface AppState {
  // Instances
  instances: Instance[];
  selectedInstance: Instance | null;
  setInstances: (instances: Instance[]) => void;
  addInstance: (instance: Instance) => void;
  updateInstance: (id: string, updates: Partial<Instance>) => void;
  removeInstance: (id: string) => void;
  selectInstance: (instance: Instance | null) => void;

  // Sessions
  sessions: Session[];
  selectedSession: Session | null;
  setSessions: (sessions: Session[]) => void;
  addSession: (session: Session) => void;
  updateSession: (id: string, updates: Partial<Session>) => void;
  removeSession: (id: string) => void;
  selectSession: (session: Session | null) => void;

  // Messages
  messages: Map<string, Message[]>;
  addMessage: (sessionId: string, message: Message) => void;
  setMessages: (sessionId: string, messages: Message[]) => void;
  clearMessages: (sessionId: string) => void;

  // UI State
  sidebarOpen: boolean;
  setSidebarOpen: (open: boolean) => void;
  isConnecting: boolean;
  setIsConnecting: (connecting: boolean) => void;
}

export const useAppStore = create<AppState>((set) => ({
  // Instances
  instances: [],
  selectedInstance: null,
  setInstances: (instances) => set({ instances }),
  addInstance: (instance) =>
    set((state) => ({
      instances: [...state.instances, instance],
    })),
  updateInstance: (id, updates) =>
    set((state) => ({
      instances: state.instances.map((i) =>
        i.id === id ? { ...i, ...updates } : i
      ),
    })),
  removeInstance: (id) =>
    set((state) => ({
      instances: state.instances.filter((i) => i.id !== id),
      selectedInstance:
        state.selectedInstance?.id === id ? null : state.selectedInstance,
    })),
  selectInstance: (instance) => set({ selectedInstance: instance }),

  // Sessions
  sessions: [],
  selectedSession: null,
  setSessions: (sessions) => set({ sessions }),
  addSession: (session) =>
    set((state) => ({
      sessions: [...state.sessions, session],
    })),
  updateSession: (id, updates) =>
    set((state) => ({
      sessions: state.sessions.map((s) =>
        s.id === id ? { ...s, ...updates } : s
      ),
    })),
  removeSession: (id) =>
    set((state) => ({
      sessions: state.sessions.filter((s) => s.id !== id),
      selectedSession:
        state.selectedSession?.id === id ? null : state.selectedSession,
    })),
  selectSession: (session) => set({ selectedSession: session }),

  // Messages
  messages: new Map(),
  addMessage: (sessionId, message) =>
    set((state) => {
      const newMessages = new Map(state.messages);
      const existing = newMessages.get(sessionId) || [];
      newMessages.set(sessionId, [...existing, message]);
      return { messages: newMessages };
    }),
  setMessages: (sessionId, messages) =>
    set((state) => {
      const newMessages = new Map(state.messages);
      newMessages.set(sessionId, messages);
      return { messages: newMessages };
    }),
  clearMessages: (sessionId) =>
    set((state) => {
      const newMessages = new Map(state.messages);
      newMessages.delete(sessionId);
      return { messages: newMessages };
    }),

  // UI State
  sidebarOpen: true,
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
  isConnecting: false,
  setIsConnecting: (connecting) => set({ isConnecting: connecting }),
}));
