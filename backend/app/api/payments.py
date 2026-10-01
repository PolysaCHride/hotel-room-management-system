from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core import config
from app.db.database import get_db
from app.models.entities import Booking, User
from app.services.payment_service import (
    create_payment,
    handle_notify,
    make_sign,
    sync_payment_status,
)

router = APIRouter(tags=["支付"])


class PaymentCreate(BaseModel):
    biz_type: str        # booking / bill
    biz_id: int
    channel: str = ""    # alipay / wechat（收银台内也可再选）


@router.post("/payments/create", summary="创建支付单，返回收银台地址")
def create(payment_data: PaymentCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    is_staff = user.role in (config.ROLE_RECEPTIONIST, config.ROLE_ADMIN)
    payment, cashier_url = create_payment(
        db, operator_id=user.id, is_staff=is_staff,
        biz_type=payment_data.biz_type, biz_id=payment_data.biz_id,
        channel=payment_data.channel,
    )
    return {
        "pay_no": payment.pay_no,
        "amount": float(payment.amount),
        "status": payment.status,
        "cashier_url": cashier_url,
    }


@router.get("/payments/{pay_no}", summary="查询支付单状态（含网关补偿查询）")
def payment_status(pay_no: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.models.entities import Payment

    payment = db.query(Payment).filter(Payment.pay_no == pay_no).first()
    if not payment:
        raise HTTPException(404, "支付单不存在")
    is_staff = user.role in (config.ROLE_RECEPTIONIST, config.ROLE_ADMIN)
    if not is_staff and payment.customer_id and payment.customer_id != user.id:
        raise HTTPException(403, "无权查看该支付单")
    payment = sync_payment_status(db, payment)
    return {
        "pay_no": payment.pay_no,
        "biz_type": payment.biz_type,
        "biz_id": payment.biz_id,
        "amount": float(payment.amount),
        "channel": payment.channel,
        "status": payment.status,
        "paid_at": payment.paid_at.strftime("%Y-%m-%d %H:%M:%S") if payment.paid_at else None,
    }


@router.post("/payment/notify", summary="网关异步回调（服务器间调用，签名鉴权）")
def notify(request_data: dict, db: Session = Depends(get_db)):
    return handle_notify(db, request_data)
