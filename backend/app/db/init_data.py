"""演示种子数据：首次启动（数据库为空）时自动初始化，保证界面一打开就有数据可看。"""
import random
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import config
from app.core.security import hash_password
from app.models.entities import Bill, Booking, CheckInRecord, Room, RoomType, User

ROOM_TYPES = [
    ("单人间", 128, 1, "一张单人床，适合独自出行的客人，配备空调、免费WiFi、独立卫浴。"),
    ("标准间", 198, 2, "两张单人床，宽敞明亮，配备空调、电视、免费WiFi、独立卫浴。"),
    ("豪华大床房", 288, 2, "一张两米大床，装修精致，配备智能电视、冰箱、免费WiFi、独立卫浴。"),
    ("行政套房", 488, 3, "独立的客厅与卧室，商务出行首选，配备办公桌、会客区、迷你吧。"),
]

# 每种房型的房间数量与楼层分布
ROOM_PLAN = [
    (0, 6, 2),   # 单人间 6 间，2 层
    (1, 8, 3),   # 标准间 8 间，3 层
    (2, 4, 5),   # 豪华大床房 4 间，5 层
    (3, 2, 6),   # 行政套房 2 间，6 层
]

DEMO_USERS = [
    ("admin", "admin123", "系统管理员", "13800000001", config.ROLE_ADMIN),
    ("reception", "123456", "李晓敏（前台）", "13800000002", config.ROLE_RECEPTIONIST),
    ("guest", "123456", "王客人", "13800000003", config.ROLE_CUSTOMER),
]

EXTRA_GUESTS = [
    ("zhangsan", "张三", "13911112222"),
    ("lisi", "李四", "13933334444"),
    ("wangwu", "王五", "13955556666"),
    ("zhaoliu", "赵六", "13977778888"),
]

NAMES = ["陈建国", "刘婷婷", "杨帆", "黄丽华", "周天宇", "吴秀英", "徐志强", "孙雅静"]


