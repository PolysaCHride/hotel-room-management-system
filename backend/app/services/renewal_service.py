"""续订业务逻辑：顾客申请、服务员确认/拒绝、服务员直接续订。

房间规则（前台批准续订时自动处理）：
- 原房间在延长的日期段内空闲 → 原房续住；
- 原房间已被其他预订占用，但同房型仍有空闲房间 → 自动为客人更换房间并同步在住记录与房态；
- 同房型已无剩余房间 → 续订自动拒绝（409）。
"""
from datetime import date
from typing import Optional, Tuple

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core import config
from app.models.entities import Booking, CheckInRecord, Room
from app.services.booking_service import (
    find_available_rooms,
    nights_between,
    parse_date,
    refresh_room_status_after_release,
    room_has_conflict,
)


def _load_booking(db: Session, booking_id: int) -> Booking:
    booking = db.get(Booking, booking_id)
    if not booking:
        raise HTTPException(404, "预订不存在")
    if booking.status not in (config.BOOKING_PENDING, config.BOOKING_CHECKED_IN):
        raise HTTPException(409, "仅待到店或已入住的预订可以续订")
    return booking


def _new_date(db: Session, booking: Booking, new_check_out: str) -> date:
    new_co = parse_date(new_check_out, "新离店日期")
    current_co = date.fromisoformat(booking.check_out_date)
    if new_co <= current_co:
        raise HTTPException(400, f"新离店日期必须晚于当前离店日期（{booking.check_out_date}）")
    return new_co


def _resolve_extension_room(db: Session, booking: Booking, new_co: date) -> Tuple[Optional[Room], bool]:
    """返回 (续订使用的房间, 是否发生了换房)。无可用房间返回 (None, False)。"""
    old_co = date.fromisoformat(booking.check_out_date)
    # 原房间在延长段内空闲 → 原房续住
    if booking.room_id and not room_has_conflict(db, booking.room_id, old_co, new_co, exclude_booking_id=booking.id):
        return db.get(Room, booking.room_id), False
    # 原房间冲突：同房型找空闲房间，有则自动换房
    candidates = find_available_rooms(db, booking.room_type_id, old_co, new_co)
    return (candidates[0], True) if candidates else (None, False)


def _apply_renewal(db: Session, booking: Booking, new_co: date, new_room, moved: bool) -> Optional[str]:
    """执行续订：延长离店日期；若换房则同步房态与在住记录。返回新房间号（未换房返回 None）。"""
    moved_to = None
    old_room = booking.room
    booking.check_out_date = new_co.isoformat()
    room_type = booking.room_type
    if room_type:
        ci = date.fromisoformat(booking.check_in_date)
        nights = nights_between(ci, new_co)
        booking.estimated_price = float(room_type.price) * nights

    if moved and new_room and old_room and new_room.id != old_room.id:
        # 释放原房间（若其有已到日期的待到店预订则标记为已订）
        refresh_room_status_after_release(db, old_room)
        # 新房间入住
        new_room.status = config.ROOM_OCCUPIED
        new_room.note = ""
        booking.room_id = new_room.id
        moved_to = new_room.room_number

    if booking.status == config.BOOKING_CHECKED_IN:
        record = booking.checkin_record
        if record is None:
            record = db.query(CheckInRecord).filter(CheckInRecord.booking_id == booking.id).first()
        if record:
            record.expected_check_out = new_co.isoformat()
            if moved_to:
                record.room_id = booking.room_id
    booking.renewal_status = "confirmed"
    return moved_to


def request_renewal(db: Session, customer_id: int, booking_id: int, new_check_out: str) -> Booking:
    """顾客申请续订：记录目标日期，等待服务员确认（房间安排由前台批准时决定）。"""
    booking = _load_booking(db, booking_id)
    if booking.customer_id != customer_id:
        raise HTTPException(403, "无权操作该预订")
    if booking.renewal_status == "pending":
        raise HTTPException(409, "该预订已有待确认的续订申请")
    new_co = _new_date(db, booking, new_check_out)
    booking.requested_check_out = new_co.isoformat()
    booking.renewal_status = "pending"
    db.commit()
    db.refresh(booking)
    return booking


def confirm_renewal(db: Session, booking_id: int) -> dict:
    """服务员确认顾客的续订申请（含自动换房/自动拒绝）。"""
    booking = _load_booking(db, booking_id)
    if booking.renewal_status != "pending" or not booking.requested_check_out:
        raise HTTPException(409, "该预订没有待确认的续订申请")
    new_co = _new_date(db, booking, booking.requested_check_out)
    room, moved = _resolve_extension_room(db, booking, new_co)
    if room is None:
        raise HTTPException(409, "该房型在续订日期段已无剩余房间，续订已自动拒绝")
    moved_to = _apply_renewal(db, booking, new_co, room, moved)
    db.commit()
    db.refresh(booking)
    return {"ok": True, "moved_to": moved_to, "room_number": booking.room.room_number if booking.room else ""}


def reject_renewal(db: Session, booking_id: int) -> Booking:
    """服务员拒绝顾客的续订申请。"""
    booking = _load_booking(db, booking_id)
    if booking.renewal_status != "pending":
        raise HTTPException(409, "该预订没有待确认的续订申请")
    booking.renewal_status = "rejected"
    db.commit()
    db.refresh(booking)
    return booking


def direct_renewal(db: Session, booking_id: int, new_check_out: str) -> dict:
    """服务员直接续订（无需顾客申请），含自动换房/自动拒绝。"""
    booking = _load_booking(db, booking_id)
    new_co = _new_date(db, booking, new_check_out)
    room, moved = _resolve_extension_room(db, booking, new_co)
    if room is None:
        raise HTTPException(409, "该房型在续订日期段已无剩余房间，续订已自动拒绝")
    moved_to = _apply_renewal(db, booking, new_co, room, moved)
    db.commit()
    db.refresh(booking)
    return {"ok": True, "moved_to": moved_to, "room_number": booking.room.room_number if booking.room else ""}
