"""Public routes: customer retrieval, push notifications, WhatsApp webhook."""
import json
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, Form
from fastapi.responses import Response

from config import db, VAPID_PUBLIC_KEY
from models import Ticket, PushSubscription
from utils import (
    get_current_user, send_whatsapp_message, notify_team_of_retrieval,
    get_client_valet_fee, get_client_wait_timer, send_fee_payment_request,
)

router = APIRouter(tags=["public"])
logger = logging.getLogger(__name__)


# ─── Push Notification Endpoints ───

@router.post("/push/subscribe")
async def push_subscribe(data: PushSubscription, current_user: dict = Depends(get_current_user)):
    endpoint = data.subscription.get("endpoint", "")
    if not endpoint:
        raise HTTPException(status_code=400, detail="Invalid subscription")

    await db.push_subscriptions.update_one(
        {"user_id": current_user['id'], "subscription.endpoint": endpoint},
        {"$set": {
            "user_id": current_user['id'],
            "subscription": data.subscription,
            "role": current_user['role'],
            "client_id": current_user.get('client_id'),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }},
        upsert=True
    )
    return {"message": "Subscribed to push notifications"}


@router.post("/push/unsubscribe")
async def push_unsubscribe(data: PushSubscription, current_user: dict = Depends(get_current_user)):
    endpoint = data.subscription.get("endpoint", "")
    await db.push_subscriptions.delete_one({
        "user_id": current_user['id'],
        "subscription.endpoint": endpoint
    })
    return {"message": "Unsubscribed from push notifications"}


@router.get("/push/vapid-key")
async def get_vapid_public_key():
    return {"public_key": VAPID_PUBLIC_KEY}


# ─── WhatsApp Webhook ───

