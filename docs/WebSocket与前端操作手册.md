# OpenClaw Control Plane - WebSocket 与前端操作手册

## 目录

1. [WebSocket 实时事件订阅](#一websocket-实时事件订阅)
2. [前端界面操作指南](#二前端界面操作指南)
3. [React Hook 使用示例](#三react-hook-使用示例)
4. [WebSocket 消息格式详解](#四websocket-消息格式详解)

---

## 一、WebSocket 实时事件订阅

### 1.1 WebSocket 连接端点

Control Plane 提供 WebSocket 端点用于实时事件订阅：

```
ws://localhost:8000/ws/events
```

### 1.2 连接与认证

**原生 WebSocket 连接：**

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/events');

// 连接建立
ws.onopen = () => {
  console.log('WebSocket 已连接');

  // 订阅特定事件（可选）
  ws.send(JSON.stringify({
    type: 'subscribe',
    channels: ['messages', 'instances', 'sessions']
  }));
};

// 接收消息
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('收到事件:', data);
};

// 连接关闭
ws.onclose = () => {
  console.log('WebSocket 已关闭');
};

// 错误处理
ws.onerror = (error) => {
  console.error('WebSocket 错误:', error);
};
```

**使用 socket.io-client（推荐）：**

```bash
npm install socket.io-client
```

```typescript
import { io } from 'socket.io-client';

const socket = io('ws://localhost:8000', {
  path: '/ws/events',
  transports: ['websocket'],
  autoConnect: true,
  reconnection: true,
  reconnectionAttempts: 5,
  reconnectionDelay: 1000,
});

// 连接事件
socket.on('connect', () => {
  console.log('已连接，ID:', socket.id);
});

// 订阅实时消息
socket.on('message', (data) => {
  console.log('新消息:', data);
});

// 实例状态变更
socket.on('instance.status', (data) => {
  console.log('实例状态变更:', data);
});

// 会话事件
socket.on('session.created', (data) => {
  console.log('会话创建:', data);
});

socket.on('session.closed', (data) => {
  console.log('会话关闭:', data);
});

// 断开连接
socket.on('disconnect', (reason) => {
  console.log('断开连接:', reason);
});
```

### 1.3 事件类型

| 事件名称 | 说明 | 数据格式 |
|----------|------|----------|
| `message` | 新消息通知 | `{ session_id, message, timestamp }` |
| `message.stream` | 流式消息片段 | `{ session_id, chunk, sequence }` |
| `instance.connected` | 实例已连接 | `{ instance_id, timestamp }` |
| `instance.disconnected` | 实例已断开 | `{ instance_id, reason, timestamp }` |
| `instance.error` | 实例错误 | `{ instance_id, error, timestamp }` |
| `session.created` | 会话创建 | `{ session_id, instance_id, target }` |
| `session.closed` | 会话关闭 | `{ session_id, reason }` |
| `system.health` | 系统健康更新 | `{ status, instances_connected, active_sessions }` |

### 1.4 React Hook 封装

```typescript
// hooks/useWebSocket.ts
import { useEffect, useRef, useState, useCallback } from 'react';

interface WebSocketMessage {
  type: string;
  data: unknown;
  timestamp: string;
}

interface UseWebSocketOptions {
  url: string;
  onMessage?: (message: WebSocketMessage) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  reconnect?: boolean;
  reconnectInterval?: number;
}

export function useWebSocket(options: UseWebSocketOptions) {
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>();

  const connect = useCallback(() => {
    const ws = new WebSocket(options.url);
    wsRef.current = ws;

    ws.onopen = () => {
      setIsConnected(true);
      options.onConnect?.();
    };

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        setLastMessage(message);
        options.onMessage?.(message);
      } catch (e) {
        console.error('解析消息失败:', e);
      }
    };

    ws.onclose = () => {
      setIsConnected(false);
      options.onDisconnect?.();

      if (options.reconnect !== false) {
        reconnectTimeoutRef.current = setTimeout(
          connect,
          options.reconnectInterval || 3000
        );
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket 错误:', error);
    };
  }, [options]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    wsRef.current?.close();
  }, []);

  const send = useCallback((data: unknown) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
      return true;
    }
    return false;
  }, []);

  useEffect(() => {
    connect();
    return () => disconnect();
  }, [connect, disconnect]);

  return { isConnected, lastMessage, send, connect, disconnect };
}
```

### 1.5 在组件中使用

```tsx
// components/RealtimeMessages.tsx
import { useEffect, useState } from 'react';
import { useWebSocket } from '@/hooks/useWebSocket';
import type { Message } from '@/types';

