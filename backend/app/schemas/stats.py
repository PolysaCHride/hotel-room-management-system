from pydantic import BaseModel


class StatsOut(BaseModel):
    total_rooms: int
    free_rooms: int
    occupied_rooms: int
    booked_rooms: int
    maintenance_rooms: int
    occupancy_rate: float          # 入住率 %
    today_arrivals: int            # 今日到店预订数
    today_checkins: int            # 今日实际入住数
    active_stays: int              # 当前在住数
    revenue_today: float           # 今日营收
    revenue_total: float           # 累计营收
    revenue_by_day: list[dict]     # [{date, amount}]
    booking_status_count: dict     # {pending, checked_in, completed, cancelled}
