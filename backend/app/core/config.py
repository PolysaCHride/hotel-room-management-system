import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# SQLite 数据库文件位置（容器内为 /data/hotel.db，本地开发默认 backend/data/hotel.db）
DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
# 注意：Windows 下 SQLAlchemy 需要正斜杠形式的路径
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{(DATA_DIR / 'hotel.db').as_posix()}")

# JWT 配置（生产部署请通过环境变量覆盖）
SECRET_KEY = os.getenv("SECRET_KEY", "hotel-training-system-secret-key-change-me")
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = int(os.getenv("TOKEN_EXPIRE_HOURS", "24"))

# 角色
ROLE_CUSTOMER = "customer"
ROLE_RECEPTIONIST = "receptionist"
ROLE_ADMIN = "admin"
ROLES = (ROLE_CUSTOMER, ROLE_RECEPTIONIST, ROLE_ADMIN)

# 房间状态
ROOM_AVAILABLE = "available"      # 空闲
ROOM_BOOKED = "booked"            # 已订（今日有到店预订）
ROOM_OCCUPIED = "occupied"        # 入住中
ROOM_MAINTENANCE = "maintenance"  # 维修中

# 预订状态
BOOKING_PENDING = "pending"        # 待到店
BOOKING_CHECKED_IN = "checked_in"  # 已入住
BOOKING_CANCELLED = "cancelled"    # 已取消
BOOKING_COMPLETED = "completed"    # 已完成（退房结算）

# 支付网关（模拟）
GATEWAY_BASE_URL = os.getenv("GATEWAY_BASE_URL", "http://127.0.0.1:18001")
GATEWAY_PUBLIC_PREFIX = os.getenv("GATEWAY_PUBLIC_PREFIX", "/gateway")  # 浏览器访问收银台的路径前缀
PAY_MERCHANT_ID = os.getenv("PAY_MERCHANT_ID", "hotel")
PAY_SECRET = os.getenv("PAY_SECRET", "demo-pay-secret-change-me")
# 网关服务器间回调本服务的地址（容器内为 http://backend:8000）
NOTIFY_BASE_URL = os.getenv("NOTIFY_BASE_URL", "http://127.0.0.1:18000")

# 自动退房：超过预计离店日的退房时限（当天 CHECKOUT_HOUR 点）再宽限 GRACE_HOURS 小时
# 仍未到前台办理退房的，由系统自动办理退房并生成待支付账单
AUTO_CHECKOUT_ENABLED = os.getenv("AUTO_CHECKOUT_ENABLED", "true").lower() == "true"
AUTO_CHECKOUT_CHECKOUT_HOUR = int(os.getenv("AUTO_CHECKOUT_CHECKOUT_HOUR", "12"))
AUTO_CHECKOUT_GRACE_HOURS = float(os.getenv("AUTO_CHECKOUT_GRACE_HOURS", "2"))
AUTO_CHECKOUT_INTERVAL_SECONDS = int(os.getenv("AUTO_CHECKOUT_INTERVAL_SECONDS", "60"))
