from fastapi import FastAPI, APIRouter, HTTPException, Depends, UploadFile, File, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional
import uuid
import random
from datetime import datetime, timezone, timedelta
import jwt
from passlib.context import CryptContext
import razorpay
import base64
import httpx
import json
from bson import ObjectId
from twilio.rest import Client as TwilioClient
from pywebpush import webpush, WebPushException


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Security
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()
SECRET_KEY = os.environ.get('JWT_SECRET', 'your-secret-key-change-in-production')
ALGORITHM = "HS256"

# Razorpay (will be configured when keys are provided)
RAZORPAY_KEY_ID = os.environ.get('RAZORPAY_KEY_ID', '')
RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET', '')

if RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET:
    razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
else:
    razorpay_client = None

# Twilio WhatsApp config
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID', '')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN', '')
TWILIO_WHATSAPP_FROM = os.environ.get('TWILIO_WHATSAPP_FROM', '')

if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
    twilio_client = TwilioClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
else:
    twilio_client = None

# VAPID push notification config
VAPID_PRIVATE_KEY = os.environ.get('VAPID_PRIVATE_KEY', '')
VAPID_PUBLIC_KEY = os.environ.get('VAPID_PUBLIC_KEY', '')
VAPID_CLAIMS_EMAIL = os.environ.get('VAPID_CLAIMS_EMAIL', 'mailto:admin@parkaro.com')

# WhatsApp Content Template SIDs
WA_TEMPLATE_PARKING = os.environ.get('WA_TEMPLATE_PARKING', '')
WA_TEMPLATE_ARRIVED = os.environ.get('WA_TEMPLATE_ARRIVED', '')
WA_TEMPLATE_RETRIEVAL = os.environ.get('WA_TEMPLATE_RETRIEVAL', '')
WA_TEMPLATE_RETURNED = os.environ.get('WA_TEMPLATE_RETURNED', '')

# Create the main app
app = FastAPI()
api_router = APIRouter(prefix="/api")

# Models
class UserRole(str):
    VALET = "valet"
    ADMIN = "admin"

class TicketStatus(str):
    PARKED = "parked"
    OPEN = "open"
    CLAIMED = "claimed"
    EN_ROUTE = "en_route"
    ARRIVED = "arrived"
    COMPLETED = "completed"
    RETURNED = "returned"

class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: str
    name: str
    phone_number: Optional[str] = None
    role: str = "valet"  # valet, admin, super_admin
    client_id: Optional[str] = None
    client_name: Optional[str] = None
    driver_license_number: Optional[str] = None
    driver_license_photo: Optional[str] = None
    password_hash: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = True

class UserCreate(BaseModel):
    email: EmailStr
    name: str
    password: Optional[str] = None
    role: str = "valet"
    client_id: Optional[str] = None
    client_name: Optional[str] = None
    driver_license_number: Optional[str] = None
    phone_number: Optional[str] = None

class ValetCreate(BaseModel):
    email: EmailStr
    name: str
    phone_number: str
    driver_license_number: Optional[str] = None

class AdminCreate(BaseModel):
    email: EmailStr
    name: str
    phone_number: str
    client_name: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class OTPRequest(BaseModel):
    phone_number: str

class OTPVerify(BaseModel):
    phone_number: str
    otp: str

