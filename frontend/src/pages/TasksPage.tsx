import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Plus,
  ClipboardList,
  Clock,
  CheckCircle,
  XCircle,
  Play,
  UserPlus,
  Trash2,
  ChevronRight,
  AlertCircle,
  Loader2,
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
import { taskApi, instanceApi } from '@/services/api';
import { useAppStore } from '@/store/appStore';
import type { TaskStatus, TaskPriority, Instance, SubTask } from '@/types';

const statusConfig: Record<TaskStatus, { label: string; color: string; icon: typeof ClipboardList }> = {
  draft: { label: '草稿', color: 'bg-gray-500', icon: ClipboardList },
  published: { label: '已发布', color: 'bg-blue-500', icon: AlertCircle },
  assigned: { label: '已分配', color: 'bg-indigo-500', icon: UserPlus },
  analyzing: { label: '分析中', color: 'bg-yellow-500', icon: Loader2 },
  decomposed: { label: '已分解', color: 'bg-orange-500', icon: ClipboardList },
  in_progress: { label: '进行中', color: 'bg-green-500', icon: Play },
  completed: { label: '已完成', color: 'bg-emerald-500', icon: CheckCircle },
  failed: { label: '失败', color: 'bg-red-500', icon: XCircle },
};

const priorityConfig: Record<TaskPriority, { label: string; color: string }> = {
  low: { label: '低', color: 'bg-gray-400' },
  medium: { label: '中', color: 'bg-blue-400' },
  high: { label: '高', color: 'bg-orange-400' },
  urgent: { label: '紧急', color: 'bg-red-400' },
};

