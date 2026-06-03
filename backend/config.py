"""Shared configuration: DB, env vars, clients, constants."""
import os
from pathlib import Path
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext
from fastapi.security import HTTPBearer

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Also read frontend .env for REACT_APP_BACKEND_URL (Emergent updates this for production)
_frontend_env = ROOT_DIR.parent / 'frontend' / '.env'
if _frontend_env.exists():
    load_dotenv(_frontend_env, override=False)

# App Base URL — prefer explicit BACKEND_URL from backend/.env (custom domain),
# fall back to REACT_APP_BACKEND_URL (auto-set by Emergent to deploy hostname)
APP_BASE_URL = os.environ.get('BACKEND_URL') or os.environ.get('REACT_APP_BACKEND_URL', '')

# MongoDB
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Security
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()
SECRET_KEY = os.environ.get('JWT_SECRET', 'your-secret-key-change-in-production')
ALGORITHM = "HS256"

# Cashfree Payment Gateway
CASHFREE_CLIENT_ID = os.environ.get('CASHFREE_CLIENT_ID', '')
CASHFREE_CLIENT_SECRET = os.environ.get('CASHFREE_CLIENT_SECRET', '')
CASHFREE_BASE_URL = os.environ.get('CASHFREE_BASE_URL', 'https://api.cashfree.com/pg')
CASHFREE_API_VERSION = os.environ.get('CASHFREE_API_VERSION', '2025-01-01')

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
