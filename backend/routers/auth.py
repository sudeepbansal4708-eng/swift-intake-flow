"""Auth routes: register, login, OTP."""
import random
import logging
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException, Depends

from config import db
from models import User, UserCreate, UserLogin, OTPRequest, OTPVerify
from utils import (
    create_access_token, verify_password, get_password_hash,
    get_current_user, send_sms,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register")
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
        "user": {"id": user_obj.id, "email": user_obj.email, "name": user_obj.name, "role": user_obj.role}
    }


@router.post("/login")
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
            "id": user['id'], "email": user['email'], "name": user['name'],
            "role": user['role'], "client_name": user.get('client_name'),
            "client_id": user.get('client_id'), "is_online": user.get('is_online', False)
        }
    }


@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    return {
        "id": current_user['id'], "email": current_user['email'],
        "name": current_user['name'], "role": current_user['role'],
        "client_name": current_user.get('client_name'),
        "client_id": current_user.get('client_id'),
        "profile_photo": current_user.get('profile_photo'),
        "is_online": current_user.get('is_online', False),
        "valet_fee": current_user.get('valet_fee', 0),
        "fee_enabled": current_user.get('fee_enabled', False),
        "wait_timer": current_user.get('wait_timer', 5),
    }


@router.post("/otp/request")
async def request_otp(data: OTPRequest):
    phone = data.phone_number.strip()
    if not phone.startswith('+'):
        phone = '+' + phone

    user = await db.users.find_one({"phone_number": phone, "role": {"$in": ["valet", "admin"]}, "is_active": True}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="No account found with this phone number")

    otp = str(random.randint(100000, 999999))
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)

    await db.otps.delete_many({"phone_number": phone})
    await db.otps.insert_one({
        "phone_number": phone, "otp": otp,
        "expires_at": expires_at.isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat()
    })

    message = f"Your Valet Guys login code is: {otp}\n\nThis code expires in 10 minutes."
    result = await send_sms(phone, message)
    logging.info(f"OTP SMS sent to {phone}: result={result}")

    return {"message": "OTP sent via SMS", "phone_number": phone, "dev_otp": otp}


@router.post("/otp/verify")
async def verify_otp(data: OTPVerify):
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

    user = await db.users.find_one({"phone_number": phone, "role": {"$in": ["valet", "admin"]}, "is_active": True}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="Account not found")

    token = create_access_token({"sub": user['email'], "role": user['role']})
    return {
        "token": token,
        "user": {
            "id": user['id'], "email": user['email'], "name": user['name'],
            "role": user['role'], "client_name": user.get('client_name'),
            "client_id": user.get('client_id'), "is_online": user.get('is_online', False)
        }
    }
