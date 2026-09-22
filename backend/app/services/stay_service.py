"""入住 / 退房业务逻辑：房态流转、自动选房、账单结算。"""
from datetime import date, datetime
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core import config
from app.models.entities import Bill, Booking, CheckInRecord, Room, RoomType
from app.services.booking_service import (
    parse_date,
    refresh_room_status_after_release,
    room_has_conflict,
)


def auto_pick_room(db: Session, room_type_id: int, expected_out: str, exclude_booking_id: Optional[int] = None) -> Room:
    """自动选房：状态空闲、且在住宿期间无待到店预订（避免占用被预订房间）。"""
    ci = datetime.now().date()
    co = parse_date(expected_out, "预计离店日期")
    rooms = db.scalars(
        select(Room)
        .where(Room.type_id == room_type_id, Room.status == config.ROOM_AVAILABLE)
        .order_by(Room.room_number)
    ).all()
    for room in rooms:
        if not room_has_conflict(db, room.id, ci, co, exclude_booking_id=exclude_booking_id):
            return room
    raise HTTPException(409, "该房型当前没有可用的空闲房间（可能已被预订占用）")


def do_check_in(db: Session, operator_id: int, data) -> CheckInRecord:
    expected_out = parse_date(data.expected_check_out, "预计离店日期")
    if expected_out <= datetime.now().date():
        raise HTTPException(400, "预计离店日期必须晚于今天")

    booking = None
    if data.booking_id:
        booking = db.get(Booking, data.booking_id)
        if not booking:
            raise HTTPException(404, "预订不存在")
        if booking.status != config.BOOKING_PENDING:
            raise HTTPException(409, "该预订不是待到店状态，无法办理入住")
        if booking.check_out_date <= datetime.now().date().isoformat():
            raise HTTPException(400, "预订已过期，无法办理入住")

    # 选房：指定房间或自动分配
    if data.room_id:
        room = db.get(Room, data.room_id)
        if not room:
            raise HTTPException(404, "房间不存在")
        if room.status not in (config.ROOM_AVAILABLE, config.ROOM_BOOKED):
            raise HTTPException(409, f"房间 {room.room_number} 当前不可用（非空闲）")
        if booking and booking.room_type_id != room.type_id:
            raise HTTPException(400, "所选房间与预订房型不一致")
        # 非本预订自己的房间不允许办理入住（被预订房间留给预订客人）
        if room.status == config.ROOM_BOOKED:
            if not booking or booking.room_id != room.id:
                raise HTTPException(409, f"房间 {room.room_number} 已被预订，无法办理入住")
        if room_has_conflict(db, room.id, datetime.now().date(), expected_out, exclude_booking_id=booking.id if booking else None):
            raise HTTPException(409, f"房间 {room.room_number} 在住宿期间已有预订，无法办理入住")
    else:
        type_id = booking.room_type_id if booking else data.room_type_id
        if not type_id:
            raise HTTPException(400, "散客开房必须指定房型或房间")
        if booking and booking.room_id:
            # 预订入住：优先使用预订分配的房间
            room = db.get(Room, booking.room_id)
            if not room or room.status not in (config.ROOM_AVAILABLE, config.ROOM_BOOKED):
                # 异常情况（房间被占用等）：改选同类型其他可用房间
                room = auto_pick_room(db, type_id, data.expected_check_out, exclude_booking_id=booking.id)
        else:
            room = auto_pick_room(db, type_id, data.expected_check_out, exclude_booking_id=booking.id if booking else None)

    # 客人信息：优先手填，预订入住时取预订人
    guest_name = data.guest_name
    guest_phone = data.guest_phone
    customer_id = None
    if booking:
        from app.models.entities import User

        customer = db.get(User, booking.customer_id)
        if customer:
            customer_id = customer.id
            guest_name = guest_name or customer.real_name or customer.username
            guest_phone = guest_phone or customer.phone

    record = CheckInRecord(
        booking_id=booking.id if booking else None,
        customer_id=customer_id,
        guest_name=guest_name or "散客",
        guest_phone=guest_phone,
        room_id=room.id,
        operator_id=operator_id,
        expected_check_out=expected_out.isoformat(),
    )
    room.status = config.ROOM_OCCUPIED
    room.note = ""
    if booking:
        booking.status = config.BOOKING_CHECKED_IN
        # 入住使用分配房间，保持订单与房间一致
        booking.room_id = room.id

    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def do_check_out(db: Session, record_id: int) -> Bill:
    record = db.get(CheckInRecord, record_id)
    if not record:
        raise HTTPException(404, "入住记录不存在")
    if record.check_out_time:
        raise HTTPException(409, "该记录已退房结算")

    now = datetime.now()
    days = max((now.date() - record.check_in_time.date()).days, 1)

    room = db.get(Room, record.room_id)
    room_type = db.get(RoomType, room.type_id) if room else None
    price = float(room_type.price) if room_type else 0.0
    amount = round(price * days, 2)

    bill = Bill(
        checkin_id=record.id,
        room_number=room.room_number if room else "",
        days=days,
        room_price=price,
        amount=amount,
        is_paid=True,
    )
    record.check_out_time = now
    if room:
        room.status = config.ROOM_AVAILABLE
        room.note = ""
        # 若该房间有已到日期的待到店预订，标记为被预订
        refresh_room_status_after_release(db, room)
    if record.booking_id:
        booking = db.get(Booking, record.booking_id)
        if booking:
            booking.status = config.BOOKING_COMPLETED

    db.add(bill)
    db.commit()
    db.refresh(bill)
    return bill


def get_active_stays(db: Session) -> list:
    return (
        db.query(CheckInRecord)
        .options(joinedload(CheckInRecord.room))
        .filter(CheckInRecord.check_out_time.is_(None))
        .order_by(CheckInRecord.check_in_time.desc())
        .all()
    )
