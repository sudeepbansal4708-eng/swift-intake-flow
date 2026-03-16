# SwiftValet - Product Requirements Document

## Original Problem Statement
Build a valet parking platform called "SwiftValet" with four user roles: Customer (WhatsApp), Valet Driver (React PWA), Admin (manage drivers/tips/cars), and Super Admin (manage admins/analytics).

## User Roles
- **Customer**: Interacts via WhatsApp (no app needed)
- **Valet Driver**: Uses React PWA for intake, scanning, logging, GPS
- **Admin**: Manages valets, tips, car statuses for their client
- **Super Admin**: Manages Admins, platform-wide analytics

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
- Preset tipping ($5, $10, $20) with payment link

## Completed Features
- JWT auth for all roles (Valet, Admin, Super Admin)
- Multi-step vehicle intake with optional GPS
- Twilio WhatsApp notifications (sandbox mode)
- Retrieval ticket system (webhook code ready)
- Admin Panel: valet CRUD, license verification, profile editor
- Super Admin Panel: client management, analytics dashboard
- Simplified retrieval workflow
- Return to Park with location update
- **Admin Profile Editor** (name + client name) — completed 2026-03-16

## Tech Stack
- **Backend**: FastAPI, Motor (async MongoDB), Pydantic, JWT, Twilio SDK
- **Frontend**: React, React Router, Tailwind CSS, Shadcn/UI, Axios
- **Database**: MongoDB

## Key Credentials
- Super Admin: superadmin@swiftvalet.com / superadmin123
- Admin: admin@swift.com / admin123
- Valet: valet@swift.com / valet123

## Known Issues
- **RETR Webhook BLOCKED**: User must configure Twilio webhook URL in their sandbox settings
- GPS is optional (mocked) for preview environment testing

## Upcoming Tasks (Priority Order)
1. P0: Guide user on Twilio webhook configuration
2. P2: Phase C - Ghosting Protocol (5-min timer)
3. P3: Phase D - Handover & Gratuity
4. Future: Drip tip reminders, PWA push notifications
5. Refactoring: Split server.py into modular route files
