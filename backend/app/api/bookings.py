from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user
from app.db.database import get_db
from app.models.entities import Booking, User
from app.schemas.booking import BookingCreate, BookingOut
from app.services.booking_service import cancel_booking, create_booking

router = APIRouter(prefix="/bookings", tags=["预订（顾客）"])


def _to_out(db: Session, booking: Booking) -> BookingOut:
    item = BookingOut.model_validate(booking)
    item.customer_name = booking.customer.real_name if booking.customer else ""
    item.room_type_name = booking.room_type.name if booking.room_type else ""
    item.estimated_price = float(booking.estimated_price)
    return item


@router.post("", response_model=BookingOut, summary="创建预订（需登录）")
def create(data: BookingCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    booking = create_booking(db, user.id, data)
    return _to_out(db, booking)


@router.get("/mine", response_model=list[BookingOut], summary="我的预订")
def my_bookings(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    bookings = (
        db.query(Booking)
        .options(joinedload(Booking.room_type), joinedload(Booking.customer))
        .filter(Booking.customer_id == user.id)
        .order_by(Booking.created_at.desc())
        .all()
    )
    return [_to_out(db, b) for b in bookings]


@router.post("/{booking_id}/cancel", response_model=BookingOut, summary="取消我的预订")
def cancel(booking_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    booking = cancel_booking(db, user.id, booking_id)
    return _to_out(db, booking)
