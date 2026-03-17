# AO 插件配置说明

本文档描述如何在 OpenClaw 实例中配置 AO 插件，使其能够与 Control Plane 进行 WebSocket 通信。

## 架构概述

AO 插件 V2 采用**服务器模式**架构：

```
┌─────────────────┐       WebSocket        ┌─────────────────┐
│  Control Plane  │ ◄──────────────────►   │   AO Plugin     │
│   (客户端)       │    ws://host:port/ws   │   (服务器)       │
└─────────────────┘                        └─────────────────┘
```

- **AO Plugin**: 作为 WebSocket 服务器运行，等待 Control Plane 连接
- **Control Plane**: 作为 WebSocket 客户端，主动连接 AO Plugin

## 基本配置结构

在 OpenClaw 的 `config.yaml` 中，AO 插件配置位于 `channels.ao` 节点：

```yaml
channels:
  ao:
    enabled: true
    listenHost: "0.0.0.0"
    listenPort: 18080
    apiKey: "your-secure-api-key"
    # ... 其他配置
```

## 服务器模式配置（推荐）

### 必需参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `listenHost` | string | `"0.0.0.0"` | WebSocket 服务器监听地址 |
| `listenPort` | number | `18080` | WebSocket 服务器监听端口 |
| `apiKey` | string | - | **必需**，用于 Control Plane 认证 |

### 可选参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `maxConnections` | number | `10` | 最大并发连接数 |
| `connectionMode` | string | `"server"` | 连接模式：`server`/`client`/`hybrid` |
| `timeoutMs` | number | `10000` | 操作超时时间（毫秒） |

### 健康检查配置

```yaml
channels:
  ao:
    healthCheck:
      enabled: true           # 是否启用健康检查
      intervalMs: 30000       # 检查间隔（毫秒）
      timeoutMs: 10000        # 超时时间（毫秒）
```

## 完整配置示例

### 单账户配置

```yaml
channels:
  ao:
    enabled: true
    listenHost: "0.0.0.0"
    listenPort: 18080
    apiKey: "your-secure-api-key-here"
    maxConnections: 10
    timeoutMs: 10000

    healthCheck:
      enabled: true
      intervalMs: 30000
      timeoutMs: 10000

    # 高级配置（可选）
    retry:
      maxAttempts: 3
      backoffMs: 800
      maxBackoffMs: 30000
      jitter: true

    circuitBreaker:
      enabled: true
      failureThreshold: 5
      recoveryTimeout: 30000
      halfOpenMaxCalls: 3
```

### 多账户配置

```yaml
channels:
  ao:
    enabled: true

    # 默认账户配置
    listenHost: "0.0.0.0"
    listenPort: 18080
    apiKey: "default-api-key"

    # 多账户支持
    accounts:
      production:
        enabled: true
        listenPort: 18081
        apiKey: "prod-api-key"
        maxConnections: 20

      development:
        enabled: true
        listenPort: 18082
        apiKey: "dev-api-key"
        maxConnections: 5
```

## 高级配置

### 重试机制

```yaml
channels:
  ao:
    retry:
      maxAttempts: 3          # 最大重试次数
      backoffMs: 800          # 初始退避时间（毫秒）
      maxBackoffMs: 30000     # 最大退避时间（毫秒）
      jitter: true            # 是否添加随机抖动
```

### 熔断器（Circuit Breaker）

防止故障级联，在连续失败后暂时停止请求：

```yaml
channels:
  ao:
    circuitBreaker:
      enabled: true              # 是否启用
      failureThreshold: 5        # 触发熔断的失败次数
      recoveryTimeout: 30000     # 熔断恢复时间（毫秒）
      halfOpenMaxCalls: 3        # 半开状态最大调用次数
```

### 消息队列

```yaml
channels:
  ao:
    messageQueue:
      enabled: true              # 是否启用
      maxSize: 1000              # 队列最大容量
      persistPath: "./data/ao-queue"  # 持久化路径
```

### 指标暴露

```yaml
channels:
  ao:
    metrics:
      enabled: true              # 是否启用
      port: 9090                 # Prometheus 指标端口
      path: "/metrics"           # 指标路径
```

### mTLS 双向认证（可选）

增强安全性，要求客户端提供证书：

```yaml
channels:
  ao:
    mtls:
      enabled: true
      certPath: "/path/to/server.crt"
      keyPath: "/path/to/server.key"
      caPath: "/path/to/ca.crt"
      autoRotate: true           # 是否自动轮换证书
```

## 环境变量支持

所有配置项都可以通过环境变量设置，环境变量优先级高于配置文件：

### 服务器模式

| 环境变量 | 对应配置 |
|----------|----------|
| `AO_LISTEN_HOST` | `listenHost` |
| `AO_LISTEN_PORT` | `listenPort` |
| `AO_API_KEY` | `apiKey` |
| `AO_MAX_CONNECTIONS` | `maxConnections` |
| `AO_CONNECTION_MODE` | `connectionMode` |

### 健康检查

| 环境变量 | 对应配置 |
|----------|----------|
| `AO_HEALTH_CHECK_ENABLED` | `healthCheck.enabled` |
| `AO_HEALTH_CHECK_INTERVAL_MS` | `healthCheck.intervalMs` |
| `AO_HEALTH_CHECK_TIMEOUT_MS` | `healthCheck.timeoutMs` |

### 重试配置

| 环境变量 | 对应配置 |
|----------|----------|
| `AO_RETRY_MAX_ATTEMPTS` | `retry.maxAttempts` |
| `AO_RETRY_BACKOFF_MS` | `retry.backoffMs` |

### 熔断器

