"""经营统计业务逻辑：房态、入住率、营收。"""
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core import config
from app.models.entities import Bill, Booking, CheckInRecord, Room


def build_stats(db: Session) -> dict:
    today = datetime.now().date()
    today_s = today.isoformat()

    total_rooms = db.scalar(select(func.count(Room.id))) or 0
    status_rows = db.query(Room.status, func.count(Room.id)).group_by(Room.status).all()
    by_status = {s: c for s, c in status_rows}
    free = by_status.get(config.ROOM_AVAILABLE, 0)
    occupied = by_status.get(config.ROOM_OCCUPIED, 0)
    booked = by_status.get(config.ROOM_BOOKED, 0)
    maintenance = by_status.get(config.ROOM_MAINTENANCE, 0)

    active_stays = db.scalar(
        select(func.count(CheckInRecord.id)).where(CheckInRecord.check_out_time.is_(None))
    ) or 0

    today_arrivals = db.scalar(
        select(func.count(Booking.id)).where(
            Booking.check_in_date == today_s,
            Booking.status == config.BOOKING_PENDING,
        )
    ) or 0

    today_checkins = db.scalar(
        select(func.count(CheckInRecord.id)).where(
            func.date(CheckInRecord.check_in_time) == today_s
        )
    ) or 0

    revenue_today = db.scalar(
        select(func.coalesce(func.sum(Bill.amount), 0)).where(
            func.date(Bill.created_at) == today_s
        )
    ) or 0
    revenue_total = db.scalar(select(func.coalesce(func.sum(Bill.amount), 0))) or 0

    # 近 7 天营收
    revenue_by_day = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        amount = db.scalar(
            select(func.coalesce(func.sum(Bill.amount), 0)).where(
                func.date(Bill.created_at) == d.isoformat()
            )
        ) or 0
        revenue_by_day.append({"date": d.isoformat(), "amount": float(amount)})

    status_rows = db.query(Booking.status, func.count(Booking.id)).group_by(Booking.status).all()
    booking_status_count = {s: c for s, c in status_rows}
    for key in (config.BOOKING_PENDING, config.BOOKING_CHECKED_IN, config.BOOKING_COMPLETED, config.BOOKING_CANCELLED):
        booking_status_count.setdefault(key, 0)

    occupancy_rate = round(occupied / total_rooms * 100, 1) if total_rooms else 0.0

    return {
        "total_rooms": total_rooms,
        "free_rooms": free,
        "occupied_rooms": occupied,
        "booked_rooms": booked,
        "maintenance_rooms": maintenance,
        "occupancy_rate": occupancy_rate,
        "today_arrivals": today_arrivals,
        "today_checkins": today_checkins,
        "active_stays": active_stays,
        "revenue_today": float(revenue_today),
        "revenue_total": float(revenue_total),
        "revenue_by_day": revenue_by_day,
        "booking_status_count": booking_status_count,
    }
