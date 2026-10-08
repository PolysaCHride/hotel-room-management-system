# 宾馆客房管理系统

个人毕业实训项目：包含完整可演示的 FastAPI 后端与 Vue 3 Web 前端，按角色划分为**顾客门户**、**服务员前台**、**管理员后台**三个独立界面。

## 系统架构

```
浏览器 ──► Nginx 容器（托管 Vue3 静态文件, 宿主机端口 9527，对外唯一入口）
              ├─ /api/*      → FastAPI 酒店后端容器（8000，仅内网）
              └─ /gateway/*  → 模拟支付网关容器（8000，仅内网）
                    ▲
                    └── 服务器间异步回调（notify，带签名验签）
```

- 对外只暴露前端端口（默认 **9527**，避开常见端口），后端与支付网关仅内网可见。
- 所有端口集中在 `docker-compose.yml` / `.env` 中，改一处即可。
- SQLite 数据落在宿主机 `./data/`（hotel.db + 网关的 gateway.db），容器重建数据不丢。

## 支付模块（模拟支付网关）

为贴合真实业务又不接入真实支付，项目内置了一个**独立的模拟支付网关服务**（`mock-gateway/`），与酒店后端的交互完全按真实第三方支付的模型实现：

1. **创建支付**：后端带 HMAC-SHA256 签名调用网关创建支付交易，得到收银台地址；
2. **收银台支付**：浏览器跳转收银台（商户名/订单号/金额 + 支付宝/微信渠道选择），点「付款成功 / 付款失败 / 取消支付」模拟支付结果；
3. **异步回调**：网关服务器间 POST 通知酒店后端（带签名），后端验签、**幂等**更新订单/账单状态；
4. **补偿查询**：若回调丢失，后端轮询网关主动补单（结果页 2 秒轮询触发）；
5. **模拟退款**：已支付预订取消时自动原路退款。

| 场景 | 入口 | 说明 |
| --- | --- | --- |
| 预订在线支付 | 顾客 → 我的预订 → 在线支付 | 跳转收银台，支付成功后订单标记"已支付" |
| 退房现金收款 | 服务员 → 退房结算 → 现金收款 | 账单立即标记已支付（现金） |
| 退房在线收款 | 服务员 → 退房结算 → 在线收款 | 打开收银台等待支付，回调后账单标记已支付（在线） |
| 取消退款 | 顾客取消已支付预订 | 自动调用网关模拟退款 |
| 未到店自动取消 | 后台定时扫描 | 预订超期未到店（入住日次日零点+宽限期）自动取消、释放房间，已支付的原路退款 |

## 三个界面与功能

| 界面       | 登录后进入   | 主要功能                                                                                      |
| ---------- | ------------ | --------------------------------------------------------------------------------------------- |
| 顾客门户   | `/customer`  | 浏览房型与剩余空房、在线预订（预订即分房）、在线支付/退款、我的预订/续订申请/取消 |
| 服务员前台 | `/reception` | 前台工作台（今日待到店、办理入住：指定房间/自动分配、续订确认）、在住与退房（双通道收款）、账单记录 |
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

模拟支付网关（另开一个终端）：

```bash
cd mock-gateway
"D:/项目/宾馆客房管理系统/backend/.venv/Scripts/python" -m uvicorn main:app --host 127.0.0.1 --port 18001
```

前端：

```bash
cd frontend
npm install
npm run dev    # http://localhost:9527，/api → 18000、/gateway → 18001 自动代理
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
├── models/entities.py   # 数据模型：User / RoomType / Room / Booking / CheckInRecord / Bill / Payment
├── schemas/             # Pydantic 请求/响应模型（auth / room / booking / stay / stats）
├── api/                 # 路由层（每个功能模块一个文件）
│   ├── deps.py          # 认证依赖：JWT 解析 + 角色隔离
│   ├── auth.py          # 注册 / 登录 / 当前用户
│   ├── rooms.py         # 房型、房间、可订查询（公开）
│   ├── bookings.py      # 顾客：创建/我的预订/取消/续订申请
│   ├── reception.py     # 服务员：待到店列表、入住、退房、收款、续订确认、房态概览
│   ├── payments.py      # 支付：创建支付单/状态查询/网关异步回调
│   └── admin.py         # 管理员：房型房价、房间、员工、预订、统计
└── services/            # 业务逻辑层
    ├── booking_service.py   # 预订即分房、房间冲突检测
    ├── stay_service.py      # 房态流转、自动选房、退房结算
    ├── payment_service.py   # 支付单、网关对接（签名/回调/补偿/退款）
    ├── renewal_service.py   # 续订：顾客申请、服务员确认/拒绝/直接续订
    └── stats_service.py     # 入住率、营收统计
```

## 技术栈

- 后端：Python 3.11 + FastAPI + SQLAlchemy 2 + SQLite + JWT
- 前端：Vue 3 + Vite + Pinia + Vue Router + Element Plus + ECharts
- 部署：Docker Compose