| 环境变量 | 对应配置 |
|----------|----------|
| `AO_CIRCUIT_BREAKER_ENABLED` | `circuitBreaker.enabled` |
| `AO_CIRCUIT_BREAKER_THRESHOLD` | `circuitBreaker.failureThreshold` |

### mTLS

| 环境变量 | 对应配置 |
|----------|----------|
| `AO_MTLS_ENABLED` | `mtls.enabled` |
| `AO_MTLS_CERT_PATH` | `mtls.certPath` |
| `AO_MTLS_KEY_PATH` | `mtls.keyPath` |
| `AO_MTLS_CA_PATH` | `mtls.caPath` |

### 使用示例

```bash
# Docker / docker-compose
environment:
  - AO_LISTEN_HOST=0.0.0.0
  - AO_LISTEN_PORT=18080
  - AO_API_KEY=your-secret-key

# Kubernetes ConfigMap/Secret
env:
  - name: AO_API_KEY
    valueFrom:
      secretKeyRef:
        name: ao-plugin-secrets
        key: api-key
```

## Control Plane 连接配置

在 Control Plane 端，需要配置连接到 AO Plugin 实例：

### 通过 API 添加实例

```bash
curl -X POST http://localhost:8100/api/instances \
  -H "Content-Type: application/json" \
  -d '{
    "name": "OpenClaw-AO-1",
    "host": "192.168.1.100",
    "port": 18080,
    "channel_id": "ao",
    "credentials": {
      "auth_type": "token",
      "token": "your-secure-api-key"
    }
  }'
```

### 参数说明

| 参数 | 说明 |
|------|------|
| `name` | 实例名称，用于识别 |
| `host` | AO Plugin 服务器的 IP 地址 |
| `port` | AO Plugin 服务器端口 |
| `channel_id` | 固定为 `"ao"` |
| `credentials.auth_type` | 认证类型：`token`/`password`/`mtls` |
| `credentials.token` | 对应 AO Plugin 的 `apiKey` |

## WebSocket 协议

### 连接端点

```
ws://<host>:<port>/ws/openclaw
```

### 消息类型

#### 1. Welcome（服务器 → 客户端）
连接建立后立即发送：
```json
{
  "type": "welcome",
  "data": {
    "version": "2.0.0",
    "connectionId": "conn-xxx"
  }
}
```

#### 2. Auth（客户端 → 服务器）
客户端发送认证：
```json
{
  "type": "auth",
  "id": "msg-xxx",
  "timestamp": 1700000000000,
  "payload": {
    "apiKey": "your-api-key",
    "controlPlaneId": "cp-001",
    "version": "1.0.0"
  }
}
```

#### 3. Auth Response（服务器 → 客户端）
```json
{
  "type": "auth_response",
  "inReplyTo": "msg-xxx",
  "timestamp": 1700000000001,
  "payload": {
    "success": true,
    "connectionId": "conn-xxx"
  }
}
```

#### 4. Chat（客户端 → 服务器）
发送消息：
```json
{
  "type": "chat",
  "id": "msg-yyy",
  "sessionId": "session-001",
  "content": "你好",
  "from": {
    "id": "user-001",
    "name": "张三",
    "type": "user"
  }
}
```

#### 5. Reply（服务器 → 客户端）
回复消息：
```json
{
  "type": "reply",
  "inReplyTo": "msg-yyy",
  "sessionId": "session-001",
  "content": "你好！有什么可以帮助你的吗？",
  "from": {
    "id": "agent-001",
    "name": "AI助手",
    "type": "agent"
  }
}
```

#### 6. Ping/Pong（心跳）
```json
// Ping
{"type": "ping", "id": "ping-001", "timestamp": 1700000000000}

// Pong
{"type": "pong", "inReplyTo": "ping-001", "timestamp": 1700000000001}
```

## 默认值汇总

| 配置项 | 默认值 |
|--------|--------|
| `listenHost` | `"0.0.0.0"` |
| `listenPort` | `18080` |
| `maxConnections` | `10` |
| `connectionMode` | `"server"` |
| `timeoutMs` | `10000` |
| `healthCheck.enabled` | `true` |
| `healthCheck.intervalMs` | `30000` |
| `healthCheck.timeoutMs` | `10000` |
| `retry.maxAttempts` | `3` |
| `retry.backoffMs` | `800` |
| `retry.maxBackoffMs` | `30000` |
| `retry.jitter` | `true` |
| `circuitBreaker.enabled` | `true` |
| `circuitBreaker.failureThreshold` | `5` |
| `circuitBreaker.recoveryTimeout` | `30000` |
| `messageQueue.enabled` | `true` |
| `messageQueue.maxSize` | `1000` |
| `metrics.enabled` | `true` |
| `metrics.port` | `9090` |
| `mtls.enabled` | `false` |

## 故障排查

### 连接失败

1. 检查网络连通性：`telnet <host> <port>`
2. 检查防火墙规则
3. 确认 `apiKey` 匹配

### 认证失败

1. 检查 Control Plane 使用的 `token` 是否与 AO Plugin 的 `apiKey` 一致
2. 检查日志中的认证错误信息

### 消息无响应

1. 检查 AO Plugin 日志
2. 确认 WebSocket 连接状态
3. 检查熔断器状态（是否触发熔断）

## 安全建议

1. **使用强密码**：`apiKey` 应使用足够长度的随机字符串
2. **启用 TLS**：在生产环境中使用 `wss://` 而非 `ws://`
3. **网络隔离**：将 AO Plugin 部署在内网，限制外部访问
4. **定期轮换**：定期更换 API Key
5. **监控日志**：关注异常连接和认证失败

---

*文档版本: 1.0.0*
*最后更新: 2026-03-17*