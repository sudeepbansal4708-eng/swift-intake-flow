"""Payment routes: Cashfree Orders API for valet fees and tips."""
import logging
import uuid
import httpx
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import RedirectResponse

from config import (
    db, CASHFREE_CLIENT_ID, CASHFREE_CLIENT_SECRET,
    CASHFREE_BASE_URL, CASHFREE_API_VERSION,
)
from utils import get_current_user, send_whatsapp_message

router = APIRouter(prefix="/payments", tags=["payments"])
logger = logging.getLogger(__name__)

CASHFREE_CHECKOUT_URL = "https://payments.cashfree.com/order/#"


def get_base_url(request: Request) -> str:
    """Derive the public base URL from the incoming request."""
    forwarded_proto = request.headers.get("x-forwarded-proto", "https")
    forwarded_host = request.headers.get("x-forwarded-host") or request.headers.get("host", "")
    return f"{forwarded_proto}://{forwarded_host}"


async def create_payment_link(base_url: str, amount_inr: float, description: str, customer_phone: str, customer_name: str = "Customer", reference_id: str = "", notes: dict = None):
    """Create a Cashfree Order and return the checkout URL."""
    if not CASHFREE_CLIENT_ID or not CASHFREE_CLIENT_SECRET:
        logger.warning("Cashfree not configured")
        return None

    try:
        order_id = reference_id or f"vg-{uuid.uuid4().hex[:12]}"
        customer_id = f"cust-{customer_phone.replace('+', '')[-10:]}"

        payload = {
            "order_id": order_id,
            "order_amount": amount_inr,
            "order_currency": "INR",
            "order_note": description,
            "customer_details": {
                "customer_id": customer_id,
                "customer_phone": customer_phone.replace("+", "")[-10:],
                "customer_name": customer_name,
            },
            "order_meta": {
                "return_url": f"{base_url}/payment/success?order_id={order_id}",
            },
            "order_tags": notes or {},
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
            logger.error(f"Cashfree error {resp.status_code}: {resp.text}")
            return None

        data = resp.json()
        session_id = data.get("payment_session_id", "")
        short_url = f"{base_url}/api/payments/pay/{order_id}"

        logger.info(f"Cashfree order created: {order_id} for Rs.{amount_inr}, url={short_url}")

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
async def create_fee_payment_link(request: Request, vehicle_id: str, current_user: dict = Depends(get_current_user)):
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

    base_url = get_base_url(request)
    result = await create_payment_link(
        base_url=base_url,
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
        "cf_order_id": result.get("cf_order_id", ""),
        "session_id": result.get("session_id", ""),
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
async def create_tip_payment_link(request: Request, vehicle_id: str, valet_id: str, amount: float = 0, current_user: dict = Depends(get_current_user)):
    """Create a tip payment order for the customer to tip the valet."""
    vehicle = await db.vehicles.find_one({"id": vehicle_id}, {"_id": 0})
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    valet = await db.users.find_one({"id": valet_id}, {"_id": 0, "name": 1, "client_name": 1})
    valet_name = valet.get("name", "your valet") if valet else "your valet"
    client_name = valet.get("client_name", "Valet Guys") if valet else "Valet Guys"

    tip_amount = amount if amount > 0 else 100

    base_url = get_base_url(request)
    result = await create_payment_link(
        base_url=base_url,
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
        "cf_order_id": result.get("cf_order_id", ""),
        "session_id": result.get("session_id", ""),
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


@router.post("/webhook")
async def cashfree_webhook(request: Request):
    """Handle Cashfree payment webhooks."""
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
                        logger.info(f"Valet fee paid for vehicle {vehicle_id}, ticket moved to open")

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


@router.get("/pay/{order_id}")
async def redirect_to_payment(order_id: str):
    """Short URL redirect to Cashfree checkout page. No auth required."""
    payment = await db.payments.find_one({"link_id": order_id}, {"_id": 0, "session_id": 1})
    if not payment or not payment.get("session_id"):
        raise HTTPException(status_code=404, detail="Payment not found or expired")

    checkout_url = f"{CASHFREE_CHECKOUT_URL}{payment['session_id']}"
    return RedirectResponse(url=checkout_url, status_code=302)
