"""超时未退房自动退房：扫描超期在住记录，由系统自动办理退房并生成待支付账单。

超时标准（可在环境变量中调整）：预计离店日当天的退房时限（默认 12:00，酒店惯例中午退房）
再宽限 GRACE_HOURS 小时后仍未办理退房，即视为超期。
"""
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session, joinedload

from app.core import config
from app.models.entities import Booking, CheckInRecord
from app.services.stay_service import do_check_out, refresh_room_status_after_release

# 最近一次扫描的结果（内存态，供管理端查看）
last_run_info = {"time": None, "count": 0, "records": []}
last_noshow_info = {"time": None, "count": 0, "records": []}


def is_overdue(record: CheckInRecord, now: datetime) -> bool:
    """预计离店日退房时限 + 宽限小时数 是否已过。"""
    try:
        expected = datetime.fromisoformat(record.expected_check_out)
    except (ValueError, TypeError):
        return False
    deadline = expected.replace(hour=config.AUTO_CHECKOUT_CHECKOUT_HOUR, minute=0, second=0, microsecond=0)
    deadline += timedelta(hours=config.AUTO_CHECKOUT_GRACE_HOURS)
    return now > deadline


def list_overdue(db: Session, now: Optional[datetime] = None) -> list:
    """当前超期未退房的在住记录。"""
    now = now or datetime.now()
    records = (
        db.query(CheckInRecord)
        .options(joinedload(CheckInRecord.room))
        .filter(CheckInRecord.check_out_time.is_(None))
        .all()
    )
    return [r for r in records if is_overdue(r, now)]


def run_auto_checkout_scan(db: Session) -> list:
    """执行一次自动退房扫描，返回本次被自动退房的记录摘要。"""
    now = datetime.now()
    overdue = list_overdue(db, now)
    processed = []
    for record in overdue:
        room = record.room
        bill = do_check_out(db, record.id, auto=True)
        processed.append({
            "record_id": record.id,
            "guest_name": record.guest_name,
            "room_number": room.room_number if room else "",
            "days": bill.days,
            "amount": float(bill.amount),
            "bill_id": bill.id,
        })
    last_run_info.update({
        "time": now.strftime("%Y-%m-%d %H:%M:%S"),
        "count": len(processed),
        "records": processed,
    })
    return processed


# ==================== 未到店自动取消（No-Show） ====================

def noshow_deadline(check_in_date: str) -> datetime:
    """No-Show 截止时间：入住日整日结束（次日零点）+ 宽限小时数。"""
    ci = datetime.fromisoformat(check_in_date)
    return ci + timedelta(days=1, hours=config.AUTO_NOSHOW_GRACE_HOURS)


def is_noshow_due(booking: Booking, now: datetime) -> bool:
    """待到店预订是否已过 No-Show 截止时间（客人整日未到且已过宽限期）。"""
    try:
        return now > noshow_deadline(booking.check_in_date)
    except (ValueError, TypeError):
        return False


def list_noshow_pending(db: Session, now: Optional[datetime] = None) -> list:
    """当前已超期未到店、待系统自动取消的预订。"""
    now = now or datetime.now()
    bookings = (
        db.query(Booking)
        .options(joinedload(Booking.room), joinedload(Booking.customer))
        .filter(Booking.status == config.BOOKING_PENDING)
        .all()
    )
    return [b for b in bookings if is_noshow_due(b, now)]


def run_auto_noshow_scan(db: Session) -> list:
    """执行一次 No-Show 扫描：自动取消超期未到店的预订，释放房间，已支付的退款。"""
    from app.services.payment_service import get_paid_booking_payment, refund_payment

    now = datetime.now()
    due = list_noshow_pending(db, now)
    processed = []
    for booking in due:
        try:
            paid = get_paid_booking_payment(db, booking.id)
            refunded = False
            if paid:
                refund_payment(db, paid)
                booking.pay_status = "unpaid"
                refunded = True
            booking.status = config.BOOKING_NOSHOW
            booking.renewal_status = "none"
            booking.requested_check_out = None
            room = booking.room
            refresh_room_status_after_release(db, room)
            db.commit()
            processed.append({
                "booking_id": booking.id,
                "guest_name": booking.customer.real_name if booking.customer else "",
                "room_number": room.room_number if room else "",
                "check_in_date": booking.check_in_date,
                "check_out_date": booking.check_out_date,
                "refunded": refunded,
            })
        except Exception as e:
            # 单笔失败不影响批次内其他订单（如网关退款失败），下一轮扫描会重试
            db.rollback()
            print(f"[未到店取消] 订单 #{booking.id} 自动取消失败：{e}")
    last_noshow_info.update({
        "time": now.strftime("%Y-%m-%d %H:%M:%S"),
        "count": len(processed),
        "records": processed,
    })
    return processed


async def auto_checkout_loop():
    """后台定时任务：周期扫描超期未退房的在住记录 + 超期未到店的预订（在 lifespan 中启动）。"""
    import asyncio

    from starlette.concurrency import run_in_threadpool

    from app.db.database import SessionLocal

    # 启动后先稍等片刻，避开建表/种子数据阶段
    await asyncio.sleep(10)
    while True:
        try:
            db = SessionLocal()
            try:
                if config.AUTO_CHECKOUT_ENABLED:
                    processed = await run_in_threadpool(run_auto_checkout_scan, db)
                    for item in processed:
                        print(f"[自动退房] {item['room_number']} 房 {item['guest_name']} "
                              f"超期未退房，已自动退房并生成待支付账单 ¥{item['amount']}")
                if config.AUTO_NOSHOW_ENABLED:
                    noshow = await run_in_threadpool(run_auto_noshow_scan, db)
                    for item in noshow:
                        refund_note = "，已支付房费原路退款" if item["refunded"] else ""
                        print(f"[未到店取消] 订单 #{item['booking_id']} {item['guest_name']} "
                              f"{item['room_number']} 房（入住日 {item['check_in_date']}）"
                              f"超期未到店，已自动取消{refund_note}")
            finally:
                db.close()
        except Exception as e:  # 定时任务不允许因异常退出
            print(f"[自动任务] 扫描异常：{e}")
        await asyncio.sleep(config.AUTO_CHECKOUT_INTERVAL_SECONDS)
