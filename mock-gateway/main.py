"""模拟支付网关：独立服务，模拟真实第三方支付的收银台、支付单与异步回调。

对接方式（与真实支付网关一致的交互模型）：
1. 商户服务端带签名调用 POST /api/create 创建支付交易，得到收银台地址；
2. 用户浏览器打开收银台 GET /pay/{txn_no}，选择支付渠道并确认支付结果；
3. 网关受理结果后，服务器间 POST 商户的 notify_url（带签名，商户验签后入账）；
4. 商户可随时 GET /api/query 查询交易状态做补偿对账；POST /api/refund 模拟退款。

收银台提供「付款成功 / 付款失败 / 取消支付」三个结果按钮，模拟真实网关的支付结果。
"""
import hashlib
import hmac
import os
import random
import time
from datetime import datetime
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy import String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

SECRET = os.getenv("PAY_SECRET", "demo-pay-secret-change-me")
MERCHANT_NAMES = {"hotel": "宾馆客房管理系统"}
# 收银台对外路径前缀（经 Nginx /gateway/ 反代时去前缀，此处用于页面内资源引用）
PUBLIC_PREFIX = os.getenv("PUBLIC_PREFIX", "/gateway")
DATA_DIR = Path(os.getenv("DATA_DIR", Path(__file__).parent / "data"))

