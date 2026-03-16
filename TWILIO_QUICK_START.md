# 🚀 Twilio WhatsApp Quick Reference

## Your Credentials Location
**File:** `/app/backend/.env`

```env
TWILIO_ACCOUNT_SID="ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
TWILIO_AUTH_TOKEN="your_auth_token_here"
TWILIO_WHATSAPP_FROM="+14155238886"
```

## Get Your Credentials

1. **Twilio Console:** https://console.twilio.com
2. **Account SID & Auth Token:** On the main dashboard
3. **WhatsApp Number:** Messaging → Try WhatsApp

## After Adding Credentials

```bash
sudo supervisorctl restart backend
```

## Test Your Setup

### Check if backend loaded credentials:
```bash
tail -20 /var/log/supervisor/backend.out.log
```

### Test vehicle parking API:
```bash
API_URL="https://handover-hub-10.preview.emergentagent.com"

TOKEN=$(curl -s -X POST "$API_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"valet@swift.com","password":"valet123"}' | \
  python3 -c "import sys,json;print(json.load(sys.stdin)['token'])")

curl -X POST "$API_URL/api/vehicles" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "+1234567890",
    "license_plate": "TEST-123",
    "zone_label": "Test Zone"
  }'
```

Replace `+1234567890` with YOUR WhatsApp number (the one that joined Twilio sandbox)

## Phone Number Format

✅ Correct:
- `+14155551234` (US)
- `+447911123456` (UK)
- `+919876543210` (India)

❌ Wrong:
- `4155551234` (missing +)
- `14155551234` (missing +)
- `+1 415 555 1234` (spaces)

## Sandbox Mode

**To receive messages, you MUST:**
1. Open WhatsApp on your phone
2. Send the join code to Twilio's number
3. Wait for confirmation
4. Then SwiftValet can send you messages

**Join Code Location:** 
Twilio Console → Messaging → Try WhatsApp

## Cost

- **Signup:** FREE with $15 credit
- **Sandbox:** FREE forever (for testing)
- **Production:** ~$0.005 per message (~$5 for 1000 messages)

## Status Check

```bash
# Check if backend is running
sudo supervisorctl status backend

# Watch live logs
tail -f /var/log/supervisor/backend.out.log

# Test API
curl https://handover-hub-10.preview.emergentagent.com/api/
```

## Common Issues

### "WhatsApp not configured"
→ Add credentials to .env and restart backend

### "Not a valid phone number"
→ Must start with + and country code (+14155551234)

### "Message not received"
→ Did you join the Twilio sandbox with your phone?

## Full Guide

See: `/app/TWILIO_SETUP_GUIDE.md` for complete step-by-step instructions

## Support

- **Twilio Docs:** https://www.twilio.com/docs/whatsapp
- **Backend Logs:** `tail -f /var/log/supervisor/backend.out.log`
- **Test API:** `curl https://handover-hub-10.preview.emergentagent.com/api/`
