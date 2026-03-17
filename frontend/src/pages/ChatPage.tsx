import { useEffect, useRef, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Send, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { sessionApi, instanceApi } from '@/services/api';
import { wsService } from '@/services/websocket';
import { useAppStore } from '@/store/appStore';
import { formatBeijingTimeShort } from '@/utils/time';
import type { Message, WebSocketEvent } from '@/types';

export function ChatPage() {
  const { sessionId } = useParams<{ sessionId?: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const scrollRef = useRef<HTMLDivElement>(null);
  const [inputMessage, setInputMessage] = useState('');
  const [sendError, setSendError] = useState<string | null>(null);

  const { selectedSession, selectSession, addMessage, setMessages } =
    useAppStore();

  const { data: sessions } = useQuery({
    queryKey: ['sessions'],
    queryFn: () => sessionApi.list(),
  });

  const { data: session } = useQuery({
    queryKey: ['session', sessionId],
    queryFn: () => (sessionId ? sessionApi.get(sessionId) : null),
    enabled: !!sessionId,
  });

  const { data: messages } = useQuery({
    queryKey: ['messages', sessionId],
    queryFn: () =>
      sessionId ? sessionApi.getMessages(sessionId) : { items: [], total: 0 },
    enabled: !!sessionId,
  });

  const { data: instances } = useQuery({
    queryKey: ['instances'],
    queryFn: instanceApi.list,
  });

  const sendMessageMutation = useMutation({
    mutationFn: (content: string) =>
      sessionApi.sendMessage(sessionId!, { content }),
    onSuccess: (message) => {
      addMessage(sessionId!, message);
      setInputMessage('');
      setSendError(null);
      // Invalidate messages query to refetch
      queryClient.invalidateQueries({ queryKey: ['messages', sessionId] });
    },
    onError: (error: Error) => {
      setSendError(error.message || '发送失败');
    },
  });

  // Set selected session from URL
  useEffect(() => {
    if (session) {
      selectSession(session);
    }
  }, [session, selectSession]);

  // Store messages in global state
  useEffect(() => {
    if (messages?.items && sessionId) {
      setMessages(sessionId, messages.items);
    }
  }, [messages, sessionId, setMessages]);

  // Connect to WebSocket and join session room
  useEffect(() => {
    if (!sessionId) return;

    // Ensure WebSocket is connected
    if (!wsService.isConnected()) {
      wsService.connect();
    }

    // Join the session room to receive pushed messages
    wsService.joinSession(sessionId);

    return () => {
      // Leave the session room when navigating away
      wsService.leaveSession(sessionId);
    };
  }, [sessionId]);

  // Subscribe to WebSocket events
  useEffect(() => {
    if (!sessionId) return;

    const unsubscribe = wsService.subscribe(
      `session:${sessionId}`,
      (event: WebSocketEvent) => {
        console.log('ChatPage received WebSocket event:', event);
        if (event.type === 'message' && event.data) {
          // The data contains the message directly from push_message_to_session
          const message = event.data as Message;
          addMessage(sessionId, message);
          // Also invalidate to ensure consistency
          queryClient.invalidateQueries({ queryKey: ['messages', sessionId] });
        }
      }
    );

    return () => {
      unsubscribe();
    };
  }, [sessionId, addMessage, queryClient]);

  // Auto-scroll to bottom
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages?.items]);

  const handleSend = () => {
    if (!inputMessage.trim() || !sessionId) return;
    setSendError(null);
    sendMessageMutation.mutate(inputMessage);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  if (!sessionId) {
    return (
      <div className="flex h-[calc(100vh-8rem)] items-center justify-center">
        <div className="text-center">
          <h3 className="text-lg font-semibold">选择一个会话</h3>
          <p className="text-muted-foreground">
            从列表中选择一个会话或创建新会话。
          </p>
          <div className="mt-4 space-y-2">
            {sessions?.items.slice(0, 5).map((s) => (
              <Button
                key={s.id}
                variant="outline"
                className="w-full justify-start"
                onClick={() => navigate(`/chat/${s.id}`)}
              >
                {s.target}
              </Button>
            ))}
            {!sessions?.items.length && (
              <Button onClick={() => navigate('/sessions')}>
                创建新会话
              </Button>
            )}
          </div>
        </div>
      </div>
    );
  }

  const instance = instances?.items.find(
    (i) => i.id === selectedSession?.instance_id
  );

  return (
    <div className="flex h-[calc(100vh-6rem)] flex-col gap-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <h2 className="text-2xl font-bold tracking-tight">
            {selectedSession?.target || '聊天'}
          </h2>
          {selectedSession?.is_active ? (
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

      {!selectedSession?.is_active && (
        <div className="flex items-center gap-2 rounded-md bg-yellow-50 p-3 text-sm text-yellow-800">
          <AlertCircle className="h-4 w-4" />
          此会话已关闭，无法发送新消息。
        </div>
      )}

      {sendError && (
        <div className="flex items-center gap-2 rounded-md bg-red-50 p-3 text-sm text-red-800">
          <AlertCircle className="h-4 w-4" />
          {sendError}
        </div>
      )}

      {instance && instance.status !== 'connected' && (
        <div className="flex items-center gap-2 rounded-md bg-orange-50 p-3 text-sm text-orange-800">
          <AlertCircle className="h-4 w-4" />
          实例未连接：{instance.name}，请先在实例管理页面连接实例。
        </div>
      )}

      <Card className="flex flex-1 flex-col overflow-hidden">
        <ScrollArea className="flex-1 p-4" ref={scrollRef}>
          <div className="space-y-4">
            {messages?.items.map((message) => (
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
                  <p className="text-sm">{message.content}</p>
                  <span className="mt-1 block text-xs opacity-70">
                    {formatBeijingTimeShort(message.created_at)}
                    {message.latency_ms && ` · ${message.latency_ms}ms`}
                  </span>
                </div>
              </div>
            ))}
            {!messages?.items.length && (
              <div className="flex h-32 items-center justify-center text-muted-foreground">
                暂无消息。开始对话吧！
              </div>
            )}
          </div>
        </ScrollArea>

        <CardContent className="border-t p-4">
          <div className="flex gap-2">
            <Textarea
              placeholder="输入您的消息..."
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={!selectedSession?.is_active}
              className="min-h-[80px] flex-1 resize-none"
            />
            <Button
              onClick={handleSend}
              disabled={
                !inputMessage.trim() ||
                !selectedSession?.is_active ||
                sendMessageMutation.isPending
              }
              className="self-end"
            >
              <Send className="h-4 w-4" />
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
