"""Shared utility functions: auth, messaging, notifications."""
import os
import jwt
import json
import asyncio
import logging
import random
from datetime import datetime, timezone, timedelta
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from pywebpush import webpush, WebPushException

from config import (
    db, pwd_context, security, SECRET_KEY, ALGORITHM,
    twilio_client, TWILIO_WHATSAPP_FROM, MESSAGING_MODE,
    VAPID_PRIVATE_KEY, VAPID_PUBLIC_KEY, VAPID_CLAIMS_EMAIL,
    WA_TEMPLATE_FEE,
)

logger = logging.getLogger(__name__)


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=7)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token")

        user = await db.users.find_one({"email": email}, {"_id": 0})
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except (jwt.InvalidTokenError, jwt.DecodeError, Exception):
        raise HTTPException(status_code=401, detail="Invalid token")


async def send_whatsapp_message(phone_number: str, message: str, content_sid: str = None, content_variables: dict = None):
    """Send a message via WhatsApp or SMS depending on MESSAGING_MODE."""
    if not twilio_client or not TWILIO_WHATSAPP_FROM:
        logger.warning(f"Twilio not configured. Would send to {phone_number}: {message}")
        return {"status": "not_configured", "message": "Twilio credentials not set"}

    try:
        if MESSAGING_MODE == 'whatsapp':
            to_addr = f"whatsapp:{phone_number}" if not phone_number.startswith('whatsapp:') else phone_number
            from_addr = f"whatsapp:{TWILIO_WHATSAPP_FROM}" if not TWILIO_WHATSAPP_FROM.startswith('whatsapp:') else TWILIO_WHATSAPP_FROM
            msg_params = {"from_": from_addr, "to": to_addr}
            if content_sid:
                msg_params["content_sid"] = content_sid
                if content_variables:
                    msg_params["content_variables"] = json.dumps(content_variables)
            else:
                msg_params["body"] = message
        else:
            to_addr = phone_number
            from_addr = TWILIO_WHATSAPP_FROM
            msg_params = {"from_": from_addr, "to": to_addr, "body": message}

        logger.info(f"Sending {MESSAGING_MODE.upper()}: From={from_addr} To={to_addr}")
        twilio_message = twilio_client.messages.create(**msg_params)
        logger.info(f"Message sent: SID={twilio_message.sid}, Status={twilio_message.status}")

        return {"status": "sent", "message_sid": twilio_message.sid, "twilio_status": twilio_message.status}
    except Exception as e:
        logger.error(f"Twilio send error: {str(e)}")
        return {"status": "error", "message": str(e)}


async def send_sms(phone_number: str, message: str):
    """Send a plain SMS (always SMS, never WhatsApp). Used for OTP delivery."""
    if not twilio_client or not TWILIO_WHATSAPP_FROM:
        logger.warning(f"Twilio not configured. Would SMS to {phone_number}: {message}")
        return {"status": "not_configured", "message": "Twilio credentials not set"}

    try:
        msg = twilio_client.messages.create(
            from_=TWILIO_WHATSAPP_FROM,
            to=phone_number,
            body=message
        )
        logger.info(f"SMS sent: SID={msg.sid}, Status={msg.status}, To={phone_number}")
        return {"status": "sent", "message_sid": msg.sid, "twilio_status": msg.status}
    except Exception as e:
        logger.error(f"SMS send error to {phone_number}: {str(e)}")
        return {"status": "error", "message": str(e)}


async def send_push_notification(user_id: str, title: str, body: str, data: dict = None):
    """Send push notification to a specific user's subscribed devices."""
    if not VAPID_PRIVATE_KEY:
        logger.warning("VAPID keys not configured, skipping push notification")
        return

    subscriptions = await db.push_subscriptions.find(
        {"user_id": user_id}, {"_id": 0}
    ).to_list(50)

    payload = json.dumps({
        "title": title,
        "body": body,
        "data": data or {},
        "icon": "/icon-192.png",
        "badge": "/icon-192.png",
        "requireInteraction": True,
        "urgency": "high"
    })

    for sub in subscriptions:
        try:
            webpush(
                subscription_info=sub["subscription"],
                data=payload,
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims={"sub": VAPID_CLAIMS_EMAIL},
                headers={"Urgency": "high", "Topic": data.get("ticket_id", "valetguys") if data else "valetguys"}
            )
        except WebPushException as e:
            logger.warning(f"Push failed for user {user_id}: {e}")
            if e.response and e.response.status_code in (404, 410):
                await db.push_subscriptions.delete_one({"_id": sub.get("_id")})
        except Exception as e:
            logger.error(f"Push notification error: {e}")


async def notify_team_of_retrieval(vehicle: dict, ticket_id: str):
    """Send multi-layer notifications to all active valets/admin when retrieval is requested.
    Layer 1: Immediate web push
    Layer 2: WhatsApp message to all online valets
    Layer 3: Repeated push pulses (at +5s, +15s, +25s) — stops if ticket is claimed
    """
    parked_by = vehicle.get("parked_by")
    if not parked_by:
        return

    parker = await db.users.find_one({"id": parked_by}, {"_id": 0})
    if not parker:
        return

    client_id = parker.get("client_id")
    if not client_id:
        return

    plate = vehicle.get("license_plate", "Unknown")
    tag = vehicle.get("tag_number")
    zone = vehicle.get("zone_label")
    tag_str = f" (Tag #{tag})" if tag else ""
    zone_str = f"\nLocation: {zone}" if zone else ""

    # Get all team members
    team_members = await db.users.find(
        {"client_id": client_id, "is_active": True, "role": {"$in": ["valet", "admin"]}},
        {"_id": 0, "id": 1, "phone_number": 1, "name": 1, "is_online": 1}
    ).to_list(500)

    # Layer 1: Immediate web push to all members
    push_data = {
        "type": "retrieval",
        "ticket_id": ticket_id,
        "vehicle_id": vehicle.get("id"),
        "plate": plate,
        "tag": tag or "",
        "zone": zone or "",
    }
    for member in team_members:
        await send_push_notification(member["id"], "Retrieval Request", f"Car {plate}{tag_str} is ready for pickup!", push_data)

    # Layer 2: WhatsApp message to all online valets
    for member in team_members:
        phone = member.get("phone_number")
        if phone and member.get("is_online", False):
            wa_msg = f"Valet Guys: New retrieval request!\nCar: {plate}{tag_str}{zone_str}\nOpen the app to claim this ticket."
            await send_whatsapp_message(phone, wa_msg)

    # Layer 3: Background pulse — repeated pushes at 5s, 15s, 25s
    asyncio.ensure_future(_pulse_notifications(ticket_id, team_members, plate, tag_str, push_data))


