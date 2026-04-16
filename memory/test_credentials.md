# Test Credentials

## Super Admin
- Email: superadmin@swiftvalet.com
- Password: superadmin123
- Login: POST /api/auth/login with email/password

## Admin / Valet (OTP Login)
- Created via Super Admin panel or POST /api/super-admin/admins
- Login: POST /api/auth/otp/request with phone_number -> returns dev_otp in response
- Verify: POST /api/auth/otp/verify with phone_number and otp
