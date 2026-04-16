"""Admin routes: valets management, profile, dashboard, reporting, checkout, tips, cleanup."""
import io
import csv
import base64
import logging
from typing import Optional
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from fastapi.responses import StreamingResponse

from config import db, WA_TEMPLATE_TIP
from models import Ticket, ValetCreate, PushSubscription
from utils import (
    get_current_user, send_whatsapp_message, send_push_notification,
    get_client_valet_fee, get_client_wait_timer,
)
from config import VAPID_PUBLIC_KEY

router = APIRouter(prefix="/admin", tags=["admin"])
logger = logging.getLogger(__name__)


@router.post("/vehicles/{vehicle_id}/checkout")
async def admin_checkout_vehicle(vehicle_id: str, current_user: dict = Depends(get_current_user)):
    """Admin or valet manual checkout: mark vehicle as handed over, send WhatsApp thank-you."""
    if current_user['role'] not in ['admin', 'super_admin', 'valet']:
        raise HTTPException(status_code=403, detail="Access required")

    vehicle = await db.vehicles.find_one({"id": vehicle_id}, {"_id": 0})
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    now = datetime.now(timezone.utc).isoformat()

    pending_ticket = await db.tickets.find_one({
        "vehicle_id": vehicle_id,
        "status": "pending_payment"
    }, {"_id": 0})
    if pending_ticket:
        raise HTTPException(status_code=400, detail="Cannot checkout — valet fee payment is still pending from the customer")

    active_ticket = await db.tickets.find_one({
        "vehicle_id": vehicle_id,
        "status": {"$in": ["open", "claimed", "en_route", "arrived"]}
    }, {"_id": 0})

    if active_ticket:
        await db.tickets.update_one(
            {"id": active_ticket['id']},
            {"$set": {"status": "completed", "completed_at": now}}
        )
    else:
        ticket_obj = Ticket(
            vehicle_id=vehicle_id,
            customer_phone=vehicle['phone_number'],
            status="completed"
        )
        doc = ticket_obj.model_dump()
        doc['created_at'] = now
        doc['completed_at'] = now
        doc['claimed_by'] = current_user['id']
        doc['claimed_at'] = now
        await db.tickets.insert_one(doc)

    await db.vehicles.update_one(
        {"id": vehicle_id},
        {"$set": {"status": "checked_out", "checked_out_at": now, "checked_out_by": current_user['id']}}
    )

    client_name_msg = current_user.get('client_name', 'Valet Guys')
    message = f"Thank you for parking at {client_name_msg}. We hope you enjoyed your time here.\nThe Valet Guys"
    await send_whatsapp_message(
        vehicle['phone_number'], message,
        content_sid=WA_TEMPLATE_TIP,
        content_variables={"1": current_user.get('name', 'your valet'), "2": client_name_msg}
    )

    return {"message": "Vehicle checked out successfully", "vehicle_id": vehicle_id}


@router.get("/valets")
async def get_valets(current_user: dict = Depends(get_current_user)):
    if current_user['role'] not in ['admin', 'super_admin']:
        raise HTTPException(status_code=403, detail="Admin access required")

    query = {}
    if current_user['role'] == 'admin':
        query['client_id'] = current_user.get('client_id')

    valets = await db.users.find(query, {"_id": 0, "password_hash": 0}).to_list(1000)
    return valets


@router.put("/valets/{valet_id}/toggle-online")
async def toggle_valet_online(valet_id: str, current_user: dict = Depends(get_current_user)):
    if current_user['role'] not in ['admin', 'super_admin']:
        raise HTTPException(status_code=403, detail="Admin access required")

    valet = await db.users.find_one({"id": valet_id, "role": "valet"}, {"_id": 0})
    if not valet:
        raise HTTPException(status_code=404, detail="Valet not found")

    new_status = not valet.get('is_online', False)
    await db.users.update_one({"id": valet_id}, {"$set": {"is_online": new_status}})

    if new_status:
        await db.online_requests.delete_many({"valet_id": valet_id})

    return {"is_online": new_status, "valet_id": valet_id}


