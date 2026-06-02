"""Ticket routes: create, list, claim, status update, valet dashboard, online requests."""
import os
import logging
from typing import Optional
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException, Depends

from config import db, WA_TEMPLATE_RETRIEVAL, WA_TEMPLATE_ARRIVED, WA_TEMPLATE_RETURNED, WA_TEMPLATE_TIP
from models import Ticket, RetrieveRequest
from utils import (
    get_current_user, send_whatsapp_message, notify_team_of_retrieval,
    notify_team_of_claim,
    send_push_notification, get_client_valet_fee, get_client_wait_timer,
    send_fee_payment_request,
)

router = APIRouter(tags=["tickets"])
logger = logging.getLogger(__name__)


@router.post("/tickets")
async def create_ticket(vehicle_id: str, current_user: dict = Depends(get_current_user)):
    vehicle = await db.vehicles.find_one({"id": vehicle_id}, {"_id": 0})
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    ticket_obj = Ticket(
        vehicle_id=vehicle_id,
        customer_phone=vehicle['phone_number'],
        status="open"
    )

    doc = ticket_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()

    await db.tickets.insert_one(doc)
    await notify_team_of_retrieval(vehicle, ticket_obj.id)

    return ticket_obj.model_dump()


@router.post("/tickets/retrieve")
async def retrieve_vehicle(data: RetrieveRequest, current_user: dict = Depends(get_current_user)):
    """Valet-initiated retrieval: lookup vehicle by customer phone and auto-assign ticket."""
    if current_user['role'] == 'valet' and not current_user.get('is_online'):
        raise HTTPException(status_code=403, detail="You must be marked online by your manager to retrieve vehicles")

    phone = data.phone_number.strip()
    if not phone.startswith('+'):
        phone = '+' + phone

    vehicle = await db.vehicles.find_one(
        {"phone_number": phone},
        {"_id": 0},
        sort=[("parked_at", -1)]
    )
    if not vehicle:
        raise HTTPException(status_code=404, detail="No vehicle found for this phone number")

    existing = await db.tickets.find_one({
        "vehicle_id": vehicle['id'],
        "status": {"$in": ["open", "claimed", "en_route", "arrived", "pending_payment"]}
    })
    if existing:
        raise HTTPException(status_code=400, detail="A retrieval ticket already exists for this vehicle")

    client_id = current_user.get('client_id')
    valet_fee = await get_client_valet_fee(client_id)

    if valet_fee > 1:
        client_name = current_user.get('client_name', 'Valet Guys')
        now = datetime.now(timezone.utc)
        ticket_obj = Ticket(
            vehicle_id=vehicle['id'],
            customer_phone=phone,
            status="pending_payment"
        )
        doc = ticket_obj.model_dump()
        doc['created_at'] = now.isoformat()
        doc['claimed_by'] = current_user['id']
        doc['claimed_at'] = now.isoformat()
        doc['valet_fee'] = valet_fee
        await db.tickets.insert_one(doc)

        await send_fee_payment_request(phone, client_name, valet_fee, vehicle['id'])

        ticket_response = {
            "id": ticket_obj.id,
            "vehicle_id": vehicle['id'],
            "customer_phone": phone,
            "status": "pending_payment",
            "valet_fee": valet_fee,
            "claimed_by": current_user['id'],
            "created_at": doc['created_at'],
            "vehicle": {
                "license_plate": vehicle.get("license_plate"),
                "tag_number": vehicle.get("tag_number"),
                "zone_label": vehicle.get("zone_label"),
                "phone_number": vehicle.get("phone_number"),
            }
        }
        return {
            "ticket": ticket_response,
            "message": f"Payment of Rs.{valet_fee:.0f} requested. Retrieval will begin after payment.",
            "pending_payment": True
        }

    now = datetime.now(timezone.utc)
    ticket_obj = Ticket(
        vehicle_id=vehicle['id'],
        customer_phone=phone,
        status="claimed"
    )

    doc = ticket_obj.model_dump()
    doc['created_at'] = now.isoformat()
    doc['claimed_by'] = current_user['id']
    doc['claimed_at'] = now.isoformat()

    await db.tickets.insert_one(doc)

    # Notify team that this valet has taken this retrieval (skip retrieval alert since already claimed)
    await notify_team_of_claim(ticket_obj.id, current_user.get('name', 'A valet'), vehicle['license_plate'])

    client_name = current_user.get('client_name', 'Valet Guys')
    message = f"Valet Guys: Valet {current_user['name']} is on the way to get your car {vehicle['license_plate']}!"
    await send_whatsapp_message(
        phone, message,
        content_sid=WA_TEMPLATE_RETRIEVAL,
        content_variables={"1": vehicle['license_plate'], "2": current_user['name'], "3": client_name}
    )

    ticket_response = {
        "id": ticket_obj.id,
        "vehicle_id": vehicle['id'],
        "customer_phone": phone,
        "status": "claimed",
        "claimed_by": current_user['id'],
        "claimed_at": doc['claimed_at'],
        "created_at": doc['created_at'],
        "vehicle": {
            "license_plate": vehicle.get("license_plate"),
            "tag_number": vehicle.get("tag_number"),
            "zone_label": vehicle.get("zone_label"),
            "phone_number": vehicle.get("phone_number"),
        }
    }

    return {
        "ticket": ticket_response,
        "message": "Retrieval ticket created and assigned to you"
    }


