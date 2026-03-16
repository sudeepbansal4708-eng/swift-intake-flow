# SwiftValet - Valet Parking Platform

A comprehensive valet parking platform with real-time ticket management, WhatsApp notifications, and integrated payments.

## Features

### Phase A: Intake & Parking
- Quick vehicle intake (phone number + license plate)
- 360° photo capture for damage documentation
- High-accuracy GPS pinning with zone/level labels
- Automatic WhatsApp notification to customer

### Phase B: Retrieval & Claiming
- Customer sends "RETR" via WhatsApp to create retrieval ticket
- Real-time ticket claiming system (first-come-first-served)
- Status updates via WhatsApp:
  - "Claimed" - Valet assigned
  - "En Route" - Valet fetching car
  - "Arrived" - Car at entrance

### Phase C: 5-Minute Rule
- 5-minute countdown timer when car arrives
- Options: Complete handover or return to park/extended hold

### Phase D: Handover & Gratuity
- Completion triggers Razorpay payment link for tipping
- Preset amounts: ₹50, ₹100, ₹200, or custom
- 12-hour follow-up reminder (if configured)

### Admin Features
- Driver management (add/deactivate valets)
- Tips tracking dashboard
- View all vehicles and tickets
- User role management

## User Roles

1. **Customer**: Interacts via WhatsApp only (no app required)
2. **Valet Driver**: Mobile PWA access for ticket management
3. **Admin**: Full access including driver management and analytics

## Demo Credentials

### Admin Account
- Email: `admin@swift.com`
- Password: `admin123`

### Valet Account
- Email: `valet@swift.com`
- Password: `valet123`

## Configuration

### 1. WhatsApp Business API Setup

Add your WhatsApp credentials to `/app/backend/.env`:

```env
WHATSAPP_API_URL=your_whatsapp_api_endpoint
WHATSAPP_TOKEN=your_whatsapp_api_token
```

**Options:**
- **WhatsApp Business API**: If you have official WhatsApp Business API access
- **Twilio WhatsApp**: Use Twilio's WhatsApp API
- **Alternative**: Follow the Baileys integration playbook for self-hosted solution

### 2. Razorpay Payment Gateway

Add your Razorpay credentials to `/app/backend/.env`:

```env
RAZORPAY_KEY_ID=your_razorpay_key_id
RAZORPAY_KEY_SECRET=your_razorpay_secret_key
```

