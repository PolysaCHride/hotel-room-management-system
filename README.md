# 宾馆客房管理系统

个人毕业实训项目：包含完整可演示的 FastAPI 后端与 Vue 3 Web 前端，按角色划分为**顾客门户**、**服务员前台**、**管理员后台**三个独立界面。后端功能模块划分清晰，面向个人 Linux 服务器 Docker 一键部署设计。

## 系统架构

```
浏览器 ──► Nginx 容器（托管 Vue3 静态文件, 宿主机端口 9527，对外唯一入口）
              │  /api/* 反向代理
              ▼
          FastAPI 容器（Uvicorn, 8000, 不对外发布端口）
              │
              ▼
          SQLite（单文件，Docker Volume 持久化到宿主机 ./data/）
```

- 对外只暴露前端端口（默认 **9527**，避开常见端口），后端仅内网可见。
- 所有端口集中在 `docker-compose.yml` / `.env` 中，改一处即可。
- SQLite 数据落在宿主机 `./data/hotel.db`，容器重建数据不丢。

## 三个界面与功能

| 界面       | 登录后进入   | 主要功能                                                                                      |
| ---------- | ------------ | --------------------------------------------------------------------------------------------- |
| 顾客门户   | `/customer`  | 浏览房型与剩余空房、在线预订（日期冲突校验）、我的预订/取消                                   |
| 服务员前台 | `/reception` | 前台工作台（今日到店、办理入住：预订入住 / 散客开房）、在住与退房结算、账单记录               |
| 管理员后台 | `/admin`     | 经营看板（入住率、营收图表）、房型与房价管理、房间管理（维修/恢复）、预订管理、员工与用户管理 |

权限用 JWT + 角色隔离，跨界面访问接口会返回 403。

## 演示账号（首次启动自动初始化）

| 角色   | 用户名      | 密码       |
| ------ | ----------- | ---------- |
| 管理员 | `admin`     | `admin123` |
| 服务员 | `reception` | `123456`   |
| 顾客   | `guest`     | `123456`   |

首次启动自动写入种子数据：4 种房型、20 间客房、若干历史账单（近 7 天）、在住记录与预订，保证界面一打开就有数据可看。

## 服务器部署

```bash
# 1. 上传项目
cd /opt/hotel

# 2. 准备环境变量
cp .env.example .env
vi .env

# 3. 构建并启动
docker compose up -d --build

# 4. 查看日志 / 状态
docker compose logs -f
docker compose ps
```

访问 `http://服务器IP:9527` 即为系统入口；API 文档（答辩演示加分项）：`http://服务器IP:9527/api/docs`。

**修改端口**：编辑 `.env` 中 `WEB_PORT` 后 `docker compose up -d` 重建即可。

**数据备份**：

```bash
cp data/hotel.db backup/hotel-$(date +%F).db   # 直接拷贝 SQLite 文件
# 恢复：停服后用备份文件覆盖 data/hotel.db 再启动
```

**重置演示数据**：停服 → 删除 `data/hotel.db` → 重启，自动重新初始化。

## 本地开发

后端（Python 3.9+）：

```bash
cd backend
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt   # Linux/Mac: .venv/bin/pip
.venv/Scripts/python -m uvicorn app.main:app --host 127.0.0.1 --port 18000
```

前端：

```bash
cd frontend
npm install
npm run dev    # http://localhost:9527，/api 自动代理到 127.0.0.1:18000
```

## 后端模块划分（backend/app/）

```
backend/app/
├── main.py              # 应用入口，挂载各路由 + 启动时建表/初始化种子数据
├── core/
│   ├── config.py        # 配置（数据库、JWT、角色与状态常量）
│   └── security.py      # JWT 签发/校验、密码哈希
├── db/
│   ├── database.py      # SQLAlchemy 引擎与会话
│   └── init_data.py     # 演示种子数据（首次启动自动执行）
├── models/entities.py   # 数据模型：User / RoomType / Room / Booking / CheckInRecord / Bill
├── schemas/             # Pydantic 请求/响应模型（auth / room / booking / stay / stats）
├── api/                 # 路由层（每个功能模块一个文件）
│   ├── deps.py          # 认证依赖：JWT 解析 + 角色隔离
│   ├── auth.py          # 注册 / 登录 / 当前用户
│   ├── rooms.py         # 房型、房间、可订查询（公开）
│   ├── bookings.py      # 顾客：创建/我的预订/取消
│   ├── reception.py     # 服务员：到店列表、入住、退房、账单、房态概览
│   └── admin.py         # 管理员：房型房价、房间、员工、预订、统计
└── services/            # 业务逻辑层
    ├── booking_service.py   # 日期冲突检测、价格估算
    ├── stay_service.py      # 房态流转、自动选房、退房结算
    └── stats_service.py     # 入住率、营收统计
```

## 技术栈

- 后端：Python 3.11 + FastAPI + SQLAlchemy 2 + SQLite + JWT
- 前端：Vue 3 + Vite + Pinia + Vue Router + Element Plus + ECharts
- 部署：Docker Compose