@router.get("/tickets")
async def get_tickets(status: Optional[str] = None, include_completed: bool = False, current_user: dict = Depends(get_current_user)):
    query = {}
    if status:
        query['status'] = status
    elif not include_completed:
        # By default, exclude completed/returned tickets from the dashboard
        query['status'] = {"$nin": ["completed", "returned"]}

    client_id = current_user.get('client_id')
    if client_id and current_user['role'] in ['valet', 'admin']:
        team = await db.users.find(
            {"client_id": client_id, "is_active": True},
            {"_id": 0, "id": 1}
        ).to_list(500)
        team_ids = [t['id'] for t in team]

        team_vehicles = await db.vehicles.find(
            {"parked_by": {"$in": team_ids}},
            {"_id": 0, "id": 1}
        ).to_list(5000)
        team_vehicle_ids = [v['id'] for v in team_vehicles]
        query['vehicle_id'] = {"$in": team_vehicle_ids}

    tickets = await db.tickets.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)

    vehicle_ids = list(set([ticket['vehicle_id'] for ticket in tickets if ticket.get('vehicle_id')]))

    if vehicle_ids:
        vehicles_list = await db.vehicles.find({"id": {"$in": vehicle_ids}}, {"_id": 0}).to_list(1000)
        vehicles_map = {v['id']: v for v in vehicles_list}

        for ticket in tickets:
            if isinstance(ticket.get('created_at'), str):
                ticket['created_at'] = datetime.fromisoformat(ticket['created_at']).isoformat()

            vehicle = vehicles_map.get(ticket['vehicle_id'])
            if vehicle:
                ticket['vehicle'] = {
                    "id": vehicle['id'],
                    "license_plate": vehicle['license_plate'],
                    "phone_number": vehicle['phone_number'],
                    "tag_number": vehicle.get('tag_number'),
                    "zone_label": vehicle.get('zone_label'),
                    "photo_url": vehicle.get('photo_url'),
                    "gps_latitude": vehicle.get('gps_latitude'),
                    "gps_longitude": vehicle.get('gps_longitude'),
                }
    else:
        for ticket in tickets:
            if isinstance(ticket.get('created_at'), str):
                ticket['created_at'] = datetime.fromisoformat(ticket['created_at']).isoformat()

    return tickets


@router.put("/tickets/{ticket_id}/extend")
async def extend_ticket_timer(ticket_id: str, current_user: dict = Depends(get_current_user)):
    """Extend the wait timer by 5 minutes from now."""
    ticket = await db.tickets.find_one({"id": ticket_id, "status": "arrived"}, {"_id": 0})
    if not ticket:
        raise HTTPException(status_code=400, detail="Ticket not in arrived state")

    new_arrived_at = datetime.now(timezone.utc).isoformat()
    wait_timer = ticket.get('wait_timer', 5)

    await db.tickets.update_one(
        {"id": ticket_id},
        {"$set": {"arrived_at": new_arrived_at, "wait_timer": wait_timer}}
    )

    return {"message": "Timer extended by 5 minutes", "arrived_at": new_arrived_at, "wait_timer": wait_timer}



