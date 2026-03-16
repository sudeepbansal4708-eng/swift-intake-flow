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
- No passwords are set for valets or admins — they are created with phone numbers

## Core Requirements
### Phase A: Intake & Parking - DONE
- 2-step intake: Car Handoff (Phone, Plate) → Parking Location (GPS optional, Landmark, Tag Number)
- WhatsApp notification with client branding and tag number

### Phase B: Retrieval & Claiming - DONE (code complete, Twilio webhook BLOCKED on user config)
- Customer replies "RETR" → creates Open Ticket
- Valet claims ticket → opens ticket details immediately
- Simplified status: "ARRIVED" at curb

### Phase C: Ghosting Protocol - NOT STARTED
- 5-minute timer after car arrives
- Return to Park with optional location update

### Phase D: Handover & Gratuity - NOT STARTED
- Handover Complete status
- Preset tipping with payment link

## Admin Reporting Dashboard ("The Nightly Pulse") - DONE (2026-03-16)
- **Section 1: Tonight's Performance** — Cars Parked, Retrieved, Active Inventory, Avg Retrieval Time (color-coded: green <8m, amber 8-12m, red >12m), Financial Snapshot (tips placeholder)
- **Section 2: Valet Leaderboard** — Table: Valet Name | Cars Parked | Cars Retrieved | Avg Speed | Tips Earned
- **Section 3: Efficiency Gaps** — Peak Hour Heatmap (Recharts bar chart), Wait-List Alert (overdue >10 min retrieval requests)
- **Section 4: Financial Reconciliation** — Pending Tips, Paid Tips, Platform Fees, Per-valet Payout Summary, CSV Export
- Shift = each calendar day (midnight UTC)
- Tip data is placeholder until payment integration is live
- Tab navigation between Management and Reporting on Admin pages

## Completed Features
- JWT auth: Super Admin (password), Admin + Valet (OTP via WhatsApp)
- OTP Login for Valets and Admins (completed 2026-03-16)
- Multi-step vehicle intake with optional GPS
- Twilio WhatsApp notifications (sandbox mode)
- Retrieval ticket system (webhook code ready)
- Admin Panel: valet CRUD (with phone number), license verification, profile editor
- Super Admin Panel: client management (with phone number), analytics dashboard
- Simplified retrieval workflow
- Return to Park with location update
- Admin Profile Editor (name + client name)
- Admin Reporting Dashboard - "The Nightly Pulse" (completed 2026-03-16)

## Tech Stack
- **Backend**: FastAPI, Motor (async MongoDB), Pydantic, JWT, Twilio SDK
- **Frontend**: React, React Router, Tailwind CSS, Shadcn/UI, Axios, Recharts
- **Database**: MongoDB (collections: users, vehicles, tickets, tips, otps)

## Key Credentials
- Super Admin: superadmin@swiftvalet.com / superadmin123
- Test Admin Phone: +919111222333 (OTP login)
- Test Valet Phone: +919999888877 (OTP login)

## DB Schema
- **users**: `{id, email, name, phone_number, role, client_id, client_name, password_hash (null for valets/admins), driver_license_number, driver_license_photo, is_active, created_at}`
- **vehicles**: `{id, phone_number, license_plate, tag_number, parked_at, parked_by, zone_label, gps_latitude, gps_longitude}`
- **tickets**: `{id, vehicle_id, customer_phone, status, created_at, claimed_by, claimed_at, arrived_at, completed_at}`
- **otps**: `{phone_number, otp, expires_at, created_at}`
- **tips**: `{id, ticket_id, valet_id, amount, razorpay_order_id, razorpay_payment_id, status, created_at, paid_at}`

## Key API Endpoints
- `/api/auth/login` - Super Admin login
- `/api/auth/otp/request` - Request OTP for Admin/Valet
- `/api/auth/otp/verify` - Verify OTP and get JWT
- `/api/admin/reporting` - GET: Admin reporting dashboard data
- `/api/admin/reporting/export` - GET: CSV export of payout data
- `/api/admin/valets` - CRUD for valets
- `/api/admin/profile` - PUT: Admin profile update
- `/api/whatsapp/webhook` - POST: Incoming Twilio messages

## Known Issues
- **RETR Webhook BLOCKED**: User must configure Twilio webhook URL in sandbox settings
- GPS is optional (mocked) for preview environment testing
- Twilio WhatsApp in sandbox mode — OTP delivery only works for sandbox-joined numbers

## Upcoming Tasks (Priority Order)
1. P0: Guide user on Twilio webhook configuration
2. P1: Phase C - Ghosting Protocol (5-min timer, return to park)
3. P2: Phase D - Handover & Gratuity (handover complete, tipping/payment)
4. Future: Drip tip reminders, PWA push notifications
5. Refactoring: Split server.py into modular route files