**How to get keys:**
1. Sign up at [Razorpay Dashboard](https://dashboard.razorpay.com/)
2. Go to Settings → API Keys
3. Generate keys for Test/Live mode
4. Copy and paste into `.env` file

After adding keys, restart the backend:
```bash
sudo supervisorctl restart backend
```

### 3. JWT Secret (Optional but Recommended)

Change the default JWT secret in `/app/backend/.env`:

```env
JWT_SECRET=your-custom-secret-key-here
```

## Tech Stack

### Backend
- FastAPI (Python)
- MongoDB (Database)
- Motor (Async MongoDB driver)
- JWT Authentication
- Razorpay SDK
- HTTPX (WhatsApp API calls)

### Frontend
- React 19
- React Router
- Axios
- Tailwind CSS
- Shadcn/UI Components
- Lucide Icons
- Sonner (Toast notifications)

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register new valet/admin
- `POST /api/auth/login` - Login
- `GET /api/auth/me` - Get current user

### Vehicles
- `POST /api/vehicles` - Park a vehicle
- `POST /api/vehicles/upload-photo` - Upload vehicle photo
- `GET /api/vehicles` - List all vehicles

### Tickets
- `POST /api/tickets` - Create retrieval ticket
- `GET /api/tickets` - List tickets (with filters)
- `PUT /api/tickets/{id}/claim` - Claim ticket
- `PUT /api/tickets/{id}/status` - Update ticket status

### Admin
- `GET /api/admin/valets` - List all valets
- `DELETE /api/admin/valets/{id}` - Deactivate valet
- `GET /api/admin/tips` - View tips analytics

### WhatsApp Webhook
- `POST /api/whatsapp/webhook` - Handle incoming WhatsApp messages

## Ticket Status Flow

```
PARKED → OPEN → CLAIMED → EN_ROUTE → ARRIVED → COMPLETED
                                               ↓
                                           RETURNED (if customer doesn't show)
```

## WhatsApp Message Templates

### Parking Confirmation
```
🚗 Welcome to SwiftValet!

Your vehicle (Plate: ABC-1234) is safely parked.
Zone: Level 3, Section B

Reply 'RETR' when you're ready to retrieve your car.
```

### Retrieval Request Confirmed
```
🚗 Got it! Your car retrieval request is now active. A valet will claim it shortly and keep you updated!
```

### Valet Claimed
```
🔔 Great news! Valet John is preparing to fetch your car.
```

### En Route
```
🚗 Valet John is on the way to fetch your car!
```

### Arrived at Entrance
```
✅ Your car is at the entrance! We can hold it for 5 minutes.
```

### Handover Complete with Tip Link
```
🎉 Thank you for using SwiftValet!

If you'd like to tip your valet, you can do so here:
[Razorpay Payment Link]

Preset amounts: ₹50, ₹100, ₹200 or custom.
```

## Mobile PWA Features

- Responsive design (mobile-first)
- GPS location capture
- Camera access for photos
- Offline-ready architecture
- Real-time updates every 5 seconds
- Touch-optimized UI

## Design System

### Colors
- Background: Zinc-950 (#09090B)
- Primary: Blue-600 (#3B82F6)
- Accent: Emerald-600 (#10B981)
- Destructive: Red-500 (#EF4444)

### Typography
- Headings: Barlow Condensed (Bold, Uppercase)
- Body: Inter (Regular, Medium)
- Mono: JetBrains Mono

### Components
- Glass-morphism cards with backdrop blur
- Glowing buttons with shadow effects
- Status badges with color coding
- 5-minute countdown timer
- Real-time ticket updates

## Development

### Run Locally
Frontend and backend are already running via supervisor.

### View Logs
```bash
# Backend logs
tail -f /var/log/supervisor/backend.out.log

# Frontend logs
tail -f /var/log/supervisor/frontend.out.log
```

### Restart Services
```bash
# Restart backend
sudo supervisorctl restart backend

# Restart frontend
sudo supervisorctl restart frontend
```

## Testing

### Create Test Vehicle
```bash
curl -X POST "https://swift-valet-preview.preview.emergentagent.com/api/vehicles" \\
  -H "Authorization: Bearer YOUR_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{
    "phone_number": "+1234567890",
    "license_plate": "ABC-1234",
    "zone_label": "Level 3, Section B",
    "gps_latitude": 37.7749,
    "gps_longitude": -122.4194
  }'
```

### Simulate WhatsApp Message
```bash
curl -X POST "https://swift-valet-preview.preview.emergentagent.com/api/whatsapp/webhook" \\
  -H "Content-Type: application/json" \\
  -d '{
    "phone_number": "+1234567890",
    "message": "RETR"
  }'
```

## Production Checklist

- [ ] Update JWT_SECRET in .env
- [ ] Add production WhatsApp Business API credentials
- [ ] Add production Razorpay keys (not test keys)
- [ ] Set up HTTPS
- [ ] Configure CORS for production domain
- [ ] Set up database backups
- [ ] Configure monitoring and alerts
- [ ] Test WhatsApp webhook endpoint
- [ ] Test Razorpay payment flow
- [ ] Verify GPS accuracy in production location
- [ ] Load test ticket claiming system

## Support

For issues or questions:
1. Check backend logs for API errors
2. Check frontend console for client errors
3. Verify WhatsApp/Razorpay credentials are set
4. Ensure MongoDB is running

## Next Steps

### Recommended Enhancements
1. **Revenue Optimization**: 
   - Implement dynamic pricing based on time/location
   - Add subscription tiers for frequent users
   - Premium features (priority retrieval, covered parking)

2. **User Experience**:
   - Push notifications (PWA)
   - Multiple photos per vehicle
   - Customer rating system
   - Historical parking data

3. **Operations**:
   - Analytics dashboard
   - Peak hours insights
   - Valet performance metrics
   - Revenue reports

4. **Integrations**:
   - Google Maps for location visualization
   - SMS fallback if WhatsApp fails
   - Apple Pay / Google Pay
   - CRM integration
