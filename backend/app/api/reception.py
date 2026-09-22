from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.api.deps import require_staff
from app.db.database import get_db
from app.models.entities import Bill, Booking, CheckInRecord, User
from app.schemas.stay import BillOut, CheckInRequest, CheckInOut
from app.services.stay_service import do_check_in, do_check_out, get_active_stays

router = APIRouter(prefix="/reception", tags=["前台（服务员）"], dependencies=[Depends(require_staff)])


@router.get("/room-summary", response_model=dict, summary="房态概览（服务员看板用）")
def room_summary(db: Session = Depends(get_db)):
    from app.models.entities import Room

    rows = db.query(Room.status, func.count(Room.id)).group_by(Room.status).all()
    by_status = {s: c for s, c in rows}
    total = sum(by_status.values())
    return {
        "total_rooms": total,
        "free_rooms": by_status.get("available", 0),
        "occupied_rooms": by_status.get("occupied", 0),
        "booked_rooms": by_status.get("booked", 0),
        "maintenance_rooms": by_status.get("maintenance", 0),
    }


@router.get("/arrivals", response_model=list[dict], summary="今日到店 / 全部待到店预订")
def arrivals(all_pending: bool = False, db: Session = Depends(get_db)):
    query = (
        db.query(Booking)
        .options(joinedload(Booking.customer), joinedload(Booking.room_type))
        .filter(Booking.status == "pending")
    )
    if not all_pending:
        query = query.filter(Booking.check_in_date == datetime.now().date().isoformat())
    rows = query.order_by(Booking.check_in_date).all()
    return [
        {
            "id": b.id,
            "customer_name": b.customer.real_name if b.customer else "",
            "customer_phone": b.customer.phone if b.customer else "",
            "room_type_name": b.room_type.name if b.room_type else "",
            "check_in_date": b.check_in_date,
            "check_out_date": b.check_out_date,
            "guests": b.guests,
            "estimated_price": float(b.estimated_price),
            "remark": b.remark,
        }
        for b in rows
    ]


@router.post("/check-in", response_model=CheckInOut, summary="办理入住（预订入住 / 散客开房）")
def check_in(data: CheckInRequest, user: User = Depends(require_staff), db: Session = Depends(get_db)):
    record = do_check_in(db, user.id, data)
    return _record_out(record)


@router.get("/stays", response_model=list[CheckInOut], summary="当前在住列表")
def stays(db: Session = Depends(get_db)):
    return [_record_out(r) for r in get_active_stays(db)]


@router.post("/check-out/{record_id}", response_model=BillOut, summary="办理退房并生成账单")
def check_out(record_id: int, db: Session = Depends(get_db)):
    bill = do_check_out(db, record_id)
    return _bill_out(db, bill)


@router.get("/bills", response_model=list[BillOut], summary="账单列表")
def bills(db: Session = Depends(get_db)):
    bills = db.query(Bill).order_by(Bill.created_at.desc()).limit(100).all()
    return [_bill_out(db, b) for b in bills]


def _record_out(record: CheckInRecord) -> CheckInOut:
    item = CheckInOut.model_validate(record)
    if record.room:
        item.room_number = record.room.room_number
        if record.room.room_type:
            item.room_type_name = record.room.room_type.name
    return item


def _bill_out(db: Session, bill: Bill) -> BillOut:
    item = BillOut.model_validate(bill)
    item.room_price = float(bill.room_price)
    item.amount = float(bill.amount)
    record = db.get(CheckInRecord, bill.checkin_id)
    if record:
        item.guest_name = record.guest_name
    return item