@router.post("/whatsapp/webhook")
async def whatsapp_webhook(
    From: str = Form(...),
    Body: str = Form(""),
    ButtonPayload: str = Form(""),
    ButtonText: str = Form(""),
):
    """Handle incoming SMS/WhatsApp messages from Twilio."""
    phone_number = From.replace('whatsapp:', '').strip()
    if not phone_number.startswith('+'):
        phone_number = '+' + phone_number

    message = (ButtonPayload or Body or ButtonText).strip()
    message_lower = message.lower()

    logger.info(f"Inbound from {phone_number}: body={Body!r} payload={ButtonPayload!r} text={ButtonText!r}")

    reply_text = ""

    # Detect tip button tap: payload like "tip_25" / "tip_50" / "tip_100"
    tip_amount = None
    for amt in (25, 50, 100, 200, 500):
        if message_lower in (f"tip_{amt}", f"tip{amt}", f"rs.{amt}", f"rs {amt}", f"₹{amt}", str(amt)):
            tip_amount = amt
            break

    if tip_amount:
        # Find the most recent tip intent for this phone within last 24h
        intent = await db.tip_intents.find_one(
            {"customer_phone": phone_number},
            {"_id": 0},
            sort=[("created_at", -1)],
        )
        if not intent:
            reply_text = "Sorry, we couldn't find a recent checkout to tip for. Please contact the valet desk."
        else:
            from routers.payments import create_payment_link
            from config import get_app_base_url
            import uuid
            result = await create_payment_link(
                amount_inr=tip_amount,
                description=f"Tip for {intent['valet_name']} - {intent['client_name']}",
                customer_phone=phone_number,
                customer_name="Customer",
                reference_id=f"tip-{intent['token']}-{tip_amount}-{uuid.uuid4().hex[:4]}",
                notes={"type": "tip", "vehicle_id": intent['vehicle_id'], "valet_id": intent['valet_id']},
            )
            if not result:
                reply_text = "Sorry, we couldn't create your tip payment right now. Please try again."
            else:
                await db.payments.insert_one({
                    "link_id": result["link_id"],
                    "session_id": result.get("session_id", ""),
                    "cf_order_id": result.get("cf_order_id", ""),
                    "type": "tip",
                    "vehicle_id": intent['vehicle_id'],
                    "valet_id": intent['valet_id'],
                    "customer_phone": phone_number,
                    "amount": tip_amount,
                    "status": "created",
                    "short_url": result["short_url"],
                    "tip_token": intent['token'],
                    "created_at": datetime.now(timezone.utc).isoformat(),
                })
                reply_text = f"Tap to pay Rs.{tip_amount} tip for {intent['valet_name']}:\n{result['short_url']}\n\nThank you!"
    elif message_lower in ['retr', 'retrieve', 'get car', 'ready']:
        vehicle = await db.vehicles.find_one(
            {"phone_number": phone_number, "status": {"$ne": "checked_out"}},
            {"_id": 0},
            sort=[("parked_at", -1)]
        )
        if not vehicle:
            reply_text = "Sorry, we couldn't find your vehicle. Please contact support."
        else:
            existing_ticket = await db.tickets.find_one({
                "vehicle_id": vehicle['id'],
                "status": {"$in": ["open", "claimed", "en_route", "arrived", "pending_payment"]}
            })

            if existing_ticket:
                if existing_ticket.get('status') == 'pending_payment':
                    reply_text = "Your retrieval is pending payment. Please complete the payment to proceed."
                else:
                    reply_text = "Your retrieval request is already in progress. A valet will be with you shortly!"
            else:
                parker = await db.users.find_one({"id": vehicle.get("parked_by")}, {"_id": 0})
                client_id = parker.get("client_id") if parker else None
                valet_fee = await get_client_valet_fee(client_id) if client_id else 0

                if valet_fee > 1:
                    client_name = parker.get("client_name", "Valet Guys") if parker else "Valet Guys"
                    ticket_obj = Ticket(
                        vehicle_id=vehicle['id'],
                        customer_phone=phone_number,
                        status="pending_payment"
                    )
                    doc = ticket_obj.model_dump()
                    doc['created_at'] = doc['created_at'].isoformat()
                    doc['valet_fee'] = valet_fee
                    await db.tickets.insert_one(doc)

                    await send_fee_payment_request(phone_number, client_name, valet_fee, vehicle['id'])
                    reply_text = f"Your valet parking fee is Rs.{valet_fee:.0f}. A payment link has been sent. Please complete payment to proceed with retrieval."
                else:
                    ticket_obj = Ticket(
                        vehicle_id=vehicle['id'],
                        customer_phone=phone_number,
                        status="open"
                    )

                    doc = ticket_obj.model_dump()
                    doc['created_at'] = doc['created_at'].isoformat()
                    await db.tickets.insert_one(doc)

                    await notify_team_of_retrieval(vehicle, ticket_obj.id)

                    reply_text = "Got it! Your car retrieval request is now active. A valet will claim it shortly and keep you updated!"
    else:
        reply_text = "Hi! Reply RETR when you're ready to retrieve your car."

    twiml = f'<?xml version="1.0" encoding="UTF-8"?><Response><Message>{reply_text}</Message></Response>'
    return Response(content=twiml, media_type="application/xml")


# ─── Public Customer Retrieval Endpoints (no auth required) ───

