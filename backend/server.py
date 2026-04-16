"""Valet Guys - FastAPI Application Entry Point."""
import os
import logging
from fastapi import FastAPI
from fastapi.security import HTTPBearer
from starlette.middleware.cors import CORSMiddleware

from config import db, client, pwd_context
from utils import get_password_hash

# Import all routers
from routers import auth, vehicles, tickets, admin, super_admin, public

# Create the main app
app = FastAPI(title="Valet Guys API")

# Include all routers under /api prefix
from fastapi import APIRouter
api_router = APIRouter(prefix="/api")
api_router.include_router(auth.router)
api_router.include_router(vehicles.router)
api_router.include_router(tickets.router)
api_router.include_router(admin.router)
api_router.include_router(super_admin.router)
api_router.include_router(public.router)
app.include_router(api_router)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@app.on_event("startup")
async def seed_super_admin():
    """Ensure the super admin account exists on startup."""
    existing = await db.users.find_one({"email": "superadmin@swiftvalet.com"})
    if not existing:
        from models import User
        from datetime import datetime, timezone
        user_obj = User(
            email="superadmin@swiftvalet.com",
            name="Super Admin",
            role="super_admin",
            password_hash=get_password_hash("superadmin123"),
        )
        doc = user_obj.model_dump()
        doc['created_at'] = doc['created_at'].isoformat()
        await db.users.insert_one(doc)
        logger.info("Super admin account seeded.")


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