engine = create_engine(
    f"sqlite:///{(DATA_DIR / 'gateway.db').as_posix()}",
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    txn_no: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    merchant_id: Mapped[str] = mapped_column(String(30))
    pay_no: Mapped[str] = mapped_column(String(40), index=True)
    amount: Mapped[float] = mapped_column()
    channel: Mapped[str] = mapped_column(String(20), default="")
    status: Mapped[str] = mapped_column(String(20), default="created")  # created/paid/failed/cancelled/refunded
    notify_url: Mapped[str] = mapped_column(String(300), default="")
    return_url: Mapped[str] = mapped_column(String(300), default="")
    created_at: Mapped[str] = mapped_column(String(30), default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    completed_at: Mapped[str] = mapped_column(String(30), default="")


def init_db():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)


def make_sign(params: dict) -> str:
    """与商户端约定一致的签名：参数按 key 排序拼接 k=v&... 后做 HMAC-SHA256。"""
    items = "&".join(f"{k}={params[k]}" for k in sorted(params))
    return hmac.new(SECRET.encode(), items.encode(), hashlib.sha256).hexdigest()


def verify_sign(params: dict, sign: str) -> bool:
    return hmac.compare_digest(make_sign(params), sign or "")


def gen_no(prefix: str) -> str:
    return f"{prefix}{datetime.now().strftime('%Y%m%d%H%M%S')}{random.randint(1000, 9999)}"


def notify_merchant(txn: Transaction):
    """服务器间异步通知商户（真实网关的关键机制），失败重试一次。"""
    if not txn.notify_url:
        return
    params = {
        "txn_no": txn.txn_no,
        "pay_no": txn.pay_no,
        "status": txn.status,
        "channel": txn.channel,
        "amount": f"{txn.amount:.2f}",
    }
    params["sign"] = make_sign(params)
    for _ in range(2):
        try:
            with httpx.Client(timeout=5) as client:
                resp = client.post(txn.notify_url, json=params)
            if resp.status_code == 200:
                return
        except Exception:
            time.sleep(0.5)


app = FastAPI(title="模拟支付网关（Mock Payment Gateway）", version="1.0.0")


class CreateRequest(BaseModel):
    merchant_id: str
    pay_no: str
    amount: str          # 两位小数字符串，避免浮点误差
    notify_url: str
    return_url: str
    sign: str


class SubmitRequest(BaseModel):
    result: str          # success / failed / cancel
    channel: str = ""


class RefundRequest(BaseModel):
    txn_no: str
    sign: str


@app.on_event("startup")
def on_startup():
    init_db()


@app.post("/api/create", summary="商户创建支付交易")
def create_payment(data: CreateRequest):
    if data.merchant_id not in MERCHANT_NAMES:
        raise HTTPException(400, "未知商户号")
    sign_params = {
        "merchant_id": data.merchant_id, "pay_no": data.pay_no,
        "amount": data.amount, "notify_url": data.notify_url, "return_url": data.return_url,
    }
    if not verify_sign(sign_params, data.sign):
        raise HTTPException(401, "签名校验失败")
    db = SessionLocal()
    try:
        # 同一商户支付单号幂等：已存在则直接返回原交易
        txn = db.scalar(select(Transaction).where(Transaction.pay_no == data.pay_no,
                                                  Transaction.merchant_id == data.merchant_id))
        if not txn:
            txn = Transaction(
                txn_no=gen_no("TXN"), merchant_id=data.merchant_id, pay_no=data.pay_no,
                amount=float(data.amount), notify_url=data.notify_url, return_url=data.return_url,
            )
            db.add(txn)
            db.commit()
            db.refresh(txn)
        return {"txn_no": txn.txn_no, "status": txn.status, "cashier_path": f"/pay/{txn.txn_no}"}
    finally:
        db.close()


@app.get("/api/query", summary="商户查询交易状态（补偿对账）")
def query(txn_no: str):
    db = SessionLocal()
    try:
        txn = db.scalar(select(Transaction).where(Transaction.txn_no == txn_no))
        if not txn:
            raise HTTPException(404, "交易不存在")
        return {"txn_no": txn.txn_no, "pay_no": txn.pay_no, "status": txn.status,
                "amount": f"{txn.amount:.2f}", "channel": txn.channel}
    finally:
        db.close()


@app.post("/api/refund", summary="商户发起模拟退款")
def refund(data: RefundRequest):
    sign_params = {"txn_no": data.txn_no}
    if not verify_sign(sign_params, data.sign):
        raise HTTPException(401, "签名校验失败")
    db = SessionLocal()
    try:
        txn = db.scalar(select(Transaction).where(Transaction.txn_no == data.txn_no))
        if not txn:
            raise HTTPException(404, "交易不存在")
        if txn.status != "paid":
            raise HTTPException(409, f"仅支付成功的交易可退款（当前 {txn.status}）")
        txn.status = "refunded"
        txn.completed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        db.commit()
        return {"txn_no": txn.txn_no, "status": txn.status}
    finally:
        db.close()


@app.post("/api/submit/{txn_no}", summary="收银台受理支付结果")
def submit(txn_no: str, data: SubmitRequest):
    status_map = {"success": "paid", "failed": "failed", "cancel": "cancelled"}
    if data.result not in status_map:
        raise HTTPException(400, "非法的支付结果")
    db = SessionLocal()
    try:
        txn = db.scalar(select(Transaction).where(Transaction.txn_no == txn_no))
        if not txn:
            raise HTTPException(404, "交易不存在")
        if txn.status != "created":
            return {"txn_no": txn.txn_no, "status": txn.status, "redirect": txn.return_url}
        txn.status = status_map[data.result]
        txn.channel = data.channel or txn.channel
        txn.completed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        db.commit()
        notify_merchant(txn)
        return {"txn_no": txn.txn_no, "status": txn.status, "redirect": txn.return_url}
    finally:
        db.close()


CASHIER_PAGE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>模拟支付收银台</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; font-family: 'PingFang SC','Microsoft YaHei',sans-serif; }}
  body {{ min-height: 100vh; display: flex; align-items: center; justify-content: center; background: #f0f2f5; }}
  .cashier {{ width: 420px; max-width: 92vw; background: #fff; border-radius: 12px; box-shadow: 0 8px 30px rgba(0,0,0,.12); overflow: hidden; }}
  .head {{ padding: 18px 24px; background: #1677ff; color: #fff; display: flex; justify-content: space-between; align-items: center; }}
  @media (max-width: 768px) {{
    .head {{ padding: 14px 16px; }}
    .body {{ padding: 18px 16px; }}
  }}
  .head .title {{ font-size: 16px; font-weight: 600; }}
  .head .sandbox {{ font-size: 11px; border: 1px solid rgba(255,255,255,.6); border-radius: 4px; padding: 2px 6px; }}
  .body {{ padding: 24px; }}
  .merchant {{ color: #666; font-size: 13px; }}
  .amount {{ margin: 14px 0 6px; }}
  .amount .rmb {{ font-size: 22px; color: #fa541c; vertical-align: top; }}
  .amount .num {{ font-size: 40px; font-weight: 700; color: #fa541c; }}
  .payno {{ color: #999; font-size: 12px; margin-bottom: 18px; }}
  .label {{ font-size: 13px; color: #666; margin-bottom: 8px; }}
  .channels {{ display: flex; gap: 10px; margin-bottom: 22px; }}
  .channel {{ flex: 1; border: 1.5px solid #e5e6eb; border-radius: 8px; padding: 10px 0; text-align: center;
              cursor: pointer; font-size: 14px; color: #333; transition: all .15s; }}
  .channel .ico {{ display: block; font-size: 20px; margin-bottom: 4px; }}
  .channel.alipay.active {{ border-color: #1677ff; color: #1677ff; background: #f0f7ff; }}
  .channel.wechat.active {{ border-color: #07c160; color: #07c160; background: #f0fff5; }}
  .btns {{ display: flex; flex-direction: column; gap: 10px; }}
  .btn {{ border: none; border-radius: 8px; padding: 12px 0; font-size: 15px; cursor: pointer; color: #fff; }}
  .btn:disabled {{ opacity: .5; cursor: not-allowed; }}
  .btn.ok {{ background: #07c160; }}
  .btn.fail {{ background: #ff4d4f; }}
  .btn.cancel {{ background: #909399; }}
  .result {{ text-align: center; padding: 8px 0 2px; font-size: 14px; }}
  .result.paid {{ color: #07c160; }}
  .result.failed {{ color: #ff4d4f; }}
  .result.cancelled {{ color: #909399; }}
  .foot {{ text-align: center; color: #bbb; font-size: 11px; padding: 0 0 14px; }}
</style>
</head>
<body>
  <div class="cashier">
    <div class="head">
      <span class="title">{merchant_name} · 收银台</span>
      <span class="sandbox">模拟环境</span>
    </div>
    <div class="body">
      <div class="merchant">商户：{merchant_name}</div>
      <div class="amount"><span class="rmb">¥</span><span class="num">{amount}</span></div>
      <div class="payno">商户订单号：{pay_no}&nbsp;&nbsp;|&nbsp;&nbsp;交易号：{txn_no}</div>
      <div class="label">选择支付方式</div>
      <div class="channels">
        <div class="channel alipay active" data-ch="alipay" onclick="pick(this)"><span class="ico">🅰</span>支付宝</div>
        <div class="channel wechat" data-ch="wechat" onclick="pick(this)"><span class="ico">💬</span>微信支付</div>
      </div>
      <div class="btns">
        <button class="btn ok" onclick="pay('success')">✓ 付款成功</button>
        <button class="btn fail" onclick="pay('failed')">✗ 付款失败</button>
        <button class="btn cancel" onclick="pay('cancel')">取消支付</button>
      </div>
      <div class="result" id="result"></div>
    </div>
    <div class="foot">模拟支付网关 · 仅用于教学演示，不产生真实资金交易</div>
  </div>
<script>
  var channel = 'alipay';
  function pick(el) {{
    document.querySelectorAll('.channel').forEach(function (c) {{ c.classList.remove('active'); }});
    el.classList.add('active');
    channel = el.dataset.ch;
  }}
  function pay(result) {{
    var btns = document.querySelectorAll('.btn');
    btns.forEach(function (b) {{ b.disabled = true; }});
    fetch('{prefix}/api/submit/{txn_no}', {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json' }},
      body: JSON.stringify({{ result: result, channel: channel }})
    }}).then(function (r) {{ return r.json(); }}).then(function (data) {{
      var box = document.getElementById('result');
      var textMap = {{ paid: '✓ 支付成功，正在跳转…', failed: '✗ 支付失败，正在返回…', cancelled: '已取消支付，正在返回…' }};
      box.textContent = textMap[data.status] || data.status;
      box.className = 'result ' + data.status;
      setTimeout(function () {{ window.location.href = data.redirect; }}, 1500);
    }}).catch(function () {{
      document.getElementById('result').textContent = '网络异常，请重试';
      btns.forEach(function (b) {{ b.disabled = false; }});
    }});
  }}
</script>
</body>
</html>"""


@app.get("/pay/{txn_no}", response_class=HTMLResponse, summary="收银台页面（用户浏览器打开）")
def cashier(txn_no: str):
    db = SessionLocal()
    try:
        txn = db.scalar(select(Transaction).where(Transaction.txn_no == txn_no))
        if not txn:
            return HTMLResponse("<h3 style='text-align:center;margin-top:80px'>交易不存在</h3>", status_code=404)
        merchant_name = MERCHANT_NAMES.get(txn.merchant_id, "商户")
        page = CASHIER_PAGE.format(
            merchant_name=merchant_name, amount=f"{txn.amount:.2f}", pay_no=txn.pay_no,
            txn_no=txn.txn_no, prefix=PUBLIC_PREFIX,
        )
        if txn.status != "created":
            # 已有终态的交易再次打开：展示状态
            text_map = {"paid": "✓ 该订单已支付", "failed": "✗ 该订单支付失败", "cancelled": "该订单已取消支付",
                        "refunded": "该订单已退款"}
            page = page.replace('<div class="btns">', f'<div class="result {txn.status}">{text_map.get(txn.status, "")}</div><div class="btns" style="display:none">')
        return HTMLResponse(page)
    finally:
        db.close()


@app.get("/api/health", tags=["系统"])
def health():
    return {"status": "ok", "service": "mock-payment-gateway"}
