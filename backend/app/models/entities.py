from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core import config
from app.db.database import Base
from typing import Optional


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(200))
    real_name: Mapped[str] = mapped_column(String(50), default="")
    phone: Mapped[str] = mapped_column(String(20), default="")
    role: Mapped[str] = mapped_column(String(20), default=config.ROLE_CUSTOMER)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    bookings: Mapped[list["Booking"]] = relationship(back_populates="customer")


class RoomType(Base):
    __tablename__ = "room_types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    price: Mapped[float] = mapped_column(Numeric(10, 2))
    capacity: Mapped[int] = mapped_column(Integer, default=2)
    description: Mapped[str] = mapped_column(Text, default="")

    rooms: Mapped[list["Room"]] = relationship(back_populates="room_type")
    bookings: Mapped[list["Booking"]] = relationship(back_populates="room_type")


class Room(Base):
    __tablename__ = "rooms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    room_number: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    type_id: Mapped[int] = mapped_column(ForeignKey("room_types.id"))
    floor: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(20), default=config.ROOM_AVAILABLE)
    note: Mapped[str] = mapped_column(String(200), default="")

    room_type: Mapped["RoomType"] = relationship(back_populates="rooms")
    checkin_records: Mapped[list["CheckInRecord"]] = relationship(back_populates="room")


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    room_type_id: Mapped[int] = mapped_column(ForeignKey("room_types.id"))
    check_in_date: Mapped[str] = mapped_column(String(10))   # YYYY-MM-DD
    check_out_date: Mapped[str] = mapped_column(String(10))  # YYYY-MM-DD
    guests: Mapped[int] = mapped_column(Integer, default=1)
    estimated_price: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    status: Mapped[str] = mapped_column(String(20), default=config.BOOKING_PENDING)
    remark: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    customer: Mapped["User"] = relationship(back_populates="bookings")
    room_type: Mapped["RoomType"] = relationship(back_populates="bookings")
    checkin_record: Mapped["CheckInRecord"] = relationship(back_populates="booking", uselist=False)


class CheckInRecord(Base):
    __tablename__ = "checkin_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    booking_id: Mapped[Optional[int]] = mapped_column(ForeignKey("bookings.id"), nullable=True)
    customer_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    guest_name: Mapped[str] = mapped_column(String(50), default="")
    guest_phone: Mapped[str] = mapped_column(String(20), default="")
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id"))
    operator_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    check_in_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    expected_check_out: Mapped[str] = mapped_column(String(10))  # YYYY-MM-DD
    check_out_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    booking: Mapped["Booking"] = relationship(back_populates="checkin_record")
    room: Mapped["Room"] = relationship(back_populates="checkin_records")
    bills: Mapped[list["Bill"]] = relationship(back_populates="checkin_record")


class Bill(Base):
    __tablename__ = "bills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    checkin_id: Mapped[int] = mapped_column(ForeignKey("checkin_records.id"))
    room_number: Mapped[str] = mapped_column(String(20))
    days: Mapped[int] = mapped_column(Integer, default=1)
    room_price: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    amount: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    is_paid: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    checkin_record: Mapped["CheckInRecord"] = relationship(back_populates="bills")
