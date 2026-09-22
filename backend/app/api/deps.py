"""认证依赖：从 JWT 解析当前用户，按角色做接口级隔离。"""
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core import config
from app.core.security import decode_access_token
from app.db.database import get_db
from app.models.entities import User

ROLE_LABELS = {
    config.ROLE_CUSTOMER: "顾客",
    config.ROLE_RECEPTIONIST: "服务员",
    config.ROLE_ADMIN: "管理员",
}


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "未登录或凭证缺失")
    payload = decode_access_token(auth.removeprefix("Bearer ").strip())
    if not payload:
        raise HTTPException(401, "登录已过期，请重新登录")
    user = db.get(User, int(payload["sub"]))
    if not user or not user.is_active:
        raise HTTPException(401, "账号不存在或已被禁用")
    return user


def require_roles(*roles: str):
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(403, f"无权访问，需要{'、'.join(ROLE_LABELS.get(r, r) for r in roles)}权限")
        return user
    return checker


# 常用角色依赖
require_staff = require_roles(config.ROLE_RECEPTIONIST, config.ROLE_ADMIN)
require_admin = require_roles(config.ROLE_ADMIN)