@router.get("/online-requests")
async def get_online_requests(current_user: dict = Depends(get_current_user)):
    if current_user['role'] not in ['admin', 'super_admin']:
        raise HTTPException(status_code=403, detail="Admin access required")

    requests = await db.online_requests.find(
        {"client_id": current_user.get('client_id'), "status": "pending"},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    return requests


@router.put("/profile")
async def update_admin_profile(
    name: Optional[str] = None,
    client_name: Optional[str] = None,
    valet_fee: Optional[float] = None,
    wait_timer: Optional[int] = None,
    current_user: dict = Depends(get_current_user)
):
    if current_user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")

    update_data = {}
    if name:
        update_data['name'] = name
    if client_name:
        update_data['client_name'] = client_name
    if valet_fee is not None:
        update_data['valet_fee'] = valet_fee
    if wait_timer is not None:
        update_data['wait_timer'] = max(1, min(wait_timer, 30))

    if not update_data:
        raise HTTPException(status_code=400, detail="No data to update")

    result = await db.users.update_one(
        {"id": current_user['id']},
        {"$set": update_data}
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Admin not found")

    if client_name:
        await db.users.update_many(
            {"client_id": current_user.get('client_id'), "role": "valet"},
            {"$set": {"client_name": client_name}}
        )

    return {"message": "Profile updated successfully", "name": name, "client_name": client_name, "valet_fee": valet_fee, "wait_timer": wait_timer}


@router.post("/profile/photo")
async def upload_profile_photo(
    photo: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    if current_user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")

    photo_data = await photo.read()
    photo_base64 = base64.b64encode(photo_data).decode('utf-8')
    photo_url = f"data:{photo.content_type};base64,{photo_base64}"

    await db.users.update_one(
        {"id": current_user['id']},
        {"$set": {"profile_photo": photo_url}}
    )

    return {"message": "Profile photo updated", "profile_photo": photo_url}


@router.get("/dashboard-stats")
async def get_admin_dashboard_stats(current_user: dict = Depends(get_current_user)):
    if current_user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")

    client_id = current_user.get('client_id')
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()

    active_valets = await db.users.find(
        {"client_id": client_id, "role": "valet", "is_active": True},
        {"_id": 0, "id": 1, "name": 1, "phone_number": 1, "email": 1, "driver_license_number": 1}
    ).to_list(500)

    valet_ids = [v['id'] for v in active_valets]
    team_ids = valet_ids + [current_user['id']]

    parked_vehicles = []
    vehicles = await db.vehicles.find(
        {"parked_by": {"$in": team_ids}, "status": {"$ne": "checked_out"}},
        {"_id": 0}
    ).sort("parked_at", -1).to_list(5000)

    valet_name_map = {v['id']: v['name'] for v in active_valets}
    valet_name_map[current_user['id']] = current_user.get('name', 'Admin')

    for v in vehicles:
        parked_vehicles.append({
            "id": v.get('id'),
            "license_plate": v.get('license_plate'),
            "phone_number": v.get('phone_number'),
            "tag_number": v.get('tag_number'),
            "zone_label": v.get('zone_label', ''),
            "parked_at": v.get('parked_at'),
            "parked_by_name": valet_name_map.get(v.get('parked_by'), 'Unknown'),
        })

    tips_today = await db.tips.find(
        {"created_at": {"$gte": today_start}},
        {"_id": 0}
    ).to_list(5000)

    tip_breakdown = []
    for t in tips_today:
        valet_name = "Unknown"
        if t.get('valet_id'):
            valet = await db.users.find_one({"id": t['valet_id']}, {"_id": 0, "name": 1})
            if valet:
                valet_name = valet.get('name', 'Unknown')
        tip_breakdown.append({
            "amount": t.get('amount', 0),
            "status": t.get('status', 'pending'),
            "valet_name": valet_name,
            "created_at": t.get('created_at', ''),
        })

    return {
        "active_valets": active_valets,
        "parked_vehicles": parked_vehicles,
        "tips": tip_breakdown,
        "totals": {
            "valets": len(active_valets),
            "vehicles": len(parked_vehicles),
            "tips_amount": sum(t.get('amount', 0) for t in tips_today),
        }
    }


@router.post("/valets")
async def create_valet(valet_data: ValetCreate, current_user: dict = Depends(get_current_user)):
    if current_user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")

    from models import User
    phone = valet_data.phone_number.strip()
    if not phone.startswith('+'):
        phone = '+' + phone

    existing_phone = await db.users.find_one({"phone_number": phone, "role": "valet"})
    if existing_phone:
        raise HTTPException(status_code=400, detail="Phone number already registered to another valet")

    # Auto-generate email from phone
    email = f"{phone.replace('+', '')}@valetguys.local"
    existing_email = await db.users.find_one({"email": email})
    if existing_email:
        raise HTTPException(status_code=400, detail="Account already exists for this phone number")

    user_obj = User(
        email=email,
        name=valet_data.name,
        phone_number=phone,
        role="valet",
        client_id=current_user.get('client_id'),
        client_name=current_user.get('client_name'),
        driver_license_number=valet_data.driver_license_number,
    )

    doc = user_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()

    await db.users.insert_one(doc)

    return {"message": "Valet created", "user": {"id": user_obj.id, "email": user_obj.email, "name": user_obj.name, "phone_number": phone}}


@router.delete("/valets/{valet_id}")
async def delete_valet(valet_id: str, current_user: dict = Depends(get_current_user)):
    if current_user['role'] not in ['admin', 'super_admin']:
        raise HTTPException(status_code=403, detail="Admin access required")

    query = {"id": valet_id}
    if current_user['role'] == 'admin':
        query['client_id'] = current_user.get('client_id')

    result = await db.users.update_one(query, {"$set": {"is_active": False}})

    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Valet not found")

    return {"message": "Valet deactivated"}


@router.post("/valets/{valet_id}/license")
async def upload_driver_license(
    valet_id: str,
    license_number: str = Form(...),
    license_photo: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    if current_user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")

    photo_data = await license_photo.read()
    photo_base64 = base64.b64encode(photo_data).decode('utf-8')
    photo_url = f"data:{license_photo.content_type};base64,{photo_base64}"

    result = await db.users.update_one(
        {"id": valet_id, "client_id": current_user.get('client_id')},
        {"$set": {
            "driver_license_number": license_number,
            "driver_license_photo": photo_url
        }}
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Valet not found")

    return {"message": "Driver license uploaded", "license_number": license_number}


@router.get("/tips")
async def get_tips(current_user: dict = Depends(get_current_user)):
    if current_user['role'] not in ['admin', 'super_admin']:
        raise HTTPException(status_code=403, detail="Admin access required")

    tips = await db.tips.find({}, {"_id": 0}).to_list(1000)
    return tips


@router.get("/reporting")
async def get_admin_reporting(current_user: dict = Depends(get_current_user)):
    """Admin Reporting Dashboard - The Nightly Pulse."""
    if current_user['role'] not in ['admin', 'super_admin']:
        raise HTTPException(status_code=403, detail="Admin access required")

    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_iso = today_start.isoformat()

    vehicle_query = {"parked_at": {"$gte": today_iso}}
    ticket_query = {"created_at": {"$gte": today_iso}}

    vehicles_today = await db.vehicles.find(vehicle_query, {"_id": 0}).to_list(5000)
    all_tickets_today = await db.tickets.find(ticket_query, {"_id": 0}).to_list(5000)

    cars_parked = len(vehicles_today)
    completed_tickets = [t for t in all_tickets_today if t.get('status') == 'completed']
    cars_retrieved = len(completed_tickets)
    active_inventory = cars_parked - cars_retrieved

    retrieval_times = []
    for t in completed_tickets:
        try:
            created = datetime.fromisoformat(t['created_at'])
            completed = datetime.fromisoformat(t['completed_at'])
            diff_mins = (completed - created).total_seconds() / 60.0
            retrieval_times.append(diff_mins)
        except Exception:
            pass

    avg_retrieval_mins = round(sum(retrieval_times) / len(retrieval_times), 1) if retrieval_times else 0
    if avg_retrieval_mins == 0:
        retrieval_status = "green"
    elif avg_retrieval_mins < 8:
        retrieval_status = "green"
    elif avg_retrieval_mins <= 12:
        retrieval_status = "amber"
    else:
        retrieval_status = "red"

    tips_today = await db.tips.find({"created_at": {"$gte": today_iso}}, {"_id": 0}).to_list(5000)
    total_tips = sum(t.get('amount', 0) for t in tips_today)
    tip_links_sent = len(completed_tickets)
    tips_paid = len([t for t in tips_today if t.get('status') == 'paid'])
    collection_rate = round((tips_paid / tip_links_sent * 100), 1) if tip_links_sent > 0 else 0

    valet_ids_parked = [v.get('parked_by') for v in vehicles_today if v.get('parked_by')]
    valet_ids_retrieved = [t.get('claimed_by') for t in completed_tickets if t.get('claimed_by')]
    all_valet_ids = list(set(valet_ids_parked + valet_ids_retrieved))

    valets_data = []
    if all_valet_ids:
        valet_users = await db.users.find({"id": {"$in": all_valet_ids}}, {"_id": 0}).to_list(500)
        valet_map = {v['id']: v for v in valet_users}

        for vid in all_valet_ids:
            valet_info = valet_map.get(vid, {})
            parked_count = sum(1 for v in vehicles_today if v.get('parked_by') == vid)
            retrieved_tickets = [t for t in completed_tickets if t.get('claimed_by') == vid]
            retrieved_count = len(retrieved_tickets)

            valet_retrieval_times = []
            for t in retrieved_tickets:
                try:
                    created = datetime.fromisoformat(t['created_at'])
                    completed = datetime.fromisoformat(t['completed_at'])
                    valet_retrieval_times.append((completed - created).total_seconds() / 60.0)
                except Exception:
                    pass
            avg_speed = round(sum(valet_retrieval_times) / len(valet_retrieval_times), 1) if valet_retrieval_times else 0

            valet_tips = sum(t.get('amount', 0) for t in tips_today if t.get('valet_id') == vid)

            valets_data.append({
                "id": vid,
                "name": valet_info.get('name', 'Unknown'),
                "cars_parked": parked_count,
                "cars_retrieved": retrieved_count,
                "avg_retrieval_speed": avg_speed,
                "tips_earned": valet_tips
            })

    valets_data.sort(key=lambda x: x['cars_parked'] + x['cars_retrieved'], reverse=True)

    hourly = {}
    for h in range(24):
        hourly[h] = {"hour": h, "intake": 0, "retrieval": 0}

    for v in vehicles_today:
        try:
            hour = datetime.fromisoformat(v['parked_at']).hour
            hourly[hour]["intake"] += 1
        except Exception:
            pass

    for t in all_tickets_today:
        try:
            hour = datetime.fromisoformat(t['created_at']).hour
            hourly[hour]["retrieval"] += 1
        except Exception:
            pass

    hourly_data = list(hourly.values())

    ten_mins_ago = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
    overdue_tickets = await db.tickets.find({
        "status": {"$in": ["open", "claimed", "en_route"]},
        "created_at": {"$lte": ten_mins_ago}
    }, {"_id": 0}).to_list(500)

    waitlist = []
    for ot in overdue_tickets:
        vehicle = await db.vehicles.find_one({"id": ot.get('vehicle_id')}, {"_id": 0})
        created = datetime.fromisoformat(ot['created_at'])
        wait_mins = round((datetime.now(timezone.utc) - created).total_seconds() / 60.0, 1)
        waitlist.append({
            "ticket_id": ot['id'],
            "status": ot['status'],
            "license_plate": vehicle.get('license_plate', 'N/A') if vehicle else 'N/A',
            "customer_phone": ot.get('customer_phone', 'N/A'),
            "wait_minutes": wait_mins,
            "created_at": ot['created_at']
        })

    waitlist.sort(key=lambda x: x['wait_minutes'], reverse=True)

    pending_tips = len([t for t in tips_today if t.get('status') == 'pending'])
    paid_tips_total = sum(t.get('amount', 0) for t in tips_today if t.get('status') == 'paid')
    platform_fee_rate = 0.05
    platform_fees = round(paid_tips_total * platform_fee_rate, 2)

    payout_data = []
    for vd in valets_data:
        valet_paid = sum(t.get('amount', 0) for t in tips_today if t.get('valet_id') == vd['id'] and t.get('status') == 'paid')
        payout_data.append({
            "valet_name": vd['name'],
            "tips_earned": vd['tips_earned'],
            "payout_amount": round(valet_paid * (1 - platform_fee_rate), 2)
        })

    return {
        "summary": {
            "cars_parked": cars_parked,
            "cars_retrieved": cars_retrieved,
            "active_inventory": active_inventory,
            "avg_retrieval_mins": avg_retrieval_mins,
            "retrieval_status": retrieval_status,
            "total_tips": total_tips,
            "collection_rate": collection_rate,
        },
        "leaderboard": valets_data,
        "hourly_volume": hourly_data,
        "waitlist": waitlist,
        "financial": {
            "pending_tips_count": pending_tips,
            "paid_tips_total": paid_tips_total,
            "platform_fees": platform_fees,
            "payout": payout_data,
        }
    }


@router.get("/reporting/export")
async def export_reporting_csv(current_user: dict = Depends(get_current_user)):
    """Export financial reconciliation as CSV."""
    if current_user['role'] not in ['admin', 'super_admin']:
        raise HTTPException(status_code=403, detail="Admin access required")

    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_iso = today_start.isoformat()

    tips = await db.tips.find({"created_at": {"$gte": today_iso}}, {"_id": 0}).to_list(5000)

    valet_ids = list(set(t.get('valet_id') for t in tips if t.get('valet_id')))
    valets = await db.users.find({"id": {"$in": valet_ids}}, {"_id": 0}).to_list(500) if valet_ids else []
    valet_map = {v['id']: v.get('name', 'Unknown') for v in valets}

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Valet Name", "Tip Amount (INR)", "Status", "Date"])

    for tip in tips:
        writer.writerow([
            valet_map.get(tip.get('valet_id'), 'Unknown'),
            tip.get('amount', 0),
            tip.get('status', 'pending'),
            tip.get('created_at', '')
        ])

    if not tips:
        writer.writerow(["No tip data for today", "", "", ""])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=valetguys_payout_{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.csv"}
    )


@router.delete("/cleanup-data")
async def cleanup_old_data(current_user: dict = Depends(get_current_user)):
    """Super admin or admin can purge all completed/old tickets and checked-out vehicles."""
    if current_user['role'] not in ['admin', 'super_admin']:
        raise HTTPException(status_code=403, detail="Admin access required")

    query = {}
    if current_user['role'] == 'admin':
        query['client_id'] = current_user.get('client_id')

    t_result = await db.tickets.delete_many({
        **query,
        "status": {"$in": ["completed", "returned"]}
    })

    v_result = await db.vehicles.delete_many({
        **({} if current_user['role'] == 'super_admin' else {"parked_by": {"$exists": True}}),
        "status": "checked_out"
    })

    return {
        "tickets_deleted": t_result.deleted_count,
        "vehicles_deleted": v_result.deleted_count
    }
