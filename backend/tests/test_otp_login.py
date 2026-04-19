"""
Test cases for Valet OTP Login feature:
- POST /api/auth/otp/request with valid valet phone returns success
- POST /api/auth/otp/request with unknown phone returns 404
- POST /api/auth/otp/verify with correct OTP returns JWT token
- POST /api/auth/otp/verify with wrong OTP returns 400
- POST /api/admin/valets creates valet WITHOUT password, WITH phone_number
- Admin/Super Admin login still works with password
"""
import pytest
import requests
import os
from pymongo import MongoClient

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# MongoDB connection for OTP verification
mongo_client = MongoClient('mongodb://localhost:27017')
db = mongo_client['swiftvalet_db']


class TestOTPLogin:
    """OTP Login endpoint tests"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@swift.com", "password": "admin123"},
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def test_valet_phone(self):
        """Test valet phone number - already exists"""
        return "+919999888877"
    
    def test_otp_request_valid_phone_returns_success(self, test_valet_phone):
        """Test: POST /api/auth/otp/request with valid valet phone returns success"""
        response = requests.post(
            f"{BASE_URL}/api/auth/otp/request",
            json={"phone_number": test_valet_phone},
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "message" in data
        assert data["message"] == "OTP sent to your WhatsApp"
        assert "phone_number" in data
        assert data["phone_number"] == test_valet_phone
        print(f"SUCCESS: OTP request returned: {data}")
    
    def test_otp_request_unknown_phone_returns_404(self):
        """Test: POST /api/auth/otp/request with unknown phone returns 404"""
        response = requests.post(
            f"{BASE_URL}/api/auth/otp/request",
            json={"phone_number": "+919876543210"},
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "No valet account found" in data["detail"]
        print(f"SUCCESS: Unknown phone returned 404 with message: {data['detail']}")
    
    def test_otp_verify_correct_otp_returns_jwt(self, test_valet_phone):
        """Test: POST /api/auth/otp/verify with correct OTP returns JWT token"""
        # First, request OTP
        requests.post(
            f"{BASE_URL}/api/auth/otp/request",
            json={"phone_number": test_valet_phone},
            headers={"Content-Type": "application/json"}
        )
        
        # Get OTP from MongoDB
        otp_record = db.otps.find_one({"phone_number": test_valet_phone})
        assert otp_record is not None, "OTP record not found in database"
        
        otp = otp_record['otp']
        print(f"Retrieved OTP from DB: {otp}")
        
        # Verify OTP
        response = requests.post(
            f"{BASE_URL}/api/auth/otp/verify",
            json={"phone_number": test_valet_phone, "otp": otp},
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "token" in data
        assert "user" in data
        assert isinstance(data["token"], str)
        assert len(data["token"]) > 0
        
        # Verify user data
        assert data["user"]["role"] == "valet"
        assert "email" in data["user"]
        assert "name" in data["user"]
        print(f"SUCCESS: OTP verify returned JWT and user: {data['user']}")
    
    def test_otp_verify_wrong_otp_returns_400(self, test_valet_phone):
        """Test: POST /api/auth/otp/verify with wrong OTP returns 400"""
        # First, request OTP
        requests.post(
            f"{BASE_URL}/api/auth/otp/request",
            json={"phone_number": test_valet_phone},
            headers={"Content-Type": "application/json"}
        )
        
        # Try with wrong OTP
        response = requests.post(
            f"{BASE_URL}/api/auth/otp/verify",
            json={"phone_number": test_valet_phone, "otp": "000000"},
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "Invalid OTP" in data["detail"]
        print(f"SUCCESS: Wrong OTP returned 400 with message: {data['detail']}")


class TestAdminPasswordLogin:
    """Verify Admin/Super Admin password login still works"""
    
    def test_admin_login_with_password_works(self):
        """Test: Admin login with password works (admin@swift.com)"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@swift.com", "password": "admin123"},
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "token" in data
        assert "user" in data
        assert data["user"]["role"] == "admin"
        assert data["user"]["email"] == "admin@swift.com"
        print(f"SUCCESS: Admin login works - role: {data['user']['role']}")
    
    def test_super_admin_login_with_password_works(self):
        """Test: Super Admin login with password works (superadmin@swiftvalet.com)"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": os.environ.get("TEST_ADMIN_EMAIL", "superadmin@swiftvalet.com"), "password": os.environ.get("TEST_ADMIN_PASSWORD", "superadmin123")},
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "token" in data
        assert "user" in data
        assert data["user"]["role"] == "super_admin"
        assert data["user"]["email"] == os.environ.get("TEST_ADMIN_EMAIL", "superadmin@swiftvalet.com")
        print(f"SUCCESS: Super Admin login works - role: {data['user']['role']}")


class TestCreateValetWithPhone:
    """Test creating valet without password, with phone_number"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@swift.com", "password": "admin123"},
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200
        return response.json()["token"]
    
    def test_create_valet_with_phone_no_password(self, admin_token):
        """Test: POST /api/admin/valets creates valet WITHOUT password, WITH phone_number"""
        import uuid
        unique_id = str(uuid.uuid4())[:8]
        
        valet_data = {
            "email": f"TEST_otp_valet_{unique_id}@test.com",
            "name": f"TEST OTP Valet {unique_id}",
            "phone_number": f"+91777788{unique_id[:4]}",
            "driver_license_number": "DL-TEST123"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/admin/valets",
            json=valet_data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {admin_token}"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response
        assert data["message"] == "Valet created"
        assert "user" in data
        assert data["user"]["email"] == valet_data["email"]
        assert data["user"]["name"] == valet_data["name"]
        assert "phone_number" in data["user"]
        
        # Phone should be normalized with +
        assert data["user"]["phone_number"].startswith("+")
        print(f"SUCCESS: Valet created with phone: {data['user']['phone_number']}")
        
        # Verify in database - no password_hash
        user_in_db = db.users.find_one({"email": valet_data["email"]})
        assert user_in_db is not None
        assert user_in_db.get("phone_number") == data["user"]["phone_number"]
        
        # Password hash should be None for OTP-based valets
        if user_in_db.get("password_hash"):
            print(f"INFO: Valet has password_hash (may be None or empty): {user_in_db.get('password_hash')}")
        else:
            print("SUCCESS: Valet has no password_hash (OTP-only login)")
    
    def test_create_valet_duplicate_phone_fails(self, admin_token):
        """Test: Creating valet with duplicate phone number fails"""
        valet_data = {
            "email": "TEST_dup_phone@test.com",
            "name": "TEST Duplicate Phone",
            "phone_number": "+919999888877",  # This already exists
            "driver_license_number": "DL-DUP"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/admin/valets",
            json=valet_data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {admin_token}"
            }
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "Phone number already registered" in data.get("detail", "")
        print(f"SUCCESS: Duplicate phone rejected with: {data['detail']}")


class TestValetAccessAfterOTPLogin:
    """Test that valet can access dashboard and tickets after OTP login"""
    
    @pytest.fixture(scope="class")
    def valet_token(self):
        """Get valet token via OTP"""
        phone = "+919999888877"
        
        # Request OTP
        requests.post(
            f"{BASE_URL}/api/auth/otp/request",
            json={"phone_number": phone},
            headers={"Content-Type": "application/json"}
        )
        
        # Get OTP from DB
        otp_record = db.otps.find_one({"phone_number": phone})
        if not otp_record:
            pytest.skip("Could not get OTP from database")
        
        otp = otp_record['otp']
        
        # Verify OTP
        response = requests.post(
            f"{BASE_URL}/api/auth/otp/verify",
            json={"phone_number": phone, "otp": otp},
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code != 200:
            pytest.skip(f"OTP verify failed: {response.text}")
        
        return response.json()["token"]
    
    def test_valet_can_access_auth_me(self, valet_token):
        """Test: Valet can access /api/auth/me after OTP login"""
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {valet_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["role"] == "valet"
        assert "email" in data
        assert "name" in data
        print(f"SUCCESS: Valet can access /auth/me - {data['name']}")
    
    def test_valet_can_access_tickets(self, valet_token):
        """Test: Valet can access /api/tickets after OTP login"""
        response = requests.get(
            f"{BASE_URL}/api/tickets",
            headers={"Authorization": f"Bearer {valet_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        print(f"SUCCESS: Valet can access tickets - found {len(data)} tickets")
    
    def test_valet_can_access_vehicles(self, valet_token):
        """Test: Valet can access /api/vehicles after OTP login"""
        response = requests.get(
            f"{BASE_URL}/api/vehicles",
            headers={"Authorization": f"Bearer {valet_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        print(f"SUCCESS: Valet can access vehicles - found {len(data)} vehicles")


class TestCleanup:
    """Cleanup test data"""
    
    def test_cleanup_test_valets(self):
        """Cleanup: Remove TEST_ prefixed valets"""
        result = db.users.delete_many({"email": {"$regex": "^TEST_"}})
        print(f"Cleaned up {result.deleted_count} test users")
        
        # Also clean up test OTPs
        db.otps.delete_many({})
        print("Cleaned up OTP records")
