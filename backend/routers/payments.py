"""Payment routes: Cashfree Orders API + JS SDK redirect for valet fees and tips."""
import logging
import uuid
import httpx
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import RedirectResponse, HTMLResponse

from config import (
    db, CASHFREE_CLIENT_ID, CASHFREE_CLIENT_SECRET,
    CASHFREE_BASE_URL, CASHFREE_API_VERSION, get_app_base_url, set_app_base_url,
)
from utils import get_current_user, send_whatsapp_message

router = APIRouter(prefix="/payments", tags=["payments"])
short_router = APIRouter(tags=["payments-short"])
logger = logging.getLogger(__name__)

# Cashfree JS SDK mode: 'production' for live, 'sandbox' for test
CASHFREE_JS_MODE = "production" if "sandbox" not in CASHFREE_BASE_URL else "sandbox"


def get_base_url(request: Request) -> str:
    """Deprecated synchronous helper. Use get_app_base_url() (async)."""
    forwarded_proto = request.headers.get("x-forwarded-proto", "https")
    forwarded_host = request.headers.get("x-forwarded-host") or request.headers.get("host", "")
    return f"{forwarded_proto}://{forwarded_host}"


async def create_payment_link(amount_inr: float, description: str, customer_phone: str, customer_name: str = "Customer", reference_id: str = "", notes: dict = None, base_url: str = None):
    """Create a Cashfree Order and return the checkout URL."""
    if not CASHFREE_CLIENT_ID or not CASHFREE_CLIENT_SECRET:
        logger.warning("Cashfree not configured")
        return None

    public_base = (base_url or await get_app_base_url()).rstrip("/")
    if not public_base:
        logger.error("No APP_BASE_URL configured; cannot generate payment short URL")
        return None

    try:
        order_id = reference_id or f"vg-{uuid.uuid4().hex[:12]}"
        customer_id = f"cust-{customer_phone.replace('+', '')[-10:]}"

        payload = {
            "order_id": order_id,
            "order_amount": float(amount_inr),
            "order_currency": "INR",
            "order_note": description,
            "customer_details": {
                "customer_id": customer_id,
                "customer_phone": customer_phone.replace("+", "")[-10:],
                "customer_name": customer_name or "Customer",
            },
            "order_meta": {
                "return_url": f"{public_base}/payment/success?order_id={order_id}",
                "notify_url": f"{public_base}/api/payments/webhook",
            },
            "order_tags": {str(k): str(v) for k, v in (notes or {}).items()},
        }

        headers = {
            "Content-Type": "application/json",
            "x-api-version": CASHFREE_API_VERSION,
            "x-client-id": CASHFREE_CLIENT_ID,
            "x-client-secret": CASHFREE_CLIENT_SECRET,
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{CASHFREE_BASE_URL}/orders",
                json=payload,
                headers=headers,
                timeout=15.0,
            )

        if resp.status_code >= 400:
            logger.error(f"Cashfree order error {resp.status_code}: {resp.text}")
            return None

        data = resp.json()
        session_id = data.get("payment_session_id", "")
        short_url = f"{public_base}/api/p/{order_id}"

        logger.info(f"Cashfree order created: {order_id} for Rs.{amount_inr}, short={short_url}")

        return {
            "link_id": order_id,
            "short_url": short_url,
            "amount": amount_inr,
            "status": data.get("order_status", "ACTIVE"),
            "cf_order_id": data.get("cf_order_id", ""),
            "session_id": session_id,
        }
    except Exception as e:
        logger.error(f"Cashfree order error: {e}")
        return None


