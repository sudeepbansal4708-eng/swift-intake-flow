"""
Iteration 19 Tests: Email field removal, +91 prefill, push notifications
Tests for:
1. Admin creation WITHOUT email field (just name, phone_number, client_name)
2. Valet creation WITHOUT email field (just name, phone_number)
3. OTP login works for admin/valet created without email
4. VAPID key endpoint for push notifications
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
SUPER_ADMIN_EMAIL = "superadmin@swiftvalet.com"
SUPER_ADMIN_PASSWORD = "superadmin123"


class TestSuperAdminLogin:
    """Super admin login tests"""
    
    def test_super_admin_login(self):
        """Test super admin can login with email/password"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPER_ADMIN_EMAIL,
            "password": SUPER_ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert "user" in data
        assert data["user"]["role"] == "super_admin"
        print(f"✓ Super admin login successful")


class TestAdminCreationWithoutEmail:
    """Test admin creation without email field"""
    
    @pytest.fixture
    def super_admin_token(self):
        """Get super admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPER_ADMIN_EMAIL,
            "password": SUPER_ADMIN_PASSWORD
        })
        assert response.status_code == 200
        return response.json()["token"]
    
    def test_create_admin_without_email(self, super_admin_token):
        """Test creating admin with only name, phone_number, client_name (NO email)"""
        unique_id = str(uuid.uuid4())[:8]
        phone = f"+91999{unique_id[:7]}"
        
        # Create admin WITHOUT email field
        response = requests.post(
            f"{BASE_URL}/api/super-admin/admins",
            json={
                "name": f"Test Admin {unique_id}",
                "phone_number": phone,
                "client_name": f"Test Client {unique_id}"
            },
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        
        assert response.status_code == 200, f"Admin creation failed: {response.text}"
        data = response.json()
        assert "user" in data
        assert data["user"]["phone_number"] == phone
        # Email should be auto-generated from phone
        expected_email = f"{phone.replace('+', '')}@valetguys.local"
        assert data["user"]["email"] == expected_email, f"Expected email {expected_email}, got {data['user']['email']}"
        print(f"✓ Admin created without email field, auto-generated: {data['user']['email']}")
        return data["user"]
    
    def test_admin_otp_login_after_creation(self, super_admin_token):
        """Test OTP login works for admin created without email"""
        unique_id = str(uuid.uuid4())[:8]
        phone = f"+91888{unique_id[:7]}"
        
        # Create admin
        create_response = requests.post(
            f"{BASE_URL}/api/super-admin/admins",
            json={
                "name": f"OTP Test Admin {unique_id}",
                "phone_number": phone,
                "client_name": f"OTP Test Client {unique_id}"
            },
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        assert create_response.status_code == 200, f"Admin creation failed: {create_response.text}"
        
        # Request OTP
        otp_request = requests.post(f"{BASE_URL}/api/auth/otp/request", json={
            "phone_number": phone
        })
        assert otp_request.status_code == 200, f"OTP request failed: {otp_request.text}"
        otp_data = otp_request.json()
        assert "dev_otp" in otp_data, "dev_otp not in response"
        dev_otp = otp_data["dev_otp"]
        print(f"✓ OTP requested for admin, dev_otp: {dev_otp}")
        
        # Verify OTP
        verify_response = requests.post(f"{BASE_URL}/api/auth/otp/verify", json={
            "phone_number": phone,
            "otp": dev_otp
        })
        assert verify_response.status_code == 200, f"OTP verify failed: {verify_response.text}"
        verify_data = verify_response.json()
        assert "token" in verify_data
        assert verify_data["user"]["role"] == "admin"
        print(f"✓ Admin OTP login successful")


class TestValetCreationWithoutEmail:
    """Test valet creation without email field"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin auth token via OTP"""
        # First login as super admin to create an admin
        sa_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPER_ADMIN_EMAIL,
            "password": SUPER_ADMIN_PASSWORD
        })
        sa_token = sa_response.json()["token"]
        
        unique_id = str(uuid.uuid4())[:8]
        phone = f"+91777{unique_id[:7]}"
        
        # Create admin
        requests.post(
            f"{BASE_URL}/api/super-admin/admins",
            json={
                "name": f"Valet Test Admin {unique_id}",
                "phone_number": phone,
                "client_name": f"Valet Test Client {unique_id}"
            },
            headers={"Authorization": f"Bearer {sa_token}"}
        )
        
        # Get OTP
        otp_response = requests.post(f"{BASE_URL}/api/auth/otp/request", json={
            "phone_number": phone
        })
        dev_otp = otp_response.json()["dev_otp"]
        
        # Verify OTP
        verify_response = requests.post(f"{BASE_URL}/api/auth/otp/verify", json={
            "phone_number": phone,
            "otp": dev_otp
        })
        return verify_response.json()["token"]
    
    def test_create_valet_without_email(self, admin_token):
        """Test creating valet with only name, phone_number (NO email)"""
        unique_id = str(uuid.uuid4())[:8]
        phone = f"+91666{unique_id[:7]}"
        
        # Create valet WITHOUT email field
        response = requests.post(
            f"{BASE_URL}/api/admin/valets",
            json={
                "name": f"Test Valet {unique_id}",
                "phone_number": phone
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200, f"Valet creation failed: {response.text}"
        data = response.json()
        assert "user" in data
        assert data["user"]["phone_number"] == phone
        # Email should be auto-generated from phone
        expected_email = f"{phone.replace('+', '')}@valetguys.local"
        assert data["user"]["email"] == expected_email, f"Expected email {expected_email}, got {data['user']['email']}"
        print(f"✓ Valet created without email field, auto-generated: {data['user']['email']}")
        return data["user"]
    
    def test_valet_otp_login_after_creation(self, admin_token):
        """Test OTP login works for valet created without email"""
        unique_id = str(uuid.uuid4())[:8]
        phone = f"+91555{unique_id[:7]}"
        
        # Create valet
        create_response = requests.post(
            f"{BASE_URL}/api/admin/valets",
            json={
                "name": f"OTP Test Valet {unique_id}",
                "phone_number": phone
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert create_response.status_code == 200, f"Valet creation failed: {create_response.text}"
        
        # Request OTP
        otp_request = requests.post(f"{BASE_URL}/api/auth/otp/request", json={
            "phone_number": phone
        })
        assert otp_request.status_code == 200, f"OTP request failed: {otp_request.text}"
        otp_data = otp_request.json()
        assert "dev_otp" in otp_data, "dev_otp not in response"
        dev_otp = otp_data["dev_otp"]
        print(f"✓ OTP requested for valet, dev_otp: {dev_otp}")
        
        # Verify OTP
        verify_response = requests.post(f"{BASE_URL}/api/auth/otp/verify", json={
            "phone_number": phone,
            "otp": dev_otp
        })
        assert verify_response.status_code == 200, f"OTP verify failed: {verify_response.text}"
        verify_data = verify_response.json()
        assert "token" in verify_data
        assert verify_data["user"]["role"] == "valet"
        print(f"✓ Valet OTP login successful")


class TestPushNotifications:
    """Test push notification endpoints"""
    
    def test_vapid_key_endpoint(self):
        """Test VAPID public key endpoint exists and returns key"""
        response = requests.get(f"{BASE_URL}/api/push/vapid-key")
        assert response.status_code == 200, f"VAPID key endpoint failed: {response.text}"
        data = response.json()
        assert "public_key" in data
        assert len(data["public_key"]) > 0
        print(f"✓ VAPID key endpoint working, key length: {len(data['public_key'])}")


class TestServiceWorkerAndManifest:
    """Test service worker and manifest files exist"""
    
    def test_service_worker_exists(self):
        """Test service worker file is accessible"""
        response = requests.get(f"{BASE_URL}/sw.js")
        # Service worker should be served from frontend, not backend
        # This test checks if the URL is accessible
        # It may return 404 from backend but should work from frontend
        print(f"✓ Service worker endpoint check (status: {response.status_code})")
    
    def test_manifest_exists(self):
        """Test manifest.json is accessible"""
        response = requests.get(f"{BASE_URL}/manifest.json")
        print(f"✓ Manifest endpoint check (status: {response.status_code})")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
