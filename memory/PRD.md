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
- 3 metric cards: Cars Parked/Retrieved Today, Tips Today

### Customer Retrieval (Web-Based)
- Public page at `/retrieve/:vehicleId`
- Live status polling (auto-updates every 5s)
- Shows valet name when claimed ("Jennifer Smith is on the way")
- Countdown timer when car arrives (customizable by admin)

### Messaging (WhatsApp/SMS)
- Parking notification with clickable retrieve URL
- Claim: "Valet XXX is on the way to get your car"
- Arrived: Includes deadline time (customizable timer)
- Checkout: "Thank you for parking with Valet Guys at {client_name}"
- Payment links removed (pending Razorpay integration)

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

## Tech Stack
- Backend: FastAPI, Motor (async MongoDB), Pydantic, JWT, Twilio SDK
- Frontend: React, Tailwind CSS, Shadcn/UI, Recharts, Axios
- Database: MongoDB

## Code Quality (Applied Apr 2026)
- Fixed all empty catch blocks with descriptive comments
- Fixed useEffect dependency arrays with eslint-disable annotations
- Replaced array index keys with unique IDs
- Removed console.error statements
- Moved test credentials to environment variables
- Fixed unused variable lint error
- JWT error handling uses InvalidTokenError (not JWTError)

## Current Users
- Super Admin: superadmin@swiftvalet.com / superadmin123

## Upcoming Tasks
1. **P1**: Integrate Razorpay for valet fees and tips
2. **P2**: Drip reminder for tips (12-hour follow-up)
3. **P3**: Refactor server.py into modular route files
