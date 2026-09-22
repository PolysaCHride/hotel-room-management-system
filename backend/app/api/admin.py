from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.core import config
from app.db.database import get_db
from app.models.entities import Booking, Room, RoomType, User
from app.schemas.auth import UserOut
from app.schemas.room import RoomOut, RoomTypeOut, RoomTypeUpdate, RoomStatusUpdate
from app.schemas.stats import StatsOut
from app.services.stats_service import build_stats
from typing import Optional

router = APIRouter(prefix="/admin", tags=["管理（管理员）"], dependencies=[Depends(require_admin)])


# ---------- 房型管理 ----------
@router.post("/room-types", response_model=RoomTypeOut, summary="新增房型")
def create_room_type(name: str, price: float, capacity: int = 2, description: str = "", db: Session = Depends(get_db)):
    if db.scalar(select(RoomType).where(RoomType.name == name)):
        raise HTTPException(409, "房型名已存在")
    rt = RoomType(name=name, price=price, capacity=capacity, description=description)
    db.add(rt)
    db.commit()
    db.refresh(rt)
    return rt


@router.put("/room-types/{type_id}", response_model=RoomTypeOut, summary="修改房型（含调价）")
def update_room_type(type_id: int, data: RoomTypeUpdate, db: Session = Depends(get_db)):
    rt = db.get(RoomType, type_id)
    if not rt:
        raise HTTPException(404, "房型不存在")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(rt, field, value)
    db.commit()
    db.refresh(rt)
    return rt


@router.delete("/room-types/{type_id}", summary="删除房型（无关联房间时）")
def delete_room_type(type_id: int, db: Session = Depends(get_db)):
    rt = db.get(RoomType, type_id)
    if not rt:
        raise HTTPException(404, "房型不存在")
    if rt.rooms:
        raise HTTPException(409, "该房型下仍有房间，不能删除")
    db.delete(rt)
    db.commit()
    return {"ok": True}


# ---------- 房间管理 ----------
@router.post("/rooms", response_model=RoomOut, summary="新增房间")
def create_room(room_number: str, type_id: int, floor: int = 1, db: Session = Depends(get_db)):
    if db.scalar(select(Room).where(Room.room_number == room_number)):
        raise HTTPException(409, "房号已存在")
    if not db.get(RoomType, type_id):
        raise HTTPException(404, "房型不存在")
    room = Room(room_number=room_number, type_id=type_id, floor=floor)
    db.add(room)
    db.commit()
    db.refresh(room)
    out = RoomOut.model_validate(room)
    rt = db.get(RoomType, type_id)
    out.type_name = rt.name
    out.price = float(rt.price)
    return out


@router.put("/rooms/{room_id}/status", response_model=RoomOut, summary="设置房间状态（含维修/恢复）")
def update_room_status(room_id: int, data: RoomStatusUpdate, db: Session = Depends(get_db)):
    if data.status not in (config.ROOM_AVAILABLE, config.ROOM_MAINTENANCE, config.ROOM_BOOKED, config.ROOM_OCCUPIED):
        raise HTTPException(400, "非法房间状态")
    room = db.get(Room, room_id)
    if not room:
        raise HTTPException(404, "房间不存在")
    if room.status == config.ROOM_OCCUPIED and data.status != config.ROOM_OCCUPIED:
        raise HTTPException(409, "房间在住中，需先办理退房")
    room.status = data.status
    room.note = data.note if data.note is not None else room.note
    db.commit()
    db.refresh(room)
    out = RoomOut.model_validate(room)
    rt = db.get(RoomType, room.type_id)
    out.type_name = rt.name
    out.price = float(rt.price)
    return out


@router.delete("/rooms/{room_id}", summary="删除房间")
def delete_room(room_id: int, db: Session = Depends(get_db)):
    room = db.get(Room, room_id)
    if not room:
        raise HTTPException(404, "房间不存在")
    if room.status == config.ROOM_OCCUPIED:
        raise HTTPException(409, "房间在住中，不能删除")
    db.delete(room)
    db.commit()
    return {"ok": True}


# ---------- 员工管理 ----------
@router.get("/users", response_model=list[UserOut], summary="用户/员工列表")
def list_users(role: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(User)
    if role:
        query = query.filter(User.role == role)
    return query.order_by(User.id).all()


@router.post("/staff", response_model=UserOut, summary="新增服务员账号")
def create_staff(username: str, password: str, real_name: str = "", phone: str = "", db: Session = Depends(get_db)):
    from app.core.security import hash_password

    if db.scalar(select(User).where(User.username == username)):
        raise HTTPException(409, "用户名已存在")
    user = User(
        username=username,
        password_hash=hash_password(password),
        real_name=real_name or username,
        phone=phone,
        role=config.ROLE_RECEPTIONIST,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.put("/users/{user_id}/active", response_model=UserOut, summary="启用/禁用账号")
def toggle_user(user_id: int, is_active: bool, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "用户不存在")
    user.is_active = is_active
    db.commit()
    db.refresh(user)
    return user


# ---------- 预订管理 ----------
@router.get("/bookings", response_model=list[dict], summary="全部预订列表")
def all_bookings(status: Optional[str] = None, db: Session = Depends(get_db)):
    from app.models.entities import Booking

    query = db.query(Booking).join(User).join(RoomType)
    if status:
        query = query.filter(Booking.status == status)
    rows = query.order_by(Booking.created_at.desc()).limit(200).all()
    return [
        {
            "id": b.id,
            "customer_name": b.customer.real_name if b.customer else "",
            "room_type_name": b.room_type.name if b.room_type else "",
            "check_in_date": b.check_in_date,
            "check_out_date": b.check_out_date,
            "guests": b.guests,
            "estimated_price": float(b.estimated_price),
            "status": b.status,
            "created_at": b.created_at.strftime("%Y-%m-%d %H:%M") if b.created_at else "",
        }
        for b in rows
    ]


@router.post("/bookings/{booking_id}/cancel", summary="管理员取消预订")
def admin_cancel_booking(booking_id: int, db: Session = Depends(get_db)):
    from app.services.booking_service import cancel_booking

    cancel_booking(db, None, booking_id, is_admin=True)
    return {"ok": True}


# ---------- 统计 ----------
@router.get("/stats", response_model=StatsOut, summary="经营统计看板")
def stats(db: Session = Depends(get_db)):
    return build_stats(db)
