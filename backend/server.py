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
from datetime import datetime, timezone, timedelta
import jwt
from passlib.context import CryptContext
import razorpay
import base64
import httpx
from bson import ObjectId
from twilio.rest import Client as TwilioClient


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
    role: str = "valet"
    password_hash: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = True

class UserCreate(BaseModel):
    email: EmailStr
    name: str
    password: str
    role: str = "valet"

class UserLogin(BaseModel):
    email: EmailStr
    password: str

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

async def send_whatsapp_message(phone_number: str, message: str):
    """Send WhatsApp message via Twilio API"""
    if not twilio_client or not TWILIO_WHATSAPP_FROM:
        logging.warning(f"❌ Twilio WhatsApp not configured. Would send to {phone_number}: {message}")
        return {"status": "not_configured", "message": "Twilio WhatsApp credentials not set"}
    
    try:
        # Format phone number for WhatsApp (must have whatsapp: prefix for Twilio)
        to_whatsapp = f"whatsapp:{phone_number}" if not phone_number.startswith("whatsapp:") else phone_number
        from_whatsapp = f"whatsapp:{TWILIO_WHATSAPP_FROM}" if not TWILIO_WHATSAPP_FROM.startswith("whatsapp:") else TWILIO_WHATSAPP_FROM
        
        logging.info(f"📱 Attempting to send WhatsApp message...")
        logging.info(f"   From: {from_whatsapp}")
        logging.info(f"   To: {to_whatsapp}")
        logging.info(f"   Message preview: {message[:50]}...")
        
        # Send message via Twilio (synchronous call)
        twilio_message = twilio_client.messages.create(
            body=message,
            from_=from_whatsapp,
            to=to_whatsapp
        )
        
        logging.info(f"✅ WhatsApp message sent successfully!")
        logging.info(f"   Message SID: {twilio_message.sid}")
        logging.info(f"   Status: {twilio_message.status}")
        
        return {
            "status": "sent",
            "message_sid": twilio_message.sid,
            "twilio_status": twilio_message.status
        }
    except Exception as e:
        logging.error(f"❌ Twilio WhatsApp send error: {str(e)}")
        logging.error(f"   Error type: {type(e).__name__}")
        return {"status": "error", "message": str(e)}

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
            "role": user['role']
        }
    }

@api_router.get("/auth/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    return {
        "id": current_user['id'],
        "email": current_user['email'],
        "name": current_user['name'],
        "role": current_user['role']
    }

@api_router.post("/vehicles")
async def create_vehicle(vehicle_data: VehicleCreate, current_user: dict = Depends(get_current_user)):
    vehicle_dict = vehicle_data.model_dump()
    vehicle_dict['parked_by'] = current_user['id']
    vehicle_obj = Vehicle(**vehicle_dict)
    
    doc = vehicle_obj.model_dump()
    doc['parked_at'] = doc['parked_at'].isoformat()
    
    await db.vehicles.insert_one(doc)
    
    # Send WhatsApp notification
    print(f"🔔 PREPARING TO SEND WHATSAPP to {vehicle_obj.phone_number}")
    location_info = f"Zone: {vehicle_obj.zone_label}" if vehicle_obj.zone_label else "Location saved"
    tag_info = f"\n🏷️ Tag Number: {vehicle_obj.tag_number}" if vehicle_obj.tag_number else ""
    message = f"🚗 Welcome to SwiftValet!\n\nYour vehicle (Plate: {vehicle_obj.license_plate}) is safely parked.\n{location_info}{tag_info}\n\nReply 'RETR' when you're ready to retrieve your car."
    
    whatsapp_result = await send_whatsapp_message(vehicle_obj.phone_number, message)
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
    
    return ticket_obj.model_dump()

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
    
    message = f"🔔 Great news! Valet {current_user['name']} is preparing to fetch your car."
    await send_whatsapp_message(ticket['customer_phone'], message)
    
    return {"message": "Ticket claimed"}

@api_router.put("/tickets/{ticket_id}/status")
async def update_ticket_status(ticket_id: str, status: str, current_user: dict = Depends(get_current_user)):
    ticket = await db.tickets.find_one({"id": ticket_id}, {"_id": 0})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    update_data = {"status": status}
    
    if status == "en_route":
        message = f"🚗 Valet {current_user['name']} is on the way to fetch your car!"
        await send_whatsapp_message(ticket['customer_phone'], message)
    
    elif status == "arrived":
        update_data['arrived_at'] = datetime.now(timezone.utc).isoformat()
        message = f"✅ Your car is at the entrance! We can hold it for 5 minutes."
        await send_whatsapp_message(ticket['customer_phone'], message)
    
    elif status == "completed":
        update_data['completed_at'] = datetime.now(timezone.utc).isoformat()
        
        # Generate tip payment link
        if razorpay_client:
            try:
                payment_link = razorpay_client.payment_link.create({
                    "amount": 500,
                    "currency": "INR",
                    "description": f"Tip for Valet Service",
                    "customer": {
                        "contact": ticket['customer_phone']
                    },
                    "notify": {
                        "sms": False,
                        "email": False
                    },
                    "callback_url": f"{os.environ.get('BACKEND_URL', '')}/api/tips/callback",
                    "callback_method": "get"
                })
                
                message = f"🎉 Thank you for using SwiftValet!\n\nIf you'd like to tip your valet, you can do so here:\n{payment_link['short_url']}\n\nPreset amounts: ₹50, ₹100, ₹200 or custom."
            except Exception as e:
                logging.error(f"Razorpay error: {str(e)}")
                message = f"🎉 Thank you for using SwiftValet! Your feedback means a lot to us."
        else:
            message = f"🎉 Thank you for using SwiftValet!"
        
        await send_whatsapp_message(ticket['customer_phone'], message)
    
    await db.tickets.update_one({"id": ticket_id}, {"$set": update_data})
    
    return {"message": "Status updated"}

@api_router.get("/admin/valets")
async def get_valets(current_user: dict = Depends(get_current_user)):
    if current_user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    
    valets = await db.users.find({}, {"_id": 0, "password_hash": 0}).to_list(1000)
    return valets

@api_router.delete("/admin/valets/{valet_id}")
async def delete_valet(valet_id: str, current_user: dict = Depends(get_current_user)):
    if current_user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await db.users.update_one(
        {"id": valet_id},
        {"$set": {"is_active": False}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Valet not found")
    
    return {"message": "Valet deactivated"}

@api_router.get("/admin/tips")
async def get_tips(current_user: dict = Depends(get_current_user)):
    if current_user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    
    tips = await db.tips.find({}, {"_id": 0}).to_list(1000)
    return tips

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
        
        print(f"🎉 Created retrieval ticket for vehicle {vehicle['license_plate']}")
        
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