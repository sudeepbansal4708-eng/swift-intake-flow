# SwiftValet - Product Requirements Document

## Original Problem Statement
Build a valet parking platform called "SwiftValet" with four user roles: Customer (WhatsApp), Valet Driver (React PWA), Admin (manage drivers/tips/cars), and Super Admin (manage admins/analytics).

## User Roles
- **Customer**: Interacts via WhatsApp (no app needed)
- **Valet Driver**: Uses React PWA, logs in via OTP sent to WhatsApp
- **Admin**: Manages valets, tips, car statuses — logs in via OTP sent to WhatsApp
- **Super Admin**: Manages Admins, platform-wide analytics (password login only)

## Authentication Model
- **OTP Login** (Valets + Admins): Phone number → 6-digit OTP via WhatsApp → 10-min expiry
- **Password Login** (Super Admin only): Email + password
- Dev mode: OTP displayed on screen when WhatsApp not configured

## Core Requirements
### Phase A: Intake & Parking - DONE
### Phase B: Retrieval & Claiming - DONE (Twilio webhook BLOCKED on user config)
### Phase C: Ghosting Protocol - NOT STARTED
### Phase D: Handover & Gratuity - NOT STARTED

## Completed Features
- JWT auth: Super Admin (password), Admin + Valet (OTP via WhatsApp)
- OTP Login for Valets and Admins
- Dev OTP display on login screen when WhatsApp not configured
- Multi-step vehicle intake with optional GPS
- Twilio WhatsApp notifications (sandbox mode)
- Retrieval ticket system (webhook code ready)
- Admin Panel: valet CRUD, license verification, profile editor, collapsible sections
- Super Admin Panel: client management, delete admins, per-client report modal
- Admin Reporting Dashboard - "The Nightly Pulse"
- Per-client report: Drivers, Cars Parked Now, Tips Today, Cars Parked Today

## Admin Reporting Dashboard ("The Nightly Pulse") - DONE
- Section 1: Tonight's Performance (Parked/Retrieved/Active Inventory, Avg Retrieval Time color-coded, Financial Snapshot placeholders)
- Section 2: Valet Leaderboard table
- Section 3: Peak Hour Heatmap, Wait-List Alert
- Section 4: Financial Reconciliation, CSV Export

## Super Admin Per-Client Report - DONE (2026-03-24)
- Click any active client card → modal shows: Number of Drivers, Cars Parked Now, Tips Today, Cars Parked Today
- Delete admin button with stopPropagation (doesn't trigger modal)
- Inactive clients dimmed and non-clickable

## Tech Stack
- **Backend**: FastAPI, Motor (async MongoDB), Pydantic, JWT, Twilio SDK
- **Frontend**: React, React Router, Tailwind CSS, Shadcn/UI, Axios, Recharts
- **Database**: MongoDB

## Key API Endpoints
- `/api/auth/login` - Super Admin login
- `/api/auth/otp/request` - Request OTP (returns dev_otp when WhatsApp not configured)
- `/api/auth/otp/verify` - Verify OTP and get JWT
- `/api/admin/reporting` - Admin reporting dashboard data
- `/api/admin/reporting/export` - CSV export
- `/api/super-admin/clients/{client_id}/report` - Per-client report
- `/api/super-admin/admins` - CRUD admins
- `/api/admin/valets` - CRUD valets

## Known Issues
- **RETR Webhook BLOCKED**: User must configure Twilio webhook URL
- GPS optional, Twilio in sandbox mode
- Tips data is placeholder until payment integration

## Upcoming Tasks (Priority Order)
1. P1: Phase C - Ghosting Protocol (5-min timer, return to park)
2. P2: Phase D - Handover & Gratuity (payment integration)
3. Future: Drip tip reminders, PWA push notifications
4. Refactoring: Split server.py into modular route files
