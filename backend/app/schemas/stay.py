from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_serializer


class CheckInRequest(BaseModel):
    booking_id: Optional[int] = None  # 有值=预订入住；为空=散客直接开房
    room_id: Optional[int] = None     # 不指定则自动分配空闲房
    room_type_id: Optional[int] = None  # 散客开房指定房型（自动分配该房型的空闲房）
    guest_name: str = ""
    guest_phone: str = ""
    expected_check_out: str        # YYYY-MM-DD


def _fmt(v: Optional[datetime]) -> str:
    return v.strftime("%Y-%m-%d %H:%M") if v else ""


class CheckInOut(BaseModel):
    id: int
    booking_id: Optional[int]
    guest_name: str
    guest_phone: str
    room_id: int
    room_number: str = ""
    room_type_name: str = ""
    check_in_time: Optional[datetime] = None
    expected_check_out: str
    check_out_time: Optional[datetime] = None

    model_config = {"from_attributes": True}

    @field_serializer("check_in_time", "check_out_time")
    def fmt_time(self, v: Optional[datetime]) -> str:
        return _fmt(v)


class BillOut(BaseModel):
    id: int
    checkin_id: int
    room_number: str
    guest_name: str = ""
    days: int
    room_price: float
    amount: float
    is_paid: bool
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

    @field_serializer("created_at")
    def fmt_created(self, v: Optional[datetime]) -> str:
        return _fmt(v)
