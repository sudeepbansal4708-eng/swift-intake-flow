"""Super Admin routes: manage clients/admins, analytics, reports."""
import uuid
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends

from config import db
from models import User, AdminCreate
from utils import get_current_user

router = APIRouter(prefix="/super-admin", tags=["super-admin"])
logger = logging.getLogger(__name__)


@router.get("/clients")
async def get_clients(current_user: dict = Depends(get_current_user)):
    if current_user['role'] != 'super_admin':
        raise HTTPException(status_code=403, detail="Super admin access required")

    admins = await db.users.find({"role": "admin"}, {"_id": 0, "password_hash": 0}).to_list(1000)

    for admin in admins:
        client_id = admin.get('client_id')
        if client_id:
            valets_count = await db.users.count_documents({"client_id": client_id, "role": "valet", "is_active": True})
            vehicles_count = await db.vehicles.count_documents({})
            admin['stats'] = {
                "valets": valets_count,
                "vehicles": vehicles_count
            }

    return admins


@router.get("/analytics")
async def get_super_admin_analytics(current_user: dict = Depends(get_current_user)):
    if current_user['role'] != 'super_admin':
        raise HTTPException(status_code=403, detail="Super admin access required")

    total_clients = await db.users.count_documents({"role": "admin", "is_active": True})

    active_tickets = await db.tickets.find(
        {"status": {"$in": ["open", "claimed", "en_route", "arrived"]}},
        {"_id": 0, "vehicle_id": 1}
    ).to_list(1000)
    active_vehicle_ids = list(set([t['vehicle_id'] for t in active_tickets]))
    cars_parked_now = len(active_vehicle_ids)

    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    tips_today = await db.tips.find({
        "created_at": {"$gte": today_start.isoformat()},
        "status": "paid"
    }, {"_id": 0}).to_list(1000)
    total_tips_today = sum([tip.get('amount', 0) for tip in tips_today])

    total_vehicles = await db.vehicles.count_documents({})
    total_valets = await db.users.count_documents({"role": "valet", "is_active": True})

    tickets_today = await db.tickets.count_documents({
        "created_at": {"$gte": today_start.isoformat()}
    })

    return {
        "total_clients": total_clients,
        "cars_parked_now": cars_parked_now,
        "total_tips_today": total_tips_today,
        "total_vehicles": total_vehicles,
        "total_valets": total_valets,
        "tickets_today": tickets_today
    }


@router.post("/admins")
async def create_admin(admin_data: AdminCreate, current_user: dict = Depends(get_current_user)):
    if current_user['role'] != 'super_admin':
        raise HTTPException(status_code=403, detail="Super admin access required")

    phone = admin_data.phone_number.strip()
    if not phone.startswith('+'):
        phone = '+' + phone

    existing = await db.users.find_one({"email": admin_data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    existing_phone = await db.users.find_one({"phone_number": phone, "role": "admin"})
    if existing_phone:
        raise HTTPException(status_code=400, detail="Phone number already registered to another admin")

    user_obj = User(
        email=admin_data.email,
        name=admin_data.name,
        phone_number=phone,
        role="admin",
        client_id=str(uuid.uuid4()),
        client_name=admin_data.client_name,
    )

    doc = user_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()

    await db.users.insert_one(doc)

    return {
        "message": "Admin created",
        "user": {
            "id": user_obj.id,
            "email": user_obj.email,
            "name": user_obj.name,
            "phone_number": phone,
            "client_id": user_obj.client_id,
            "client_name": user_obj.client_name
        }
    }


@router.delete("/admins/{admin_id}")
async def delete_admin(admin_id: str, current_user: dict = Depends(get_current_user)):
    if current_user['role'] != 'super_admin':
        raise HTTPException(status_code=403, detail="Super admin access required")

    result = await db.users.update_one(
        {"id": admin_id, "role": "admin"},
        {"$set": {"is_active": False}}
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Admin not found")

    return {"message": "Admin deactivated"}


@router.get("/clients/{client_id}/report")
async def get_client_report(client_id: str, current_user: dict = Depends(get_current_user)):
    if current_user['role'] != 'super_admin':
        raise HTTPException(status_code=403, detail="Super admin access required")

    admin = await db.users.find_one({"client_id": client_id, "role": "admin"}, {"_id": 0})
    if not admin:
        raise HTTPException(status_code=404, detail="Client not found")

    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_iso = today_start.isoformat()

    num_drivers = await db.users.count_documents({"client_id": client_id, "role": "valet", "is_active": True})

    valets = await db.users.find({"client_id": client_id, "role": "valet"}, {"_id": 0, "id": 1}).to_list(500)
    valet_ids = [v['id'] for v in valets]

    cars_parked_today = 0
    if valet_ids:
        cars_parked_today = await db.vehicles.count_documents({
            "parked_by": {"$in": valet_ids},
            "parked_at": {"$gte": today_iso}
        })

    cars_parked_now = 0
    if valet_ids:
        vehicles_by_client = await db.vehicles.find(
            {"parked_by": {"$in": valet_ids}},
            {"_id": 0, "id": 1}
        ).to_list(5000)
        client_vehicle_ids = [v['id'] for v in vehicles_by_client]
        if client_vehicle_ids:
            completed_today = await db.tickets.count_documents({
                "vehicle_id": {"$in": client_vehicle_ids},
                "status": "completed",
                "completed_at": {"$gte": today_iso}
            })
            cars_parked_now = cars_parked_today - completed_today
            if cars_parked_now < 0:
                cars_parked_now = 0

    tips_today = 0

    return {
        "client_id": client_id,
        "client_name": admin.get('client_name', 'Unknown'),
        "admin_name": admin.get('name', 'Unknown'),
        "num_drivers": num_drivers,
        "cars_parked_now": cars_parked_now,
        "cars_parked_today": cars_parked_today,
        "tips_today": tips_today,
    }
