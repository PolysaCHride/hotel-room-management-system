"""预订相关业务逻辑：冲突检测、价格估算。"""
from datetime import date

from fastapi import HTTPException
from sqlalchemy import func, select
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


def count_free_rooms(db: Session, room_type_id: int, ci: date, co: date) -> int:
    """某房型在给定日期段内的可订数量 = 该房型总房数 - 重叠的未取消预订数。"""
    total = db.scalar(
        select(func.count(Room.id)).where(Room.type_id == room_type_id)
    ) or 0
    overlapping = db.scalar(
        select(func.count(Booking.id)).where(
            Booking.room_type_id == room_type_id,
            Booking.status.in_([config.BOOKING_PENDING, config.BOOKING_CHECKED_IN]),
            Booking.check_in_date < co.isoformat(),
            Booking.check_out_date > ci.isoformat(),
        )
    ) or 0
    return max(total - overlapping, 0)


def create_booking(db: Session, customer_id: int, data) -> Booking:
    ci = parse_date(data.check_in_date, "入住日期")
    co = parse_date(data.check_out_date, "离店日期")
    validate_range(ci, co)

    room_type = db.get(RoomType, data.room_type_id)
    if not room_type:
        raise HTTPException(404, "房型不存在")

    free = count_free_rooms(db, data.room_type_id, ci, co)
    if free <= 0:
        raise HTTPException(409, "该日期段房型已订满，请更换日期或房型")

    nights = nights_between(ci, co)
    booking = Booking(
        customer_id=customer_id,
        room_type_id=data.room_type_id,
        check_in_date=ci.isoformat(),
        check_out_date=co.isoformat(),
        guests=data.guests,
        estimated_price=float(room_type.price) * nights,
        remark=data.remark,
        status=config.BOOKING_PENDING,
    )
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
    db.commit()
    db.refresh(booking)
    return booking
