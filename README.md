# OpenClaw Control Plane - 多 OpenClaw 接入控制平台

一个集中管理多个 OpenClaw 实例的 Web 应用。

## 架构

```
┌─────────────────────────────────────────────────────────────┐
│                     用户浏览器                               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  OpenClaw Control Plane                     │
│  ┌─────────────────────┐    ┌─────────────────────┐        │
│  │   React Frontend    │    │   FastAPI Backend   │        │
│  │   (Port 80)         │◄──►│   (Port 8000)       │        │
│  └─────────────────────┘    └─────────────────────┘        │
│                                       │                     │
│                                       ▼                     │
│                              ┌─────────────────────┐       │
│                              │   PostgreSQL DB     │       │
│                              │   (Port 5432)       │       │
│                              └─────────────────────┘       │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  OpenClaw #1    │ │  OpenClaw #2    │ │  OpenClaw #N    │
│  (AO Plugin)    │ │  (AO Plugin)    │ │  (AO Plugin)    │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

## 快速开始

### 使用 Docker Compose 部署

```bash
# 克隆项目后进入目录
cd control-plane

# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

访问 http://localhost 即可使用。

### 开发模式

#### 后端

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

后端 API 文档: http://localhost:8000/docs

#### 前端

```bash
cd frontend
npm install
npm run dev
```

前端开发服务器: http://localhost:3000

## 功能特性

### 实例管理
- 添加/删除 OpenClaw 实例
- 连接/断开实例
- 查看实例健康状态和指标

### 会话管理
- 创建新的对话会话
- 查看会话列表
- 关闭/删除会话

### 实时对话
- 通过 AO Plugin 与 OpenClaw 对话
- WebSocket 实时消息推送
- 消息历史记录

## API 接口

### 实例管理
- `GET /api/v1/instances` - 列出所有实例
- `POST /api/v1/instances` - 创建实例
- `GET /api/v1/instances/{id}` - 获取实例详情
- `PATCH /api/v1/instances/{id}` - 更新实例
- `DELETE /api/v1/instances/{id}` - 删除实例
- `POST /api/v1/instances/{id}/connect` - 连接实例
- `POST /api/v1/instances/{id}/disconnect` - 断开实例

### 会话管理
- `GET /api/v1/sessions` - 列出会话
- `POST /api/v1/sessions` - 创建会话
- `GET /api/v1/sessions/{id}` - 获取会话详情
- `DELETE /api/v1/sessions/{id}` - 删除会话
- `POST /api/v1/sessions/{id}/close` - 关闭会话
- `GET /api/v1/sessions/{id}/messages` - 获取会话消息
- `POST /api/v1/sessions/{id}/messages` - 发送消息

## 技术栈

### 后端
- Python 3.11+
- FastAPI
- SQLAlchemy (async)
- PostgreSQL
- WebSocket

### 前端
- React 18
- TypeScript
- TanStack Query
- Zustand
- Tailwind CSS
- shadcn/ui
- Socket.io-client

## 项目结构

```
control-plane/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 入口
│   │   ├── config.py            # 配置
│   │   ├── database.py          # 数据库
│   │   ├── models.py            # 数据模型
│   │   ├── schemas.py           # Pydantic 模型
│   │   ├── routers/             # API 路由
│   │   ├── services/            # 业务逻辑
│   │   └── connectors/          # 连接器
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/          # UI 组件
│   │   ├── pages/               # 页面
│   │   ├── services/            # API 客户端
│   │   ├── store/               # 状态管理
│   │   └── types/               # TypeScript 类型
│   ├── package.json
│   └── Dockerfile
└── docker-compose.yml
```

## 配置说明

### 后端环境变量

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `DATABASE_URL` | `sqlite+aiosqlite:///./control-plane.db` | 数据库连接字符串 |
| `REDIS_URL` | - | Redis 连接（可选） |
| `SECRET_KEY` | - | JWT 签名密钥 |
| `DEBUG` | `false` | 调试模式 |
| `HOST` | `0.0.0.0` | 监听地址 |
| `PORT` | `8000` | 监听端口 |

### 前端配置

前端通过 Vite 代理配置自动连接到后端 API:
- `/api/*` → `http://localhost:8000`
- `/ws/*` → `ws://localhost:8000`

## 开发计划

### Phase 1: AO Plugin V2 重构（已完成）
- [x] 类型定义与配置管理
- [x] 断路器模式
- [x] 连接池
- [x] 消息队列
- [x] 安全层（ED25519、mTLS）
- [x] 指标收集

### Phase 2: Control Plane 开发（已完成）
- [x] 后端 FastAPI 项目
- [x] 前端 React 项目
- [x] Docker 部署配置

### Phase 3: 高级功能（待开发）
- [ ] 用户认证与授权
- [ ] 审计日志
- [ ] Prometheus 指标导出
- [ ] 消息批量处理
- [ ] 多租户支持

## License

MIT