export function TasksPage() {
  const queryClient = useQueryClient();
  const { selectedTask, selectTask, tasks, setTasks } = useAppStore();

  // State
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [assignDialogOpen, setAssignDialogOpen] = useState(false);
  const [newTask, setNewTask] = useState({
    title: '',
    description: '',
    priority: 'medium' as TaskPriority,
    tags: '',
  });
  const [selectedManagerId, setSelectedManagerId] = useState<string>('');

  // Queries
  const { data: tasksData, isLoading: tasksLoading } = useQuery({
    queryKey: ['tasks'],
    queryFn: () => taskApi.list({ limit: 100 }),
  });

  const { data: instancesData } = useQuery({
    queryKey: ['instances'],
    queryFn: () => instanceApi.list(),
  });

  const { data: subtasksData } = useQuery({
    queryKey: ['subtasks', selectedTask?.id],
    queryFn: () => (selectedTask ? taskApi.getSubtasks(selectedTask.id) : null),
    enabled: !!selectedTask,
  });

  const { data: progressData } = useQuery({
    queryKey: ['progress', selectedTask?.id],
    queryFn: () => (selectedTask ? taskApi.getProgress(selectedTask.id) : null),
    enabled: !!selectedTask,
  });

  // Update store when data loads
  useEffect(() => {
    if (tasksData?.items) {
      setTasks(tasksData.items);
    }
  }, [tasksData, setTasks]);

  // Mutations
  const createMutation = useMutation({
    mutationFn: (data: typeof newTask) =>
      taskApi.create({
        title: data.title,
        description: data.description || undefined,
        priority: data.priority,
        tags: data.tags ? data.tags.split(',').map((t) => t.trim()) : undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      setCreateDialogOpen(false);
      setNewTask({ title: '', description: '', priority: 'medium', tags: '' });
    },
  });

  const publishMutation = useMutation({
    mutationFn: (id: string) => taskApi.publish(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
    },
  });

  const assignManagerMutation = useMutation({
    mutationFn: (data: { taskId: string; managerId: string }) =>
      taskApi.assignManager(data.taskId, { manager_instance_id: data.managerId }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      setAssignDialogOpen(false);
      setSelectedManagerId('');
    },
  });

  const analyzeMutation = useMutation({
    mutationFn: (id: string) => taskApi.analyze(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
    },
  });

  const confirmMutation = useMutation({
    mutationFn: (id: string) => taskApi.confirm(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
    },
  });

  const startMutation = useMutation({
    mutationFn: (id: string) => taskApi.start(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => taskApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      selectTask(null);
    },
  });

  // Helper functions
  const getStatusBadge = (status: TaskStatus) => {
    const config = statusConfig[status];
    const Icon = config.icon;
    return (
      <Badge className={`${config.color} text-white gap-1`}>
        <Icon className={`h-3 w-3 ${status === 'analyzing' ? 'animate-spin' : ''}`} />
        {config.label}
      </Badge>
    );
  };

  const getPriorityBadge = (priority: TaskPriority) => {
    const config = priorityConfig[priority];
    return <Badge className={`${config.color} text-white`}>{config.label}</Badge>;
  };

  const connectedInstances = instancesData?.items.filter(
    (i) => i.status === 'connected'
  ) || [];

  return (
    <div className="flex h-[calc(100vh-120px)] gap-4">
      {/* Task List */}
      <Card className="w-80 flex-shrink-0 overflow-hidden flex flex-col">
        <CardHeader className="flex-shrink-0">
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg">任务列表</CardTitle>
            <Button
              size="sm"
              onClick={() => setCreateDialogOpen(true)}
            >
              <Plus className="h-4 w-4 mr-1" />
              新建
            </Button>
          </div>
        </CardHeader>
        <CardContent className="flex-1 overflow-auto p-0">
          {tasksLoading ? (
            <div className="flex items-center justify-center h-32">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : tasks.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-32 text-muted-foreground">
              <ClipboardList className="h-8 w-8 mb-2" />
              <p className="text-sm">暂无任务</p>
            </div>
          ) : (
            <div className="divide-y">
              {tasks.map((task) => (
                <div
                  key={task.id}
                  className={`p-4 cursor-pointer hover:bg-accent transition-colors ${
                    selectedTask?.id === task.id ? 'bg-accent' : ''
                  }`}
                  onClick={() => selectTask(task)}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      <h4 className="font-medium truncate">{task.title}</h4>
                      <p className="text-sm text-muted-foreground line-clamp-2 mt-1">
                        {task.description || '无描述'}
                      </p>
                    </div>
                    <ChevronRight className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                  </div>
                  <div className="flex items-center gap-2 mt-2">
                    {getStatusBadge(task.status)}
                    {getPriorityBadge(task.priority)}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Task Detail */}
      <Card className="flex-1 overflow-hidden flex flex-col">
        {selectedTask ? (
          <>
            <CardHeader className="flex-shrink-0 border-b">
              <div className="flex items-start justify-between">
                <div>
                  <CardTitle>{selectedTask.title}</CardTitle>
                  <p className="text-sm text-muted-foreground mt-1">
                    {selectedTask.description || '无描述'}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  {selectedTask.status === 'draft' && (
                    <Button
                      size="sm"
                      onClick={() => publishMutation.mutate(selectedTask.id)}
                      disabled={publishMutation.isPending}
                    >
                      发布
                    </Button>
                  )}
                  {selectedTask.status === 'published' && (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => setAssignDialogOpen(true)}
                    >
                      <UserPlus className="h-4 w-4 mr-1" />
                      分配总管
                    </Button>
                  )}
                  {selectedTask.status === 'assigned' && (
                    <Button
                      size="sm"
                      onClick={() => analyzeMutation.mutate(selectedTask.id)}
                      disabled={analyzeMutation.isPending}
                    >
                      {analyzeMutation.isPending ? (
                        <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                      ) : null}
                      开始分析
                    </Button>
                  )}
                  {selectedTask.status === 'analyzing' && (
                    <Button
                      size="sm"
                      onClick={() => confirmMutation.mutate(selectedTask.id)}
                      disabled={confirmMutation.isPending}
                    >
                      确认分解
                    </Button>
                  )}
                  {selectedTask.status === 'decomposed' && (
                    <Button
                      size="sm"
                      onClick={() => startMutation.mutate(selectedTask.id)}
                      disabled={startMutation.isPending}
                    >
                      <Play className="h-4 w-4 mr-1" />
                      开始执行
                    </Button>
                  )}
                  <Button
                    size="sm"
                    variant="destructive"
                    onClick={() => deleteMutation.mutate(selectedTask.id)}
                    disabled={deleteMutation.isPending}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </div>
              <div className="flex items-center gap-4 mt-4">
                <div className="flex items-center gap-2">
                  <span className="text-sm text-muted-foreground">状态:</span>
                  {getStatusBadge(selectedTask.status)}
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-sm text-muted-foreground">优先级:</span>
                  {getPriorityBadge(selectedTask.priority)}
                </div>
                {selectedTask.manager_instance_id && (
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-muted-foreground">总管:</span>
                    <Badge variant="outline">
                      {instancesData?.items.find(
                        (i) => i.id === selectedTask.manager_instance_id
                      )?.name || selectedTask.manager_instance_id}
                    </Badge>
                  </div>
                )}
              </div>
            </CardHeader>

            <CardContent className="flex-1 overflow-auto p-0">
              <div className="grid grid-cols-2 gap-0 h-full">
                {/* SubTasks */}
                <div className="border-r overflow-auto">
                  <div className="p-4 border-b bg-muted/30">
                    <h3 className="font-medium">子任务</h3>
                  </div>
                  {subtasksData?.items.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-32 text-muted-foreground">
                      <ClipboardList className="h-6 w-6 mb-2" />
                      <p className="text-sm">暂无子任务</p>
                    </div>
                  ) : (
                    <div className="divide-y">
                      {subtasksData?.items.map((subtask: SubTask) => (
                        <div key={subtask.id} className="p-4">
                          <div className="flex items-center justify-between">
                            <h4 className="font-medium">{subtask.title}</h4>
                            <Badge
                              variant={
                                subtask.status === 'completed'
                                  ? 'default'
                                  : subtask.status === 'failed'
                                  ? 'destructive'
                                  : 'outline'
                              }
                            >
                              {subtask.status}
                            </Badge>
                          </div>
                          {subtask.description && (
                            <p className="text-sm text-muted-foreground mt-1">
                              {subtask.description}
                            </p>
                          )}
                          {subtask.result && (
                            <p className="text-sm mt-2 p-2 bg-muted rounded">
                              {subtask.result}
                            </p>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Progress */}
                <div className="overflow-auto">
                  <div className="p-4 border-b bg-muted/30">
                    <h3 className="font-medium">进度记录</h3>
                  </div>
                  {progressData?.items.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-32 text-muted-foreground">
                      <Clock className="h-6 w-6 mb-2" />
                      <p className="text-sm">暂无进度记录</p>
                    </div>
                  ) : (
                    <div className="divide-y">
                      {progressData?.items.map((progress) => (
                        <div key={progress.id} className="p-4">
                          <div className="flex items-center gap-2">
                            <Badge variant="outline" className="text-xs">
                              {progress.event_type}
                            </Badge>
                            <span className="text-xs text-muted-foreground">
                              {new Date(progress.created_at).toLocaleString('zh-CN')}
                            </span>
                          </div>
                          {progress.message && (
                            <p className="text-sm mt-1">{progress.message}</p>
                          )}
                          {progress.progress_percent > 0 && (
                            <div className="mt-2 h-2 bg-muted rounded-full overflow-hidden">
                              <div
                                className="h-full bg-primary transition-all"
                                style={{ width: `${progress.progress_percent}%` }}
                              />
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </CardContent>
          </>
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
            <ClipboardList className="h-12 w-12 mb-4" />
            <p>选择一个任务查看详情</p>
          </div>
        )}
      </Card>

      {/* Create Task Dialog */}
      <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>创建新任务</DialogTitle>
            <DialogDescription>创建一个新的任务，指定标题和优先级</DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="title">标题</Label>
              <Input
                id="title"
                value={newTask.title}
                onChange={(e) => setNewTask({ ...newTask, title: e.target.value })}
                placeholder="输入任务标题"
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="description">描述</Label>
              <Textarea
                id="description"
                value={newTask.description}
                onChange={(e) => setNewTask({ ...newTask, description: e.target.value })}
                placeholder="输入任务描述（可选）"
                rows={3}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="priority">优先级</Label>
              <Select
                value={newTask.priority}
                onValueChange={(value: TaskPriority) =>
                  setNewTask({ ...newTask, priority: value })
                }
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="low">低</SelectItem>
                  <SelectItem value="medium">中</SelectItem>
                  <SelectItem value="high">高</SelectItem>
                  <SelectItem value="urgent">紧急</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="grid gap-2">
              <Label htmlFor="tags">标签</Label>
              <Input
                id="tags"
                value={newTask.tags}
                onChange={(e) => setNewTask({ ...newTask, tags: e.target.value })}
                placeholder="输入标签，用逗号分隔"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateDialogOpen(false)}>
              取消
            </Button>
            <Button
              onClick={() => createMutation.mutate(newTask)}
              disabled={!newTask.title || createMutation.isPending}
            >
              {createMutation.isPending && (
                <Loader2 className="h-4 w-4 mr-1 animate-spin" />
              )}
              创建
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Assign Manager Dialog */}
      <Dialog open={assignDialogOpen} onOpenChange={setAssignDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>分配任务总管</DialogTitle>
            <DialogDescription>选择一个已连接的智能体实例作为任务总管</DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            {connectedInstances.length === 0 ? (
              <div className="text-center text-muted-foreground py-4">
                <AlertCircle className="h-8 w-8 mx-auto mb-2" />
                <p>没有可用的已连接实例</p>
                <p className="text-sm mt-1">请先在实例管理页面连接一个实例</p>
              </div>
            ) : (
              <div className="grid gap-2">
                <Label>选择实例</Label>
                <Select value={selectedManagerId} onValueChange={setSelectedManagerId}>
                  <SelectTrigger>
                    <SelectValue placeholder="选择一个实例" />
                  </SelectTrigger>
                  <SelectContent>
                    {connectedInstances.map((instance: Instance) => (
                      <SelectItem key={instance.id} value={instance.id}>
                        {instance.name} ({instance.host}:{instance.port})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setAssignDialogOpen(false)}>
              取消
            </Button>
            <Button
              onClick={() => {
                if (selectedTask && selectedManagerId) {
                  assignManagerMutation.mutate({
                    taskId: selectedTask.id,
                    managerId: selectedManagerId,
                  });
                }
              }}
              disabled={!selectedManagerId || assignManagerMutation.isPending}
            >
              {assignManagerMutation.isPending && (
                <Loader2 className="h-4 w-4 mr-1 animate-spin" />
              )}
              确认分配
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}