export function RealtimeMessages({ sessionId }: { sessionId: string }) {
  const [messages, setMessages] = useState<Message[]>([]);

  const { isConnected, lastMessage } = useWebSocket({
    url: 'ws://localhost:8000/ws/events',
    onMessage: (msg) => {
      if (msg.type === 'message' && msg.data.session_id === sessionId) {
        setMessages((prev) => [...prev, msg.data.message]);
      }
    },
  });

  return (
    <div>
      <div className="connection-status">
        {isConnected ? '🟢 实时连接中' : '🔴 已断开'}
      </div>
      <div className="messages">
        {messages.map((msg) => (
          <div key={msg.id} className={`message ${msg.role}`}>
            {msg.content}
          </div>
        ))}
      </div>
    </div>
  );
}
```

---

## 二、前端界面操作指南

### 2.1 启动前端

```bash
cd control-plane/frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

前端访问地址：http://localhost:5173

### 2.2 界面布局说明

```
┌─────────────────────────────────────────────────────────────────────┐
│  OpenClaw Control Plane                                    [🟢]     │
├──────────────┬──────────────────────────────────────────────────────┤
│              │                                                      │
│  NAVIGATION  │                    MAIN CONTENT                      │
│              │                                                      │
│  🖥️ Instances│  ┌────────────────────────────────────────────────┐  │
│  💬 Sessions │  │  Instance List / Session Chat / System Metrics │  │
│  📊 Metrics  │  └────────────────────────────────────────────────┘  │
│  ⚙️ System   │                                                      │
│              │                                                      │
└──────────────┴──────────────────────────────────────────────────────┘
```

### 2.3 实例管理页面

**路径：** `/instances`

**功能说明：**

| 操作 | 步骤 | 说明 |
|------|------|------|
| **添加实例** | 1. 点击右上角 "Add Instance" 按钮<br>2. 填写名称、主机地址、端口<br>3. 点击 "Create" | 注册新的 OpenClaw 实例 |
| **连接实例** | 点击实例卡片上的 "Connect" 按钮 | 建立 WebSocket 连接 |
| **断开实例** | 点击实例卡片上的 "Disconnect" 按钮 | 断开 WebSocket 连接 |
| **删除实例** | 点击实例卡片上的 🗑️ 删除按钮 | 从系统中移除实例 |
| **查看状态** | 观察状态图标和 Badge | 🟢 Connected / 🔴 Error / ⚪ Disconnected |

**实例卡片信息：**
- 实例名称
- 主机:端口
- 连接状态
- 消息数量统计
- 最后错误信息（如有）

### 2.4 会话管理页面

**路径：** `/sessions`

**功能说明：**

| 操作 | 步骤 | 说明 |
|------|------|------|
| **创建会话** | 1. 选择实例<br>2. 输入目标 ID<br>3. 点击 "Create Session" | 在指定实例上创建新会话 |
| **发送消息** | 1. 选择会话<br>2. 在输入框输入内容<br>3. 点击 "Send" 或按 Enter | 向 OpenClaw 发送消息 |
| **查看历史** | 进入会话自动加载历史消息 | 滚动加载更多 |
| **关闭会话** | 点击会话设置中的 "Close" | 标记会话为非活跃 |

**会话界面布局：**

