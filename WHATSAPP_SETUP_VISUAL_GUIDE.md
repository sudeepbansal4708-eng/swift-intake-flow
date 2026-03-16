# 📱 Twilio WhatsApp Sandbox - Visual Setup Guide

## What You're Doing
Connecting YOUR phone's WhatsApp to Twilio so SwiftValet can send you messages.

---

## Step 1: Open Twilio Console

**Go to:** https://console.twilio.com/us1/develop/sms/try-it-out/whatsapp-learn

**You'll see a page like this:**

```
┌─────────────────────────────────────────────────┐
│  Twilio Sandbox for WhatsApp                    │
├─────────────────────────────────────────────────┤
│                                                 │
│  To connect your phone to the sandbox:         │
│                                                 │
│  1. From your WhatsApp, send:                  │
│                                                 │
│     join <word>-<word>                         │
│     ^^^^^^^^^^^^^^^^^^^^                       │
│     This is YOUR unique code                   │
│     (example: join happy-tiger)                │
│                                                 │
│  2. To this number:                            │
│                                                 │
│     +1 415 523 8886                           │
│                                                 │
│  3. Wait for confirmation (instant)            │
│                                                 │
└─────────────────────────────────────────────────┘
```

**YOUR SPECIFIC JOIN CODE** will be shown on that page (unique to your account)

---

## Step 2: On Your Phone

### Open WhatsApp

```
WhatsApp Screen:
┌─────────────────────────────┐
│  WhatsApp                   │
├─────────────────────────────┤
│                             │
│  [+ New Chat]              │  ← Tap here
│                             │
└─────────────────────────────┘
```

### Add the Twilio Number

```
New Chat:
┌─────────────────────────────┐
│  New chat                   │
├─────────────────────────────┤
│  Search name or number      │
│  +14155238886              │  ← Type this
│                             │
└─────────────────────────────┘
```

### Send the Join Message

```
Chat with +1 415 523 8886:
┌─────────────────────────────┐
│  +1 415 523 8886           │
├─────────────────────────────┤
│                             │
│  You:                       │
│  join happy-tiger          │  ← Your code from Twilio console
│  [Send]                     │  ← Tap
│                             │
└─────────────────────────────┘
```

---

## Step 3: Wait for Confirmation

**Within seconds, you'll receive:**

```
┌─────────────────────────────┐
│  +1 415 523 8886           │
├─────────────────────────────┤
│                             │
│  Twilio Sandbox:            │
│  ✅ You are all set!        │  ← You'll see this!
│                             │
│  The sandbox can now        │
│  send/receive messages      │
│  from this number.          │
│                             │
│  Reply STOP to leave        │
│  sandbox any time.          │
│                             │
└─────────────────────────────┘
```

**✅ If you see this, you're connected!**

---

## Step 4: Test with SwiftValet

### Now use SwiftValet:

1. **Go to:** https://swift-valet-preview-1.preview.emergentagent.com
2. **Login:** valet@swift.com / valet123
3. **Click:** Blue "+" button
4. **Fill in:**
   ```
   Phone: YOUR_PHONE_NUMBER (with + and country code)
   Plate: TEST-001
   ```
5. **Click:** START PARK
6. **Fill in:**
   ```
   GPS: Click "Skip"
   Zone: Test Zone
   Tag: TAG-001
   ```
7. **Click:** PARK VEHICLE

### Check Your WhatsApp!

You should receive:

```
┌─────────────────────────────┐
│  +1 656 259 3936           │  ← SwiftValet number
├─────────────────────────────┤
│                             │
│  🚗 Welcome to SwiftValet! │
│                             │
│  Your vehicle (Plate:       │
│  TEST-001) is safely        │
│  parked.                    │
│                             │
│  Zone: Test Zone            │
│  🏷️ Tag Number: TAG-001    │
│                             │
│  Reply 'RETR' when you're   │
│  ready to retrieve your     │
│  car.                       │
│                             │
└─────────────────────────────┘
```

---

## Troubleshooting

### ❌ "Not a valid phone number"

**Problem:** Using fake number like +1234567890

**Fix:** Use YOUR real phone number (the one you used to join sandbox)

---

### ❌ "Not able to send message to this number"

**Problem:** You haven't joined the sandbox yet

**Fix:** Complete Step 2 above (send join message)

---

### ❌ No message received

**Checklist:**
- [ ] Did you join the Twilio sandbox?
- [ ] Did you receive the "You are all set!" confirmation?
- [ ] Are you using YOUR real phone number in SwiftValet?
- [ ] Did you include the + and country code?
- [ ] Is your number WhatsApp-enabled?

---

## Quick Test Command

After joining sandbox, test with curl:

```bash
# Replace +YOUR_PHONE_NUMBER with your actual number!
python3 /tmp/test_twilio.py +YOUR_PHONE_NUMBER
```

Example:
```bash
python3 /tmp/test_twilio.py +14155551234
```

This will send a test message directly through Twilio.

---

## Phone Number Format Examples

**✅ Correct:**
- US: `+14155551234`
- UK: `+447911123456`
- India: `+919876543210`
- Singapore: `+6591234567`

**❌ Wrong:**
- `4155551234` (missing +)
- `+1 415 555 1234` (spaces)
- `+1-415-555-1234` (dashes)
- `+1234567890` (fake number)

---

## Still Not Working?

Share with me:
1. Your phone number (with country code)
2. Did you receive the "You are all set!" confirmation?
3. Screenshot of the Twilio console page

I'll test it directly for you!
