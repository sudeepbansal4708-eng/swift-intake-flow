# ParKaro - Product Requirements Document

## Original Problem Statement
Build a valet parking platform called "ParKaro" with four user roles: Customer (SMS/WhatsApp), Valet Driver (React PWA), Admin (manage drivers/tips/cars), and Super Admin (manage admins/analytics).

## User Roles
- **Customer**: Receives SMS/WhatsApp notifications, taps a link to retrieve their car (no app needed)
- **Valet Driver**: Uses React PWA, logs in via OTP
- **Admin**: Manages valets, tips, car statuses — logs in via OTP
- **Super Admin**: Manages Admins, platform-wide analytics (password login only)

## Authentication
- OTP Login (Valets + Admins): Phone → 6-digit OTP → 10-min expiry
- Password Login (Super Admin only): Email + password
- Dev mode: OTP always displayed on screen for testing

## Completed Features

### Core
- JWT auth (hybrid: password for super admin, OTP for admin/valet)
- Multi-step vehicle intake with optional GPS
- Twilio WhatsApp messaging (verified, production ready)
- Retrieval ticket system with full lifecycle

### Customer Retrieval (Web-Based) — Apr 2026
- Public web page at `/retrieve/:vehicleId` (no login required)
- Customer taps link from SMS/WhatsApp to request car retrieval
- Shows license plate, tag number, valet fee, and "Get My Car" button
- Handles all states: confirm, pending payment, in progress, already collected
- Endpoints: `GET /api/retrieve/{vehicle_id}`, `POST /api/retrieve/{vehicle_id}/confirm`
- Replaces SMS "Reply RETR" flow (bypasses A2P 10DLC / inbound SMS limitations)

### Messaging — Apr 2026
- Dual-mode messaging: WhatsApp (primary) or SMS (fallback via MESSAGING_MODE env var)
- All messages use plain text body (no WhatsApp templates — simpler, works in both modes)
- Webhook returns TwiML XML for Twilio compatibility
- Parking SMS/WhatsApp includes clickable retrieve URL

### Admin Panel
- Collapsible My Profile (name, client name, profile photo upload)
- Collapsible Team Management (valet CRUD, license verification)
- Clickable stat cards: Active Valets, Vehicles, Tips (with detail modals)
- Tab navigation to Reporting dashboard

### Admin Reporting ("The Nightly Pulse")
- Tonight's Performance, Valet Leaderboard, Peak Hour Heatmap, Wait-List Alert, Financial Reconciliation, CSV Export

### Super Admin Panel
- Client management (create/deactivate), per-client report modal
- Archive for deactivated clients (collapsible)
- Inline delete confirmation (no browser dialogs)

### Valet Dashboard
- 3 metric cards: Cars Parked Today, Cars Retrieved Today, Tips Today
- FAB with Park/Retrieve dropdown options
- Polling-based in-app notifications for new tickets

### Shift Management
- Admin toggle to mark valets online/offline
- Only online valets can park/retrieve vehicles
- Valets can request to go online; admin sees and approves

### Ghosting Protocol (Phase C)
- 5-minute countdown timer after car arrives at entrance
- "RETURN TO PARK (GHOSTED)" action when timer expires
- Vehicle resets to parked status; customer notified via SMS/WhatsApp

### Valet Parking Fee & Payment Gate
- Admin sets valet fee in profile settings
- If fee > Rs.1, retrieval creates pending_payment ticket
- Payment link sent to customer (currently MOCKED)

### Admin Manual Vehicle Checkout
- Admins can force-checkout vehicles from dashboard
- Blocked if vehicle has pending_payment ticket

### Data Cleanup
- `DELETE /api/admin/cleanup-data` purges completed tickets and checked-out vehicles

## Key API Endpoints
- Auth: `/api/auth/login`, `/api/auth/otp/request`, `/api/auth/otp/verify`, `/api/auth/me`
- Vehicles: `/api/vehicles`, `/api/vehicles/lookup`
- Tickets: `/api/tickets`, `/api/tickets/retrieve`, `/api/tickets/{id}/claim`, `/api/tickets/{id}/status`
- Public Retrieval: `/api/retrieve/{vehicle_id}`, `/api/retrieve/{vehicle_id}/confirm`
- Admin: `/api/admin/dashboard-stats`, `/api/admin/valets`, `/api/admin/profile`, `/api/admin/reporting-nightly`
- Super Admin: `/api/super-admin/clients/{id}`, `/api/super-admin/admins/{id}`
- Webhook: `/api/whatsapp/webhook` (TwiML response)
- Cleanup: `DELETE /api/admin/cleanup-data`

## Tech Stack
- Backend: FastAPI, Motor (async MongoDB), Pydantic, JWT, Twilio SDK
- Frontend: React, Tailwind CSS, Shadcn/UI, Recharts, Axios
- Database: MongoDB

## Known Issues / MOCKED
- Payment links (tip, valet fee) are placeholder URLs — Stripe/Razorpay not integrated
- Tips data is all zeros until payment integration

## Upcoming Tasks
1. **P1**: Integrate real payment processing (Stripe/Razorpay) for valet fees and tips
2. **P2**: Drip reminder for tips (12-hour follow-up if no payment)
3. **P3**: Refactor server.py into modular route files (auth, tickets, vehicles, admin)