@router.put("/tickets/{ticket_id}/claim")
async def claim_ticket(ticket_id: str, current_user: dict = Depends(get_current_user)):
    # Atomic claim: findOneAndUpdate ensures only one valet can claim
    now = datetime.now(timezone.utc).isoformat()
    result = await db.tickets.find_one_and_update(
        {"id": ticket_id, "status": "open"},
        {"$set": {
            "status": "claimed",
            "claimed_by": current_user['id'],
            "claimed_at": now
        }},
        return_document=False
    )

    if not result:
        raise HTTPException(status_code=409, detail="Ticket already claimed by another valet")

    vehicle = await db.vehicles.find_one({"id": result.get("vehicle_id")}, {"_id": 0})
    plate = vehicle.get("license_plate", "your car") if vehicle else "your car"

    client_name = current_user.get('client_name', 'Valet Guys')
    message = f"Valet Guys: Valet {current_user['name']} is on the way to get your car {plate}!"
    await send_whatsapp_message(
        result.get('customer_phone', ''), message,
        content_sid=WA_TEMPLATE_RETRIEVAL,
        content_variables={"1": plate, "2": current_user['name'], "3": client_name}
    )

    # Notify other valets that this ticket was claimed
    await notify_team_of_claim(ticket_id, current_user.get('name', 'A valet'), plate)

    return {"message": "Ticket claimed"}


@router.put("/tickets/{ticket_id}/status")
async def update_ticket_status(ticket_id: str, status: str, current_user: dict = Depends(get_current_user)):
    ticket = await db.tickets.find_one({"id": ticket_id}, {"_id": 0})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    vehicle = await db.vehicles.find_one({"id": ticket.get('vehicle_id')}, {"_id": 0})
    plate = vehicle.get('license_plate', 'your car') if vehicle else 'your car'

    update_data = {"status": status}

    if status == "en_route":
        client_name = current_user.get('client_name', 'Valet Guys')
        message = f"Valet Guys: Valet {current_user['name']} is on the way to get your car {plate}!"
        await send_whatsapp_message(
            ticket['customer_phone'], message,
            content_sid=WA_TEMPLATE_RETRIEVAL,
            content_variables={"1": plate, "2": current_user['name'], "3": client_name}
        )

    elif status == "arrived":
        arrived_time = datetime.now(timezone.utc)
        update_data['arrived_at'] = arrived_time.isoformat()
        client_id = current_user.get('client_id')
        wait_mins = await get_client_wait_timer(client_id)
        update_data['wait_timer'] = wait_mins
        deadline = arrived_time + timedelta(minutes=wait_mins)
        deadline_str = deadline.strftime("%I:%M %p")
        message = f"Valet Guys: Your car {plate} is at the entrance! Please collect by {deadline_str} UTC ({wait_mins} min). After that, your car will be returned to parking."
        await send_whatsapp_message(
            ticket['customer_phone'], message,
            content_sid=WA_TEMPLATE_ARRIVED,
            content_variables={"1": plate}
        )

    elif status == "returned":
        now = datetime.now(timezone.utc).isoformat()
        update_data['returned_at'] = now

        await db.vehicles.update_one(
            {"id": ticket['vehicle_id']},
            {"$set": {"status": "parked"}}
        )

        message = f"Valet Guys: Your car {plate} has been returned to parking as you did not arrive within 5 minutes. Please contact the valet desk when you are ready."
        await send_whatsapp_message(
            ticket['customer_phone'], message,
            content_sid=WA_TEMPLATE_RETURNED,
            content_variables={"1": plate}
        )

    elif status == "completed":
        update_data['completed_at'] = datetime.now(timezone.utc).isoformat()

        await db.vehicles.update_one(
            {"id": ticket['vehicle_id']},
            {"$set": {"status": "checked_out", "checked_out_at": update_data['completed_at']}}
        )

        client_name_msg = current_user.get('client_name', 'Valet Guys')
        valet_name_msg = current_user.get('name', 'your valet')

        # Create tip payment link first, then send combined thank-you + tip message
        from routers.payments import create_payment_link
        claimed_by = ticket.get('claimed_by') or current_user['id']
        tip_result = await create_payment_link(
            amount_inr=100,
            description=f"Tip for {valet_name_msg} - {client_name_msg}",
            customer_phone=ticket['customer_phone'],
            reference_id=f"tip-{ticket['vehicle_id'][:31]}",
            notes={"type": "tip", "vehicle_id": ticket['vehicle_id'], "valet_id": claimed_by, "valet_name": valet_name_msg}
        )

        tip_url = tip_result['short_url'] if tip_result else os.environ.get('BACKEND_URL', 'https://thevaletguys.in')

        # Send combined thank-you + tip as plain text (within 24hr conversation window)
        message = f"Thank you for parking with the Valet Guys at {client_name_msg}! We hope you had a great experience. Tip your valet {valet_name_msg} here: {tip_url}\n\nDrive Safe!"
        await send_whatsapp_message(ticket['customer_phone'], message)

        if tip_result:
            await db.payments.insert_one({
                "link_id": tip_result["link_id"],
                "type": "tip",
                "vehicle_id": ticket['vehicle_id'],
                "valet_id": claimed_by,
                "customer_phone": ticket['customer_phone'],
                "amount": 100,
                "status": "created",
                "short_url": tip_result["short_url"],
                "created_at": datetime.now(timezone.utc).isoformat(),
            })

    await db.tickets.update_one({"id": ticket_id}, {"$set": update_data})

    return {"message": "Status updated"}


