import { useEffect, useRef, useState } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Send,
  AlertCircle,
  Plus,
  Trash2,
  X,
  MessageSquare,
  RefreshCw,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Input } from '@/components/ui/input';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { sessionApi, instanceApi } from '@/services/api';
import { wsService } from '@/services/websocket';
import { useAppStore } from '@/store/appStore';
import { formatBeijingTimeShort } from '@/utils/time';
import type { Message, WebSocketEvent, SessionCreate } from '@/types';

export function ChatPage() {
  const { sessionId: urlSessionId } = useParams<{ sessionId?: string }>();
  const queryClient = useQueryClient();
  const scrollRef = useRef<HTMLDivElement>(null);
  const [inputMessage, setInputMessage] = useState('');
  const [sendError, setSendError] = useState<string | null>(null);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [isWaitingForReply, setIsWaitingForReply] = useState(false);
  const [showNewMessage, setShowNewMessage] = useState(false);
  const [isAtBottom, setIsAtBottom] = useState(true);
  const [newSession, setNewSession] = useState<Partial<SessionCreate>>({
    instance_id: '',
    target: '',
    context: {},
  });

  const { selectedSession, selectSession, addMessage, setMessages } =
    useAppStore();

  // 获取会话列表
  const { data: sessions, isLoading: sessionsLoading } = useQuery({
    queryKey: ['sessions'],
    queryFn: () => sessionApi.list(),
  });

  // 获取当前选中的会话详情
  const sessionId = selectedSession?.id;
  const { data: session } = useQuery({
    queryKey: ['session', sessionId],
    queryFn: () => (sessionId ? sessionApi.get(sessionId) : null),
    enabled: !!sessionId,
  });

  // 获取消息
  const { data: messages } = useQuery({
    queryKey: ['messages', sessionId],
    queryFn: () =>
      sessionId ? sessionApi.getMessages(sessionId) : { items: [], total: 0 },
    enabled: !!sessionId,
  });

  // 获取实例列表
  const { data: instances } = useQuery({
    queryKey: ['instances'],
    queryFn: instanceApi.list,
  });

  // 创建会话
  const createMutation = useMutation({
    mutationFn: sessionApi.create,
    onSuccess: (session) => {
      queryClient.invalidateQueries({ queryKey: ['sessions'] });
      setIsCreateOpen(false);
      setNewSession({ instance_id: '', target: '', context: {} });
      selectSession(session);
    },
  });

  // 删除会话
  const deleteMutation = useMutation({
    mutationFn: sessionApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sessions'] });
      if (selectedSession) {
        selectSession(null);
      }
    },
  });

  // 关闭会话
  const closeMutation = useMutation({
    mutationFn: sessionApi.close,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sessions'] });
    },
  });

  // 发送消息
  const sendMessageMutation = useMutation({
    mutationFn: (content: string) =>
      sessionApi.sendMessage(sessionId!, { content }),
    onSuccess: (message) => {
      addMessage(sessionId!, message);
      setInputMessage('');
      setSendError(null);
      // 注意：isWaitingForReply 已在 handleSend 中设置，这里不需要再设置
      queryClient.invalidateQueries({ queryKey: ['messages', sessionId] });
    },
    onError: (error: Error) => {
      setSendError(error.message || '发送失败');
      setIsWaitingForReply(false);
    },
  });

  // 同步 session 数据
  useEffect(() => {
    if (session) {
      selectSession(session);
    }
  }, [session, selectSession]);

  // 根据 URL 参数自动选中会话
  useEffect(() => {
    if (urlSessionId && sessions?.items && !selectedSession) {
      const targetSession = sessions.items.find((s) => s.id === urlSessionId);
      if (targetSession) {
        selectSession(targetSession);
      }
    }
  }, [urlSessionId, sessions, selectedSession, selectSession]);

  // 存储消息到全局状态
  useEffect(() => {
    if (messages?.items && sessionId) {
      setMessages(sessionId, messages.items);
    }
  }, [messages, sessionId, setMessages]);

  // WebSocket 连接
  useEffect(() => {
    if (!sessionId) return;

    if (!wsService.isConnected()) {
      wsService.connect();
    }

    wsService.joinSession(sessionId);

    return () => {
      wsService.leaveSession(sessionId);
    };
  }, [sessionId]);

  // WebSocket 事件订阅
  // 注意：使用 ref 存储 isAtBottom 以避免重新订阅
  const isAtBottomRef = useRef(isAtBottom);
  isAtBottomRef.current = isAtBottom;

  useEffect(() => {
    if (!sessionId) return;

    const unsubscribe = wsService.subscribe(
      `session:${sessionId}`,
      (event: WebSocketEvent) => {
        console.log('ChatPage 收到 WebSocket 事件:', event);
        if (event.type === 'message' && event.data) {
          const message = event.data as Message;
          console.log('收到消息, role:', message.role, 'content:', message.content?.substring(0, 50));
          addMessage(sessionId, message);

          // 收到助手或系统消息时清除等待状态
          if (message.role === 'assistant' || message.role === 'system') {
            console.log('收到助手/系统消息，清除等待状态');
            setIsWaitingForReply(false);
          }
          // 如果不在底部，显示新消息提示
          if (!isAtBottomRef.current) {
            setShowNewMessage(true);
          }
          queryClient.invalidateQueries({ queryKey: ['messages', sessionId] });
        }
      }
    );

    return () => {
      unsubscribe();
    };
  }, [sessionId, addMessage, queryClient]);

  // 检测是否在底部
  const checkIsAtBottom = () => {
    const scrollElement = scrollRef.current?.querySelector('[data-radix-scroll-area-viewport]');
    if (scrollElement) {
      const { scrollTop, scrollHeight, clientHeight } = scrollElement;
      const isBottom = scrollHeight - scrollTop - clientHeight < 50;
      setIsAtBottom(isBottom);
      if (isBottom) {
        setShowNewMessage(false);
      }
    }
  };

  // 滚动事件监听
  useEffect(() => {
    const scrollElement = scrollRef.current?.querySelector('[data-radix-scroll-area-viewport]');
    if (scrollElement) {
      scrollElement.addEventListener('scroll', checkIsAtBottom);
      return () => {
        scrollElement.removeEventListener('scroll', checkIsAtBottom);
      };
    }
  }, [messages?.items]);

  // 自动滚动到底部（仅在用户已在底部时）
  useEffect(() => {
    const scrollElement = scrollRef.current?.querySelector('[data-radix-scroll-area-viewport]');
    if (scrollElement && isAtBottom) {
      scrollElement.scrollTop = scrollElement.scrollHeight;
    }
  }, [messages?.items, isWaitingForReply, isAtBottom]);

  // 切换会话时重置状态
  useEffect(() => {
    setShowNewMessage(false);
    setIsAtBottom(true);
    setIsWaitingForReply(false); // 重置等待回复状态
  }, [sessionId]);

  // 点击滚动到底部
  const scrollToBottom = () => {
    const scrollElement = scrollRef.current?.querySelector('[data-radix-scroll-area-viewport]');
    if (scrollElement) {
      scrollElement.scrollTop = scrollElement.scrollHeight;
      setShowNewMessage(false);
      setIsAtBottom(true);
    }
  };

  const handleSend = () => {
    if (!inputMessage.trim() || !sessionId) return;
    setSendError(null);
    // 设置等待状态，让动画显示
    setIsWaitingForReply(true);
    // 使用 setTimeout 确保动画有机会渲染
    setTimeout(() => {
      sendMessageMutation.mutate(inputMessage);
    }, 0);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleSelectSession = (session: any) => {
    selectSession(session);
    setSendError(null);
  };

  const instance = instances?.items.find(
    (i) => i.id === selectedSession?.instance_id
  );

  return (
    <div className="flex h-[calc(100vh-6rem)] gap-0">
      {/* 左侧会话列表 */}
      <div
        className={`flex flex-col border-r bg-muted/30 transition-all duration-300 ${
          sidebarCollapsed ? 'w-12' : 'w-80'
        }`}
      >
        {/* 折叠按钮 */}
        <div className="flex items-center justify-between border-b p-2">
          {!sidebarCollapsed && (
            <div className="flex items-center gap-2">
              <MessageSquare className="h-5 w-5" />
              <span className="font-semibold">会话列表</span>
            </div>
          )}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
          >
            {sidebarCollapsed ? (
              <ChevronRight className="h-4 w-4" />
            ) : (
              <ChevronLeft className="h-4 w-4" />
            )}
          </Button>
        </div>

        {!sidebarCollapsed && (
          <>
            {/* 新建会话按钮 */}
            <div className="p-2">
              <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
                <DialogTrigger asChild>
                  <Button className="w-full" size="sm">
                    <Plus className="mr-2 h-4 w-4" />
                    新建会话
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>创建新会话</DialogTitle>
                  </DialogHeader>
                  <div className="space-y-4 py-4">
                    <div className="space-y-2">
                      <label className="text-sm font-medium">实例</label>
                      <Select
                        value={newSession.instance_id}
                        onValueChange={(value) =>
                          setNewSession({ ...newSession, instance_id: value })
                        }
                      >
                        <SelectTrigger>
                          <SelectValue placeholder="选择一个实例" />
                        </SelectTrigger>
                        <SelectContent>
                          {instances?.items
                            .filter((i) => i.status === 'connected')
                            .map((instance) => (
                              <SelectItem key={instance.id} value={instance.id}>
                                {instance.name}
                              </SelectItem>
                            ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <label className="text-sm font-medium">目标会话 ID</label>
                      <Input
                        placeholder="输入目标会话 ID"
                        value={newSession.target}
                        onChange={(e) =>
                          setNewSession({ ...newSession, target: e.target.value })
                        }
                      />
                    </div>
                  </div>
                  <div className="flex justify-end gap-2">
                    <Button variant="outline" onClick={() => setIsCreateOpen(false)}>
                      取消
                    </Button>
                    <Button
                      onClick={() =>
                        createMutation.mutate(newSession as SessionCreate)
                      }
                      disabled={!newSession.instance_id || !newSession.target}
                    >
                      创建
                    </Button>
                  </div>
                </DialogContent>
              </Dialog>
            </div>

            {/* 会话列表 */}
            <ScrollArea className="flex-1">
              <div className="space-y-1 p-2">
                {sessionsLoading ? (
                  <div className="flex items-center justify-center py-8">
                    <RefreshCw className="h-6 w-6 animate-spin text-muted-foreground" />
                  </div>
                ) : sessions?.items.length === 0 ? (
                  <div className="py-8 text-center text-sm text-muted-foreground">
                    暂无会话
                  </div>
                ) : (
                  sessions?.items.map((s) => (
                    <div
                      key={s.id}
                      className={`group flex cursor-pointer items-center justify-between rounded-lg p-3 transition-colors ${
                        selectedSession?.id === s.id
                          ? 'bg-primary/10 text-primary'
                          : 'hover:bg-muted'
                      }`}
                      onClick={() => handleSelectSession(s)}
                    >
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <span className="truncate font-medium">{s.target}</span>
                          {s.is_active ? (
                            <Badge variant="default" className="text-xs">
                              活跃
                            </Badge>
                          ) : (
                            <Badge variant="secondary" className="text-xs">
                              已关闭
                            </Badge>
                          )}
                        </div>
                        <div className="mt-1 truncate text-xs text-muted-foreground">
                          {instances?.items.find((i) => i.id === s.instance_id)?.name}
                        </div>
                      </div>
                      <div className="flex gap-1 opacity-0 transition-opacity group-hover:opacity-100">
                        {s.is_active && (
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-6 w-6 p-0"
                            onClick={(e) => {
                              e.stopPropagation();
                              closeMutation.mutate(s.id);
                            }}
                          >
                            <X className="h-3 w-3" />
                          </Button>
                        )}
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-6 w-6 p-0 text-destructive hover:text-destructive"
                          onClick={(e) => {
                            e.stopPropagation();
                            deleteMutation.mutate(s.id);
                          }}
                        >
                          <Trash2 className="h-3 w-3" />
                        </Button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </ScrollArea>
          </>
        )}
      </div>

      {/* 右侧聊天区域 */}
      <div className="flex flex-1 flex-col">
        {!selectedSession ? (
          // 未选择会话时的占位
          <div className="flex flex-1 items-center justify-center">
            <div className="text-center">
              <MessageSquare className="mx-auto h-16 w-16 text-muted-foreground/50" />
              <h3 className="mt-4 text-lg font-semibold">选择一个会话</h3>
              <p className="mt-2 text-muted-foreground">
                从左侧列表选择会话或创建新会话开始聊天
              </p>
            </div>
          </div>
        ) : (
          <>
            {/* 聊天头部 */}
            <div className="flex items-center justify-between border-b px-4 py-3">
              <div className="flex items-center gap-3">
                <h2 className="text-lg font-semibold">
                  {selectedSession.target}
                </h2>
                {selectedSession.is_active ? (
                  <Badge variant="default">活跃</Badge>
                ) : (
                  <Badge variant="secondary">已关闭</Badge>
                )}
                {instance && (
                  <span className="text-sm text-muted-foreground">
                    通过 {instance.name}
                  </span>
                )}
              </div>
            </div>

            {/* 警告信息 */}
            {!selectedSession.is_active && (
              <div className="flex items-center gap-2 bg-yellow-50 p-3 text-sm text-yellow-800">
                <AlertCircle className="h-4 w-4" />
                此会话已关闭，无法发送新消息
              </div>
            )}

            {sendError && (
              <div className="flex items-center gap-2 bg-red-50 p-3 text-sm text-red-800">
                <AlertCircle className="h-4 w-4" />
                {sendError}
              </div>
            )}

            {instance && instance.status !== 'connected' && (
              <div className="flex items-center gap-2 bg-orange-50 p-3 text-sm text-orange-800">
                <AlertCircle className="h-4 w-4" />
                实例未连接：{instance.name}，请先在实例管理页面连接实例
              </div>
            )}

            {/* 消息区域 */}
            <Card className="relative flex flex-1 flex-col overflow-hidden rounded-none border-0 shadow-none">
              <ScrollArea className="flex-1 p-4" ref={scrollRef}>
                <div className="space-y-4">
                  {messages?.items
                    .slice()
                    .reverse()
                    .map((message) => (
                    <div
                      key={message.id}
                      className={`flex ${
                        message.role === 'user' ? 'justify-end' : 'justify-start'
                      }`}
                    >
                      <div
                        className={`max-w-[70%] rounded-lg px-4 py-2 ${
                          message.role === 'user'
                            ? 'bg-primary text-primary-foreground'
                            : message.role === 'system'
                            ? 'bg-muted text-muted-foreground'
                            : 'bg-secondary text-secondary-foreground'
                        }`}
                      >
                        <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                        <span className="mt-1 block text-xs opacity-70">
                          {formatBeijingTimeShort(message.created_at)}
                          {message.latency_ms && ` · ${message.latency_ms}ms`}
                        </span>
                      </div>
                    </div>
                  ))}
                  {!messages?.items.length && (
                    <div className="flex h-32 items-center justify-center text-muted-foreground">
                      暂无消息，开始对话吧！
                    </div>
                  )}
                  {/* 正在思考动画 */}
                  {isWaitingForReply && (
                    <div className="flex justify-start">
                      <div className="flex items-center gap-1 rounded-lg bg-secondary px-4 py-3">
                        <span className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground [animation-delay:0ms]" />
                        <span className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground [animation-delay:150ms]" />
                        <span className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground [animation-delay:300ms]" />
                      </div>
                    </div>
                  )}
                </div>
              </ScrollArea>

              {/* 有新消息提示 */}
              {showNewMessage && (
                <div className="absolute bottom-20 left-1/2 -translate-x-1/2">
                  <Button
                    variant="secondary"
                    size="sm"
                    className="animate-pulse rounded-full shadow-lg"
                    onClick={scrollToBottom}
                  >
                    <ChevronDown className="mr-1 h-4 w-4" />
                    有新消息
                  </Button>
                </div>
              )}

              {/* 输入区域 */}
              <CardContent className="border-t p-4">
                <div className="flex gap-2">
                  <Textarea
                    placeholder="输入您的消息..."
                    value={inputMessage}
                    onChange={(e) => setInputMessage(e.target.value)}
                    onKeyDown={handleKeyDown}
                    disabled={!selectedSession.is_active}
                    className="min-h-[80px] flex-1 resize-none"
                  />
                  <Button
                    onClick={handleSend}
                    disabled={
                      !inputMessage.trim() ||
                      !selectedSession.is_active ||
                      sendMessageMutation.isPending
                    }
                    className="self-end"
                  >
                    <Send className="h-4 w-4" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          </>
        )}
      </div>
    </div>
  );
}