```
┌─────────────────────────────────────────────────────────────┐
│ Session: user-session-123                    [Close] [⚙️]   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────┐                                    │
│  │ User: 你好          │                                    │
│  └─────────────────────┘                                    │
│                      ┌──────────────────────────┐           │
│                      │ Assistant: 你好！有什么   │           │
│                      │ 我可以帮你的吗？          │           │
│                      └──────────────────────────┘           │
│  ┌─────────────────────┐                                    │
│  │ User: 写个 Python   │                                    │
│  └─────────────────────┘                                    │
│                      ┌──────────────────────────┐           │
│                      │ Assistant: 好的，这是...  │           │
│                      └──────────────────────────┘           │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│ ┌──────────────────────────────────────────┐ ┌──────────┐  │
│ │ 输入消息...                               │ │  Send    │  │
│ └──────────────────────────────────────────┘ └──────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 2.5 系统监控页面

**路径：** `/metrics` 或 `/system`

**显示内容：**

| 指标 | 说明 |
|------|------|
| **系统状态** | healthy / degraded / unhealthy |
| **运行时间** | 系统启动至今的运行时间 |
| **实例统计** | 已连接数 / 总数 |
| **活跃会话** | 当前活跃会话数量 |
| **消息总量** | 累计发送的消息数 |
| **平均延迟** | 平均响应延迟（毫秒） |
| **错误统计** | 累计错误次数 |

### 2.6 前端路由说明

| 路由 | 页面 | 说明 |
|------|------|------|
| `/` | 首页 / Dashboard | 系统概览 |
| `/instances` | 实例管理 | 管理 OpenClaw 实例 |
| `/instances/:id` | 实例详情 | 单个实例的详细信息和会话列表 |
| `/sessions` | 会话列表 | 所有会话的列表 |
| `/sessions/:id` | 会话详情 | 聊天界面，发送和接收消息 |
| `/metrics` | 系统指标 | 性能监控图表 |
| `/system` | 系统设置 | 系统配置和状态 |

---

## 三、React Hook 使用示例

### 3.1 使用 React Query 获取数据

```typescript
// hooks/useInstances.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { instanceApi } from '@/services/api';

export function useInstances() {
  return useQuery({
    queryKey: ['instances'],
    queryFn: instanceApi.list,
    refetchInterval: 30000, // 每30秒自动刷新
  });
}

export function useInstance(id: string) {
  return useQuery({
    queryKey: ['instances', id],
    queryFn: () => instanceApi.get(id),
    enabled: !!id,
  });
}

export function useCreateInstance() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: instanceApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['instances'] });
    },
  });
}

export function useConnectInstance() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: instanceApi.connect,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['instances'] });
    },
  });
}
```

### 3.2 使用 Hook 的组件示例

```tsx
// components/InstanceList.tsx
import { useInstances, useConnectInstance } from '@/hooks/useInstances';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { CheckCircle, XCircle, AlertCircle, Power } from 'lucide-react';

