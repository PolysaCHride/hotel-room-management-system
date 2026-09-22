from datetime import date
from pydantic import BaseModel
from typing import Optional


class RoomTypeOut(BaseModel):
    id: int
    name: str
    price: float
    capacity: int
    description: str
    room_count: int = 0
    free_count: int = 0

    model_config = {"from_attributes": True}


class RoomTypeUpdate(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = None
    capacity: Optional[int] = None
    description: Optional[str] = None


class RoomOut(BaseModel):
    id: int
    room_number: str
    type_id: int
    type_name: str = ""
    price: float = 0
    floor: int
    status: str
    note: str

    model_config = {"from_attributes": True}


class RoomStatusUpdate(BaseModel):
    status: str
    note: Optional[str] = None


class AvailabilityQuery(BaseModel):
    room_type_id: int
    check_in_date: str
    check_out_date: str


class AvailabilityOut(BaseModel):
    room_type_id: int
    total_rooms: int
    available: int
