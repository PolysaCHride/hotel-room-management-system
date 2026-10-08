"""支付业务逻辑：创建支付单、网关回调处理（验签+幂等）、补偿查询、模拟退款。"""
import hashlib
import hmac
import random
from datetime import datetime
from typing import Optional

import httpx
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import config
from app.models.entities import Bill, Booking, Payment

GATEWAY = config.GATEWAY_BASE_URL


def make_sign(params: dict) -> str:
    """与网关约定一致的签名：参数按 key 排序拼接 k=v&... 后做 HMAC-SHA256。"""
    items = "&".join(f"{k}={params[k]}" for k in sorted(params))
    return hmac.new(config.PAY_SECRET.encode(), items.encode(), hashlib.sha256).hexdigest()


def verify_sign(params: dict, sign: str) -> bool:
    return hmac.compare_digest(make_sign(params), sign or "")


def gen_pay_no() -> str:
    return f"PAY{datetime.now().strftime('%Y%m%d%H%M%S')}{random.randint(1000, 9999)}"


def _gateway_create(db: Session, payment: Payment) -> str:
    """调用网关创建支付交易，返回收银台地址。"""
    params = {
        "merchant_id": config.PAY_MERCHANT_ID,
        "pay_no": payment.pay_no,
        "amount": f"{float(payment.amount):.2f}",
        "notify_url": f"{config.NOTIFY_BASE_URL}/api/payment/notify",
        "return_url": f"/customer/pay-result?pay_no={payment.pay_no}",
    }
    params["sign"] = make_sign({k: params[k] for k in ("merchant_id", "pay_no", "amount", "notify_url", "return_url")})
    try:
        resp = httpx.post(f"{GATEWAY}/api/create", json=params, timeout=10)
    except httpx.HTTPError:
        raise HTTPException(502, "支付网关不可用，请稍后重试")
    if resp.status_code != 200:
        detail = resp.json().get("detail", "创建支付失败") if resp.headers.get("content-type", "").startswith("application/json") else "创建支付失败"
        raise HTTPException(resp.status_code, f"支付网关返回错误：{detail}")
    data = resp.json()
    payment.gateway_txn_no = data["txn_no"]
    return f"{config.GATEWAY_PUBLIC_PREFIX}{data['cashier_path']}"


def create_payment(db: Session, *, operator_id: int, is_staff: bool, biz_type: str, biz_id: int, channel: str = "") -> tuple:
    """创建支付单；返回 (Payment, cashier_url)。"""
    if biz_type == "booking":
        booking = db.get(Booking, biz_id)
        if not booking:
            raise HTTPException(404, "预订不存在")
        if not is_staff and booking.customer_id != operator_id:
            raise HTTPException(403, "无权为该预订支付")
        if booking.status != config.BOOKING_PENDING:
            raise HTTPException(409, "仅待到店的预订可以在线支付")
        if booking.pay_status == "paid":
            raise HTTPException(409, "该预订已支付，请勿重复支付")
        # 预订在线支付收取定金（默认房费的 20%，比例可配），尾款退房时结算
        amount = round(float(booking.estimated_price) * config.PAY_DEPOSIT_RATE, 2)
        customer_id = booking.customer_id
        # 已有待支付的支付单：复用（收银台可重复打开），避免重复下单
        pending = db.scalar(
            select(Payment).where(Payment.biz_type == "booking", Payment.biz_id == biz_id,
                                  Payment.status == "pending").limit(1)
        )
        if pending:
            cashier_url = _gateway_create(db, pending)
            db.commit()
            return pending, cashier_url
    elif biz_type == "bill":
        if not is_staff:
            raise HTTPException(403, "仅前台服务员可以发起账单收款")
        bill = db.get(Bill, biz_id)
        if not bill:
            raise HTTPException(404, "账单不存在")
        if bill.is_paid:
            raise HTTPException(409, "该账单已支付")
        amount = float(bill.amount)
        customer_id = None
    else:
        raise HTTPException(400, "非法的支付对象类型")

    payment = Payment(
        pay_no=gen_pay_no(), biz_type=biz_type, biz_id=biz_id, customer_id=customer_id,
        amount=amount, channel=channel, status="pending",
    )
    db.add(payment)
    db.flush()
    cashier_url = _gateway_create(db, payment)
    db.commit()
    db.refresh(payment)
    return payment, cashier_url