@router.post("/create-fee-link")
async def create_fee_payment_link(vehicle_id: str, current_user: dict = Depends(get_current_user)):
    """Create a payment order for valet parking fee and send via WhatsApp."""
    vehicle = await db.vehicles.find_one({"id": vehicle_id}, {"_id": 0})
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    client_id = current_user.get("client_id")
    admin = await db.users.find_one(
        {"client_id": client_id, "role": "admin", "is_active": True},
        {"_id": 0, "valet_fee": 1, "client_name": 1}
    )
    valet_fee = admin.get("valet_fee", 0) if admin else 0
    client_name = admin.get("client_name", "Valet Guys") if admin else "Valet Guys"

    if valet_fee <= 0:
        raise HTTPException(status_code=400, detail="No valet fee configured for this client")

    result = await create_payment_link(
        amount_inr=valet_fee,
        description=f"Valet Parking Fee - {client_name}",
        customer_phone=vehicle.get("phone_number", ""),
        reference_id=f"fee-{uuid.uuid4().hex[:12]}",
        notes={"type": "valet_fee", "vehicle_id": vehicle_id, "client_name": client_name}
    )

    if not result:
        raise HTTPException(status_code=500, detail="Failed to create payment link")

    await db.payments.insert_one({
        "link_id": result["link_id"],
        "session_id": result.get("session_id", ""),
        "cf_order_id": result.get("cf_order_id", ""),
        "type": "valet_fee",
        "vehicle_id": vehicle_id,
        "customer_phone": vehicle.get("phone_number"),
        "amount": valet_fee,
        "status": "created",
        "short_url": result["short_url"],
        "client_id": client_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    msg = f"Valet Guys ({client_name}): Your valet parking fee is Rs.{valet_fee:.0f}. Pay here to get your car: {result['short_url']}"
    await send_whatsapp_message(vehicle.get("phone_number", ""), msg)

    return {"message": "Payment link sent", "short_url": result["short_url"], "amount": valet_fee}


@router.post("/create-tip-link")
async def create_tip_payment_link(vehicle_id: str, valet_id: str, amount: float = 0, current_user: dict = Depends(get_current_user)):
    """Create a tip payment order for the customer to tip the valet."""
    vehicle = await db.vehicles.find_one({"id": vehicle_id}, {"_id": 0})
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    valet = await db.users.find_one({"id": valet_id}, {"_id": 0, "name": 1, "client_name": 1})
    valet_name = valet.get("name", "your valet") if valet else "your valet"
    client_name = valet.get("client_name", "Valet Guys") if valet else "Valet Guys"

    tip_amount = amount if amount > 0 else 100

    result = await create_payment_link(
        amount_inr=tip_amount,
        description=f"Tip for {valet_name} - {client_name}",
        customer_phone=vehicle.get("phone_number", ""),
        customer_name="Customer",
        reference_id=f"tip-{uuid.uuid4().hex[:12]}",
        notes={"type": "tip", "vehicle_id": vehicle_id, "valet_id": valet_id, "valet_name": valet_name}
    )

    if not result:
        raise HTTPException(status_code=500, detail="Failed to create payment link")

    await db.payments.insert_one({
        "link_id": result["link_id"],
        "session_id": result.get("session_id", ""),
        "cf_order_id": result.get("cf_order_id", ""),
        "type": "tip",
        "vehicle_id": vehicle_id,
        "valet_id": valet_id,
        "customer_phone": vehicle.get("phone_number"),
        "amount": tip_amount,
        "status": "created",
        "short_url": result["short_url"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    return {"message": "Tip link created", "short_url": result["short_url"], "amount": tip_amount}


@router.get("/quick-tip/{token}/{amount}", response_class=HTMLResponse)
async def quick_tip_redirect(token: str, amount: int):
    """Customer tapped a tip-amount link. Look up the intent by token,
    create a Cashfree order for the chosen amount, and serve the JS-SDK
    payment page. No auth required."""
    intent = await db.tip_intents.find_one({"token": token}, {"_id": 0})
    if not intent:
        raise HTTPException(status_code=404, detail="Tip link not found or expired")

    if amount not in (25, 50, 100, 200, 500):
        raise HTTPException(status_code=400, detail="Invalid tip amount")

    # Check if a payment already exists for this token + amount (idempotent)
    existing = await db.payments.find_one(
        {"tip_token": token, "amount": amount, "status": {"$in": ["created", "paid"]}},
        {"_id": 0}
    )
    if existing and existing.get("link_id"):
        return await redirect_to_payment(existing["link_id"])

    result = await create_payment_link(
        amount_inr=amount,
        description=f"Tip for {intent['valet_name']} - {intent['client_name']}",
        customer_phone=intent['customer_phone'],
        customer_name="Customer",
        reference_id=f"tip-{token}-{amount}",
        notes={"type": "tip", "vehicle_id": intent['vehicle_id'], "valet_id": intent['valet_id']},
    )
    if not result:
        raise HTTPException(status_code=500, detail="Failed to create tip payment")

    await db.payments.insert_one({
        "link_id": result["link_id"],
        "session_id": result.get("session_id", ""),
        "cf_order_id": result.get("cf_order_id", ""),
        "type": "tip",
        "vehicle_id": intent['vehicle_id'],
        "valet_id": intent['valet_id'],
        "customer_phone": intent['customer_phone'],
        "amount": amount,
        "status": "created",
        "short_url": result["short_url"],
        "tip_token": token,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    return await redirect_to_payment(result["link_id"])


@router.post("/webhook")
async def cashfree_webhook(request: Request):
    """Handle Cashfree Orders API payment webhooks."""
    body = await request.body()

    import json
    try:
        payload = json.loads(body)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid payload")

    event_type = payload.get("type", "")
    logger.info(f"Cashfree webhook: {event_type}")

    if event_type in ("PAYMENT_SUCCESS_WEBHOOK", "PAYMENT_SUCCESS"):
        order_data = payload.get("data", {}).get("order", {})
        payment_data = payload.get("data", {}).get("payment", {})
        order_id = order_data.get("order_id", "")
        order_tags = order_data.get("order_tags", {}) or {}
        amount_paid = payment_data.get("payment_amount", 0)

        if order_id:
            await db.payments.update_one(
                {"link_id": order_id},
                {"$set": {
                    "status": "paid",
                    "paid_at": datetime.now(timezone.utc).isoformat(),
                    "amount_paid": float(amount_paid) if amount_paid else 0,
                }}
            )

            payment = await db.payments.find_one({"link_id": order_id}, {"_id": 0})
            payment_type = payment.get("type", "") if payment else order_tags.get("type", "")

            if payment_type == "valet_fee":
                vehicle_id = payment.get("vehicle_id", "") if payment else order_tags.get("vehicle_id", "")
                if vehicle_id:
                    ticket = await db.tickets.find_one(
                        {"vehicle_id": vehicle_id, "status": "pending_payment"},
                        {"_id": 0}
                    )
                    if ticket:
                        await db.tickets.update_one(
                            {"id": ticket["id"]},
                            {"$set": {"status": "open", "fee_paid": True, "fee_paid_at": datetime.now(timezone.utc).isoformat()}}
                        )
                        logger.info(f"Valet fee paid for vehicle {vehicle_id}")

            elif payment_type == "tip":
                valet_id = payment.get("valet_id", "") if payment else order_tags.get("valet_id", "")
                vehicle_id = payment.get("vehicle_id", "") if payment else order_tags.get("vehicle_id", "")
                tip_amount = float(amount_paid) if amount_paid else (payment.get("amount", 0) if payment else 0)
                if valet_id:
                    await db.tips.insert_one({
                        "valet_id": valet_id,
                        "vehicle_id": vehicle_id,
                        "amount": tip_amount,
                        "status": "paid",
                        "link_id": order_id,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    })
                    logger.info(f"Tip of Rs.{tip_amount} recorded for valet {valet_id}")

    return {"status": "ok"}


@router.get("/status/{order_id}")
async def get_payment_status(order_id: str, current_user: dict = Depends(get_current_user)):
    """Check payment status."""
    payment = await db.payments.find_one({"link_id": order_id}, {"_id": 0})
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    return {
        "link_id": payment.get("link_id"),
        "type": payment.get("type"),
        "amount": payment.get("amount"),
        "status": payment.get("status"),
        "short_url": payment.get("short_url"),
        "created_at": payment.get("created_at"),
        "paid_at": payment.get("paid_at"),
    }


@router.get("/pay/{order_id}", response_class=HTMLResponse)
async def redirect_to_payment(order_id: str):
    """Serve an HTML page that loads Cashfree's JS SDK and launches checkout
    using the order's payment_session_id. No auth required.
    Self-heals if session_id is missing by fetching it from Cashfree."""
    payment = await db.payments.find_one({"link_id": order_id}, {"_id": 0})
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found or expired")

    session_id = payment.get("session_id", "")

    if not session_id and CASHFREE_CLIENT_ID and CASHFREE_CLIENT_SECRET:
        headers = {
            "x-api-version": CASHFREE_API_VERSION,
            "x-client-id": CASHFREE_CLIENT_ID,
            "x-client-secret": CASHFREE_CLIENT_SECRET,
        }
        try:
            async with httpx.AsyncClient() as cf:
                resp = await cf.get(f"{CASHFREE_BASE_URL}/orders/{order_id}", headers=headers, timeout=10.0)
            if resp.status_code < 400:
                data = resp.json()
                session_id = data.get("payment_session_id", "")
                if session_id:
                    await db.payments.update_one(
                        {"link_id": order_id},
                        {"$set": {"session_id": session_id}}
                    )
        except Exception as e:
            logger.error(f"Failed to refetch Cashfree session for {order_id}: {e}")

    if not session_id:
        raise HTTPException(status_code=404, detail="Payment not found or expired")

    amount = payment.get("amount", 0)
    ptype = "Tip" if payment.get("type") == "tip" else "Valet Fee"

    import json as _json
    session_id_js = _json.dumps(session_id)
    mode_js = _json.dumps(CASHFREE_JS_MODE)

    html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Pay __PTYPE__ - Valet Guys</title>
<script src="https://sdk.cashfree.com/js/v3/cashfree.js"></script>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
  body { background: #0b0f17; color: #fff; min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 24px; }
  .card { background: #141a26; border: 1px solid #1f2937; border-radius: 20px; padding: 32px 24px; max-width: 380px; width: 100%; text-align: center; box-shadow: 0 12px 48px rgba(0,0,0,0.4); }
  .logo { font-size: 28px; font-weight: 700; letter-spacing: -0.5px; margin-bottom: 4px; color: #fbbf24; }
  .tag { font-size: 12px; opacity: 0.6; letter-spacing: 2px; text-transform: uppercase; margin-bottom: 28px; }
  .label { font-size: 13px; opacity: 0.6; margin-bottom: 6px; }
  .amount { font-size: 44px; font-weight: 700; margin-bottom: 4px; letter-spacing: -1px; }
  .type { font-size: 14px; opacity: 0.7; margin-bottom: 28px; }
  .btn { background: #fbbf24; color: #0b0f17; border: none; border-radius: 12px; padding: 14px 32px; font-size: 16px; font-weight: 600; cursor: pointer; width: 100%; transition: opacity 0.2s; }
  .btn:hover { opacity: 0.9; }
  .btn:disabled { opacity: 0.5; cursor: not-allowed; }
  .secure { font-size: 11px; opacity: 0.4; margin-top: 16px; }
  .spinner { display: none; width: 20px; height: 20px; border: 3px solid rgba(11,15,23,0.3); border-top-color: #0b0f17; border-radius: 50%; animation: spin 0.7s linear infinite; margin: 0 auto; }
  @keyframes spin { to { transform: rotate(360deg); } }
  .btn.loading .spinner { display: inline-block; }
  .btn.loading .text { display: none; }
</style>
</head>
<body>
  <div class="card">
    <div class="logo">VALET GUYS</div>
    <div class="tag">Secure Payment</div>
    <div class="label">Amount</div>
    <div class="amount">Rs. __AMOUNT__</div>
    <div class="type">__PTYPE__ Payment</div>
    <button id="payBtn" class="btn" onclick="startCheckout()">
      <span class="text">Pay Now</span>
      <span class="spinner"></span>
    </button>
    <div class="secure">Powered by Cashfree</div>
  </div>
<script>
  const sessionId = __SESSION_ID__;
  const cashfree = Cashfree({ mode: __MODE__ });

  function startCheckout() {
    const btn = document.getElementById("payBtn");
    btn.classList.add("loading");
    btn.disabled = true;
    cashfree.checkout({
      paymentSessionId: sessionId,
      redirectTarget: "_self"
    }).then(() => {
      btn.classList.remove("loading");
      btn.disabled = false;
    }).catch((err) => {
      console.error(err);
      btn.classList.remove("loading");
      btn.disabled = false;
      alert("Payment could not be started: " + (err.message || "unknown error"));
    });
  }

  // Auto-launch checkout immediately
  window.addEventListener("load", () => { setTimeout(startCheckout, 250); });
</script>
</body>
</html>"""
    html = (html
        .replace("__PTYPE__", ptype)
        .replace("__AMOUNT__", f"{amount:.0f}")
        .replace("__SESSION_ID__", session_id_js)
        .replace("__MODE__", mode_js))
    return HTMLResponse(content=html, status_code=200)



# ─── Short-path aliases (so WhatsApp links stay compact) ───

@short_router.get("/p/{order_id}", response_class=HTMLResponse)
async def short_redirect_to_payment(order_id: str):
    """Alias for /api/payments/pay/{order_id}."""
    return await redirect_to_payment(order_id)


@short_router.get("/qt/{token}/{amount}", response_class=HTMLResponse)
async def short_quick_tip(token: str, amount: int):
    """Alias for /api/payments/quick-tip/{token}/{amount}."""
    return await quick_tip_redirect(token, amount)
