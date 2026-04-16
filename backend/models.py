"""Pydantic models and enums."""
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import Optional
from datetime import datetime, timezone
import uuid


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
    PENDING_PAYMENT = "pending_payment"


class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: str
    name: str
    phone_number: Optional[str] = None
    role: str = "valet"
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


class RetrieveRequest(BaseModel):
    phone_number: str


class PushSubscription(BaseModel):
    subscription: dict
