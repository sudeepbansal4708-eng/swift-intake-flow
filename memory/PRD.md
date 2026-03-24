# SwiftValet - Product Requirements Document

## Original Problem Statement
Build a valet parking platform called "SwiftValet" with four user roles: Customer (WhatsApp), Valet Driver (React PWA), Admin (manage drivers/tips/cars), and Super Admin (manage admins/analytics).

## User Roles
- **Customer**: Interacts via WhatsApp (no app needed)
- **Valet Driver**: Uses React PWA, logs in via OTP
- **Admin**: Manages valets, tips, car statuses — logs in via OTP
- **Super Admin**: Manages Admins, platform-wide analytics (password login only)

## Authentication
- OTP Login (Valets + Admins): Phone → 6-digit OTP → 10-min expiry
- Password Login (Super Admin only): Email + password
- Dev mode: OTP always displayed on screen (WhatsApp not configured)

## Completed Features
- JWT auth (hybrid: password for super admin, OTP for admin/valet)
- Multi-step vehicle intake with optional GPS
- Twilio WhatsApp notifications (sandbox mode)
- Retrieval ticket system (webhook code ready, blocked on user config)
- **Admin Panel**: 
  - Collapsible My Profile (name, client name, **profile photo upload**)
  - Collapsible Team Management (valet CRUD, license verification)
  - **Clickable stat cards**: Active Valets → detail modal, Vehicles → parked list with landmarks, Tips → breakdown
  - Tab navigation to Reporting dashboard
- **Admin Reporting ("The Nightly Pulse")**:
  - Tonight's Performance, Valet Leaderboard, Peak Hour Heatmap, Wait-List Alert, Financial Reconciliation, CSV Export
- **Super Admin Panel**:
  - Client management (create/delete), per-client report modal (Drivers, Parked Now, Tips, Parked Today)
  - Archive for deactivated clients (collapsible)
- Inline delete confirmation (no browser dialogs)

## Key API Endpoints
- `/api/auth/login`, `/api/auth/otp/request`, `/api/auth/otp/verify`, `/api/auth/me`
- `/api/admin/dashboard-stats` - Clickable card details (valets, vehicles, tips)
- `/api/admin/profile` (PUT), `/api/admin/profile/photo` (POST)
- `/api/admin/reporting`, `/api/admin/reporting/export`
- `/api/super-admin/clients/{client_id}/report`
- `/api/vehicles`, `/api/tickets`, `/api/admin/valets`, `/api/admin/tips`

## Tech Stack
- Backend: FastAPI, Motor, Pydantic, JWT, Twilio SDK
- Frontend: React, Tailwind, Shadcn/UI, Recharts, Axios
- Database: MongoDB

## Known Issues
- RETR Webhook BLOCKED (user must configure Twilio webhook URL)
- Tips data is placeholder until payment integration
- GPS optional, Twilio in sandbox mode

## Upcoming Tasks
1. P1: Phase C — Ghosting Protocol (5-min timer, return to park)
2. P2: Phase D — Handover & Gratuity (payment/tipping integration)
3. Future: Drip tip reminders, PWA push notifications
4. Refactoring: Split server.py into modular route files
