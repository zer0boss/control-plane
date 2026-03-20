import { useState, useEffect, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Plus,
  Users,
  CheckCircle,
  XCircle,
  Play,
  Pause,
  MessageSquare,
  Trash2,
  ChevronRight,
  AlertCircle,
  Loader2,
  SkipForward,
  UserPlus,
  Mic,
  Mail,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { ScrollArea } from '@/components/ui/scroll-area';
import { meetingApi, instanceApi, meetingTypeRoleApi } from '@/services/api';
import { wsService } from '@/services/websocket';
import { useAppStore } from '@/store/appStore';
import type {
  MeetingStatus,
  MeetingType,
  MeetingParticipant,
  Instance,
  MeetingMessage,
  MeetingMessageEvent,
  MeetingUpdateEvent,
} from '@/types';

const statusConfig: Record<MeetingStatus, { label: string; color: string; icon: typeof Users }> = {
  draft: { label: '草稿', color: 'bg-gray-500', icon: Users },
  ready: { label: '准备就绪', color: 'bg-blue-500', icon: CheckCircle },
  in_progress: { label: '进行中', color: 'bg-green-500', icon: Play },
  paused: { label: '已暂停', color: 'bg-yellow-500', icon: Pause },
  completed: { label: '已完成', color: 'bg-emerald-500', icon: CheckCircle },
  cancelled: { label: '已取消', color: 'bg-red-500', icon: XCircle },
};

const meetingTypeConfig: Record<MeetingType, { label: string }> = {
  brainstorm: { label: '头脑风暴' },
  expert_discussion: { label: '专家讨论' },
  decision_making: { label: '决策制定' },
  problem_solving: { label: '问题解决' },
  review: { label: '评审' },
};

export function MeetingsPage() {
  const queryClient = useQueryClient();
  const { meetings, setMeetings, selectedMeeting, selectMeeting, updateMeeting } = useAppStore();

  // State
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [participantDialogOpen, setParticipantDialogOpen] = useState(false);
  const [directMessageDialogOpen, setDirectMessageDialogOpen] = useState(false);
  const [selectedParticipantForMessage, setSelectedParticipantForMessage] = useState<MeetingParticipant | null>(null);
  const [directMessageContent, setDirectMessageContent] = useState('');
  const [directMessageError, setDirectMessageError] = useState<string | null>(null);
  const [newMeeting, setNewMeeting] = useState({
    title: '',
    description: '',
    meeting_type: 'brainstorm' as MeetingType,
    host_instance_id: '',
    max_rounds: 5,
  });
  const [newParticipant, setNewParticipant] = useState({
    instance_id: '',
    role: 'participant' as 'host' | 'expert' | 'participant' | 'observer',
    expertise: '',
    // 预定义角色
    role_code: '',
    role_name: '',
    role_color: '',
  });
  const [meetingMessages, setMeetingMessages] = useState<MeetingMessage[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Queries
  const { data: meetingsData, isLoading: meetingsLoading } = useQuery({
    queryKey: ['meetings'],
    queryFn: () => meetingApi.list({ limit: 100 }),
  });

  const { data: instancesData, refetch: refetchInstances } = useQuery({
    queryKey: ['instances'],
    queryFn: () => instanceApi.list(),
    staleTime: 0, // Always consider data stale
    refetchOnMount: 'always', // Always refetch when component mounts
  });

  const { data: participantsData } = useQuery({
    queryKey: ['participants', selectedMeeting?.id],
    queryFn: () => (selectedMeeting ? meetingApi.getParticipants(selectedMeeting.id) : null),
    enabled: !!selectedMeeting,
  });

  const { data: messagesData } = useQuery({
    queryKey: ['meeting-messages', selectedMeeting?.id],
    queryFn: () => (selectedMeeting ? meetingApi.getMessages(selectedMeeting.id, undefined, 200) : null),
    enabled: !!selectedMeeting,
  });

  // 获取会议类型角色配置
  const { data: roleConfigsData } = useQuery({
    queryKey: ['meeting-type-roles'],
    queryFn: meetingTypeRoleApi.list,
  });

  // Update store when data loads
  useEffect(() => {
    if (meetingsData?.items) {
      setMeetings(meetingsData.items);
    }
  }, [meetingsData, setMeetings]);

  // Update messages when data loads
  useEffect(() => {
    if (messagesData?.items) {
      setMeetingMessages(messagesData.items);
    }
  }, [messagesData]);

  // Auto-scroll to bottom when new messages arrive during meeting
  useEffect(() => {
    if (selectedMeeting?.status === 'in_progress' && messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [meetingMessages, selectedMeeting?.status]);

  // WebSocket event handlers for real-time updates
  useEffect(() => {
    if (!selectedMeeting) return;

    // Join meeting room
    wsService.joinMeeting(selectedMeeting.id);

    // Handle meeting messages
    const handleMeetingMessage = (event: unknown) => {
      const msgEvent = event as MeetingMessageEvent;
      if (msgEvent.meeting_id === selectedMeeting.id) {
        setMeetingMessages((prev) => [...prev, msgEvent.message]);
      }
    };

    // Handle meeting updates
    const handleMeetingUpdate = (event: unknown) => {
      const updateEvent = event as MeetingUpdateEvent;
      if (updateEvent.meeting_id === selectedMeeting.id) {
        // Invalidate queries to refetch data
        queryClient.invalidateQueries({ queryKey: ['meetings'] });
        queryClient.invalidateQueries({ queryKey: ['participants', selectedMeeting.id] });
        queryClient.invalidateQueries({ queryKey: ['meeting-messages', selectedMeeting.id] });

        // If the update contains status change, also update selectedMeeting directly
        if (updateEvent.data?.status) {
          const { updateMeeting } = useAppStore.getState();
          updateMeeting(selectedMeeting.id, { status: updateEvent.data.status as MeetingStatus });
        }
      }
    };

    wsService.on('meeting_message', handleMeetingMessage);
    wsService.on('meeting_update', handleMeetingUpdate);

    return () => {
      wsService.leaveMeeting(selectedMeeting.id);
      wsService.off('meeting_message', handleMeetingMessage);
      wsService.off('meeting_update', handleMeetingUpdate);
    };
  }, [selectedMeeting, queryClient]);

  // Mutations
  const createMutation = useMutation({
    mutationFn: (data: typeof newMeeting) =>
      meetingApi.create({
        title: data.title,
        description: data.description || undefined,
        meeting_type: data.meeting_type,
        host_instance_id: data.host_instance_id,
        max_rounds: data.max_rounds,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['meetings'] });
      setCreateDialogOpen(false);
      setNewMeeting({
        title: '',
        description: '',
        meeting_type: 'brainstorm',
        host_instance_id: '',
        max_rounds: 5,
      });
    },
  });

  const addParticipantMutation = useMutation({
    mutationFn: (data: typeof newParticipant) =>
      meetingApi.addParticipant(selectedMeeting!.id, {
        instance_id: data.instance_id,
        role: data.role,
        expertise: data.expertise || undefined,
        role_code: data.role_code || undefined,
        role_name: data.role_name || undefined,
        role_color: data.role_color || undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['participants', selectedMeeting?.id] });
      setParticipantDialogOpen(false);
      setNewParticipant({
        instance_id: '',
        role: 'participant',
        expertise: '',
        role_code: '',
        role_name: '',
        role_color: '',
      });
    },
  });

  const setReadyMutation = useMutation({
    mutationFn: (id: string) => meetingApi.setReady(id),
    onSuccess: (data) => {
      if (selectedMeeting?.id === data.id) {
        updateMeeting(data.id, { status: 'ready' });
      }
      queryClient.invalidateQueries({ queryKey: ['meetings'] });
    },
  });

  const startMutation = useMutation({
    mutationFn: (id: string) => meetingApi.start(id),
    onSuccess: (data) => {
      if (selectedMeeting?.id === data.id) {
        updateMeeting(data.id, { status: 'in_progress', current_round: data.current_round });
      }
      queryClient.invalidateQueries({ queryKey: ['meetings'] });
      queryClient.invalidateQueries({ queryKey: ['meeting-rounds', selectedMeeting?.id] });
    },
  });

  const pauseMutation = useMutation({
    mutationFn: (id: string) => meetingApi.pause(id),
    onSuccess: (data) => {
      if (selectedMeeting?.id === data.id) {
        updateMeeting(data.id, { status: 'paused' });
      }
      queryClient.invalidateQueries({ queryKey: ['meetings'] });
    },
  });

  const resumeMutation = useMutation({
    mutationFn: (id: string) => meetingApi.resume(id),
    onSuccess: (data) => {
      if (selectedMeeting?.id === data.id) {
        updateMeeting(data.id, { status: 'in_progress' });
      }
      queryClient.invalidateQueries({ queryKey: ['meetings'] });
    },
  });

  const endMutation = useMutation({
    mutationFn: (id: string) => meetingApi.end(id),
    onSuccess: (data) => {
      if (selectedMeeting?.id === data.id) {
        updateMeeting(data.id, { status: 'completed' });
      }
      queryClient.invalidateQueries({ queryKey: ['meetings'] });
    },
  });

  const cancelMutation = useMutation({
    mutationFn: (id: string) => meetingApi.cancel(id),
    onSuccess: (data) => {
      if (selectedMeeting?.id === data.id) {
        updateMeeting(data.id, { status: 'cancelled' });
      }
      queryClient.invalidateQueries({ queryKey: ['meetings'] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => meetingApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['meetings'] });
      selectMeeting(null);
    },
  });

  const nextRoundMutation = useMutation({
    mutationFn: (id: string) => meetingApi.startNextRound(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['meeting-rounds', selectedMeeting?.id] });
      queryClient.invalidateQueries({ queryKey: ['meetings'] });
    },
  });

  const inviteSpeakMutation = useMutation({
    mutationFn: (data: { meetingId: string; participantId: string }) =>
      meetingApi.inviteSpeak(data.meetingId, data.participantId),
  });

  const sendDirectMessageMutation = useMutation({
    mutationFn: (data: { meetingId: string; participantId: string; content: string }) =>
      meetingApi.sendDirectMessage(data.meetingId, {
        participant_id: data.participantId,
        content: data.content,
      }),
    onSuccess: () => {
      setDirectMessageDialogOpen(false);
      setDirectMessageContent('');
      setSelectedParticipantForMessage(null);
      setDirectMessageError(null);
    },
    onError: (error: Error) => {
      setDirectMessageError(error.message || '发送失败');
    },
  });

  // Helper functions
  const getStatusBadge = (status: MeetingStatus) => {
    const config = statusConfig[status];
    const Icon = config.icon;
    return (
      <Badge className={`${config.color} text-white gap-1`}>
        <Icon className="h-3 w-3" />
        {config.label}
      </Badge>
    );
  };

  const getMeetingTypeBadge = (type: MeetingType) => {
    const config = meetingTypeConfig[type];
    return <Badge variant="outline">{config.label}</Badge>;
  };

  // Get all instances for display, with status info
  const allInstances = instancesData?.items || [];
  const instanceMap = new Map(allInstances.map((i) => [i.id, i]));

  // 计算过滤后的实例列表（添加参会者用）- 过滤已连接且未添加为参会者的实例
  const availableInstancesForParticipant = allInstances
    .filter((i) => i.status === 'connected')
    .filter((i) =>
      !participantsData?.items.some((p: MeetingParticipant) => p.instance_id === i.id)
    );

  // 获取当前会议类型的预定义角色
  const currentMeetingTypeRoles = roleConfigsData?.items.find(
    (r) => r.meeting_type === selectedMeeting?.meeting_type
  )?.roles || [];

  // 获取已被分配的角色代码
  const assignedRoleCodes = new Set(
    participantsData?.items
      .filter((p: MeetingParticipant) => p.role_code)
      .map((p: MeetingParticipant) => p.role_code) || []
  );

  // 过滤出可用的预定义角色（未被分配的）
  const availablePredefinedRoles = currentMeetingTypeRoles.filter(
    (role) => !assignedRoleCodes.has(role.code)
  );

  return (
    <div className="flex h-[calc(100vh-120px)] gap-4">
      {/* Meeting List */}
      <Card className="w-80 flex-shrink-0 overflow-hidden flex flex-col">
        <CardHeader className="flex-shrink-0">
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg">会议列表</CardTitle>
            <Button size="sm" onClick={() => {
              refetchInstances();
              setCreateDialogOpen(true);
            }}>
              <Plus className="h-4 w-4 mr-1" />
              新建
            </Button>
          </div>
        </CardHeader>
        <CardContent className="flex-1 overflow-auto p-0">
          {meetingsLoading ? (
            <div className="flex items-center justify-center h-32">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : meetings.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-32 text-muted-foreground">
              <Users className="h-8 w-8 mb-2" />
              <p className="text-sm">暂无会议</p>
            </div>
          ) : (
            <div className="divide-y">
              {meetings.map((meeting) => (
                <div
                  key={meeting.id}
                  className={`p-4 cursor-pointer hover:bg-accent transition-colors ${
                    selectedMeeting?.id === meeting.id ? 'bg-accent' : ''
                  }`}
                  onClick={() => selectMeeting(meeting)}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      <h4 className="font-medium truncate">{meeting.title}</h4>
                      <p className="text-sm text-muted-foreground line-clamp-2 mt-1">
                        {meeting.description || '无描述'}
                      </p>
                    </div>
                    <ChevronRight className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                  </div>
                  <div className="flex items-center gap-2 mt-2">
                    {getStatusBadge(meeting.status)}
                    {getMeetingTypeBadge(meeting.meeting_type)}
                  </div>
                  <div className="flex items-center gap-2 mt-2 text-xs text-muted-foreground">
                    <span>
                      轮次: {meeting.current_round}/{meeting.max_rounds}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Meeting Detail */}
      <Card className="flex-1 overflow-hidden flex flex-col">
        {selectedMeeting ? (
          <>
            <CardHeader className="flex-shrink-0 border-b">
              <div className="flex items-start justify-between">
                <div>
                  <CardTitle>{selectedMeeting.title}</CardTitle>
                  <p className="text-sm text-muted-foreground mt-1">
                    {selectedMeeting.description || '无描述'}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  {selectedMeeting.status === 'draft' && (
                    <Button
                      size="sm"
                      onClick={() => setReadyMutation.mutate(selectedMeeting.id)}
                      disabled={setReadyMutation.isPending}
                    >
                      准备就绪
                    </Button>
                  )}
                  {selectedMeeting.status === 'ready' && (
                    <Button
                      size="sm"
                      onClick={() => startMutation.mutate(selectedMeeting.id)}
                      disabled={startMutation.isPending}
                    >
                      <Play className="h-4 w-4 mr-1" />
                      开始会议
                    </Button>
                  )}
                  {selectedMeeting.status === 'in_progress' && (
                    <>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => pauseMutation.mutate(selectedMeeting.id)}
                        disabled={pauseMutation.isPending}
                      >
                        <Pause className="h-4 w-4 mr-1" />
                        暂停
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => nextRoundMutation.mutate(selectedMeeting.id)}
                        disabled={nextRoundMutation.isPending}
                      >
                        <SkipForward className="h-4 w-4 mr-1" />
                        下一轮
                      </Button>
                      <Button
                        size="sm"
                        variant="destructive"
                        onClick={() => endMutation.mutate(selectedMeeting.id)}
                        disabled={endMutation.isPending}
                      >
                        结束会议
                      </Button>
                    </>
                  )}
                  {selectedMeeting.status === 'paused' && (
                    <>
                      <Button
                        size="sm"
                        onClick={() => resumeMutation.mutate(selectedMeeting.id)}
                        disabled={resumeMutation.isPending}
                      >
                        <Play className="h-4 w-4 mr-1" />
                        继续
                      </Button>
                      <Button
                        size="sm"
                        variant="destructive"
                        onClick={() => endMutation.mutate(selectedMeeting.id)}
                        disabled={endMutation.isPending}
                      >
                        结束会议
                      </Button>
                    </>
                  )}
                  {selectedMeeting.status === 'completed' && (
                    <Button size="sm" variant="outline" onClick={() => meetingApi.summarize(selectedMeeting.id)}>
                      生成总结
                    </Button>
                  )}
                  {['draft', 'ready'].includes(selectedMeeting.status) && (
                    <Button
                      size="sm"
                      variant="destructive"
                      onClick={() => cancelMutation.mutate(selectedMeeting.id)}
                      disabled={cancelMutation.isPending}
                    >
                      取消
                    </Button>
                  )}
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => deleteMutation.mutate(selectedMeeting.id)}
                    disabled={deleteMutation.isPending}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </div>
              <div className="flex items-center gap-4 mt-4">
                <div className="flex items-center gap-2">
                  <span className="text-sm text-muted-foreground">状态:</span>
                  {getStatusBadge(selectedMeeting.status)}
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-sm text-muted-foreground">类型:</span>
                  {getMeetingTypeBadge(selectedMeeting.meeting_type)}
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-sm text-muted-foreground">轮次:</span>
                  <Badge variant="outline">
                    {selectedMeeting.current_round}/{selectedMeeting.max_rounds}
                  </Badge>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-sm text-muted-foreground">主持人:</span>
                  <Badge variant="outline">
                    {instanceMap.get(selectedMeeting.host_instance_id)?.name ||
                      selectedMeeting.host_instance_id}
                  </Badge>
                </div>
              </div>
            </CardHeader>

            <CardContent className="flex-1 overflow-auto p-0">
              <div className="grid grid-cols-3 gap-0 h-full">
                {/* Participants */}
                <div className="border-r overflow-auto">
                  <div className="p-4 border-b bg-muted/30 flex items-center justify-between">
                    <h3 className="font-medium">参会者</h3>
                    {selectedMeeting.status !== 'in_progress' && (
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => {
                          refetchInstances();
                          setParticipantDialogOpen(true);
                        }}
                      >
                        <UserPlus className="h-4 w-4" />
                      </Button>
                    )}
                  </div>
                  {participantsData?.items.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-32 text-muted-foreground">
                      <Users className="h-6 w-6 mb-2" />
                      <p className="text-sm">暂无参会者</p>
                    </div>
                  ) : (
                    <div className="divide-y">
                      {participantsData?.items.map((participant: MeetingParticipant) => (
                        <div key={participant.id} className="p-4">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                              <span className="font-medium">
                                {instanceMap.get(participant.instance_id)?.name ||
                                  participant.instance_id}
                              </span>
                              {/* 显示预定义角色或默认角色 */}
                              {participant.role_name ? (
                                <Badge
                                  className="text-xs"
                                  style={{
                                    backgroundColor: participant.role_color || '#6B7280',
                                    color: '#fff',
                                  }}
                                >
                                  {participant.role_name}
                                </Badge>
                              ) : (
                                <Badge
                                  variant={
                                    participant.role === 'host'
                                      ? 'default'
                                      : participant.role === 'expert'
                                      ? 'secondary'
                                      : 'outline'
                                  }
                                  className="text-xs"
                                >
                                  {participant.role === 'host'
                                    ? '主持人'
                                    : participant.role === 'expert'
                                    ? '专家'
                                    : participant.role === 'observer'
                                    ? '观察员'
                                    : '参会者'}
                                </Badge>
                              )}
                            </div>
                            {selectedMeeting.status === 'in_progress' &&
                              participant.role !== 'host' && (
                                <>
                                  <Button
                                    size="sm"
                                    variant="ghost"
                                    onClick={() =>
                                      inviteSpeakMutation.mutate({
                                        meetingId: selectedMeeting.id,
                                        participantId: participant.id,
                                      })
                                    }
                                    disabled={inviteSpeakMutation.isPending}
                                    title="邀请发言"
                                  >
                                    <Mic className="h-4 w-4" />
                                  </Button>
                                  <Button
                                    size="sm"
                                    variant="ghost"
                                    onClick={() => {
                                      setSelectedParticipantForMessage(participant);
                                      setDirectMessageDialogOpen(true);
                                    }}
                                    title="发送私信"
                                  >
                                    <Mail className="h-4 w-4" />
                                  </Button>
                                </>
                              )}
                          </div>
                          {participant.expertise && (
                            <p className="text-sm text-muted-foreground mt-1">
                              专业: {participant.expertise}
                            </p>
                          )}
                          <p className="text-xs text-muted-foreground mt-1">
                            发言顺序: {participant.speaking_order}
                          </p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Messages */}
                <div className="col-span-2 overflow-auto">
                  <div className="p-4 border-b bg-muted/30">
                    <h3 className="font-medium">会议记录</h3>
                  </div>
                  {meetingMessages.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-32 text-muted-foreground">
                      <MessageSquare className="h-6 w-6 mb-2" />
                      <p className="text-sm">暂无消息</p>
                    </div>
                  ) : (
                    <ScrollArea className="h-[calc(100%-60px)]">
                      <div className="divide-y">
                        {meetingMessages.map((msg) => (
                          <div key={msg.id} className="p-4">
                            <div className="flex items-center gap-2 mb-1">
                              <Badge variant="outline" className="text-xs">
                                R{msg.round_number}
                              </Badge>
                              <span className="font-medium text-sm">
                                {instanceMap.get(msg.instance_id)?.name || msg.instance_id}
                              </span>
                              <span className="text-xs text-muted-foreground">
                                {new Date(msg.created_at).toLocaleTimeString('zh-CN')}
                              </span>
                            </div>
                            <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                          </div>
                        ))}
                      </div>
                      <div ref={messagesEndRef} />
                    </ScrollArea>
                  )}
                </div>
              </div>
            </CardContent>
          </>
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
            <Users className="h-12 w-12 mb-4" />
            <p>选择一个会议查看详情</p>
          </div>
        )}
      </Card>

      {/* Create Meeting Dialog */}
      <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>创建新会议</DialogTitle>
            <DialogDescription>创建一个新的智能体会议，选择主持人和会议类型</DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="title">会议主题</Label>
              <Input
                id="title"
                value={newMeeting.title}
                onChange={(e) => setNewMeeting({ ...newMeeting, title: e.target.value })}
                placeholder="输入会议主题"
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="description">会议描述</Label>
              <Textarea
                id="description"
                value={newMeeting.description}
                onChange={(e) => setNewMeeting({ ...newMeeting, description: e.target.value })}
                placeholder="输入会议描述（可选）"
                rows={3}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="meeting_type">会议类型</Label>
              <Select
                value={newMeeting.meeting_type}
                onValueChange={(value: MeetingType) =>
                  setNewMeeting({ ...newMeeting, meeting_type: value })
                }
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="brainstorm">头脑风暴</SelectItem>
                  <SelectItem value="expert_discussion">专家讨论</SelectItem>
                  <SelectItem value="decision_making">决策制定</SelectItem>
                  <SelectItem value="problem_solving">问题解决</SelectItem>
                  <SelectItem value="review">评审</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="grid gap-2">
              <Label htmlFor="host_instance_id">主持人</Label>
              <Select
                value={newMeeting.host_instance_id}
                onValueChange={(value) =>
                  setNewMeeting({ ...newMeeting, host_instance_id: value })
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="选择主持人实例" />
                </SelectTrigger>
                <SelectContent>
                  {allInstances.length === 0 ? (
                    <div className="px-2 py-1 text-muted-foreground text-sm">
                      没有配置实例
                    </div>
                  ) : (
                    allInstances.map((instance: Instance) => (
                      <SelectItem
                        key={instance.id}
                        value={instance.id}
                        disabled={instance.status !== 'connected'}
                      >
                        <div className="flex items-center gap-2">
                          <span>{instance.name} ({instance.host}:{instance.port})</span>
                          {instance.status === 'connected' ? (
                            <Badge variant="default" className="text-xs bg-green-500">已连接</Badge>
                          ) : instance.status === 'connecting' ? (
                            <Badge variant="secondary" className="text-xs">连接中</Badge>
                          ) : instance.status === 'error' ? (
                            <Badge variant="destructive" className="text-xs">错误</Badge>
                          ) : (
                            <Badge variant="outline" className="text-xs">未连接</Badge>
                          )}
                        </div>
                      </SelectItem>
                    ))
                  )}
                </SelectContent>
              </Select>
            </div>
            <div className="grid gap-2">
              <Label htmlFor="max_rounds">最大轮次</Label>
              <Input
                id="max_rounds"
                type="number"
                min={1}
                max={20}
                value={newMeeting.max_rounds}
                onChange={(e) =>
                  setNewMeeting({ ...newMeeting, max_rounds: parseInt(e.target.value) || 5 })
                }
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateDialogOpen(false)}>
              取消
            </Button>
            <Button
              onClick={() => createMutation.mutate(newMeeting)}
              disabled={!newMeeting.title || !newMeeting.host_instance_id || createMutation.isPending}
            >
              {createMutation.isPending && <Loader2 className="h-4 w-4 mr-1 animate-spin" />}
              创建
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Add Participant Dialog */}
      <Dialog open={participantDialogOpen} onOpenChange={(open) => {
        setParticipantDialogOpen(open);
        if (!open) {
          // 重置表单
          setNewParticipant({
            instance_id: '',
            role: 'participant',
            expertise: '',
            role_code: '',
            role_name: '',
            role_color: '',
          });
        }
      }}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>添加参会者</DialogTitle>
            <DialogDescription>
              添加一个智能体实例作为会议参会者
              {currentMeetingTypeRoles.length > 0 && (
                <span className="block mt-1 text-blue-500">
                  当前会议类型有 {currentMeetingTypeRoles.length} 个预定义角色可用
                </span>
              )}
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            {/* 预定义角色选择 */}
            {currentMeetingTypeRoles.length > 0 && (
              <div className="grid gap-2">
                <Label>预定义角色</Label>
                <div className="grid grid-cols-2 gap-2">
                  {availablePredefinedRoles.length > 0 ? (
                    availablePredefinedRoles.map((role) => (
                      <div
                        key={role.code}
                        className={`p-3 border rounded-lg cursor-pointer transition-all ${
                          newParticipant.role_code === role.code
                            ? 'border-primary bg-primary/10'
                            : 'hover:border-primary/50'
                        }`}
                        onClick={() => {
                          setNewParticipant({
                            ...newParticipant,
                            role_code: role.code,
                            role_name: role.name,
                            role_color: role.color,
                            role: role.is_host ? 'host' : 'participant',
                          });
                        }}
                      >
                        <div className="flex items-center gap-2">
                          <div
                            className="w-4 h-4 rounded-full"
                            style={{ backgroundColor: role.color }}
                          />
                          <span className="font-medium text-sm">{role.name}</span>
                        </div>
                        <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                          {role.description}
                        </p>
                      </div>
                    ))
                  ) : (
                    <div className="col-span-2 text-sm text-muted-foreground p-2">
                      所有预定义角色已分配完毕
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* 实例选择 */}
            <div className="grid gap-2">
              <Label htmlFor="participant_instance_id">实例</Label>
              <Select
                value={newParticipant.instance_id}
                onValueChange={(value) =>
                  setNewParticipant({ ...newParticipant, instance_id: value })
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="选择实例" />
                </SelectTrigger>
                <SelectContent>
                  {availableInstancesForParticipant.length === 0 ? (
                    <div className="px-2 py-1 text-muted-foreground text-sm">
                      没有可用的已连接实例
                    </div>
                  ) : (
                    availableInstancesForParticipant.map((instance: Instance) => (
                      <SelectItem key={instance.id} value={instance.id}>
                        <div className="flex items-center gap-2">
                          <span>{instance.name} ({instance.host}:{instance.port})</span>
                          <Badge variant="default" className="text-xs bg-green-500">已连接</Badge>
                        </div>
                      </SelectItem>
                    ))
                  )}
                </SelectContent>
              </Select>
            </div>

            {/* 角色（如果没有选择预定义角色） */}
            {currentMeetingTypeRoles.length === 0 && (
              <div className="grid gap-2">
                <Label htmlFor="role">角色类型</Label>
                <Select
                  value={newParticipant.role}
                  onValueChange={(value: typeof newParticipant.role) =>
                    setNewParticipant({ ...newParticipant, role: value })
                  }
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="expert">专家</SelectItem>
                    <SelectItem value="participant">参会者</SelectItem>
                    <SelectItem value="observer">观察员</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            )}

            {/* 专业领域 */}
            <div className="grid gap-2">
              <Label htmlFor="expertise">专业领域</Label>
              <Input
                id="expertise"
                value={newParticipant.expertise}
                onChange={(e) =>
                  setNewParticipant({ ...newParticipant, expertise: e.target.value })
                }
                placeholder="描述该参会者的专业领域（可选）"
              />
            </div>

            {/* 显示选中的预定义角色 */}
            {newParticipant.role_code && (
              <div className="flex items-center gap-2 p-2 bg-muted rounded">
                <div
                  className="w-4 h-4 rounded-full"
                  style={{ backgroundColor: newParticipant.role_color }}
                />
                <span className="text-sm">已选择: {newParticipant.role_name}</span>
                <Button
                  variant="ghost"
                  size="sm"
                  className="ml-auto"
                  onClick={() => setNewParticipant({
                    ...newParticipant,
                    role_code: '',
                    role_name: '',
                    role_color: '',
                    role: 'participant',
                  })}
                >
                  清除
                </Button>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setParticipantDialogOpen(false)}>
              取消
            </Button>
            <Button
              onClick={() => addParticipantMutation.mutate(newParticipant)}
              disabled={!newParticipant.instance_id || addParticipantMutation.isPending}
            >
              {addParticipantMutation.isPending && (
                <Loader2 className="h-4 w-4 mr-1 animate-spin" />
              )}
              添加
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Direct Message Dialog */}
      <Dialog open={directMessageDialogOpen} onOpenChange={(open) => {
        setDirectMessageDialogOpen(open);
        if (!open) {
          setDirectMessageError(null);
          setDirectMessageContent('');
          setSelectedParticipantForMessage(null);
        }
      }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>发送私信</DialogTitle>
            <DialogDescription>
              向 {selectedParticipantForMessage && instanceMap.get(selectedParticipantForMessage.instance_id)?.name} 发送消息
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            {directMessageError && (
              <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative">
                <AlertCircle className="h-4 w-4 inline mr-2" />
                {directMessageError}
              </div>
            )}
            <div className="grid gap-2">
              <Label htmlFor="direct_message">消息内容</Label>
              <Textarea
                id="direct_message"
                value={directMessageContent}
                onChange={(e) => setDirectMessageContent(e.target.value)}
                placeholder="输入要发送的消息..."
                rows={4}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => {
              setDirectMessageDialogOpen(false);
              setDirectMessageContent('');
              setSelectedParticipantForMessage(null);
              setDirectMessageError(null);
            }}>
              取消
            </Button>
            <Button
              onClick={() => {
                if (selectedMeeting && selectedParticipantForMessage && directMessageContent.trim()) {
                  sendDirectMessageMutation.mutate({
                    meetingId: selectedMeeting.id,
                    participantId: selectedParticipantForMessage.id,
                    content: directMessageContent.trim(),
                  });
                }
              }}
              disabled={!directMessageContent.trim() || sendDirectMessageMutation.isPending}
            >
              {sendDirectMessageMutation.isPending && (
                <Loader2 className="h-4 w-4 mr-1 animate-spin" />
              )}
              发送
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}