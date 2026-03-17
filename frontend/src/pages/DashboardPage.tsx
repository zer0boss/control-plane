import { useQuery } from '@tanstack/react-query';
import {
  Server,
  MessageSquare,
  Activity,
  TrendingUp,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { instanceApi, sessionApi } from '@/services/api';
import { formatBeijingDate } from '@/utils/time';

export function DashboardPage() {
  const { data: instances } = useQuery({
    queryKey: ['instances'],
    queryFn: instanceApi.list,
  });

  const { data: sessions } = useQuery({
    queryKey: ['sessions'],
    queryFn: () => sessionApi.list(),
  });

  const connectedInstances =
    instances?.items.filter((i) => i.status === 'connected').length || 0;
  const activeSessions =
    sessions?.items.filter((s) => s.is_active).length || 0;
  const totalMessages =
    instances?.items.reduce((acc, i) => acc + (i.health?.message_count || 0), 0) || 0;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">仪表盘</h2>
        <p className="text-muted-foreground">
          概览您的 OpenClaw 实例和会话。
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">实例总数</CardTitle>
            <Server className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{instances?.total || 0}</div>
            <p className="text-xs text-muted-foreground">
              {connectedInstances} 已连接
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">活跃会话</CardTitle>
            <MessageSquare className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{activeSessions}</div>
            <p className="text-xs text-muted-foreground">
              共 {sessions?.total || 0} 个
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">消息总数</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{totalMessages.toLocaleString()}</div>
            <p className="text-xs text-muted-foreground">跨所有实例</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">平均延迟</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {instances?.items.length
                ? Math.round(
                    instances.items.reduce(
                      (acc, i) => acc + (i.health?.latency_ms || 0),
                      0
                    ) / instances.items.length
                  )
                : 0}
              ms
            </div>
            <p className="text-xs text-muted-foreground">平均响应时间</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>最近实例</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {instances?.items.slice(0, 5).map((instance) => (
                <div
                  key={instance.id}
                  className="flex items-center justify-between"
                >
                  <div>
                    <p className="font-medium">{instance.name}</p>
                    <p className="text-sm text-muted-foreground">
                      {instance.host}:{instance.port}
                    </p>
                  </div>
                  <div
                    className={`h-2 w-2 rounded-full ${
                      instance.status === 'connected'
                        ? 'bg-green-500'
                        : instance.status === 'error'
                        ? 'bg-red-500'
                        : 'bg-gray-500'
                    }`}
                  />
                </div>
              ))}
              {!instances?.items.length && (
                <p className="text-sm text-muted-foreground">
                  暂无实例配置。
                </p>
              )}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>活跃会话</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {sessions?.items
                .filter((s) => s.is_active)
                .slice(0, 5)
                .map((session) => (
                  <div
                    key={session.id}
                    className="flex items-center justify-between"
                  >
                    <div>
                      <p className="font-medium">{session.target}</p>
                      <p className="text-sm text-muted-foreground">
                        {formatBeijingDate(session.created_at)}
                      </p>
                    </div>
                    <span className="text-xs text-green-600">活跃</span>
                  </div>
                ))}
              {!sessions?.items.filter((s) => s.is_active).length && (
                <p className="text-sm text-muted-foreground">
                  暂无活跃会话。
                </p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
