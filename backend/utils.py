"""Shared utility functions: auth, messaging, notifications."""
import os
import jwt
import json
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
        "icon": "/favicon.ico",
        "badge": "/favicon.ico"
    })

    for sub in subscriptions:
        try:
            webpush(
                subscription_info=sub["subscription"],
                data=payload,
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims={"sub": VAPID_CLAIMS_EMAIL}
            )
        except WebPushException as e:
            logger.warning(f"Push failed for user {user_id}: {e}")
            if e.response and e.response.status_code in (404, 410):
                await db.push_subscriptions.delete_one({"_id": sub.get("_id")})
        except Exception as e:
            logger.error(f"Push notification error: {e}")


async def notify_team_of_retrieval(vehicle: dict, ticket_id: str):
    """Send push notifications to all active valets and admin for a client when retrieval is requested."""
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
    tag_str = f" (Tag #{tag})" if tag else ""
    title = "New Retrieval Request"
    body = f"Car {plate}{tag_str} is ready for pickup!"
    data = {"type": "retrieval", "ticket_id": ticket_id, "vehicle_id": vehicle.get("id")}

    team_members = await db.users.find(
        {"client_id": client_id, "is_active": True, "role": {"$in": ["valet", "admin"]}},
        {"_id": 0, "id": 1}
    ).to_list(500)

    for member in team_members:
        await send_push_notification(member["id"], title, body, data)


async def get_client_valet_fee(client_id: str) -> float:
    """Get the valet fee for a client. Returns 0 if not set."""
    if not client_id:
        return 0
    admin = await db.users.find_one(
        {"client_id": client_id, "role": "admin", "is_active": True},
        {"_id": 0, "valet_fee": 1}
    )
    return admin.get("valet_fee", 0) if admin else 0


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
    """Send payment request for valet fee before retrieval."""
    fee_str = f"Rs.{fee:.0f}" if fee == int(fee) else f"Rs.{fee:.2f}"
    message = f"Valet Guys ({client_name}): Your valet parking fee is {fee_str}. Please complete your payment to proceed with vehicle retrieval."
    await send_whatsapp_message(
        phone, message,
        content_sid=WA_TEMPLATE_FEE,
        content_variables={"1": client_name, "2": fee_str}
    )
