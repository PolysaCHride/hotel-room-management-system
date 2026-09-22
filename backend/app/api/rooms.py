from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.entities import Room, RoomType
from app.schemas.room import AvailabilityOut, RoomOut, RoomTypeOut
from app.services.booking_service import count_free_rooms, parse_date
from typing import Optional

router = APIRouter(prefix="/rooms", tags=["客房"])


@router.get("/types", response_model=list[RoomTypeOut], summary="房型列表（公开，含空房数）")
def list_room_types(db: Session = Depends(get_db)):
    types = db.scalars(select(RoomType)).all()
    result = []
    for t in types:
        item = RoomTypeOut.model_validate(t)
        item.room_count = len(t.rooms)
        item.free_count = sum(1 for r in t.rooms if r.status == "available")
        result.append(item)
    return result


@router.get("", response_model=list[RoomOut], summary="房间列表（公开）")
def list_rooms(
    type_id: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(Room).join(RoomType)
    if type_id:
        query = query.filter(Room.type_id == type_id)
    if status:
        query = query.filter(Room.status == status)
    rooms = query.order_by(Room.room_number).all()
    result = []
    for r in rooms:
        item = RoomOut.model_validate(r)
        item.type_name = r.room_type.name
        item.price = float(r.room_type.price)
        result.append(item)
    return result


@router.get("/availability", response_model=AvailabilityOut, summary="查询日期段内某房型可订数量（公开）")
def availability(room_type_id: int, check_in_date: str, check_out_date: str, db: Session = Depends(get_db)):
    ci = parse_date(check_in_date, "入住日期")
    co = parse_date(check_out_date, "离店日期")
    if co <= ci:
        raise HTTPException(400, "离店日期必须晚于入住日期")
    room_type = db.get(RoomType, room_type_id)
    if not room_type:
        raise HTTPException(404, "房型不存在")
    total = db.query(Room).filter(Room.type_id == room_type_id).count()
    free = count_free_rooms(db, room_type_id, ci, co)
    return AvailabilityOut(room_type_id=room_type_id, total_rooms=total, available=free)
