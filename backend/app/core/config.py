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
