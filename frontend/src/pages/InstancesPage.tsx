import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Plus,
  Power,
  PowerOff,
  Trash2,
  RefreshCw,
  Server,
  CheckCircle,
  XCircle,
  AlertCircle,
  Key,
  Settings,
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
  DialogFooter,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { instanceApi } from '@/services/api';
import type { InstanceCreate, AuthType } from '@/types';

export function InstancesPage() {
  const queryClient = useQueryClient();
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [newInstance, setNewInstance] = useState<Partial<InstanceCreate>>({
    name: '',
    host: '',
    port: 18080,
    channel_id: 'ao',
    credentials: {
      auth_type: 'token',
      token: '',
      password: '',
    },
  });

  const { data: instances, isLoading } = useQuery({
    queryKey: ['instances'],
    queryFn: instanceApi.list,
    staleTime: 0, // Always consider data stale
    refetchOnMount: 'always', // Always refetch when component mounts
  });

  const createMutation = useMutation({
    mutationFn: instanceApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['instances'] });
      setIsCreateOpen(false);
      setNewInstance({
        name: '',
        host: '',
        port: 18080,
        channel_id: 'ao',
        credentials: {
          auth_type: 'token',
          token: '',
          password: '',
        },
      });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: instanceApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['instances'] });
    },
  });

  const connectMutation = useMutation({
    mutationFn: instanceApi.connect,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['instances'] });
    },
  });

  const disconnectMutation = useMutation({
    mutationFn: instanceApi.disconnect,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['instances'] });
    },
  });

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'connected':
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case 'error':
        return <XCircle className="h-5 w-5 text-red-500" />;
      default:
        return <AlertCircle className="h-5 w-5 text-gray-500" />;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'connected':
        return <Badge variant="default">已连接</Badge>;
      case 'error':
        return <Badge variant="destructive">错误</Badge>;
      case 'connecting':
        return <Badge variant="secondary">连接中...</Badge>;
      default:
        return <Badge variant="secondary">已断开</Badge>;
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">实例管理</h2>
          <p className="text-muted-foreground">
            管理您的 OpenClaw 实例与 AO 插件连接。
          </p>
        </div>
        <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="mr-2 h-4 w-4" />
              添加实例
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>添加新实例</DialogTitle>
            </DialogHeader>
            <div className="space-y-6 py-4">
              <div className="space-y-4">
                <h3 className="text-lg font-semibold">基本设置</h3>
                <div className="space-y-2">
                  <label className="text-sm font-medium">名称</label>
                  <Input
                    placeholder="生产服务器"
                    value={newInstance.name}
                    onChange={(e) =>
                      setNewInstance({ ...newInstance, name: e.target.value })
                    }
                  />
                  <p className="text-xs text-muted-foreground">
                    实例的友好名称
                  </p>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <label className="text-sm font-medium">主机</label>
                    <Input
                      placeholder="localhost 或 IP 地址"
                      value={newInstance.host}
                      onChange={(e) =>
                        setNewInstance({ ...newInstance, host: e.target.value })
                      }
                    />
                    <p className="text-xs text-muted-foreground">
                      AO 插件 WebSocket 服务器地址
                    </p>
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium">端口</label>
                    <Input
                      type="number"
                      value={newInstance.port}
                      onChange={(e) =>
                        setNewInstance({
                          ...newInstance,
                          port: parseInt(e.target.value),
                        })
                      }
                    />
                    <p className="text-xs text-muted-foreground">
                      默认：18080 (AO Plugin V2)
                    </p>
                  </div>
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">频道 ID</label>
                  <Input
                    placeholder="ao"
                    value={newInstance.channel_id}
                    onChange={(e) =>
                      setNewInstance({ ...newInstance, channel_id: e.target.value })
                    }
                  />
                  <p className="text-xs text-muted-foreground">
                    频道标识符（默认：ao）
                  </p>
                </div>
              </div>

              <div className="border-t pt-4">
                <h3 className="text-lg font-semibold mb-4">认证配置</h3>
                <div className="space-y-2">
                  <label className="text-sm font-medium">认证类型</label>
                  <Select
                    value={newInstance.credentials?.auth_type || 'token'}
                    onValueChange={(value: AuthType) =>
                      setNewInstance({
                        ...newInstance,
                        credentials: {
                          ...newInstance.credentials,
                          auth_type: value,
                        },
                      })
                    }
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="token">Token (API Key)</SelectItem>
                      <SelectItem value="password">密码</SelectItem>
                      <SelectItem value="mtls">mTLS (证书)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {newInstance.credentials?.auth_type === 'token' && (
                  <div className="space-y-2">
                    <label className="text-sm font-medium">
                      <Key className="inline h-4 w-4 mr-1" />
                      API Key (Token)
                    </label>
                    <Input
                      type="password"
                      placeholder="请输入 AO 插件 API Key"
                      value={newInstance.credentials?.token || ''}
                      onChange={(e) =>
                        setNewInstance({
                          ...newInstance,
                          credentials: {
                            auth_type: 'token',
                            ...newInstance.credentials,
                            token: e.target.value,
                            password: '',
                          },
                        })
                      }
                    />
                    <p className="text-xs text-muted-foreground">
                      AO 插件中配置的 API Key (channels.ao.apiKey)
                    </p>
                  </div>
                )}

                {newInstance.credentials?.auth_type === 'password' && (
                  <div className="space-y-2">
                    <label className="text-sm font-medium">
                      <Key className="inline h-4 w-4 mr-1" />
                      密码
                    </label>
                    <Input
                      type="password"
                      placeholder="请输入 AO 插件密码"
                      value={newInstance.credentials?.password || ''}
                      onChange={(e) =>
                        setNewInstance({
                          ...newInstance,
                          credentials: {
                            auth_type: 'password',
                            ...newInstance.credentials,
                            token: '',
                            password: e.target.value,
                          },
                        })
                      }
                    />
                    <p className="text-xs text-muted-foreground">
                      AO 插件中配置的密码
                    </p>
                  </div>
                )}

                {newInstance.credentials?.auth_type === 'mtls' && (
                  <div className="space-y-4">
                    <div className="space-y-2">
                      <label className="text-sm font-medium">证书路径</label>
                      <Input
                        placeholder="/path/to/client.crt"
                        value={newInstance.credentials?.cert_path || ''}
                        onChange={(e) =>
                          setNewInstance({
                            ...newInstance,
                            credentials: {
                              auth_type: 'mtls',
                              ...newInstance.credentials,
                              cert_path: e.target.value,
                            },
                          })
                        }
                      />
                    </div>
                    <div className="space-y-2">
                      <label className="text-sm font-medium">密钥路径</label>
                      <Input
                        placeholder="/path/to/client.key"
                        value={newInstance.credentials?.key_path || ''}
                        onChange={(e) =>
                          setNewInstance({
                            ...newInstance,
                            credentials: {
                              auth_type: 'mtls',
                              ...newInstance.credentials,
                              key_path: e.target.value,
                            },
                          })
                        }
                      />
                    </div>
                    <div className="space-y-2">
                      <label className="text-sm font-medium">CA 路径（可选）</label>
                      <Input
                        placeholder="/path/to/ca.crt"
                        value={newInstance.credentials?.ca_path || ''}
                        onChange={(e) =>
                          setNewInstance({
                            ...newInstance,
                            credentials: {
                              auth_type: 'mtls',
                              ...newInstance.credentials,
                              ca_path: e.target.value,
                            },
                          })
                        }
                      />
                    </div>
                  </div>
                )}

                <div className="rounded-md bg-blue-50 p-4 mt-4">
                  <div className="flex items-start gap-3">
                    <Settings className="h-5 w-5 text-blue-600 mt-0.5" />
                    <div className="text-sm text-blue-800">
                      <p className="font-medium mb-1">AO Plugin V2 配置</p>
                      <p className="text-xs text-blue-700">
                        确保 OpenClaw 配置包含：
                      </p>
                      <ul className="text-xs text-blue-700 mt-2 space-y-1">
                        <li>• <code className="bg-blue-100 px-1 rounded">channels.ao.enabled: true</code></li>
                        <li>• <code className="bg-blue-100 px-1 rounded">channels.ao.connectionMode: server</code></li>
                        <li>• <code className="bg-blue-100 px-1 rounded">channels.ao.listenPort: {newInstance.port || 18080}</code></li>
                        <li>• <code className="bg-blue-100 px-1 rounded">channels.ao.apiKey: {'<your-api-key>'}</code></li>
                      </ul>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setIsCreateOpen(false)}>
                取消
              </Button>
              <Button
                onClick={() =>
                  createMutation.mutate(newInstance as InstanceCreate)
                }
                disabled={
                  !newInstance.name ||
                  !newInstance.host ||
                  (newInstance.credentials?.auth_type === 'token' && !newInstance.credentials?.token) ||
                  (newInstance.credentials?.auth_type === 'password' && !newInstance.credentials?.password)
                }
              >
                创建
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {isLoading ? (
        <div className="flex h-64 items-center justify-center">
          <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {instances?.items.map((instance) => (
            <Card key={instance.id}>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  {instance.name}
                </CardTitle>
                {getStatusIcon(instance.status)}
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Server className="h-4 w-4" />
                    {instance.host}:{instance.port}
                  </div>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      {getStatusBadge(instance.status)}
                      <span className="text-xs text-muted-foreground">
                        {instance.health?.message_count || 0} messages
                      </span>
                    </div>
                    <span className="text-xs text-muted-foreground">
                      {instance.channel_id}
                    </span>
                  </div>
                  {instance.status_message && (
                    <p className="text-xs text-red-500">
                      {instance.status_message}
                    </p>
                  )}
                  <div className="flex gap-2 pt-2">
                    {instance.status === 'connected' ? (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => disconnectMutation.mutate(instance.id)}
                      >
                        <PowerOff className="mr-2 h-4 w-4" />
                        Disconnect
                      </Button>
                    ) : (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => connectMutation.mutate(instance.id)}
                      >
                        <Power className="mr-2 h-4 w-4" />
                        Connect
                      </Button>
                    )}
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={() => deleteMutation.mutate(instance.id)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {!isLoading && !instances?.items.length && (
        <div className="flex h-64 flex-col items-center justify-center text-center">
          <Server className="h-12 w-12 text-muted-foreground" />
          <h3 className="mt-4 text-lg font-semibold">No instances yet</h3>
          <p className="text-muted-foreground">
            Add your first OpenClaw instance to get started.
          </p>
        </div>
      )}
    </div>
  );
}
