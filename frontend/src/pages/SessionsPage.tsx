import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import {
  Plus,
  Trash2,
  MessageSquare,
  RefreshCw,
  X,
  ExternalLink,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { instanceApi, sessionApi } from '@/services/api';
import { formatBeijingTime } from '@/utils/time';
import type { SessionCreate } from '@/types';

export function SessionsPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [newSession, setNewSession] = useState<Partial<SessionCreate>>({
    instance_id: '',
    target: '',
    context: {},
  });

  const { data: sessions, isLoading } = useQuery({
    queryKey: ['sessions'],
    queryFn: () => sessionApi.list(),
  });

  const { data: instances } = useQuery({
    queryKey: ['instances'],
    queryFn: instanceApi.list,
  });

  const createMutation = useMutation({
    mutationFn: sessionApi.create,
    onSuccess: (session) => {
      queryClient.invalidateQueries({ queryKey: ['sessions'] });
      setIsCreateOpen(false);
      setNewSession({ instance_id: '', target: '', context: {} });
      navigate(`/chat/${session.id}`);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: sessionApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sessions'] });
    },
  });

  const closeMutation = useMutation({
    mutationFn: sessionApi.close,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sessions'] });
    },
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">会话管理</h2>
          <p className="text-muted-foreground">
            管理您的 OpenClaw 实例聊天会话。
          </p>
        </div>
        <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
          <DialogTrigger asChild>
            <Button>
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
                    {instances?.items.map((instance) => (
                      <SelectItem key={instance.id} value={instance.id}>
                        {instance.name} ({instance.host}:{instance.port})
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

      {isLoading ? (
        <div className="flex h-64 items-center justify-center">
          <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : (
        <div className="grid gap-4">
          {sessions?.items.map((session) => (
            <Card key={session.id}>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <div className="flex items-center gap-2">
                  <MessageSquare className="h-5 w-5 text-muted-foreground" />
                  <CardTitle className="text-base font-medium">
                    {session.target}
                  </CardTitle>
                  {session.is_active ? (
                    <Badge variant="default">活跃</Badge>
                  ) : (
                    <Badge variant="secondary">已关闭</Badge>
                  )}
                </div>
                <div className="flex gap-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => navigate(`/chat/${session.id}`)}
                  >
                    <ExternalLink className="h-4 w-4" />
                  </Button>
                  {session.is_active && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => closeMutation.mutate(session.id)}
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  )}
                  <Button
                    variant="destructive"
                    size="sm"
                    onClick={() => deleteMutation.mutate(session.id)}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <div className="flex items-center justify-between text-sm text-muted-foreground">
                  <div className="flex gap-4">
                    <span>
                      实例：
                      {
                        instances?.items.find(
                          (i) => i.id === session.instance_id
                        )?.name
                      }
                    </span>
                    <span>
                      创建时间：
                      {formatBeijingTime(session.created_at)}
                    </span>
                  </div>
                  {session.last_message_at && (
                    <span>
                      最后消息：
                      {formatBeijingTime(session.last_message_at)}
                    </span>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {!isLoading && !sessions?.items.length && (
        <div className="flex h-64 flex-col items-center justify-center text-center">
          <MessageSquare className="h-12 w-12 text-muted-foreground" />
          <h3 className="mt-4 text-lg font-semibold">暂无会话</h3>
          <p className="text-muted-foreground">
            创建新会话以开始与 OpenClaw 聊天。
          </p>
        </div>
      )}
    </div>
  );
}
