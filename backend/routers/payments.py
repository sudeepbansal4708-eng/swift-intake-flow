"""Payment routes: Cashfree payment links for valet fees and tips."""
import logging
import uuid
import httpx
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, Request

from config import (
    db, CASHFREE_CLIENT_ID, CASHFREE_CLIENT_SECRET,
    CASHFREE_BASE_URL, CASHFREE_API_VERSION,
)
from utils import get_current_user, send_whatsapp_message

router = APIRouter(prefix="/payments", tags=["payments"])
logger = logging.getLogger(__name__)


async def create_payment_link(amount_inr: float, description: str, customer_phone: str, customer_name: str = "Customer", reference_id: str = "", notes: dict = None):
    """Create a Cashfree Payment Link and return the short URL."""
    if not CASHFREE_CLIENT_ID or not CASHFREE_CLIENT_SECRET:
        logger.warning("Cashfree not configured")
        return None

    try:
        link_id = reference_id or f"vg-{uuid.uuid4().hex[:12]}"

        payload = {
            "link_id": link_id,
            "link_amount": amount_inr,
            "link_currency": "INR",
            "link_purpose": description,
            "customer_details": {
                "customer_phone": customer_phone.replace("+", ""),
                "customer_name": customer_name,
            },
            "link_notify": {
                "send_sms": False,
                "send_email": False,
            },
            "link_meta": notes or {},
        }

        headers = {
            "Content-Type": "application/json",
            "x-api-version": CASHFREE_API_VERSION,
            "x-client-id": CASHFREE_CLIENT_ID,
            "x-client-secret": CASHFREE_CLIENT_SECRET,
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{CASHFREE_BASE_URL}/links",
                json=payload,
                headers=headers,
                timeout=15.0,
            )

        if resp.status_code >= 400:
            logger.error(f"Cashfree error {resp.status_code}: {resp.text}")
            return None

        data = resp.json()
        short_url = data.get("link_url", "")
        cf_link_id = data.get("link_id", link_id)

        logger.info(f"Cashfree payment link created: {cf_link_id} for Rs.{amount_inr}, url={short_url}")

        return {
            "link_id": cf_link_id,
            "short_url": short_url,
            "amount": amount_inr,
            "status": data.get("link_status", "created"),
        }
    except Exception as e:
        logger.error(f"Cashfree payment link error: {e}")
        return None


@router.post("/create-fee-link")
async def create_fee_payment_link(vehicle_id: str, current_user: dict = Depends(get_current_user)):
    """Create a payment link for valet parking fee and send via WhatsApp."""
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
    """Create a tip payment link for the customer to tip the valet."""
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
    """Handle Cashfree payment link webhooks."""
    body = await request.body()

    import json
    try:
        payload = json.loads(body)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid payload")

    event_type = payload.get("type", "")
    logger.info(f"Cashfree webhook: {event_type}")

    if event_type == "PAYMENT_LINK_EVENT":
        link_data = payload.get("data", {}).get("link_payment", {}) or payload.get("data", {})
        link_id = link_data.get("link_id", "")
        link_status = link_data.get("link_status", "")
        amount_paid = link_data.get("link_amount_paid", 0)
        link_meta = link_data.get("link_meta", {}) or {}

        if link_id:
            await db.payments.update_one(
                {"link_id": link_id},
                {"$set": {
                    "status": "paid" if link_status == "PAID" else link_status.lower(),
                    "paid_at": datetime.now(timezone.utc).isoformat(),
                    "amount_paid": float(amount_paid) if amount_paid else 0,
                }}
            )

            payment = await db.payments.find_one({"link_id": link_id}, {"_id": 0})
            payment_type = payment.get("type", "") if payment else link_meta.get("type", "")

            if link_status == "PAID":
                if payment_type == "valet_fee":
                    vehicle_id = payment.get("vehicle_id", "") if payment else link_meta.get("vehicle_id", "")
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
                    valet_id = payment.get("valet_id", "") if payment else link_meta.get("valet_id", "")
                    vehicle_id = payment.get("vehicle_id", "") if payment else link_meta.get("vehicle_id", "")
                    tip_amount = float(amount_paid) if amount_paid else (payment.get("amount", 0) if payment else 0)
                    if valet_id:
                        await db.tips.insert_one({
                            "valet_id": valet_id,
                            "vehicle_id": vehicle_id,
                            "amount": tip_amount,
                            "status": "paid",
                            "link_id": link_id,
                            "created_at": datetime.now(timezone.utc).isoformat(),
                        })
                        logger.info(f"Tip of Rs.{tip_amount} recorded for valet {valet_id}")

    return {"status": "ok"}


@router.get("/status/{link_id}")
async def get_payment_status(link_id: str, current_user: dict = Depends(get_current_user)):
    """Check payment status."""
    payment = await db.payments.find_one({"link_id": link_id}, {"_id": 0})
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
