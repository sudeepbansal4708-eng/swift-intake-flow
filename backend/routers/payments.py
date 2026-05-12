"""Payment routes: Razorpay payment links for valet fees and tips."""
import logging
import hmac
import hashlib
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, Request

from config import db, razorpay_client, RAZORPAY_KEY_SECRET
from utils import get_current_user, send_whatsapp_message

router = APIRouter(prefix="/payments", tags=["payments"])
logger = logging.getLogger(__name__)


async def create_payment_link(amount_inr: float, description: str, customer_phone: str, customer_name: str = "Customer", reference_id: str = "", notes: dict = None):
    """Create a Razorpay Payment Link and return the short URL."""
    if not razorpay_client:
        logger.warning("Razorpay not configured")
        return None

    try:
        amount_paise = int(amount_inr * 100)

        payload = {
            "amount": amount_paise,
            "currency": "INR",
            "description": description,
            "customer": {
                "contact": customer_phone,
                "name": customer_name,
            },
            "notify": {
                "sms": False,
                "email": False,
                "whatsapp": False,
            },
            "callback_url": "",
            "callback_method": "get",
        }

        if reference_id:
            payload["reference_id"] = reference_id[:40]

        if notes:
            payload["notes"] = notes

        link = razorpay_client.payment_link.create(payload)
        logger.info(f"Payment link created: {link.get('id')} for Rs.{amount_inr}, phone={customer_phone}")

        return {
            "link_id": link.get("id"),
            "short_url": link.get("short_url"),
            "amount": amount_inr,
            "status": link.get("status"),
        }
    except Exception as e:
        logger.error(f"Razorpay payment link error: {e}")
        return None


@router.post("/create-fee-link")
async def create_fee_payment_link(vehicle_id: str, current_user: dict = Depends(get_current_user)):
    """Create a payment link for valet parking fee and send via WhatsApp."""
    vehicle = await db.vehicles.find_one({"id": vehicle_id}, {"_id": 0})
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    # Get client's valet fee
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
        reference_id=f"fee-{vehicle_id[:30]}",
        notes={"type": "valet_fee", "vehicle_id": vehicle_id, "client_name": client_name}
    )

    if not result:
        raise HTTPException(status_code=500, detail="Failed to create payment link")

    # Store payment record
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

    # Send payment link via WhatsApp
    msg = f"Valet Guys ({client_name}): Your valet parking fee is Rs.{valet_fee:.0f}. Pay here: {result['short_url']}"
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

    # If no fixed amount, create a link with a suggested amount (can be customized)
    tip_amount = amount if amount > 0 else 100  # Default Rs.100 tip suggestion

    result = await create_payment_link(
        amount_inr=tip_amount,
        description=f"Tip for {valet_name} - {client_name}",
        customer_phone=vehicle.get("phone_number", ""),
        customer_name="Customer",
        reference_id=f"tip-{vehicle_id[:31]}",
        notes={"type": "tip", "vehicle_id": vehicle_id, "valet_id": valet_id, "valet_name": valet_name}
    )

    if not result:
        raise HTTPException(status_code=500, detail="Failed to create payment link")

    # Store payment record
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
async def razorpay_webhook(request: Request):
    """Handle Razorpay payment webhooks."""
    body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature", "")

    # Verify signature if webhook secret is configured
    webhook_secret = RAZORPAY_KEY_SECRET
    if webhook_secret and signature:
        try:
            expected = hmac.new(
                webhook_secret.encode(),
                body,
                hashlib.sha256
            ).hexdigest()
            if not hmac.compare_digest(expected, signature):
                logger.warning("Razorpay webhook signature mismatch")
        except Exception as e:
            logger.warning(f"Webhook verification error: {e}")

    import json
    try:
        payload = json.loads(body)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid payload")

    event = payload.get("event", "")
    logger.info(f"Razorpay webhook: {event}")

    if event == "payment_link.paid":
        link_entity = payload.get("payload", {}).get("payment_link", {}).get("entity", {})
        link_id = link_entity.get("id")
        amount_paise = link_entity.get("amount", 0)
        amount_inr = amount_paise / 100
        notes = link_entity.get("notes", {})

        # Update payment record
        await db.payments.update_one(
            {"link_id": link_id},
            {"$set": {
                "status": "paid",
                "paid_at": datetime.now(timezone.utc).isoformat(),
                "amount_paid": amount_inr,
            }}
        )

        payment_type = notes.get("type", "unknown")
        vehicle_id = notes.get("vehicle_id", "")

        if payment_type == "valet_fee" and vehicle_id:
            # Mark ticket as paid — move from pending_payment to open
            ticket = await db.tickets.find_one(
                {"vehicle_id": vehicle_id, "status": "pending_payment"},
                {"_id": 0}
            )
            if ticket:
                await db.tickets.update_one(
                    {"id": ticket["id"]},
                    {"$set": {"status": "open", "fee_paid": True, "fee_paid_at": datetime.now(timezone.utc).isoformat()}}
                )
                logger.info(f"Valet fee paid for vehicle {vehicle_id}, ticket {ticket['id']} moved to open")

        elif payment_type == "tip":
            valet_id = notes.get("valet_id", "")
            if valet_id:
                await db.tips.insert_one({
                    "valet_id": valet_id,
                    "vehicle_id": vehicle_id,
                    "amount": amount_inr,
                    "status": "paid",
                    "link_id": link_id,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                })
                logger.info(f"Tip of Rs.{amount_inr} recorded for valet {valet_id}")

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
