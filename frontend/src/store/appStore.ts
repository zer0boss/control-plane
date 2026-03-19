import { create } from 'zustand';
import type { Instance, Session, Message, Task, SubTask, TaskProgress, Meeting, MeetingParticipant, MeetingMessage, MeetingRound } from '@/types';

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

  // Tasks
  tasks: Task[];
  selectedTask: Task | null;
  setTasks: (tasks: Task[]) => void;
  addTask: (task: Task) => void;
  updateTask: (id: string, updates: Partial<Task>) => void;
  removeTask: (id: string) => void;
  selectTask: (task: Task | null) => void;

  // SubTasks
  subtasks: Map<string, SubTask[]>;
  setSubtasks: (taskId: string, subtasks: SubTask[]) => void;
  addSubtask: (taskId: string, subtask: SubTask) => void;
  updateSubtask: (taskId: string, subtaskId: string, updates: Partial<SubTask>) => void;
  removeSubtask: (taskId: string, subtaskId: string) => void;

  // Task Progress
  progressEvents: Map<string, TaskProgress[]>;
  setProgressEvents: (taskId: string, events: TaskProgress[]) => void;
  addProgressEvent: (taskId: string, event: TaskProgress) => void;

  // Meetings
  meetings: Meeting[];
  selectedMeeting: Meeting | null;
  setMeetings: (meetings: Meeting[]) => void;
  addMeeting: (meeting: Meeting) => void;
  updateMeeting: (id: string, updates: Partial<Meeting>) => void;
  removeMeeting: (id: string) => void;
  selectMeeting: (meeting: Meeting | null) => void;

  // Meeting Participants
  participants: Map<string, MeetingParticipant[]>;
  setParticipants: (meetingId: string, participants: MeetingParticipant[]) => void;
  addParticipant: (meetingId: string, participant: MeetingParticipant) => void;
  updateParticipant: (meetingId: string, participantId: string, updates: Partial<MeetingParticipant>) => void;
  removeParticipant: (meetingId: string, participantId: string) => void;

  // Meeting Messages
  meetingMessages: Map<string, MeetingMessage[]>;
  setMeetingMessages: (meetingId: string, messages: MeetingMessage[]) => void;
  addMeetingMessage: (meetingId: string, message: MeetingMessage) => void;

  // Meeting Rounds
  meetingRounds: Map<string, MeetingRound[]>;
  setMeetingRounds: (meetingId: string, rounds: MeetingRound[]) => void;

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

  // Tasks
  tasks: [],
  selectedTask: null,
  setTasks: (tasks) => set({ tasks }),
  addTask: (task) =>
    set((state) => ({
      tasks: [...state.tasks, task],
    })),
  updateTask: (id, updates) =>
    set((state) => ({
      tasks: state.tasks.map((t) =>
        t.id === id ? { ...t, ...updates } : t
      ),
      selectedTask:
        state.selectedTask?.id === id
          ? { ...state.selectedTask, ...updates }
          : state.selectedTask,
    })),
  removeTask: (id) =>
    set((state) => ({
      tasks: state.tasks.filter((t) => t.id !== id),
      selectedTask:
        state.selectedTask?.id === id ? null : state.selectedTask,
    })),
  selectTask: (task) => set({ selectedTask: task }),

  // SubTasks
  subtasks: new Map(),
  setSubtasks: (taskId, subtasks) =>
    set((state) => {
      const newSubtasks = new Map(state.subtasks);
      newSubtasks.set(taskId, subtasks);
      return { subtasks: newSubtasks };
    }),
  addSubtask: (taskId, subtask) =>
    set((state) => {
      const newSubtasks = new Map(state.subtasks);
      const existing = newSubtasks.get(taskId) || [];
      newSubtasks.set(taskId, [...existing, subtask]);
      return { subtasks: newSubtasks };
    }),
  updateSubtask: (taskId, subtaskId, updates) =>
    set((state) => {
      const newSubtasks = new Map(state.subtasks);
      const existing = newSubtasks.get(taskId) || [];
      newSubtasks.set(
        taskId,
        existing.map((s) => (s.id === subtaskId ? { ...s, ...updates } : s))
      );
      return { subtasks: newSubtasks };
    }),
  removeSubtask: (taskId, subtaskId) =>
    set((state) => {
      const newSubtasks = new Map(state.subtasks);
      const existing = newSubtasks.get(taskId) || [];
      newSubtasks.set(
        taskId,
        existing.filter((s) => s.id !== subtaskId)
      );
      return { subtasks: newSubtasks };
    }),

  // Task Progress
  progressEvents: new Map(),
  setProgressEvents: (taskId, events) =>
    set((state) => {
      const newProgressEvents = new Map(state.progressEvents);
      newProgressEvents.set(taskId, events);
      return { progressEvents: newProgressEvents };
    }),
  addProgressEvent: (taskId, event) =>
    set((state) => {
      const newProgressEvents = new Map(state.progressEvents);
      const existing = newProgressEvents.get(taskId) || [];
      newProgressEvents.set(taskId, [...existing, event]);
      return { progressEvents: newProgressEvents };
    }),

  // Meetings
  meetings: [],
  selectedMeeting: null,
  setMeetings: (meetings) =>
    set((state) => ({
      meetings,
      // Update selectedMeeting if it exists and is in the new meetings list
      selectedMeeting: state.selectedMeeting
        ? meetings.find((m) => m.id === state.selectedMeeting?.id) || state.selectedMeeting
        : null,
    })),
  addMeeting: (meeting) =>
    set((state) => ({
      meetings: [...state.meetings, meeting],
    })),
  updateMeeting: (id, updates) =>
    set((state) => ({
      meetings: state.meetings.map((m) =>
        m.id === id ? { ...m, ...updates } : m
      ),
      selectedMeeting:
        state.selectedMeeting?.id === id
          ? { ...state.selectedMeeting, ...updates }
          : state.selectedMeeting,
    })),
  removeMeeting: (id) =>
    set((state) => ({
      meetings: state.meetings.filter((m) => m.id !== id),
      selectedMeeting:
        state.selectedMeeting?.id === id ? null : state.selectedMeeting,
    })),
  selectMeeting: (meeting) => set({ selectedMeeting: meeting }),

  // Meeting Participants
  participants: new Map(),
  setParticipants: (meetingId, participants) =>
    set((state) => {
      const newParticipants = new Map(state.participants);
      newParticipants.set(meetingId, participants);
      return { participants: newParticipants };
    }),
  addParticipant: (meetingId, participant) =>
    set((state) => {
      const newParticipants = new Map(state.participants);
      const existing = newParticipants.get(meetingId) || [];
      newParticipants.set(meetingId, [...existing, participant]);
      return { participants: newParticipants };
    }),
  updateParticipant: (meetingId, participantId, updates) =>
    set((state) => {
      const newParticipants = new Map(state.participants);
      const existing = newParticipants.get(meetingId) || [];
      newParticipants.set(
        meetingId,
        existing.map((p) => (p.id === participantId ? { ...p, ...updates } : p))
      );
      return { participants: newParticipants };
    }),
  removeParticipant: (meetingId, participantId) =>
    set((state) => {
      const newParticipants = new Map(state.participants);
      const existing = newParticipants.get(meetingId) || [];
      newParticipants.set(
        meetingId,
        existing.filter((p) => p.id !== participantId)
      );
      return { participants: newParticipants };
    }),

  // Meeting Messages
  meetingMessages: new Map(),
  setMeetingMessages: (meetingId, messages) =>
    set((state) => {
      const newMessages = new Map(state.meetingMessages);
      newMessages.set(meetingId, messages);
      return { meetingMessages: newMessages };
    }),
  addMeetingMessage: (meetingId, message) =>
    set((state) => {
      const newMessages = new Map(state.meetingMessages);
      const existing = newMessages.get(meetingId) || [];
      newMessages.set(meetingId, [...existing, message]);
      return { meetingMessages: newMessages };
    }),

  // Meeting Rounds
  meetingRounds: new Map(),
  setMeetingRounds: (meetingId, rounds) =>
    set((state) => {
      const newRounds = new Map(state.meetingRounds);
      newRounds.set(meetingId, rounds);
      return { meetingRounds: newRounds };
    }),
}));