class Vehicle(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    phone_number: str
    license_plate: str
    tag_number: Optional[str] = None
    photo_url: Optional[str] = None
    gps_latitude: Optional[float] = None
    gps_longitude: Optional[float] = None
    zone_label: Optional[str] = None
    parked_by: str
    parked_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class VehicleCreate(BaseModel):
    phone_number: str
    license_plate: str
    tag_number: Optional[str] = None
    gps_latitude: Optional[float] = None
    gps_longitude: Optional[float] = None
    zone_label: Optional[str] = None

class Ticket(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    vehicle_id: str
    customer_phone: str
    status: str = "open"
    claimed_by: Optional[str] = None
    claimed_at: Optional[datetime] = None
    arrived_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Tip(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    ticket_id: str
    valet_id: str
    amount: float
    razorpay_order_id: Optional[str] = None
    razorpay_payment_id: Optional[str] = None
    status: str = "pending"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    paid_at: Optional[datetime] = None

# Helper functions
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
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def send_whatsapp_message(phone_number: str, message: str, content_sid: str = None, content_variables: dict = None):
    """Send WhatsApp message via Twilio API using content templates or fallback to free-form"""
    if not twilio_client or not TWILIO_WHATSAPP_FROM:
        logging.warning(f"Twilio WhatsApp not configured. Would send to {phone_number}: {message}")
        return {"status": "not_configured", "message": "Twilio WhatsApp credentials not set"}
    
    try:
        to_whatsapp = f"whatsapp:{phone_number}" if not phone_number.startswith("whatsapp:") else phone_number
        from_whatsapp = f"whatsapp:{TWILIO_WHATSAPP_FROM}" if not TWILIO_WHATSAPP_FROM.startswith("whatsapp:") else TWILIO_WHATSAPP_FROM
        
        logging.info(f"Sending WhatsApp: From={from_whatsapp} To={to_whatsapp}")
        
        msg_params = {
            "from_": from_whatsapp,
            "to": to_whatsapp
        }
        
        if content_sid:
            msg_params["content_sid"] = content_sid
            if content_variables:
                msg_params["content_variables"] = json.dumps(content_variables)
        else:
            msg_params["body"] = message
        
        twilio_message = twilio_client.messages.create(**msg_params)
        
        logging.info(f"WhatsApp message sent: SID={twilio_message.sid}, Status={twilio_message.status}")
        
        return {
            "status": "sent",
            "message_sid": twilio_message.sid,
            "twilio_status": twilio_message.status
        }
    except Exception as e:
        logging.error(f"Twilio WhatsApp send error: {str(e)}")
        return {"status": "error", "message": str(e)}


async def send_push_notification(user_id: str, title: str, body: str, data: dict = None):
    """Send push notification to a specific user's subscribed devices"""
    if not VAPID_PRIVATE_KEY:
        logging.warning("VAPID keys not configured, skipping push notification")
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
            logging.warning(f"Push failed for user {user_id}: {e}")
            if e.response and e.response.status_code in (404, 410):
                await db.push_subscriptions.delete_one({"_id": sub.get("_id")})
        except Exception as e:
            logging.error(f"Push notification error: {e}")


async def notify_team_of_retrieval(vehicle: dict, ticket_id: str):
    """Send push notifications to all active valets and admin for a client when retrieval is requested"""
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

    # Get all active valets + admin for this client
    team_members = await db.users.find(
        {"client_id": client_id, "is_active": True, "role": {"$in": ["valet", "admin"]}},
        {"_id": 0, "id": 1}
    ).to_list(500)

    for member in team_members:
        await send_push_notification(member["id"], title, body, data)

# Routes
@api_router.post("/auth/register")
async def register(user_data: UserCreate):
    existing = await db.users.find_one({"email": user_data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_dict = user_data.model_dump()
    user_dict['password_hash'] = get_password_hash(user_dict.pop('password'))
    user_obj = User(**user_dict)
    
    doc = user_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    
    await db.users.insert_one(doc)
    
    token = create_access_token({"sub": user_obj.email, "role": user_obj.role})
    return {
        "token": token,
        "user": {
            "id": user_obj.id,
            "email": user_obj.email,
            "name": user_obj.name,
            "role": user_obj.role
        }
    }

@api_router.post("/auth/login")
async def login(credentials: UserLogin):
    user = await db.users.find_one({"email": credentials.email}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not verify_password(credentials.password, user['password_hash']):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not user.get('is_active', True):
        raise HTTPException(status_code=401, detail="Account is inactive")
    
    token = create_access_token({"sub": user['email'], "role": user['role']})
    return {
        "token": token,
        "user": {
            "id": user['id'],
            "email": user['email'],
            "name": user['name'],
            "role": user['role'],
            "client_name": user.get('client_name'),
            "client_id": user.get('client_id'),
            "is_online": user.get('is_online', False)
        }
    }

@api_router.get("/auth/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    return {
        "id": current_user['id'],
        "email": current_user['email'],
        "name": current_user['name'],
        "role": current_user['role'],
        "client_name": current_user.get('client_name'),
        "client_id": current_user.get('client_id'),
        "profile_photo": current_user.get('profile_photo'),
        "is_online": current_user.get('is_online', False)
    }

@api_router.post("/auth/otp/request")
async def request_otp(data: OTPRequest):
    """Send OTP to valet or admin's WhatsApp number"""
    phone = data.phone_number.strip()
    if not phone.startswith('+'):
        phone = '+' + phone

    user = await db.users.find_one({"phone_number": phone, "role": {"$in": ["valet", "admin"]}}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="No account found with this phone number")

    if not user.get('is_active', True):
        raise HTTPException(status_code=401, detail="Account is inactive")

    otp = str(random.randint(100000, 999999))
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)

    await db.otps.delete_many({"phone_number": phone})
    await db.otps.insert_one({
        "phone_number": phone,
        "otp": otp,
        "expires_at": expires_at.isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat()
    })

    message = f"Your ParKaro login code is: {otp}\n\nThis code expires in 10 minutes."
    whatsapp_result = await send_whatsapp_message(phone, message)
    logging.info(f"OTP sent to {phone}: result={whatsapp_result}")

    # Always include OTP in response until WhatsApp is fully configured
    response = {"message": "OTP sent to your WhatsApp", "phone_number": phone, "dev_otp": otp}
    return response

@api_router.post("/auth/otp/verify")
async def verify_otp(data: OTPVerify):
    """Verify OTP and return JWT token"""
    phone = data.phone_number.strip()
    if not phone.startswith('+'):
        phone = '+' + phone

    otp_record = await db.otps.find_one({"phone_number": phone}, {"_id": 0})
    if not otp_record:
        raise HTTPException(status_code=400, detail="No OTP found. Please request a new one.")

    if otp_record['otp'] != data.otp.strip():
        raise HTTPException(status_code=400, detail="Invalid OTP")

    expires_at = datetime.fromisoformat(otp_record['expires_at'])
    if datetime.now(timezone.utc) > expires_at:
        await db.otps.delete_many({"phone_number": phone})
        raise HTTPException(status_code=400, detail="OTP expired. Please request a new one.")

    await db.otps.delete_many({"phone_number": phone})

    user = await db.users.find_one({"phone_number": phone, "role": {"$in": ["valet", "admin"]}}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="Account not found")

    token = create_access_token({"sub": user['email'], "role": user['role']})
    return {
        "token": token,
        "user": {
            "id": user['id'],
            "email": user['email'],
            "name": user['name'],
            "role": user['role'],
            "client_name": user.get('client_name'),
            "client_id": user.get('client_id'),
            "is_online": user.get('is_online', False)
        }
    }

@api_router.post("/vehicles")
async def create_vehicle(vehicle_data: VehicleCreate, current_user: dict = Depends(get_current_user)):
    # Only online valets can park
    if current_user['role'] == 'valet' and not current_user.get('is_online'):
        raise HTTPException(status_code=403, detail="You must be marked online by your manager to park vehicles")

    vehicle_dict = vehicle_data.model_dump()
    vehicle_dict['parked_by'] = current_user['id']
    vehicle_obj = Vehicle(**vehicle_dict)
    
    doc = vehicle_obj.model_dump()
    doc['parked_at'] = doc['parked_at'].isoformat()
    
    await db.vehicles.insert_one(doc)
    
    # Send WhatsApp notification with client branding
    print(f"🔔 PREPARING TO SEND WHATSAPP to {vehicle_obj.phone_number}")
    
    # Get client name from the valet who parked it
    valet = await db.users.find_one({"id": current_user['id']}, {"_id": 0})
    client_name = valet.get('client_name', 'ParKaro') if valet else 'ParKaro'
    
    location_info = vehicle_obj.zone_label or "Location saved"
    
    message = f"Your car {vehicle_obj.license_plate} has been parked at {location_info} by our valet team. Reply RETR when you're ready to pick it up."
    
    whatsapp_result = await send_whatsapp_message(
        vehicle_obj.phone_number, message,
        content_sid=WA_TEMPLATE_PARKING,
        content_variables={"1": vehicle_obj.license_plate, "2": location_info}
    )
    print(f"🔔 WHATSAPP RESULT: {whatsapp_result}")
    
    return {"vehicle": vehicle_obj.model_dump(), "message": "Vehicle parked successfully"}

@api_router.post("/vehicles/upload-photo")
async def upload_vehicle_photo(vehicle_id: str = Form(...), photo: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    photo_data = await photo.read()
    photo_base64 = base64.b64encode(photo_data).decode('utf-8')
    photo_url = f"data:{photo.content_type};base64,{photo_base64}"
    
    await db.vehicles.update_one(
        {"id": vehicle_id},
        {"$set": {"photo_url": photo_url}}
    )
    
    return {"message": "Photo uploaded", "photo_url": photo_url}

@api_router.get("/vehicles")
async def get_vehicles(current_user: dict = Depends(get_current_user)):
    vehicles = await db.vehicles.find({}, {"_id": 0}).to_list(1000)
    
    for vehicle in vehicles:
        if isinstance(vehicle.get('parked_at'), str):
            vehicle['parked_at'] = datetime.fromisoformat(vehicle['parked_at']).isoformat()
    
    return vehicles

@api_router.put("/vehicles/{vehicle_id}/location")
async def update_vehicle_location(
    vehicle_id: str,
    zone_label: Optional[str] = None,
    gps_latitude: Optional[float] = None,
    gps_longitude: Optional[float] = None,
    current_user: dict = Depends(get_current_user)
):
    """Update vehicle parking location (used when returning to different spot)"""
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
    
    # Send WhatsApp notification about new location
    if zone_label:
        message = f"🔄 Your vehicle has been moved to a new location:\n\n📍 {zone_label}\n\nThis spot is closer/better for pickup!"
        await send_whatsapp_message(vehicle['phone_number'], message)
    
    return {"message": "Location updated", "vehicle_id": vehicle_id}

@api_router.post("/tickets")
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
    
    # Send push notifications to team
    await notify_team_of_retrieval(vehicle, ticket_obj.id)
    
    return ticket_obj.model_dump()


class RetrieveRequest(BaseModel):
    phone_number: str


@api_router.post("/tickets/retrieve")
async def retrieve_vehicle(data: RetrieveRequest, current_user: dict = Depends(get_current_user)):
    """Valet-initiated retrieval: lookup vehicle by customer phone and auto-assign ticket"""
    # Only online valets can retrieve
    if current_user['role'] == 'valet' and not current_user.get('is_online'):
        raise HTTPException(status_code=403, detail="You must be marked online by your manager to retrieve vehicles")

    phone = data.phone_number.strip()
    if not phone.startswith('+'):
        phone = '+' + phone

    # Find the most recently parked vehicle for this phone number
    vehicle = await db.vehicles.find_one(
        {"phone_number": phone},
        {"_id": 0},
        sort=[("parked_at", -1)]
    )
    if not vehicle:
        raise HTTPException(status_code=404, detail="No vehicle found for this phone number")

    # Check for existing active ticket
    existing = await db.tickets.find_one({
        "vehicle_id": vehicle['id'],
        "status": {"$in": ["open", "claimed", "en_route", "arrived"]}
    })
    if existing:
        raise HTTPException(status_code=400, detail="A retrieval ticket already exists for this vehicle")

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

    # Send push notifications to team
    await notify_team_of_retrieval(vehicle, ticket_obj.id)

    # Send WhatsApp notification to customer
    message = f"Your car {vehicle['license_plate']} is being retrieved by valet {current_user['name']}."
    await send_whatsapp_message(
        phone, message,
        content_sid=WA_TEMPLATE_RETRIEVAL,
        content_variables={"1": vehicle['license_plate'], "2": current_user['name']}
    )

    # Build clean response without _id
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


@api_router.get("/vehicles/lookup")
async def lookup_vehicle_by_phone(phone: str, current_user: dict = Depends(get_current_user)):
    """Lookup the most recent vehicle for a given phone number"""
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

    # Check if there's already an active ticket
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

@api_router.get("/tickets")
async def get_tickets(status: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    query = {}
    if status:
        query['status'] = status
    
    tickets = await db.tickets.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    
    # Batch fetch all vehicles to avoid N+1 query pattern
    vehicle_ids = list(set([ticket['vehicle_id'] for ticket in tickets if ticket.get('vehicle_id')]))
    
    if vehicle_ids:
        vehicles_list = await db.vehicles.find({"id": {"$in": vehicle_ids}}, {"_id": 0}).to_list(1000)
        vehicles_map = {v['id']: v for v in vehicles_list}
        
        # Enrich tickets with vehicle data
        for ticket in tickets:
            if isinstance(ticket.get('created_at'), str):
                ticket['created_at'] = datetime.fromisoformat(ticket['created_at']).isoformat()
            
            vehicle = vehicles_map.get(ticket['vehicle_id'])
            if vehicle:
                ticket['vehicle'] = {
                    "license_plate": vehicle['license_plate'],
                    "phone_number": vehicle['phone_number'],
                    "tag_number": vehicle.get('tag_number'),
                    "zone_label": vehicle.get('zone_label'),
                    "photo_url": vehicle.get('photo_url')
                }
    else:
        # No vehicles to fetch, just format timestamps
        for ticket in tickets:
            if isinstance(ticket.get('created_at'), str):
                ticket['created_at'] = datetime.fromisoformat(ticket['created_at']).isoformat()
    
    return tickets

@api_router.put("/tickets/{ticket_id}/claim")
async def claim_ticket(ticket_id: str, current_user: dict = Depends(get_current_user)):
    ticket = await db.tickets.find_one({"id": ticket_id, "status": "open"}, {"_id": 0})
    if not ticket:
        raise HTTPException(status_code=400, detail="Ticket not available")
    
    result = await db.tickets.update_one(
        {"id": ticket_id, "status": "open"},
        {
            "$set": {
                "status": "claimed",
                "claimed_by": current_user['id'],
                "claimed_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=400, detail="Ticket already claimed")
    
    message = f"Your car {vehicle.get('license_plate', '')} is being retrieved by valet {current_user['name']}."
    await send_whatsapp_message(
        ticket['customer_phone'], message,
        content_sid=WA_TEMPLATE_RETRIEVAL,
        content_variables={"1": vehicle.get('license_plate', 'your car'), "2": current_user['name']}
    )
    
    return {"message": "Ticket claimed"}

@api_router.put("/tickets/{ticket_id}/status")
async def update_ticket_status(ticket_id: str, status: str, current_user: dict = Depends(get_current_user)):
    ticket = await db.tickets.find_one({"id": ticket_id}, {"_id": 0})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    # Get vehicle info for template variables
    vehicle = await db.vehicles.find_one({"id": ticket.get('vehicle_id')}, {"_id": 0})
    plate = vehicle.get('license_plate', 'your car') if vehicle else 'your car'
    
    update_data = {"status": status}
    
    if status == "en_route":
        message = f"Your car {plate} is being retrieved by valet {current_user['name']}."
        await send_whatsapp_message(
            ticket['customer_phone'], message,
            content_sid=WA_TEMPLATE_RETRIEVAL,
            content_variables={"1": plate, "2": current_user['name']}
        )
    
    elif status == "arrived":
        update_data['arrived_at'] = datetime.now(timezone.utc).isoformat()
        message = f"Your car {plate} is at the entrance! We can hold it for 5 minutes. Please come to the pickup area."
        await send_whatsapp_message(
            ticket['customer_phone'], message,
            content_sid=WA_TEMPLATE_ARRIVED,
            content_variables={"1": plate}
        )
    
    elif status == "returned":
        now = datetime.now(timezone.utc).isoformat()
        update_data['returned_at'] = now

        # Reset vehicle back to active parking
        await db.vehicles.update_one(
            {"id": ticket['vehicle_id']},
            {"$set": {"status": "parked"}}
        )

        message = f"Your car {plate} has been returned to parking as you did not arrive within 5 minutes. Please contact the valet desk when you are ready."
        await send_whatsapp_message(
            ticket['customer_phone'], message,
            content_sid=WA_TEMPLATE_RETURNED,
            content_variables={"1": plate}
        )

    elif status == "completed":
        update_data['completed_at'] = datetime.now(timezone.utc).isoformat()
        
        # Mark vehicle as checked out
        await db.vehicles.update_one(
            {"id": ticket['vehicle_id']},
            {"$set": {"status": "checked_out", "checked_out_at": update_data['completed_at']}}
        )
        
        # Send thank you (free-form within 24hr window since customer interacted)
        message = "Thank you for using ParKaro! We hope you had a great experience."
        await send_whatsapp_message(ticket['customer_phone'], message)
    
    await db.tickets.update_one({"id": ticket_id}, {"$set": update_data})
    
    return {"message": "Status updated"}

@api_router.get("/valet/dashboard-stats")
async def get_valet_dashboard_stats(current_user: dict = Depends(get_current_user)):
    """Get individual valet dashboard stats"""
    if current_user['role'] not in ['valet', 'admin']:
        raise HTTPException(status_code=403, detail="Valet or admin access required")

    valet_id = current_user['id']
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()

    # Cars parked today by this valet
    cars_parked_today = await db.vehicles.count_documents({
        "parked_by": valet_id,
        "parked_at": {"$gte": today_start}
    })

    # Cars retrieved today by this valet (tickets claimed_by this valet and completed today)
    cars_retrieved_today = await db.tickets.count_documents({
        "claimed_by": valet_id,
        "status": "completed",
        "completed_at": {"$gte": today_start}
    })

    # Tips today for this valet
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


class PushSubscription(BaseModel):
    subscription: dict


@api_router.post("/admin/vehicles/{vehicle_id}/checkout")
async def admin_checkout_vehicle(vehicle_id: str, current_user: dict = Depends(get_current_user)):
    """Admin manual checkout: mark vehicle as handed over, send WhatsApp thank-you"""
    if current_user['role'] not in ['admin', 'super_admin']:
        raise HTTPException(status_code=403, detail="Admin access required")

    vehicle = await db.vehicles.find_one({"id": vehicle_id}, {"_id": 0})
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    now = datetime.now(timezone.utc).isoformat()

    # Check if there's an active ticket for this vehicle
    active_ticket = await db.tickets.find_one({
        "vehicle_id": vehicle_id,
        "status": {"$in": ["open", "claimed", "en_route", "arrived"]}
    }, {"_id": 0})

    if active_ticket:
        # Complete the existing ticket
        await db.tickets.update_one(
            {"id": active_ticket['id']},
            {"$set": {"status": "completed", "completed_at": now}}
        )
    else:
        # Create a completed ticket for record-keeping
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

    # Mark vehicle as checked out
    await db.vehicles.update_one(
        {"id": vehicle_id},
        {"$set": {"status": "checked_out", "checked_out_at": now, "checked_out_by": current_user['id']}}
    )

    # Send WhatsApp thank-you message (free-form within conversation window)
    message = f"Thank you for using ParKaro! Your vehicle ({vehicle['license_plate']}) has been checked out. We hope you had a great experience!"
    await send_whatsapp_message(vehicle['phone_number'], message)

    return {"message": "Vehicle checked out successfully", "vehicle_id": vehicle_id}


@api_router.post("/push/subscribe")
async def push_subscribe(data: PushSubscription, current_user: dict = Depends(get_current_user)):
    """Store a push subscription for the current user"""
    endpoint = data.subscription.get("endpoint", "")
    if not endpoint:
        raise HTTPException(status_code=400, detail="Invalid subscription")

    # Upsert: one subscription per endpoint per user
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


@api_router.post("/push/unsubscribe")
async def push_unsubscribe(data: PushSubscription, current_user: dict = Depends(get_current_user)):
    """Remove a push subscription"""
    endpoint = data.subscription.get("endpoint", "")
    await db.push_subscriptions.delete_one({
        "user_id": current_user['id'],
        "subscription.endpoint": endpoint
    })
    return {"message": "Unsubscribed from push notifications"}


@api_router.get("/push/vapid-key")
async def get_vapid_public_key():
    """Return the VAPID public key for the frontend"""
    return {"public_key": VAPID_PUBLIC_KEY}


@api_router.get("/admin/valets")
async def get_valets(current_user: dict = Depends(get_current_user)):
    if current_user['role'] not in ['admin', 'super_admin']:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Admin sees only their client's valets
    # Super admin sees all
    query = {}
    if current_user['role'] == 'admin':
        query['client_id'] = current_user.get('client_id')
    
    valets = await db.users.find(query, {"_id": 0, "password_hash": 0}).to_list(1000)
    return valets


@api_router.put("/admin/valets/{valet_id}/toggle-online")
async def toggle_valet_online(valet_id: str, current_user: dict = Depends(get_current_user)):
    """Admin toggles a valet's online/offline status"""
    if current_user['role'] not in ['admin', 'super_admin']:
        raise HTTPException(status_code=403, detail="Admin access required")

    valet = await db.users.find_one({"id": valet_id, "role": "valet"}, {"_id": 0})
    if not valet:
        raise HTTPException(status_code=404, detail="Valet not found")

    new_status = not valet.get('is_online', False)
    await db.users.update_one({"id": valet_id}, {"$set": {"is_online": new_status}})

    # If going online, clear any pending online request
    if new_status:
        await db.online_requests.delete_many({"valet_id": valet_id})

    return {"is_online": new_status, "valet_id": valet_id}


@api_router.post("/valet/request-online")
async def valet_request_online(current_user: dict = Depends(get_current_user)):
    """Valet sends a request to their admin to be marked online"""
    if current_user['role'] != 'valet':
        raise HTTPException(status_code=403, detail="Valet access required")

    if current_user.get('is_online'):
        return {"message": "You are already online"}

    # Check for existing pending request
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

    # Notify admin(s) via push
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


@api_router.get("/admin/online-requests")
async def get_online_requests(current_user: dict = Depends(get_current_user)):
    """Get pending online requests for this admin's team"""
    if current_user['role'] not in ['admin', 'super_admin']:
        raise HTTPException(status_code=403, detail="Admin access required")

    requests = await db.online_requests.find(
        {"client_id": current_user.get('client_id'), "status": "pending"},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    return requests

@api_router.put("/admin/profile")
async def update_admin_profile(
    name: Optional[str] = None,
    client_name: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Update admin profile (name and client name)"""
    if current_user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    
    update_data = {}
    if name:
        update_data['name'] = name
    if client_name:
        update_data['client_name'] = client_name
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No data to update")
    
    result = await db.users.update_one(
        {"id": current_user['id']},
        {"$set": update_data}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Admin not found")
    
    # Also update all valets under this admin with new client name
    if client_name:
        await db.users.update_many(
            {"client_id": current_user.get('client_id'), "role": "valet"},
            {"$set": {"client_name": client_name}}
        )
    
    return {"message": "Profile updated successfully", "name": name, "client_name": client_name}

@api_router.post("/admin/profile/photo")
async def upload_profile_photo(
    photo: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Upload admin profile photo"""
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

@api_router.get("/admin/dashboard-stats")
async def get_admin_dashboard_stats(current_user: dict = Depends(get_current_user)):
    """Get admin dashboard card details"""
    if current_user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")

    client_id = current_user.get('client_id')
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()

    # Active valets with details
    active_valets = await db.users.find(
        {"client_id": client_id, "role": "valet", "is_active": True},
        {"_id": 0, "id": 1, "name": 1, "phone_number": 1, "email": 1, "driver_license_number": 1}
    ).to_list(500)

    # Get valet IDs + admin's own ID (admin can also park vehicles)
    valet_ids = [v['id'] for v in active_valets]
    team_ids = valet_ids + [current_user['id']]

    # Parked vehicles (all active, by this client's team, exclude checked out)
    parked_vehicles = []
    vehicles = await db.vehicles.find(
        {"parked_by": {"$in": team_ids}, "status": {"$ne": "checked_out"}},
        {"_id": 0}
    ).sort("parked_at", -1).to_list(5000)

    # Name map includes admin
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

    # Tips today (placeholder)
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

@api_router.post("/admin/valets")
async def create_valet(valet_data: ValetCreate, current_user: dict = Depends(get_current_user)):
    """Admin can create valets for their client (no password — valets use OTP login)"""
    if current_user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Normalize phone number
    phone = valet_data.phone_number.strip()
    if not phone.startswith('+'):
        phone = '+' + phone

    existing = await db.users.find_one({"email": valet_data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    existing_phone = await db.users.find_one({"phone_number": phone, "role": "valet"})
    if existing_phone:
        raise HTTPException(status_code=400, detail="Phone number already registered to another valet")
    
    user_obj = User(
        email=valet_data.email,
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

@api_router.delete("/admin/valets/{valet_id}")
async def delete_valet(valet_id: str, current_user: dict = Depends(get_current_user)):
    if current_user['role'] not in ['admin', 'super_admin']:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Admin can only delete their client's valets
    query = {"id": valet_id}
    if current_user['role'] == 'admin':
        query['client_id'] = current_user.get('client_id')
    
    result = await db.users.update_one(query, {"$set": {"is_active": False}})
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Valet not found")
    
    return {"message": "Valet deactivated"}

@api_router.post("/admin/valets/{valet_id}/license")
async def upload_driver_license(
    valet_id: str,
    license_number: str = Form(...),
    license_photo: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Upload driver license for valet verification"""
    if current_user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Read and encode photo
    photo_data = await license_photo.read()
    photo_base64 = base64.b64encode(photo_data).decode('utf-8')
    photo_url = f"data:{license_photo.content_type};base64,{photo_base64}"
    
    # Update valet with license info
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

@api_router.get("/super-admin/clients")
async def get_clients(current_user: dict = Depends(get_current_user)):
    """Get all clients (admins)"""
    if current_user['role'] != 'super_admin':
        raise HTTPException(status_code=403, detail="Super admin access required")
    
    admins = await db.users.find({"role": "admin"}, {"_id": 0, "password_hash": 0}).to_list(1000)
    
    # Get stats for each client
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

@api_router.get("/super-admin/analytics")
async def get_super_admin_analytics(current_user: dict = Depends(get_current_user)):
    """Get platform-wide analytics for super admin"""
    if current_user['role'] != 'super_admin':
        raise HTTPException(status_code=403, detail="Super admin access required")
    
    # Total clients
    total_clients = await db.users.count_documents({"role": "admin", "is_active": True})
    
    # Total cars parked right now (vehicles that have open/claimed/en_route/arrived tickets)
    active_tickets = await db.tickets.find(
        {"status": {"$in": ["open", "claimed", "en_route", "arrived"]}},
        {"_id": 0, "vehicle_id": 1}
    ).to_list(1000)
    active_vehicle_ids = list(set([t['vehicle_id'] for t in active_tickets]))
    cars_parked_now = len(active_vehicle_ids)
    
    # Total tips for today (cumulative across all clients)
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    tips_today = await db.tips.find({
        "created_at": {"$gte": today_start.isoformat()},
        "status": "paid"
    }, {"_id": 0}).to_list(1000)
    total_tips_today = sum([tip.get('amount', 0) for tip in tips_today])
    
    # Total vehicles all time
    total_vehicles = await db.vehicles.count_documents({})
    
    # Total valets across all clients
    total_valets = await db.users.count_documents({"role": "valet", "is_active": True})
    
    # Total tickets today
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

@api_router.post("/super-admin/admins")
async def create_admin(admin_data: AdminCreate, current_user: dict = Depends(get_current_user)):
    """Super admin can create client admins (no password — admins use OTP login)"""
    if current_user['role'] != 'super_admin':
        raise HTTPException(status_code=403, detail="Super admin access required")
    
    # Normalize phone number
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

@api_router.delete("/super-admin/admins/{admin_id}")
async def delete_admin(admin_id: str, current_user: dict = Depends(get_current_user)):
    """Super admin can deactivate client admins"""
    if current_user['role'] != 'super_admin':
        raise HTTPException(status_code=403, detail="Super admin access required")
    
    result = await db.users.update_one(
        {"id": admin_id, "role": "admin"},
        {"$set": {"is_active": False}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Admin not found")
    
    return {"message": "Admin deactivated"}

@api_router.get("/super-admin/clients/{client_id}/report")
async def get_client_report(client_id: str, current_user: dict = Depends(get_current_user)):
    """Get per-client report for super admin"""
    if current_user['role'] != 'super_admin':
        raise HTTPException(status_code=403, detail="Super admin access required")

    admin = await db.users.find_one({"client_id": client_id, "role": "admin"}, {"_id": 0})
    if not admin:
        raise HTTPException(status_code=404, detail="Client not found")

    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_iso = today_start.isoformat()

    # Number of active drivers
    num_drivers = await db.users.count_documents({"client_id": client_id, "role": "valet", "is_active": True})

    # Get all valet IDs for this client
    valets = await db.users.find({"client_id": client_id, "role": "valet"}, {"_id": 0, "id": 1}).to_list(500)
    valet_ids = [v['id'] for v in valets]

    # Cars parked today by these valets
    cars_parked_today = 0
    if valet_ids:
        cars_parked_today = await db.vehicles.count_documents({
            "parked_by": {"$in": valet_ids},
            "parked_at": {"$gte": today_iso}
        })

    # Cars parked now (vehicles with active tickets, parked by this client's valets)
    cars_parked_now = 0
    if valet_ids:
        vehicles_by_client = await db.vehicles.find(
            {"parked_by": {"$in": valet_ids}},
            {"_id": 0, "id": 1}
        ).to_list(5000)
        client_vehicle_ids = [v['id'] for v in vehicles_by_client]
        if client_vehicle_ids:
            # "now" = parked today minus completed today
            completed_today = await db.tickets.count_documents({
                "vehicle_id": {"$in": client_vehicle_ids},
                "status": "completed",
                "completed_at": {"$gte": today_iso}
            })
            cars_parked_now = cars_parked_today - completed_today
            if cars_parked_now < 0:
                cars_parked_now = 0

    # Tips today (placeholder)
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

@api_router.get("/admin/tips")
async def get_tips(current_user: dict = Depends(get_current_user)):
    if current_user['role'] not in ['admin', 'super_admin']:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    tips = await db.tips.find({}, {"_id": 0}).to_list(1000)
    return tips

@api_router.get("/admin/reporting")
async def get_admin_reporting(current_user: dict = Depends(get_current_user)):
    """Admin Reporting Dashboard - The Nightly Pulse"""
    if current_user['role'] not in ['admin', 'super_admin']:
        raise HTTPException(status_code=403, detail="Admin access required")

    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_iso = today_start.isoformat()

    vehicle_query = {"parked_at": {"$gte": today_iso}}
    ticket_query = {"created_at": {"$gte": today_iso}}

    # Fetch today's vehicles and tickets
    vehicles_today = await db.vehicles.find(vehicle_query, {"_id": 0}).to_list(5000)
    all_tickets_today = await db.tickets.find(ticket_query, {"_id": 0}).to_list(5000)

    cars_parked = len(vehicles_today)
    completed_tickets = [t for t in all_tickets_today if t.get('status') == 'completed']
    cars_retrieved = len(completed_tickets)
    active_inventory = cars_parked - cars_retrieved

    # Avg retrieval time (completed_at - created_at)
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

    # Financial placeholder
    tips_today = await db.tips.find({"created_at": {"$gte": today_iso}}, {"_id": 0}).to_list(5000)
    total_tips = sum(t.get('amount', 0) for t in tips_today)
    tip_links_sent = len(completed_tickets)
    tips_paid = len([t for t in tips_today if t.get('status') == 'paid'])
    collection_rate = round((tips_paid / tip_links_sent * 100), 1) if tip_links_sent > 0 else 0

    # -- Valet Leaderboard --
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

    # -- Hourly Volume --
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

    # -- Wait-List Alert (tickets > 10 mins old, not completed) --
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

    # -- Financial Reconciliation (placeholder structure) --
    pending_tips = len([t for t in tips_today if t.get('status') == 'pending'])
    paid_tips_total = sum(t.get('amount', 0) for t in tips_today if t.get('status') == 'paid')
    platform_fee_rate = 0.05
    platform_fees = round(paid_tips_total * platform_fee_rate, 2)

    # Per-valet payout
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

@api_router.get("/admin/reporting/export")
async def export_reporting_csv(current_user: dict = Depends(get_current_user)):
    """Export financial reconciliation as CSV"""
    if current_user['role'] not in ['admin', 'super_admin']:
        raise HTTPException(status_code=403, detail="Admin access required")

    from fastapi.responses import StreamingResponse
    import io
    import csv

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
        headers={"Content-Disposition": f"attachment; filename=parkaro_payout_{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.csv"}
    )

@api_router.post("/whatsapp/webhook")
async def whatsapp_webhook(From: str = Form(...), Body: str = Form(...)):
    """Handle incoming WhatsApp messages from Twilio
    Twilio sends form data with 'From' and 'Body' fields
    """
    # Twilio sends phone number with 'whatsapp:' prefix, remove it
    phone_number = From.replace('whatsapp:', '').strip()
    
    # Add + if not present
    if not phone_number.startswith('+'):
        phone_number = '+' + phone_number
    
    message = Body.strip()
    message_lower = message.lower()
    
    print(f"📱 Received WhatsApp message from {phone_number}: {message}")
    
    if message_lower in ['retr', 'retrieve', 'get car', 'ready']:
        # Find vehicle by phone
        vehicle = await db.vehicles.find_one({"phone_number": phone_number}, {"_id": 0})
        if not vehicle:
            print(f"❌ No vehicle found for {phone_number}")
            return {"reply": "Sorry, we couldn't find your vehicle. Please contact support."}
        
        print(f"✅ Found vehicle: {vehicle['license_plate']}")
        
        # Check if ticket already exists
        existing_ticket = await db.tickets.find_one({
            "vehicle_id": vehicle['id'],
            "status": {"$in": ["open", "claimed", "en_route", "arrived"]}
        })
        
        if existing_ticket:
            return {"reply": "Your retrieval request is already in progress. A valet will be with you shortly!"}
        
        # Create new ticket
        ticket_obj = Ticket(
            vehicle_id=vehicle['id'],
            customer_phone=phone_number,
            status="open"
        )
        
        doc = ticket_obj.model_dump()
        doc['created_at'] = doc['created_at'].isoformat()
        await db.tickets.insert_one(doc)
        
        # Send push notifications to team
        await notify_team_of_retrieval(vehicle, ticket_obj.id)
        
        print(f"Created retrieval ticket for vehicle {vehicle['license_plate']}")
        
        return {"reply": "🚗 Got it! Your car retrieval request is now active. A valet will claim it shortly and keep you updated!"}
    
    return {"reply": "Hi! Reply 'RETR' when you're ready to retrieve your car."}

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()