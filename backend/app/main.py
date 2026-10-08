import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import admin, auth, bookings, payments, reception, rooms
from app.core.config import DATA_DIR
from app.db.database import Base, SessionLocal, engine
from app.db.init_data import init_database
from app.services.auto_checkout_service import auto_checkout_loop


def _ensure_columns():
    """轻量迁移：为已有库补齐后加的列（SQLite ALTER TABLE ADD COLUMN）。"""
    from sqlalchemy import text

    with engine.connect() as conn:
        cols = [row[1] for row in conn.execute(text("PRAGMA table_info(checkin_records)"))]
        if "checkout_type" not in cols:
            conn.execute(text("ALTER TABLE checkin_records ADD COLUMN checkout_type VARCHAR(20) DEFAULT 'manual'"))
            conn.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    _ensure_columns()
    db = SessionLocal()
    try:
        init_database(db)
    finally:
        db.close()
    # 超时未退房自动退房后台任务
    task = asyncio.create_task(auto_checkout_loop())
    yield
    task.cancel()


app = FastAPI(
    title="宾馆客房管理系统",
    description="学生毕业实训项目：顾客在线预订 + 前台入住退房 + 管理员经营统计",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 由 Nginx 反代统一入口，本地开发放宽
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(rooms.router, prefix="/api")
app.include_router(bookings.router, prefix="/api")
app.include_router(reception.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(payments.router, prefix="/api")


@app.get("/api/health", tags=["系统"])
def health():
    return {"status": "ok"}