export function InstanceList() {
  const { data: instances, isLoading } = useInstances();
  const connectMutation = useConnectInstance();

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

  if (isLoading) {
    return <div>加载中...</div>;
  }

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {instances?.items.map((instance) => (
        <Card key={instance.id}>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              {instance.name}
              {getStatusIcon(instance.status)}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-gray-500">
              {instance.host}:{instance.port}
            </p>
            <Badge variant={instance.status === 'connected' ? 'default' : 'secondary'}>
              {instance.status}
            </Badge>
            {instance.status !== 'connected' && (
              <Button
                size="sm"
                onClick={() => connectMutation.mutate(instance.id)}
                disabled={connectMutation.isPending}
              >
                <Power className="mr-2 h-4 w-4" />
                连接
              </Button>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
```

### 3.3 实时聊天组件

```tsx
// components/ChatSession.tsx
import { useState, useEffect, useRef } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { sessionApi } from '@/services/api';
import { useWebSocket } from '@/hooks/useWebSocket';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';

interface ChatSessionProps {
  sessionId: string;
}

export function ChatSession({ sessionId }: ChatSessionProps) {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<any[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);

  // 加载历史消息
  const { data: history } = useQuery({
    queryKey: ['messages', sessionId],
    queryFn: () => sessionApi.getMessages(sessionId, 100),
  });

  // 发送消息
  const sendMutation = useMutation({
    mutationFn: (content: string) =>
      sessionApi.sendMessage(sessionId, { content, stream: false }),
  });

  // WebSocket 实时消息
  const { isConnected, lastMessage } = useWebSocket({
    url: 'ws://localhost:8000/ws/events',
    onMessage: (msg) => {
      if (msg.type === 'message' && msg.data.session_id === sessionId) {
        setMessages((prev) => [...prev, msg.data.message]);
      }
    },
  });

  // 初始化历史消息
  useEffect(() => {
    if (history?.items) {
      setMessages(history.items);
    }
  }, [history]);

  // 自动滚动到底部
  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = () => {
    if (!input.trim()) return;

    // 乐观更新：立即显示用户消息
    const userMessage = {
      id: `temp-${Date.now()}`,
      role: 'user',
      content: input,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');

    // 发送请求
    sendMutation.mutate(input);
  };

  return (
    <div className="flex h-full flex-col">
      {/* 连接状态 */}
      <div className="border-b px-4 py-2">
        <span className={`text-sm ${isConnected ? 'text-green-500' : 'text-red-500'}`}>
          {isConnected ? '🟢 实时连接中' : '🔴 已断开'}
        </span>
      </div>

      {/* 消息列表 */}
      <ScrollArea className="flex-1 p-4">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`mb-4 flex ${
              msg.role === 'user' ? 'justify-end' : 'justify-start'
            }`}
          >
            <div
              className={`max-w-[70%] rounded-lg px-4 py-2 ${
                msg.role === 'user'
                  ? 'bg-blue-500 text-white'
                  : 'bg-gray-100 text-gray-900'
              }`}
            >
              <p>{msg.content}</p>
              <span className="text-xs opacity-70">
                {new Date(msg.created_at).toLocaleTimeString()}
              </span>
            </div>
          </div>
        ))}
        <div ref={scrollRef} />
      </ScrollArea>

      {/* 输入框 */}
      <div className="border-t p-4">
        <div className="flex gap-2">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            placeholder="输入消息..."
            disabled={sendMutation.isPending}
          />
          <Button onClick={handleSend} disabled={sendMutation.isPending}>
            {sendMutation.isPending ? '发送中...' : '发送'}
          </Button>
        </div>
      </div>
    </div>
  );
}
```

---

## 四、WebSocket 消息格式详解

### 4.1 客户端 → 服务端

**订阅事件：**

```json
{
  "type": "subscribe",
  "channels": ["messages", "instances", "sessions"]
}
```

**取消订阅：**

```json
{
  "type": "unsubscribe",
  "channels": ["messages"]
}
```

**心跳：**

```json
{
  "type": "ping",
  "timestamp": "2026-03-15T10:30:00Z"
}
```

### 4.2 服务端 → 客户端

**新消息事件：**

```json
{
  "type": "message",
  "data": {
    "session_id": "sess_xxx",
    "message": {
      "id": "msg_xxx",
      "role": "assistant",
      "content": "你好！有什么我可以帮你的吗？",
      "created_at": "2026-03-15T10:30:00Z"
    }
  },
  "timestamp": "2026-03-15T10:30:00Z"
}
```

**流式消息片段：**

```json
{
  "type": "message.stream",
  "data": {
    "session_id": "sess_xxx",
    "chunk": "这是",
    "sequence": 1,
    "is_end": false
  },
  "timestamp": "2026-03-15T10:30:00Z"
}
```

**实例状态变更：**

```json
{
  "type": "instance.connected",
  "data": {
    "instance_id": "inst_xxx",
    "host": "192.168.1.100",
    "port": 18080
  },
  "timestamp": "2026-03-15T10:30:00Z"
}
```

```json
{
  "type": "instance.disconnected",
  "data": {
    "instance_id": "inst_xxx",
    "reason": "connection_lost"
  },
  "timestamp": "2026-03-15T10:30:00Z"
}
```

```json
{
  "type": "instance.error",
  "data": {
    "instance_id": "inst_xxx",
    "error": "Authentication failed",
    "error_code": "AUTH_FAILED"
  },
  "timestamp": "2026-03-15T10:30:00Z"
}
```

**会话事件：**

```json
{
  "type": "session.created",
  "data": {
    "session_id": "sess_xxx",
    "instance_id": "inst_xxx",
    "target": "user-123",
    "context": {}
  },
  "timestamp": "2026-03-15T10:30:00Z"
}
```

**系统健康更新：**

```json
{
  "type": "system.health",
  "data": {
    "status": "healthy",
    "instances_connected": 3,
    "instances_total": 3,
    "active_sessions": 12,
    "messages_per_minute": 45.5
  },
  "timestamp": "2026-03-15T10:30:00Z"
}
```

### 4.3 TypeScript 类型定义

```typescript
// types/websocket.ts

export type WebSocketEventType =
  | 'message'
  | 'message.stream'
  | 'instance.connected'
  | 'instance.disconnected'
  | 'instance.error'
  | 'session.created'
  | 'session.closed'
  | 'system.health';

export interface WebSocketEvent {
  type: WebSocketEventType;
  data: unknown;
  timestamp: string;
}

export interface MessageEvent {
  type: 'message';
  data: {
    session_id: string;
    message: {
      id: string;
      role: 'user' | 'assistant' | 'system';
      content: string;
      created_at: string;
    };
  };
  timestamp: string;
}

export interface MessageStreamEvent {
  type: 'message.stream';
  data: {
    session_id: string;
    chunk: string;
    sequence: number;
    is_end: boolean;
  };
  timestamp: string;
}

export interface InstanceConnectedEvent {
  type: 'instance.connected';
  data: {
    instance_id: string;
    host: string;
    port: number;
  };
  timestamp: string;
}

export interface InstanceDisconnectedEvent {
  type: 'instance.disconnected';
  data: {
    instance_id: string;
    reason: string;
  };
  timestamp: string;
}

export interface InstanceErrorEvent {
  type: 'instance.error';
  data: {
    instance_id: string;
    error: string;
    error_code: string;
  };
  timestamp: string;
}

export interface SessionCreatedEvent {
  type: 'session.created';
  data: {
    session_id: string;
    instance_id: string;
    target: string;
    context: Record<string, unknown>;
  };
  timestamp: string;
}

export interface SystemHealthEvent {
  type: 'system.health';
  data: {
    status: 'healthy' | 'degraded' | 'unhealthy';
    instances_connected: number;
    instances_total: number;
    active_sessions: number;
    messages_per_minute: number;
  };
  timestamp: string;
}
```

---

## 五、完整示例：实时聊天应用

```tsx
// App.tsx
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { InstancesPage } from '@/pages/InstancesPage';
import { SessionsPage } from '@/pages/SessionsPage';
import { ChatSession } from '@/components/ChatSession';
import { Layout } from '@/components/layout/Layout';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 3,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Layout>
          <Routes>
            <Route path="/" element={<InstancesPage />} />
            <Route path="/instances" element={<InstancesPage />} />
            <Route path="/sessions" element={<SessionsPage />} />
            <Route path="/sessions/:id" element={<ChatSessionWrapper />} />
          </Routes>
        </Layout>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

function ChatSessionWrapper() {
  const { id } = useParams<{ id: string }>();
  return id ? <ChatSession sessionId={id} /> : null;
}

export default App;
```

---

**文档版本：** v1.0
**更新日期：** 2026-03-15
**适用版本：** Control Plane 1.0.0+
