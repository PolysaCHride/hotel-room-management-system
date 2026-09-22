from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_serializer


class BookingCreate(BaseModel):
    room_type_id: int
    check_in_date: str   # YYYY-MM-DD
    check_out_date: str  # YYYY-MM-DD
    guests: int = 1
    remark: str = ""


class RenewalRequest(BaseModel):
    new_check_out_date: str  # YYYY-MM-DD


class BookingOut(BaseModel):
    id: int
    customer_id: int
    customer_name: str = ""
    room_type_id: int
    room_type_name: str = ""
    room_id: Optional[int] = None
    room_number: str = ""
    check_in_date: str
    check_out_date: str
    guests: int
    estimated_price: float
    status: str
    remark: str
    requested_check_out: Optional[str] = None
    renewal_status: str = "none"
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

    @field_serializer("created_at")
    def fmt_created(self, v: Optional[datetime]) -> str:
        return v.strftime("%Y-%m-%d %H:%M") if v else ""
