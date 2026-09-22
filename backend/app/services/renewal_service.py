"""续订业务逻辑：顾客申请、服务员确认/拒绝、服务员直接续订。"""
from datetime import date
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core import config
from app.models.entities import Booking, CheckInRecord
from app.services.booking_service import nights_between, parse_date, room_has_conflict


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


def _check_extension_available(db: Session, booking: Booking, new_co: date):
    """延长区间 [原离店, 新离店) 内，该房间不能有其他有效预订。"""
    old_co = date.fromisoformat(booking.check_out_date)
    if booking.room_id and room_has_conflict(db, booking.room_id, old_co, new_co, exclude_booking_id=booking.id):
        raise HTTPException(409, "该房间在续订日期段已被其他预订占用，无法续订")


def _apply_renewal(db: Session, booking: Booking, new_co: date):
    booking.check_out_date = new_co.isoformat()
    room_type = booking.room_type
    if room_type:
        ci = date.fromisoformat(booking.check_in_date)
        nights = nights_between(ci, new_co)
        booking.estimated_price = float(room_type.price) * nights
    if booking.status == config.BOOKING_CHECKED_IN:
        record = db.get(CheckInRecord, booking.checkin_record.id) if booking.checkin_record else None
        if not record:
            record = db.query(CheckInRecord).filter(CheckInRecord.booking_id == booking.id).first()
        if record:
            record.expected_check_out = new_co.isoformat()
    booking.renewal_status = "confirmed"


def request_renewal(db: Session, customer_id: int, booking_id: int, new_check_out: str) -> Booking:
    """顾客申请续订：记录目标日期，等待服务员确认。"""
    booking = _load_booking(db, booking_id)
    if booking.customer_id != customer_id:
        raise HTTPException(403, "无权操作该预订")
    if booking.renewal_status == "pending":
        raise HTTPException(409, "该预订已有待确认的续订申请")
    new_co = _new_date(db, booking, new_check_out)
    _check_extension_available(db, booking, new_co)
    booking.requested_check_out = new_co.isoformat()
    booking.renewal_status = "pending"
    db.commit()
    db.refresh(booking)
    return booking


def confirm_renewal(db: Session, booking_id: int) -> Booking:
    """服务员确认顾客的续订申请。"""
    booking = _load_booking(db, booking_id)
    if booking.renewal_status != "pending" or not booking.requested_check_out:
        raise HTTPException(409, "该预订没有待确认的续订申请")
    new_co = _new_date(db, booking, booking.requested_check_out)
    _check_extension_available(db, booking, new_co)
    _apply_renewal(db, booking, new_co)
    db.commit()
    db.refresh(booking)
    return booking


def reject_renewal(db: Session, booking_id: int) -> Booking:
    """服务员拒绝顾客的续订申请。"""
    booking = _load_booking(db, booking_id)
    if booking.renewal_status != "pending":
        raise HTTPException(409, "该预订没有待确认的续订申请")
    booking.renewal_status = "rejected"
    db.commit()
    db.refresh(booking)
    return booking


def direct_renewal(db: Session, booking_id: int, new_check_out: str) -> Booking:
    """服务员直接续订（无需顾客申请）。"""
    booking = _load_booking(db, booking_id)
    new_co = _new_date(db, booking, new_check_out)
    _check_extension_available(db, booking, new_co)
    booking.requested_check_out = new_co.isoformat()
    _apply_renewal(db, booking, new_co)
    db.commit()
    db.refresh(booking)
    return booking
