# ParKaro - Product Requirements Document

## Original Problem Statement
Build a valet parking platform called "ParKaro" with four user roles: Customer (WhatsApp), Valet Driver (React PWA), Admin (manage drivers/tips/cars), and Super Admin (manage admins/analytics).

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
- **Valet Dashboard Stats** (NEW - Mar 24, 2026):
  - 3 metric cards: Cars Parked Today, Cars Retrieved Today, Tips Today (individual valet level)
  - Endpoint: GET /api/valet/dashboard-stats
- **Push Notifications** (NEW - Mar 24, 2026):
  - Web Push API with VAPID keys and service worker (sw.js)
  - Valets and client admins receive push notifications on every retrieval request
  - Endpoints: POST /api/push/subscribe, POST /api/push/unsubscribe, GET /api/push/vapid-key
  - Subscription storage in MongoDB push_subscriptions collection
- **FAB with Park/Retrieve Options** (NEW - Mar 24, 2026):
  - Replaced single "+" button with expandable FAB showing Park and Retrieve options
  - Park: navigates to /intake (existing parking workflow)
  - Retrieve: opens modal to enter customer phone, lookup vehicle, and auto-assign retrieval ticket to initiating valet
  - Endpoints: POST /api/tickets/retrieve, GET /api/vehicles/lookup
- **Admin Manual Vehicle Checkout** (NEW - Mar 24, 2026):
  - Admins can checkout vehicles directly from the Parked Vehicles modal on dashboard
  - Inline confirmation flow (Checkout → Confirm/Cancel)
  - Creates a completed ticket for record-keeping, sends WhatsApp thank-you message
  - Endpoint: POST /api/admin/vehicles/{vehicle_id}/checkout
- **Shift Management** (NEW - Mar 27, 2026):
  - Admin toggle to mark valets online/offline (Switch component on each valet card)
  - Only online valets can park/retrieve vehicles (offline get 403)
  - Valets can send "Request Online" to admin when offline
  - Admin sees pending shift requests with Approve button
  - Endpoints: PUT /api/admin/valets/{id}/toggle-online, POST /api/valet/request-online, GET /api/admin/online-requests
- **Ghosting Protocol - Phase C** (NEW - Mar 27, 2026):
  - 5-minute countdown timer starts when ticket status is "arrived"
  - Timer card turns red with "TIME UP" when expired, "RETURN TO PARK (GHOSTED)" becomes primary action
  - Valet can still complete handover if customer arrives late (secondary button)
  - On return: vehicle status resets to "parked" (can be retrieved again), WhatsApp notification sent to customer
  - Status flow: claimed → arrived (timer) → returned (ghosted) OR completed
- **Valet Parking Fee & Payment Gate** (NEW - Mar 28, 2026):
  - Admin can set valet parking fee in profile settings (Rs. amount)
  - If fee > Rs.1, retrieval creates a "pending_payment" ticket and sends WhatsApp payment request to customer
  - If fee = 0 or 1, retrieval proceeds directly (no payment gate)
  - WhatsApp template `valet_fee_payment` for payment requests
  - Dummy payment link for now (https://pay.parkaro.com/fee/{id})
- **WhatsApp Content Templates** (NEW - Mar 28, 2026):
  - Migrated from free-form to approved Meta templates for all message types
  - Templates: parking_confirmation, car_retrieval_v4, car_arrived, car_returned, valet_tip_v2, valet_fee_payment
  - Production WhatsApp sender: +16562593936

## Key API Endpoints
- `/api/auth/login`, `/api/auth/otp/request`, `/api/auth/otp/verify`, `/api/auth/me`
- `/api/valet/dashboard-stats` - Individual valet metrics (parked, retrieved, tips today)
- `/api/admin/dashboard-stats` - Clickable card details (valets, vehicles, tips)
- `/api/admin/profile` (PUT), `/api/admin/profile/photo` (POST)
- `/api/admin/reporting`, `/api/admin/reporting/export`
- `/api/super-admin/clients/{client_id}/report`
- `/api/vehicles`, `/api/vehicles/lookup`, `/api/tickets`, `/api/tickets/retrieve`, `/api/admin/valets`, `/api/admin/tips`
- `/api/push/subscribe`, `/api/push/unsubscribe`, `/api/push/vapid-key`

## Tech Stack
- Backend: FastAPI, Motor, Pydantic, JWT, Twilio SDK
- Frontend: React, Tailwind, Shadcn/UI, Recharts, Axios
- Database: MongoDB

## Known Issues
- RETR Webhook BLOCKED (user must configure Twilio webhook URL)
- Tips data is placeholder until payment integration
- GPS optional, Twilio in sandbox mode

## Upcoming Tasks
1. P0: Guide user to configure Twilio webhook for RETR feature
2. P1: Phase C — Ghosting Protocol (5-min timer, return to park)
3. P2: Phase D — Handover & Gratuity (payment/tipping integration)
4. Future: Drip tip reminders
5. Refactoring: Split server.py into modular route files