@router.get("/retrieve/{vehicle_id}")
async def get_vehicle_for_retrieval(vehicle_id: str):
    """Public endpoint: Get vehicle info for the customer retrieval page."""
    vehicle = await db.vehicles.find_one({"id": vehicle_id}, {"_id": 0})
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    parker = await db.users.find_one({"id": vehicle.get("parked_by")}, {"_id": 0})
    client_name = parker.get("client_name", "Valet Guys") if parker else "Valet Guys"
    client_id = parker.get("client_id") if parker else None
    valet_fee = await get_client_valet_fee(client_id) if client_id else 0

    existing_ticket = await db.tickets.find_one({
        "vehicle_id": vehicle_id,
        "status": {"$in": ["open", "claimed", "en_route", "arrived", "pending_payment"]}
    }, {"_id": 0})

    ticket_status = existing_ticket.get("status") if existing_ticket else None
    valet_name = None
    arrived_at = None
    wait_timer = 5

    if existing_ticket and existing_ticket.get("claimed_by"):
        claimer = await db.users.find_one({"id": existing_ticket["claimed_by"]}, {"_id": 0, "name": 1})
        valet_name = claimer.get("name") if claimer else None
    if existing_ticket:
        arrived_at = existing_ticket.get("arrived_at")
        wait_timer = existing_ticket.get("wait_timer", 5)

    if not existing_ticket or "wait_timer" not in (existing_ticket or {}):
        wait_timer = await get_client_wait_timer(client_id) if client_id else 5

    return {
        "vehicle_id": vehicle['id'],
        "license_plate": vehicle.get("license_plate"),
        "tag_number": vehicle.get("tag_number"),
        "zone_label": vehicle.get("zone_label"),
        "parked_at": vehicle.get("parked_at"),
        "status": vehicle.get("status"),
        "client_name": client_name,
        "valet_fee": valet_fee,
        "active_ticket_status": ticket_status,
        "valet_name": valet_name,
        "arrived_at": arrived_at,
        "wait_timer": wait_timer,
    }


@router.post("/retrieve/{vehicle_id}/confirm")
async def confirm_vehicle_retrieval(vehicle_id: str):
    """Public endpoint: Customer confirms retrieval request."""
    vehicle = await db.vehicles.find_one({"id": vehicle_id}, {"_id": 0})
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    if vehicle.get("status") == "checked_out":
        raise HTTPException(status_code=400, detail="This vehicle has already been checked out")

    phone_number = vehicle.get("phone_number", "")

    existing_ticket = await db.tickets.find_one({
        "vehicle_id": vehicle_id,
        "status": {"$in": ["open", "claimed", "en_route", "arrived", "pending_payment"]}
    })
    if existing_ticket:
        status = existing_ticket.get("status")
        if status == "pending_payment":
            raise HTTPException(status_code=400, detail="Retrieval is pending payment. Please complete payment first.")
        raise HTTPException(status_code=400, detail="A retrieval request is already in progress.")

    parker = await db.users.find_one({"id": vehicle.get("parked_by")}, {"_id": 0})
    client_id = parker.get("client_id") if parker else None
    valet_fee = await get_client_valet_fee(client_id) if client_id else 0

    if valet_fee > 1:
        client_name = parker.get("client_name", "Valet Guys") if parker else "Valet Guys"
        ticket_obj = Ticket(
            vehicle_id=vehicle_id,
            customer_phone=phone_number,
            status="pending_payment"
        )
        doc = ticket_obj.model_dump()
        doc['created_at'] = doc['created_at'].isoformat()
        doc['valet_fee'] = valet_fee
        doc['client_id'] = client_id
        await db.tickets.insert_one(doc)

        await send_fee_payment_request(phone_number, client_name, valet_fee, vehicle_id)
        return {
            "status": "pending_payment",
            "message": f"Valet fee of Rs.{valet_fee:.0f} applies. A payment link has been sent to your phone.",
            "valet_fee": valet_fee
        }

    ticket_obj = Ticket(
        vehicle_id=vehicle_id,
        customer_phone=phone_number,
        status="open"
    )
    doc = ticket_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['client_id'] = client_id
    await db.tickets.insert_one(doc)

    await notify_team_of_retrieval(vehicle, ticket_obj.id)

    message = f"Valet Guys: Your retrieval request for {vehicle.get('license_plate')} is confirmed! A valet will bring your car shortly."
    await send_whatsapp_message(phone_number, message)

    return {
        "status": "open",
        "message": "Your car retrieval request is confirmed! A valet will claim it shortly."
    }