def init_database(db: Session):
    if db.scalar(select(User).limit(1)):
        return  # 已有数据，不重复初始化

    # 用户
    for username, password, real_name, phone, role in DEMO_USERS:
        db.add(User(username=username, password_hash=hash_password(password),
                    real_name=real_name, phone=phone, role=role))

    guest_users = []
    for username, real_name, phone in EXTRA_GUESTS:
        u = User(username=username, password_hash=hash_password("123456"),
                 real_name=real_name, phone=phone, role=config.ROLE_CUSTOMER)
        db.add(u)
        guest_users.append(u)

    # 房型与房间
    types = []
    for name, price, capacity, desc in ROOM_TYPES:
        types.append(db.query(RoomType).filter_by(name=name).one_or_none()
                     or RoomType(name=name, price=price, capacity=capacity, description=desc))
        db.add(types[-1])
    db.flush()

    rooms = []
    for type_idx, count, floor in ROOM_PLAN:
        rt = types[type_idx]
        for i in range(1, count + 1):
            room = Room(room_number=f"{floor}0{i}", type_id=rt.id, floor=floor)
            db.add(room)
            rooms.append(room)
    db.flush()

    today = datetime.now().date()
    reception = db.scalar(select(User).where(User.username == "reception"))
    main_guest = db.scalar(select(User).where(User.username == "guest"))

    # 历史账单（近 7 天，供统计图表展示）
    for i in range(7, 0, -1):
        check_out_day = today - timedelta(days=i)
        room = random.choice(rooms)
        rt = db.get(RoomType, room.type_id)
        days = random.randint(1, 3)
        checkin_time = datetime.combine(check_out_day - timedelta(days=days), datetime.min.time()).replace(hour=14)
        record = CheckInRecord(
            guest_name=random.choice(NAMES), guest_phone=f"137{random.randint(10000000, 99999999)}",
            room_id=room.id, operator_id=reception.id, check_in_time=checkin_time,
            expected_check_out=check_out_day.isoformat(), check_out_time=checkin_time + timedelta(days=days),
        )
        db.add(record)
        db.flush()
        db.add(Bill(checkin_id=record.id, room_number=room.room_number, days=days,
                    room_price=float(rt.price), amount=float(rt.price) * days, is_paid=True,
                    created_at=checkin_time + timedelta(days=days)))
    db.flush()

    # 在住记录（3 间正在住的房）
    occupied_rooms = rooms[8:11]
    for idx, room in enumerate(occupied_rooms):
        room.status = config.ROOM_OCCUPIED
        rt = db.get(RoomType, room.type_id)
        record = CheckInRecord(
            guest_name=EXTRA_GUESTS[idx][1], guest_phone=EXTRA_GUESTS[idx][2],
            customer_id=guest_users[idx].id, room_id=room.id, operator_id=reception.id,
            check_in_time=datetime.combine(today - timedelta(days=idx), datetime.min.time()).replace(hour=14),
            expected_check_out=(today + timedelta(days=idx + 1)).isoformat(),
        )
        db.add(record)
    db.flush()

    # 一间维修中的房
    rooms[-1].status = config.ROOM_MAINTENANCE
    rooms[-1].note = "空调检修中"

    # 预订：guest 今天到店（演示前台办理入住）、未来预订、在住关联预订、历史完成预订
    # 预订即分房：每条预订创建时锁定具体房间；已到入住日的房间标记为被预订
    def free_room_of(type_id: int, ci: str, co: str, exclude_room_ids=()):
        """按房间冲突检测挑选一间可分配的房间。"""
        for room in [r for r in rooms if r.type_id == type_id and r.id not in exclude_room_ids
                     and r.status in (config.ROOM_AVAILABLE, config.ROOM_BOOKED)]:
            conflict = any(
                b.room_id == room.id and b.status in (config.BOOKING_PENDING, config.BOOKING_CHECKED_IN)
                and b.check_in_date < co and b.check_out_date > ci
                for b in db.query(Booking).all()
            )
            if not conflict:
                return room
        return None

    std = types[1]
    guest_room = free_room_of(std.id, today.isoformat(), (today + timedelta(days=2)).isoformat())
    if guest_room:
        guest_room.status = config.ROOM_BOOKED  # 已到入住日：标记为被预订（演示功能5）
    db.add(Booking(customer_id=main_guest.id, room_type_id=std.id, room_id=guest_room.id if guest_room else None,
                   check_in_date=today.isoformat(), check_out_date=(today + timedelta(days=2)).isoformat(),
                   guests=2, estimated_price=float(std.price) * 2,
                   remark="靠电梯近一点的房间", status=config.BOOKING_PENDING))

    lux = types[2]
    lux_room = free_room_of(lux.id, (today + timedelta(days=1)).isoformat(), (today + timedelta(days=3)).isoformat())
    db.add(Booking(customer_id=guest_users[3].id, room_type_id=lux.id, room_id=lux_room.id if lux_room else None,
                   check_in_date=(today + timedelta(days=1)).isoformat(),
                   check_out_date=(today + timedelta(days=3)).isoformat(),
                   guests=2, estimated_price=float(lux.price) * 2, status=config.BOOKING_PENDING))

    # 已入住的预订（关联在住记录）
    pending_records = db.query(CheckInRecord).filter(CheckInRecord.check_out_time.is_(None)).all()
    checked_in_bookings = []
    for record in pending_records:
        rt = db.get(RoomType, record.room.type_id)
        nights = (datetime.fromisoformat(record.expected_check_out).date()
                  - record.check_in_time.date()).days or 1
        booking = Booking(customer_id=record.customer_id, room_type_id=rt.id, room_id=record.room.id,
                          check_in_date=record.check_in_time.date().isoformat(),
                          check_out_date=record.expected_check_out,
                          guests=1, estimated_price=float(rt.price) * nights,
                          status=config.BOOKING_CHECKED_IN)
        db.add(booking)
        db.flush()
        record.booking_id = booking.id
        checked_in_bookings.append(booking)

    # 一条已完成的历史预订
    done_room = free_room_of(types[0].id, (today - timedelta(days=10)).isoformat(), (today - timedelta(days=8)).isoformat())
    db.add(Booking(customer_id=main_guest.id, room_type_id=types[0].id, room_id=done_room.id if done_room else None,
                   check_in_date=(today - timedelta(days=10)).isoformat(),
                   check_out_date=(today - timedelta(days=8)).isoformat(),
                   guests=1, estimated_price=float(types[0].price) * 2,
                   status=config.BOOKING_COMPLETED))

    # 一条待确认的续订申请（演示功能2：顾客申请 → 服务员确认）
    if checked_in_bookings:
        sample = checked_in_bookings[0]
        sample.requested_check_out = (datetime.fromisoformat(sample.check_out_date).date()
                                      + timedelta(days=1)).isoformat()
        sample.renewal_status = "pending"

    db.commit()
