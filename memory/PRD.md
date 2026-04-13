# ParKaro - Product Requirements Document

## Original Problem Statement
Build a valet parking platform called "ParKaro" with four user roles: Customer (SMS/WhatsApp), Valet Driver (React PWA), Admin (manage drivers/tips/cars), and Super Admin (manage admins/analytics).

## User Roles
- **Customer**: Receives SMS/WhatsApp notifications, taps a link to retrieve their car (no app needed)
- **Valet Driver**: Uses React PWA, logs in via OTP. Can park, retrieve, and checkout vehicles.
- **Admin**: Manages valets, tips, car statuses — logs in via OTP
- **Super Admin**: Manages Admins, platform-wide analytics (password login only)

## Authentication
- OTP Login (Valets + Admins): Phone -> 6-digit OTP -> 10-min expiry
- Password Login (Super Admin only): Email + password
- Dev mode: OTP always displayed on screen for testing

## Completed Features

### Core
- JWT auth (hybrid: password for super admin, OTP for admin/valet)
- Multi-step vehicle intake with optional GPS
- Twilio WhatsApp messaging (verified, production ready) with SMS fallback
- Retrieval ticket system with full lifecycle
- Web-based customer retrieval page (no login required)

### Valet Dashboard — Apr 2026
- 3 metric cards: Cars Parked Today, Cars Retrieved Today, Tips Today
- **Bottom action ribbon** with Park and Retrieve buttons (replaced FAB)
- **Valet checkout capability** — valets can now checkout vehicles directly
- Polling-based in-app notifications for new tickets
- Checkout sends thank-you + tip message to customer via WhatsApp

### Customer Retrieval (Web-Based) — Apr 2026
- Public web page at `/retrieve/:vehicleId` (no login required)
- Customer taps link from WhatsApp to request car retrieval
- Shows license plate, tag number, valet fee, "Get My Car" button
- **Live status polling** — auto-updates every 5 seconds
- **Shows valet name** when ticket is claimed/en_route ("Jennifer Smith is on the way")
- **Countdown timer** when car arrives — 5-minute timer with urgency colors
- Handles all states: confirm, pending payment, in progress, already collected

### Messaging — Apr 2026
- Dual-mode: WhatsApp (primary, MESSAGING_MODE=whatsapp) or SMS fallback
- Plain text body (no WhatsApp templates)
- Webhook returns TwiML XML for Twilio compatibility
- Parking WhatsApp includes clickable retrieve URL
- **Claim message**: "Valet XXX is on the way to get your car"
- **Arrived message**: Includes deadline time ("Please collect by XX:XX PM UTC")
- **Checkout message**: Thank-you + tip link

### Ghosting Protocol (Phase C)
- 5-minute countdown timer after car arrives at entrance
- "RETURN TO PARK (GHOSTED)" action when timer expires
- Vehicle resets to parked status; customer notified

### Shift Management
- Admin toggle to mark valets online/offline
- Only online valets can park/retrieve vehicles

### Valet Parking Fee & Payment Gate
- Admin sets valet fee in profile settings
- If fee > Rs.1, retrieval creates pending_payment ticket
- Payment link sent to customer (currently MOCKED)

### Admin Panel
- Collapsible My Profile (name, client name, profile photo upload)
- Collapsible Team Management (valet CRUD, license verification)
- Clickable stat cards with detail modals

### Admin Reporting ("The Nightly Pulse")
- Performance metrics, Valet Leaderboard, Peak Hour Heatmap, Financial Reconciliation, CSV Export

### Super Admin Panel
- Client management (create/deactivate), per-client report modal
- Archive for deactivated clients

### Data Cleanup
- `DELETE /api/admin/cleanup-data` purges completed tickets and checked-out vehicles

## Tech Stack
- Backend: FastAPI, Motor (async MongoDB), Pydantic, JWT, Twilio SDK
- Frontend: React, Tailwind CSS, Shadcn/UI, Recharts, Axios
- Database: MongoDB

## Known Issues / MOCKED
- Payment links (tip, valet fee) are placeholder URLs — Stripe/Razorpay not integrated
- Tips data is all zeros until payment integration

## Current Users in DB
- Super Admin: superadmin@swiftvalet.com / superadmin123
- Admin: Sudeep test (+18139006037, OTP login)
- Valet: Jennifer Smith (+919922668866, OTP login)
- Valet: Sudeep valet (+919372991136, OTP login)

## Upcoming Tasks
1. **P1**: Integrate real payment processing (Stripe/Razorpay) for valet fees and tips
2. **P2**: Drip reminder for tips (12-hour follow-up if no payment)
3. **P3**: Refactor server.py into modular route files (auth, tickets, vehicles, admin)
