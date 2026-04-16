"""Shared configuration: DB, env vars, clients, constants."""
import os
from pathlib import Path
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext
from fastapi.security import HTTPBearer

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Security
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()
SECRET_KEY = os.environ.get('JWT_SECRET', 'your-secret-key-change-in-production')
ALGORITHM = "HS256"

# Razorpay
RAZORPAY_KEY_ID = os.environ.get('RAZORPAY_KEY_ID', '')
RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET', '')
try:
    import razorpay
    if RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET:
        razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
    else:
        razorpay_client = None
except ImportError:
    razorpay_client = None

# Twilio
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID', '')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN', '')
TWILIO_WHATSAPP_FROM = os.environ.get('TWILIO_WHATSAPP_FROM', '')

from twilio.rest import Client as TwilioClient
if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
    twilio_client = TwilioClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
else:
    twilio_client = None

# VAPID push notification
VAPID_PRIVATE_KEY = os.environ.get('VAPID_PRIVATE_KEY', '')
VAPID_PUBLIC_KEY = os.environ.get('VAPID_PUBLIC_KEY', '')
VAPID_CLAIMS_EMAIL = os.environ.get('VAPID_CLAIMS_EMAIL', 'mailto:admin@valetguys.com')

# WhatsApp template SIDs
WA_TEMPLATE_PARKING = os.environ.get('WA_TEMPLATE_PARKING', '')
WA_TEMPLATE_ARRIVED = os.environ.get('WA_TEMPLATE_ARRIVED', '')
WA_TEMPLATE_RETRIEVAL = os.environ.get('WA_TEMPLATE_RETRIEVAL', '')
WA_TEMPLATE_RETURNED = os.environ.get('WA_TEMPLATE_RETURNED', '')
WA_TEMPLATE_TIP = os.environ.get('WA_TEMPLATE_TIP', '')
WA_TEMPLATE_FEE = os.environ.get('WA_TEMPLATE_FEE', '')
MESSAGING_MODE = os.environ.get('MESSAGING_MODE', 'sms')
