"""预订相关业务逻辑：按房间冲突检测、预订即分房、价格估算。"""
from datetime import date

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import config
from app.models.entities import Booking, Room, RoomType
from typing import Optional


def parse_date(s: str, field: str) -> date:
    try:
        return date.fromisoformat(s)
    except ValueError:
        raise HTTPException(400, f"{field} 格式不正确，应为 YYYY-MM-DD")


def validate_range(check_in: date, check_out: date):
    if check_in < date.today():
        raise HTTPException(400, "入住日期不能早于今天")
    if check_out <= check_in:
        raise HTTPException(400, "离店日期必须晚于入住日期")


def nights_between(check_in: date, check_out: date) -> int:
    return max((check_out - check_in).days, 1)


def room_has_conflict(db: Session, room_id: int, ci: date, co: date, exclude_booking_id: Optional[int] = None) -> bool:
    """某房间在 [ci, co) 内是否已有有效预订（待到店/已入住）。"""
    query = select(Booking).where(
        Booking.room_id == room_id,
        Booking.status.in_([config.BOOKING_PENDING, config.BOOKING_CHECKED_IN]),
        Booking.check_in_date < co.isoformat(),
        Booking.check_out_date > ci.isoformat(),
    )
    if exclude_booking_id:
        query = query.where(Booking.id != exclude_booking_id)
    return db.scalar(query.limit(1)) is not None


def find_assignable_room(db: Session, room_type_id: int, ci: date, co: date) -> Room:
    """找该房型下可分配给 [ci, co) 的房间：状态非维修/在住，且无重叠预订。"""
    rooms = db.scalars(
        select(Room)
        .where(Room.type_id == room_type_id, Room.status.notin_([config.ROOM_MAINTENANCE, config.ROOM_OCCUPIED]))
        .order_by(Room.room_number)
    ).all()
    for room in rooms:
        if not room_has_conflict(db, room.id, ci, co):
            return room
    raise HTTPException(409, "该日期段房型已订满，请更换日期或房型")


def find_available_rooms(db: Session, room_type_id: int, ci: date, co: date) -> list:
    """该房型下在 [ci, co) 可用的房间列表（前台选房用）。"""
    rooms = db.scalars(
        select(Room)
        .where(Room.type_id == room_type_id, Room.status.notin_([config.ROOM_MAINTENANCE, config.ROOM_OCCUPIED]))
        .order_by(Room.room_number)
    ).all()
    return [r for r in rooms if not room_has_conflict(db, r.id, ci, co)]


def count_free_rooms(db: Session, room_type_id: int, ci: date, co: date) -> int:
    """某房型在给定日期段内的可订数量。"""
    return len(find_available_rooms(db, room_type_id, ci, co))


def mark_room_booked_if_due(db: Session, room: Room, check_in_date: str):
    """预订已到入住日时，房间标记为被预订。"""
    if room and check_in_date <= date.today().isoformat() and room.status == config.ROOM_AVAILABLE:
        room.status = config.ROOM_BOOKED


def refresh_room_status_after_release(db: Session, room: Optional[Room]):
    """房间释放（退房/取消预订）后：若有已到日期的待到店预订 → booked，否则 available。"""
    if not room or room.status not in (config.ROOM_AVAILABLE, config.ROOM_BOOKED):
        return
    today = date.today().isoformat()
    due = db.scalar(
        select(Booking).where(
            Booking.room_id == room.id,
            Booking.status == config.BOOKING_PENDING,
            Booking.check_in_date <= today,
        ).limit(1)
    )
    room.status = config.ROOM_BOOKED if due else config.ROOM_AVAILABLE


def create_booking(db: Session, customer_id: int, data) -> Booking:
    ci = parse_date(data.check_in_date, "入住日期")
    co = parse_date(data.check_out_date, "离店日期")
    validate_range(ci, co)

    room_type = db.get(RoomType, data.room_type_id)
    if not room_type:
        raise HTTPException(404, "房型不存在")

    # 预订即分房：创建时锁定具体房间
    room = find_assignable_room(db, data.room_type_id, ci, co)
    nights = nights_between(ci, co)
    booking = Booking(
        customer_id=customer_id,
        room_type_id=data.room_type_id,
        room_id=room.id,
        check_in_date=ci.isoformat(),
        check_out_date=co.isoformat(),
        guests=data.guests,
        estimated_price=float(room_type.price) * nights,
        remark=data.remark,
        status=config.BOOKING_PENDING,
    )
    mark_room_booked_if_due(db, room, booking.check_in_date)
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


def cancel_booking(db: Session, customer_id: Optional[int], booking_id: int, is_admin: bool = False) -> Booking:
    booking = db.get(Booking, booking_id)
    if not booking:
        raise HTTPException(404, "预订不存在")
    if not is_admin and booking.customer_id != customer_id:
        raise HTTPException(403, "无权操作该预订")
    if booking.status != config.BOOKING_PENDING:
        raise HTTPException(409, "仅待到店的预订可以取消")
    booking.status = config.BOOKING_CANCELLED
    booking.renewal_status = "none"
    booking.requested_check_out = None
    refresh_room_status_after_release(db, booking.room)
    db.commit()
    db.refresh(booking)
    return booking