def _apply_payment_success(db: Session, payment: Payment):
    payment.status = "success"
    payment.paid_at = datetime.now()
    if payment.biz_type == "booking":
        booking = db.get(Booking, payment.biz_id)
        if booking:
            booking.pay_status = "deposit_paid"
    elif payment.biz_type == "bill":
        bill = db.get(Bill, payment.biz_id)
        if bill:
            bill.is_paid = True
            bill.pay_via = "online"
            bill.pay_no = payment.pay_no


def handle_notify(db: Session, payload: dict) -> dict:
    """网关服务器间回调：验签 + 幂等更新。"""
    sign = payload.pop("sign", "")
    if not verify_sign(payload, sign):
        raise HTTPException(401, "回调签名校验失败")
    pay_no = payload.get("pay_no")
    status = payload.get("status")
    payment = db.scalar(select(Payment).where(Payment.pay_no == pay_no))
    if not payment:
        raise HTTPException(404, "支付单不存在")
    if payload.get("txn_no") and payment.gateway_txn_no and payload["txn_no"] != payment.gateway_txn_no:
        raise HTTPException(400, "交易号不匹配")
    # 幂等：终态回调直接确认
    if payment.status != "pending":
        return {"code": "SUCCESS", "msg": "重复通知已忽略", "pay_no": pay_no}
    if status == "paid":
        payment.channel = payload.get("channel") or payment.channel
        _apply_payment_success(db, payment)
    elif status in ("failed", "cancelled"):
        payment.status = "failed" if status == "failed" else "cancelled"
    else:
        return {"code": "SUCCESS", "msg": "状态无需处理", "pay_no": pay_no}
    db.commit()
    return {"code": "SUCCESS", "pay_no": pay_no, "status": payment.status}


def sync_payment_status(db: Session, payment: Payment) -> Payment:
    """补偿查询：支付单仍为 pending 时，主动向网关查询交易状态并同步。"""
    if payment.status != "pending" or not payment.gateway_txn_no:
        return payment
    try:
        resp = httpx.get(f"{GATEWAY}/api/query", params={"txn_no": payment.gateway_txn_no}, timeout=5)
        if resp.status_code != 200:
            return payment
        data = resp.json()
    except httpx.HTTPError:
        return payment
    if data["status"] == "paid":
        payment.channel = data.get("channel") or payment.channel
        _apply_payment_success(db, payment)
    elif data["status"] in ("failed", "cancelled"):
        payment.status = "failed" if data["status"] == "failed" else "cancelled"
    elif data["status"] == "refunded":
        payment.status = "refunded"
    db.commit()
    db.refresh(payment)
    return payment


def refund_payment(db: Session, payment: Payment) -> Payment:
    """调用网关模拟退款（仅支付成功的支付单）；无网关交易号的支付单（离线/种子数据）直接本地标记退款。"""
    if payment.status != "success":
        raise HTTPException(409, f"仅支付成功的支付单可退款（当前 {payment.status}）")
    if payment.gateway_txn_no:
        params = {"txn_no": payment.gateway_txn_no}
        params["sign"] = make_sign(params)
        try:
            resp = httpx.post(f"{GATEWAY}/api/refund", json=params, timeout=10)
        except httpx.HTTPError:
            raise HTTPException(502, "支付网关不可用，退款失败")
        if resp.status_code != 200:
            detail = resp.json().get("detail", "退款失败")
            raise HTTPException(resp.status_code, f"支付网关返回错误：{detail}")
    payment.status = "refunded"
    db.commit()
    db.refresh(payment)
    return payment


def get_paid_booking_payment(db: Session, booking_id: int) -> Optional[Payment]:
    return db.scalar(
        select(Payment).where(Payment.biz_type == "booking", Payment.biz_id == booking_id,
                              Payment.status == "success").limit(1)
    )