async def _pulse_notifications(ticket_id: str, team_members: list, plate: str, tag_str: str, push_data: dict):
    """Send repeated push pulses until ticket is claimed or 30s elapsed."""
    delays = [5, 10, 10]  # seconds between pulses: at +5s, +15s, +25s
    for delay in delays:
        await asyncio.sleep(delay)

        # Check if ticket is still open
        ticket = await db.tickets.find_one({"id": ticket_id}, {"_id": 0, "status": 1})
        if not ticket or ticket.get("status") != "open":
            logger.info(f"Pulse stopped for ticket {ticket_id[:8]}... — status: {ticket.get('status') if ticket else 'deleted'}")
            return

        # Send another push to all members
        for member in team_members:
            await send_push_notification(
                member["id"],
                "Retrieval Waiting!",
                f"Car {plate}{tag_str} still waiting — claim now!",
                push_data
            )

    logger.info(f"Pulse complete for ticket {ticket_id[:8]}...")


async def notify_team_of_claim(ticket_id: str, claimer_name: str, plate: str):
    """Notify all team valets via WhatsApp that a ticket has been claimed."""
    ticket = await db.tickets.find_one({"id": ticket_id}, {"_id": 0, "vehicle_id": 1, "claimed_by": 1})
    if not ticket:
        return

    vehicle = await db.vehicles.find_one({"id": ticket.get("vehicle_id")}, {"_id": 0, "parked_by": 1})
    if not vehicle:
        return

    parker = await db.users.find_one({"id": vehicle.get("parked_by")}, {"_id": 0, "client_id": 1})
    if not parker:
        return

    client_id = parker.get("client_id")
    if not client_id:
        return

    team_members = await db.users.find(
        {"client_id": client_id, "is_active": True, "role": {"$in": ["valet", "admin"]}, "id": {"$ne": ticket.get("claimed_by")}},
        {"_id": 0, "phone_number": 1, "is_online": 1}
    ).to_list(500)

    for member in team_members:
        phone = member.get("phone_number")
        if phone and member.get("is_online", False):
            msg = f"Valet Guys: {claimer_name} has claimed the retrieval for car {plate}."
            await send_whatsapp_message(phone, msg)


async def get_client_valet_fee(client_id: str) -> float:
    """Get the valet fee for a client. Returns 0 if fee is not enabled or not set."""
    if not client_id:
        return 0
    admin = await db.users.find_one(
        {"client_id": client_id, "role": "admin", "is_active": True},
        {"_id": 0, "valet_fee": 1, "fee_enabled": 1}
    )
    if not admin:
        return 0
    if not admin.get("fee_enabled", False):
        return 0
    return admin.get("valet_fee", 0)


async def get_client_wait_timer(client_id: str) -> int:
    """Get the wait timer (in minutes) for a client. Returns 5 if not set."""
    if not client_id:
        return 5
    admin = await db.users.find_one(
        {"client_id": client_id, "role": "admin", "is_active": True},
        {"_id": 0, "wait_timer": 1}
    )
    return admin.get("wait_timer", 5) if admin else 5


async def send_fee_payment_request(phone: str, client_name: str, fee: float, vehicle_id: str):
    """Send Cashfree payment link for valet fee before retrieval."""
    import uuid
    from routers.payments import create_payment_link

    fee_str = f"Rs.{fee:.0f}" if fee == int(fee) else f"Rs.{fee:.2f}"

    result = await create_payment_link(
        amount_inr=fee,
        description=f"Valet Parking Fee - {client_name}",
        customer_phone=phone,
        reference_id=f"fee-{uuid.uuid4().hex[:12]}",
        notes={"type": "valet_fee", "vehicle_id": vehicle_id, "client_name": client_name}
    )

    if result and result.get("short_url"):
        await db.payments.insert_one({
            "link_id": result["link_id"],
            "session_id": result.get("session_id", ""),
            "cf_order_id": result.get("cf_order_id", ""),
            "type": "valet_fee",
            "vehicle_id": vehicle_id,
            "customer_phone": phone,
            "amount": fee,
            "status": "created",
            "short_url": result["short_url"],
            "created_at": datetime.now(timezone.utc).isoformat(),
        })

        message = f"Valet Guys ({client_name}): Your valet parking fee is {fee_str}. Pay here to get your car: {result['short_url']}"
        await send_whatsapp_message(phone, message,
            content_sid=WA_TEMPLATE_FEE,
            content_variables={"1": client_name, "2": fee_str}
        )
    else:
        message = f"Valet Guys ({client_name}): Your valet parking fee is {fee_str}. Please complete your payment to proceed with vehicle retrieval."
        await send_whatsapp_message(phone, message,
            content_sid=WA_TEMPLATE_FEE,
            content_variables={"1": client_name, "2": fee_str}
        )