@router.get("/valet/dashboard-stats")
async def get_valet_dashboard_stats(current_user: dict = Depends(get_current_user)):
    if current_user['role'] not in ['valet', 'admin']:
        raise HTTPException(status_code=403, detail="Valet or admin access required")

    valet_id = current_user['id']
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()

    cars_parked_today = await db.vehicles.count_documents({
        "parked_by": valet_id,
        "parked_at": {"$gte": today_start}
    })

    cars_retrieved_today = await db.tickets.count_documents({
        "claimed_by": valet_id,
        "status": "completed",
        "completed_at": {"$gte": today_start}
    })

    tips_today = await db.tips.find(
        {"valet_id": valet_id, "created_at": {"$gte": today_start}},
        {"_id": 0}
    ).to_list(500)
    tips_amount = sum(t.get('amount', 0) for t in tips_today)

    return {
        "cars_parked_today": cars_parked_today,
        "cars_retrieved_today": cars_retrieved_today,
        "tips_today": tips_amount
    }


@router.post("/valet/request-online")
async def valet_request_online(current_user: dict = Depends(get_current_user)):
    if current_user['role'] != 'valet':
        raise HTTPException(status_code=403, detail="Valet access required")

    if current_user.get('is_online'):
        return {"message": "You are already online"}

    existing = await db.online_requests.find_one(
        {"valet_id": current_user['id'], "status": "pending"}, {"_id": 0}
    )
    if existing:
        return {"message": "Request already pending"}

    now = datetime.now(timezone.utc).isoformat()
    await db.online_requests.insert_one({
        "valet_id": current_user['id'],
        "valet_name": current_user.get('name', 'Unknown'),
        "client_id": current_user.get('client_id'),
        "status": "pending",
        "created_at": now
    })

    admins = await db.users.find(
        {"client_id": current_user.get('client_id'), "role": "admin", "is_active": True},
        {"_id": 0, "id": 1}
    ).to_list(20)
    for admin in admins:
        await send_push_notification(
            admin['id'],
            "Shift Request",
            f"{current_user.get('name', 'A valet')} is requesting to go online",
            {"type": "online_request", "valet_id": current_user['id']}
        )

    return {"message": "Request sent to your manager"}
