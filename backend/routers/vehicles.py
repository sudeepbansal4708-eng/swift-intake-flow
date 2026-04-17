"""Vehicle routes: create, list, upload photo, update location, lookup."""
import os
import base64
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form

from config import db, WA_TEMPLATE_PARKING
from models import Vehicle, VehicleCreate
from utils import get_current_user, send_whatsapp_message

router = APIRouter(prefix="/vehicles", tags=["vehicles"])
logger = logging.getLogger(__name__)


@router.post("")
async def create_vehicle(vehicle_data: VehicleCreate, current_user: dict = Depends(get_current_user)):
    if current_user['role'] == 'valet' and not current_user.get('is_online'):
        raise HTTPException(status_code=403, detail="You must be marked online by your manager to park vehicles")

    vehicle_dict = vehicle_data.model_dump()
    vehicle_dict['parked_by'] = current_user['id']
    vehicle_obj = Vehicle(**vehicle_dict)

    doc = vehicle_obj.model_dump()
    doc['parked_at'] = doc['parked_at'].isoformat()

    await db.vehicles.insert_one(doc)

    valet = await db.users.find_one({"id": current_user['id']}, {"_id": 0})
    client_name = valet.get('client_name', 'Valet Guys') if valet else 'Valet Guys'
    valet_name = current_user.get('name', 'our valet driver')

    backend_url = os.environ.get('BACKEND_URL', '')
    retrieve_url = f"{backend_url}/retrieve/{vehicle_obj.id}"

    # Build Google Maps link from GPS if available, otherwise use retrieve URL
    gps_lat = vehicle_obj.gps_latitude
    gps_lng = vehicle_obj.gps_longitude
    if gps_lat and gps_lng and gps_lat != 0:
        maps_link = f"https://www.google.com/maps?q={gps_lat},{gps_lng}"
    else:
        maps_link = retrieve_url

    message = f"Thank you for parking with the Valet Guys at {client_name}. Your car {vehicle_obj.license_plate} has been parked at {maps_link} by our valet driver {valet_name}.\nPlease reply RETR when you are ready to pick up your car."

    sms_result = await send_whatsapp_message(
        vehicle_obj.phone_number, message,
        content_sid=WA_TEMPLATE_PARKING,
        content_variables={"1": client_name, "2": vehicle_obj.license_plate, "3": maps_link, "4": valet_name}
    )
    logger.info(f"Message result for {vehicle_obj.phone_number}: {sms_result}")

    return {"vehicle": vehicle_obj.model_dump(), "message": "Vehicle parked successfully"}


@router.post("/upload-photo")
async def upload_vehicle_photo(vehicle_id: str = Form(...), photo: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    photo_data = await photo.read()
    photo_base64 = base64.b64encode(photo_data).decode('utf-8')
    photo_url = f"data:{photo.content_type};base64,{photo_base64}"

    await db.vehicles.update_one(
        {"id": vehicle_id},
        {"$set": {"photo_url": photo_url}}
    )

    return {"message": "Photo uploaded", "photo_url": photo_url}


@router.get("")
async def get_vehicles(current_user: dict = Depends(get_current_user)):
    vehicles = await db.vehicles.find({}, {"_id": 0}).to_list(1000)

    for vehicle in vehicles:
        if isinstance(vehicle.get('parked_at'), str):
            vehicle['parked_at'] = vehicle['parked_at']

    return vehicles


@router.put("/{vehicle_id}/location")
async def update_vehicle_location(
    vehicle_id: str,
    zone_label: Optional[str] = None,
    gps_latitude: Optional[float] = None,
    gps_longitude: Optional[float] = None,
    current_user: dict = Depends(get_current_user)
):
    vehicle = await db.vehicles.find_one({"id": vehicle_id}, {"_id": 0})
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    update_data = {}
    if zone_label is not None:
        update_data['zone_label'] = zone_label
    if gps_latitude is not None:
        update_data['gps_latitude'] = gps_latitude
    if gps_longitude is not None:
        update_data['gps_longitude'] = gps_longitude

    await db.vehicles.update_one(
        {"id": vehicle_id},
        {"$set": update_data}
    )

    if zone_label:
        message = f"Valet Guys: Your vehicle has been moved to a new location: {zone_label}."
        await send_whatsapp_message(vehicle['phone_number'], message)

    return {"message": "Location updated", "vehicle_id": vehicle_id}


@router.get("/lookup")
async def lookup_vehicle_by_phone(phone: str, current_user: dict = Depends(get_current_user)):
    phone = phone.strip()
    if not phone.startswith('+'):
        phone = '+' + phone

    vehicle = await db.vehicles.find_one(
        {"phone_number": phone},
        {"_id": 0},
        sort=[("parked_at", -1)]
    )
    if not vehicle:
        raise HTTPException(status_code=404, detail="No vehicle found for this phone number")

    existing_ticket = await db.tickets.find_one({
        "vehicle_id": vehicle['id'],
        "status": {"$in": ["open", "claimed", "en_route", "arrived"]}
    }, {"_id": 0})

    return {
        "vehicle": {
            "id": vehicle.get("id"),
            "license_plate": vehicle.get("license_plate"),
            "tag_number": vehicle.get("tag_number"),
            "zone_label": vehicle.get("zone_label"),
            "phone_number": vehicle.get("phone_number"),
            "parked_at": vehicle.get("parked_at"),
        },
        "has_active_ticket": existing_ticket is not None
    }
