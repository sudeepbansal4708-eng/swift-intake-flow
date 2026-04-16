# Valet Guys - Product Requirements Document

## Original Problem Statement
Build a valet parking platform called "Valet Guys" with four user roles: Customer (SMS/WhatsApp), Valet Driver (React PWA), Admin (manage drivers/tips/cars), and Super Admin (manage admins/analytics).

## User Roles
- **Customer**: Receives WhatsApp notifications, taps a link to retrieve their car (no app needed)
- **Valet Driver**: Uses React PWA, logs in via OTP. Can park, retrieve, and checkout vehicles.
- **Admin**: Manages valets, tips, car statuses — logs in via OTP
- **Super Admin**: Manages Admins, platform-wide analytics (password login only)

## Authentication
- OTP Login (Valets + Admins): Phone -> 6-digit OTP via WhatsApp -> 10-min expiry
- Password Login (Super Admin only): Email + password
- OTP display removed (WhatsApp delivery is working)

## Completed Features

### Core
- JWT auth (hybrid: password for super admin, OTP for admin/valet)
- Multi-step vehicle intake with optional GPS, TAG prefilled
- Twilio WhatsApp messaging (verified, production ready) with SMS fallback
- Retrieval ticket system with full lifecycle
- Web-based customer retrieval page (no login required)

### Valet Dashboard
- Bottom action ribbon (Park / Retrieve buttons)
- Valet checkout capability with thank-you WhatsApp message
- Polling-based in-app notifications for new tickets
- 3 metric cards: Cars Parked/Retrieved Today, Tips Today (Coming Soon)

### Customer Retrieval (Web-Based)
- Public page at `/retrieve/:vehicleId`
- Live status polling (auto-updates every 5s)
- Shows valet name when claimed ("Jennifer Smith is on the way")
- Countdown timer when car arrives (customizable by admin)

### Messaging (WhatsApp/SMS)
- Parking notification with clickable retrieve URL
- Claim: "Valet XXX is on the way to get your car"
- Arrived: Includes deadline time (customizable timer)
- Checkout: "Thank you for parking at [Client Name]. We hope you enjoyed your time here. The Valet Guys"
- Payment links removed (pilot phase — no charges)

### Admin Features
- Customizable wait timer (1-30 min, default 5)
- Valet fee settings
- Collapsible My Profile + Team Management
- Clickable stat cards with detail modals
- Reporting dashboard ("The Nightly Pulse")

### Ghosting Protocol
- Customizable countdown timer after car arrives
- "RETURN TO PARK (GHOSTED)" action when timer expires

### Shift Management
- Admin toggle for online/offline valets
- Only online valets can park/retrieve

### Code Quality & Architecture (Apr 2026)
- Fixed all empty catch blocks with descriptive comments
- Fixed useEffect dependency arrays with eslint-disable annotations
- Replaced array index keys with unique IDs
- Removed console.error statements
- Moved test credentials to environment variables
- JWT error handling uses InvalidTokenError (not JWTError)
- **Backend refactored from monolithic 2000-line server.py into modular router files**

### Pilot Phase UI Changes (Feb 2026)
- Tips/payment UI hidden with "COMING SOON" tags across Dashboard, AdminReporting, SuperAdminPanel
- Thank-you message updated: "Thank you for parking at [Client Name]. We hope you enjoyed your time here. The Valet Guys"
- Financial Reconciliation section in reporting shows "COMING SOON"
- Super Admin home screen now shows SuperAdminPanel content directly (analytics, client management)
- Super Admin no longer sees ticket claiming UI or bottom action ribbon
- Crown navigation icon removed — super admin content is the home screen

## Tech Stack
- Backend: FastAPI, Motor (async MongoDB), Pydantic, JWT, Twilio SDK
- Frontend: React, Tailwind CSS, Shadcn/UI, Recharts, Axios
- Database: MongoDB

## Backend Architecture
```
/app/backend/
├── server.py          # Slim entry point (app init, router includes, startup seed)
├── config.py          # Shared config (DB, security, Twilio, VAPID, templates)
├── models.py          # All Pydantic models
├── utils.py           # Auth helpers, messaging, notifications, fee utilities
└── routers/
    ├── auth.py        # /auth/* (login, register, OTP)
    ├── vehicles.py    # /vehicles/* (CRUD, upload, lookup)
    ├── tickets.py     # /tickets/*, /valet/* (lifecycle, dashboard, online requests)
    ├── admin.py       # /admin/* (valets mgmt, profile, dashboard, reporting, checkout)
    ├── super_admin.py # /super-admin/* (clients, analytics, admin mgmt)
    └── public.py      # /retrieve/*, /push/*, /whatsapp/webhook
```

## Current Users
- Super Admin: superadmin@swiftvalet.com / superadmin123

## Upcoming Tasks
1. **P1**: Integrate payment processing (Stripe/Razorpay) for valet fees and tips (post-pilot)
2. **P2**: Drip reminder for tips (12-hour follow-up)
3. **P3**: Real-time push notifications for PWA
