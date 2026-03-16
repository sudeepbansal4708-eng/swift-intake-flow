# 📱 Twilio WhatsApp Setup Guide for SwiftValet

## 🎯 Quick Setup (5 Minutes)

Follow these steps to get Twilio WhatsApp working with SwiftValet:

---

## Step 1: Create Twilio Account

1. **Go to Twilio:**
   - Visit: https://www.twilio.com/try-twilio
   - Click "Sign up" (it's FREE!)

2. **Fill in your details:**
   - Email address
   - Password
   - Phone number (for verification)

3. **Verify your email and phone**
   - Check your email for verification link
   - Enter the verification code sent to your phone

4. **You get $15 FREE credit!** 🎉
   - No credit card required to start
   - Enough for ~3,000 WhatsApp messages

---

## Step 2: Get Your Twilio Credentials

Once logged in to Twilio Console:

### A. Get Account SID and Auth Token

1. On the dashboard, you'll see:
   ```
   Account Info
   ├── ACCOUNT SID: ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   └── AUTH TOKEN: [Show] ← Click to reveal
   ```

2. **Copy these values** (you'll need them in Step 3)

### B. Enable WhatsApp Sandbox

1. **Go to:** Messaging → Try it out → Send a WhatsApp message
   - Direct link: https://console.twilio.com/us1/develop/sms/try-it-out/whatsapp-learn

2. **Join the Sandbox:**
   - You'll see a WhatsApp number (e.g., `+1 415 523 8886`)
   - You'll see a join code (e.g., `join <code>`)
   - **On your phone:** Open WhatsApp and send that join code to the Twilio number
   - You'll get a confirmation message

3. **Get the Twilio WhatsApp Number:**
   - This is shown as "From: +14155238886" (or similar)
   - **Copy this number** (you'll need it in Step 3)

---

## Step 3: Configure SwiftValet

### Add Credentials to Backend

1. **SSH/Terminal access** to your server

2. **Edit the .env file:**
   ```bash
   nano /app/backend/.env
   ```

3. **Fill in your Twilio credentials:**
   ```env
   TWILIO_ACCOUNT_SID="ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
   TWILIO_AUTH_TOKEN="your_auth_token_here"
   TWILIO_WHATSAPP_FROM="+14155238886"
   ```

   Replace:
   - `ACxxxxxxx...` with your actual Account SID
   - `your_auth_token_here` with your actual Auth Token
   - `+14155238886` with your Twilio WhatsApp number

4. **Save the file:**
   - Press `Ctrl + X`
   - Press `Y` to confirm
   - Press `Enter`

5. **Restart the backend:**
   ```bash
   sudo supervisorctl restart backend
   ```

---

## Step 4: Test It!

### Option A: Test via Dashboard

1. **Login to SwiftValet** as valet:
   - Email: `valet@swift.com`
   - Password: `valet123`

2. **Park a vehicle:**
   - Click the blue "+" button
   - Enter your **WhatsApp number** (the one you used to join sandbox)
   - Format: `+1234567890` (with country code)
   - Enter license plate: `TEST-123`
   - Click "PARK VEHICLE"

3. **Check your WhatsApp:**
   - You should receive: "🚗 Welcome to SwiftValet! Your vehicle..."

### Option B: Test via API

```bash
API_URL="https://swift-valet-preview-1.preview.emergentagent.com"

# Login
TOKEN=$(curl -s -X POST "$API_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"valet@swift.com","password":"valet123"}' | \
  python3 -c "import sys,json;print(json.load(sys.stdin)['token'])")

# Park a vehicle (use YOUR WhatsApp number)
curl -X POST "$API_URL/api/vehicles" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "+1234567890",
    "license_plate": "TEST-123",
    "zone_label": "Level 1, Section A"
  }'
```

---

## 📝 Important Notes

### Phone Number Format
- **MUST include country code** with `+`
- Format: `+[country][number]`
- Examples:
  - US: `+14155551234`
  - UK: `+447911123456`
  - India: `+919876543210`

### Sandbox Limitations
- Only numbers that "joined" your sandbox can receive messages
- To send to ANY number, you need to upgrade (see below)

### Testing with Multiple Numbers
To test with different phone numbers:
1. Each person sends the join code to the Twilio number
2. Then they can receive WhatsApp messages from SwiftValet

---

## 🚀 Going to Production (Optional)

### Why Upgrade from Sandbox?

**Sandbox Mode:**
- ✅ FREE to test
- ❌ Can only message numbers that joined sandbox
- ❌ Shows "using a Twilio sandbox" in messages

**Production Mode:**
- ✅ Send to ANY WhatsApp number
- ✅ Your own branded sender name
- ✅ Professional messages
- 💰 ~$0.005 per message (very cheap!)

### How to Upgrade

1. **Request WhatsApp Sender Approval:**
   - Go to: https://console.twilio.com/us1/develop/sms/senders/whatsapp-senders
   - Click "Request to enable my Twilio numbers for WhatsApp"
   - Fill in business details
   - **Approval time:** Usually 1-3 business days

2. **Get a Dedicated WhatsApp Number:**
   - Go to: Phone Numbers → Buy a Number
   - Search for US/UK numbers with "SMS" capability
   - Cost: ~$1-2/month for the number

3. **Update SwiftValet:**
   ```bash
   # Replace sandbox number with your new number in .env
   TWILIO_WHATSAPP_FROM="+1234567890"
   ```

4. **Restart backend:**
   ```bash
   sudo supervisorctl restart backend
   ```

---

## 💰 Pricing

### Free Tier
- $15 credit on signup
- ~3,000 WhatsApp messages FREE
- Perfect for MVP/testing

### After Free Credit
- **WhatsApp messages:** $0.005 per message
- **Phone number rental:** ~$1-2/month
- **Example:** 1,000 messages/month = $5-7/month total

**Very affordable for a valet parking service!**

---

## 🔍 Troubleshooting

### "WhatsApp not configured" in logs

**Problem:** Credentials not set or backend not restarted

**Solution:**
```bash
# Check if credentials are set
cat /app/backend/.env | grep TWILIO

# Restart backend
sudo supervisorctl restart backend

# Check logs
tail -f /var/log/supervisor/backend.out.log
```

### "Not a valid phone number"

**Problem:** Phone number format incorrect

**Solution:**
- Make sure it starts with `+` and country code
- Example: `+14155551234` (not `4155551234`)

### "Sandbox number not found"

**Problem:** You haven't joined the Twilio sandbox

**Solution:**
- Go to Twilio Console → Messaging → Try WhatsApp
- Send the join code from your phone
- Wait for confirmation message

### Messages not being received

**Checklist:**
- ✅ Phone number joined Twilio sandbox?
- ✅ Phone number format correct (+country code)?
- ✅ Backend credentials set correctly?
- ✅ Backend restarted after adding credentials?
- ✅ Check backend logs for errors?

---

## 📊 Monitor Usage

**Check your message usage:**
1. Go to: https://console.twilio.com/us1/monitor/logs/messages
2. See all sent messages, status, and costs
3. Set up alerts when credit is low

**View logs in SwiftValet:**
```bash
# Backend logs show WhatsApp send attempts
tail -f /var/log/supervisor/backend.out.log | grep WhatsApp
```

---

## 🎉 What Gets Sent via WhatsApp

### 1. Vehicle Parked
```
🚗 Welcome to SwiftValet!

Your vehicle (Plate: ABC-1234) is safely parked.
Zone: Level 3, Section B

Reply 'RETR' when you're ready to retrieve your car.
```

### 2. Retrieval Request Confirmed
```
🚗 Got it! Your car retrieval request is now active. 
A valet will claim it shortly and keep you updated!
```

### 3. Valet Claimed
```
🔔 Great news! Valet John is preparing to fetch your car.
```

### 4. Valet En Route
```
🚗 Valet John is on the way to fetch your car!
```

### 5. Car at Entrance
```
✅ Your car is at the entrance! We can hold it for 5 minutes.
```

### 6. Handover Complete
```
🎉 Thank you for using SwiftValet! Your feedback means a lot to us.
```

---

## 🆘 Need Help?

**Twilio Support:**
- Help Center: https://support.twilio.com
- WhatsApp Docs: https://www.twilio.com/docs/whatsapp
- Community: https://www.twilio.com/community

**SwiftValet Backend Logs:**
```bash
tail -f /var/log/supervisor/backend.out.log
```

**Test Endpoint:**
```bash
curl https://swift-valet-preview-1.preview.emergentagent.com/api/
# Should return: {"message": "Hello World"}
```

---

## ✅ Quick Checklist

Before going live, make sure:

- [ ] Twilio account created
- [ ] $15 free credit received
- [ ] Joined WhatsApp sandbox from your phone
- [ ] Copied Account SID, Auth Token, WhatsApp number
- [ ] Added credentials to `/app/backend/.env`
- [ ] Restarted backend: `sudo supervisorctl restart backend`
- [ ] Tested vehicle parking with YOUR phone number
- [ ] Received WhatsApp message on your phone

**If all checked, you're READY! 🚀**

---

## 🎯 Next Steps

1. **Test the full flow:**
   - Park a vehicle
   - Create retrieval ticket (send "RETR" via WhatsApp)
   - Claim ticket as valet
   - Update status
   - Complete handover

2. **Add more test users:**
   - Have team members join the sandbox
   - Test with multiple phone numbers

3. **Monitor usage:**
   - Watch your Twilio console
   - Check SwiftValet logs

4. **When ready for production:**
   - Request WhatsApp sender approval
   - Get dedicated number
   - Remove sandbox limitations

---

**You're all set! Happy parking! 🚗💨**
