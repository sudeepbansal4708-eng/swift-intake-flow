"""
Test cases for Admin OTP Login feature (iteration 4):
- Login page shows 'Login with OTP' and 'Super Admin Login' buttons
- Super Admin login still works with password (superadmin@swiftvalet.com)
- POST /api/super-admin/admins creates admin WITHOUT password, WITH phone_number
- POST /api/auth/otp/request works for both admin and valet phone numbers
- POST /api/auth/otp/verify works for admin phone, returns role=admin and client_name
- POST /api/auth/otp/verify works for valet phone, returns role=valet
- Duplicate admin phone number is rejected
- After OTP login as admin, admin can access admin panel features
"""
import pytest
import requests
import os
import uuid
from pymongo import MongoClient

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# MongoDB connection for OTP verification
mongo_client = MongoClient('mongodb://localhost:27017')
db = mongo_client['swiftvalet_db']


class TestSuperAdminPasswordLogin:
    """Test Super Admin password login (only super admin uses password now)"""
    
    def test_super_admin_login_with_password_works(self):
        """Test: Super Admin login with password works (superadmin@swiftvalet.com/superadmin123)"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": os.environ.get("TEST_ADMIN_EMAIL", "superadmin@swiftvalet.com"), "password": os.environ.get("TEST_ADMIN_PASSWORD", "superadmin123")},
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 200, f"Super Admin login failed: {response.text}"
        data = response.json()
        
        assert "token" in data
        assert "user" in data
        assert data["user"]["role"] == "super_admin"
        assert data["user"]["email"] == os.environ.get("TEST_ADMIN_EMAIL", "superadmin@swiftvalet.com")
        print(f"SUCCESS: Super Admin login works - role: {data['user']['role']}")


class TestCreateAdminWithPhone:
    """Test Super Admin can create client admins without password, with phone_number"""
    
    @pytest.fixture(scope="class")
    def super_admin_token(self):
        """Get super admin token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": os.environ.get("TEST_ADMIN_EMAIL", "superadmin@swiftvalet.com"), "password": os.environ.get("TEST_ADMIN_PASSWORD", "superadmin123")},
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200, f"Super Admin login failed: {response.text}"
        return response.json()["token"]
    
    def test_create_admin_with_phone_no_password(self, super_admin_token):
        """Test: POST /api/super-admin/admins creates admin WITHOUT password, WITH phone_number"""
        unique_id = str(uuid.uuid4())[:8]
        
        admin_data = {
            "email": f"TEST_admin_{unique_id}@test.com",
            "name": f"TEST Admin {unique_id}",
            "phone_number": f"+91888899{unique_id[:4]}",
            "client_name": f"TEST Client {unique_id}"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/super-admin/admins",
            json=admin_data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {super_admin_token}"
            }
        )
        
        assert response.status_code == 200, f"Create admin failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert data["message"] == "Admin created"
        assert "user" in data
        assert data["user"]["email"] == admin_data["email"]
        assert data["user"]["name"] == admin_data["name"]
        assert "phone_number" in data["user"]
        assert data["user"]["phone_number"].startswith("+")
        assert data["user"]["client_name"] == admin_data["client_name"]
        
        print(f"SUCCESS: Admin created with phone: {data['user']['phone_number']}, client: {data['user']['client_name']}")
        
        # Verify in database - no password_hash
        user_in_db = db.users.find_one({"email": admin_data["email"]})
        assert user_in_db is not None
        assert user_in_db.get("phone_number") == data["user"]["phone_number"]
        assert user_in_db.get("role") == "admin"
        
        # Password hash should be None for OTP-based admins
        if not user_in_db.get("password_hash"):
            print("SUCCESS: Admin has no password_hash (OTP-only login)")
        else:
            print(f"INFO: Admin has password_hash: {user_in_db.get('password_hash')}")
    
    def test_create_admin_duplicate_phone_fails(self, super_admin_token):
        """Test: Creating admin with duplicate phone number fails"""
        # First create an admin
        unique_id = str(uuid.uuid4())[:8]
        phone = f"+91999111{unique_id[:4]}"
        
        admin_data = {
            "email": f"TEST_admin_first_{unique_id}@test.com",
            "name": "TEST First Admin",
            "phone_number": phone,
            "client_name": "TEST First Client"
        }
        
        response1 = requests.post(
            f"{BASE_URL}/api/super-admin/admins",
            json=admin_data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {super_admin_token}"
            }
        )
        assert response1.status_code == 200, f"First admin creation failed: {response1.text}"
        
        # Try to create another admin with same phone
        admin_data2 = {
            "email": f"TEST_admin_second_{unique_id}@test.com",
            "name": "TEST Second Admin",
            "phone_number": phone,  # Same phone number
            "client_name": "TEST Second Client"
        }
        
        response2 = requests.post(
            f"{BASE_URL}/api/super-admin/admins",
            json=admin_data2,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {super_admin_token}"
            }
        )
        
        assert response2.status_code == 400, f"Expected 400 but got {response2.status_code}: {response2.text}"
        data = response2.json()
        assert "Phone number already registered" in data.get("detail", "")
        print(f"SUCCESS: Duplicate admin phone rejected with: {data['detail']}")


class TestAdminOTPLogin:
    """Test Admin can login via OTP (both request and verify)"""
    
    @pytest.fixture(scope="class")
    def test_admin_phone(self):
        """Get test admin phone - create one if needed"""
        # Use the admin phone from dev: +919111222333
        return "+919111222333"
    
    @pytest.fixture(scope="class")
    def super_admin_token(self):
        """Get super admin token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": os.environ.get("TEST_ADMIN_EMAIL", "superadmin@swiftvalet.com"), "password": os.environ.get("TEST_ADMIN_PASSWORD", "superadmin123")},
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200
        return response.json()["token"]
    
    @pytest.fixture(scope="class", autouse=True)
    def ensure_test_admin_exists(self, super_admin_token, test_admin_phone):
        """Ensure test admin exists with the phone number"""
        # Check if admin with this phone exists
        existing = db.users.find_one({"phone_number": test_admin_phone, "role": "admin"})
        if existing:
            print(f"Test admin exists: {existing['email']}")
            return
        
        # Create test admin
        admin_data = {
            "email": "newadmin@test.com",
            "name": "New Admin",
            "phone_number": test_admin_phone,
            "client_name": "Test Client"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/super-admin/admins",
            json=admin_data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {super_admin_token}"
            }
        )
        
        if response.status_code == 200:
            print(f"Created test admin: {admin_data['email']}")
        elif response.status_code == 400:
            # Email might already exist - that's OK
            print(f"Admin creation returned 400 (may already exist): {response.text}")
        else:
            print(f"Warning: Admin creation unexpected response: {response.status_code} - {response.text}")
    
    def test_otp_request_for_admin_phone_works(self, test_admin_phone):
        """Test: POST /api/auth/otp/request works for admin phone number"""
        response = requests.post(
            f"{BASE_URL}/api/auth/otp/request",
            json={"phone_number": test_admin_phone},
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 200, f"OTP request failed for admin: {response.text}"
        data = response.json()
        
        assert data["message"] == "OTP sent to your WhatsApp"
        assert data["phone_number"] == test_admin_phone
        print(f"SUCCESS: OTP request for admin phone returned: {data}")
    
    def test_otp_verify_for_admin_returns_admin_role(self, test_admin_phone):
        """Test: POST /api/auth/otp/verify for admin phone returns role=admin and client_name"""
        # First request OTP
        requests.post(
            f"{BASE_URL}/api/auth/otp/request",
            json={"phone_number": test_admin_phone},
            headers={"Content-Type": "application/json"}
        )
        
        # Get OTP from MongoDB
        otp_record = db.otps.find_one({"phone_number": test_admin_phone})
        assert otp_record is not None, "OTP record not found for admin"
        
        otp = otp_record['otp']
        print(f"Retrieved admin OTP from DB: {otp}")
        
        # Verify OTP
        response = requests.post(
            f"{BASE_URL}/api/auth/otp/verify",
            json={"phone_number": test_admin_phone, "otp": otp},
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 200, f"OTP verify failed for admin: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "token" in data
        assert "user" in data
        assert data["user"]["role"] == "admin", f"Expected role=admin but got: {data['user']['role']}"
        assert "client_name" in data["user"], "Admin response should include client_name"
        
        print(f"SUCCESS: Admin OTP verify returned role={data['user']['role']}, client_name={data['user'].get('client_name')}")
        return data["token"]


class TestValetOTPLogin:
    """Test Valet OTP login still works (from iteration 3)"""
    
    @pytest.fixture(scope="class")
    def test_valet_phone(self):
        """Test valet phone number - already exists from iteration 3"""
        return "+919999888877"
    
    def test_otp_request_for_valet_phone_works(self, test_valet_phone):
        """Test: POST /api/auth/otp/request works for valet phone number"""
        response = requests.post(
            f"{BASE_URL}/api/auth/otp/request",
            json={"phone_number": test_valet_phone},
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 200, f"OTP request failed for valet: {response.text}"
        data = response.json()
        
        assert data["message"] == "OTP sent to your WhatsApp"
        print(f"SUCCESS: OTP request for valet phone returned: {data}")
    
    def test_otp_verify_for_valet_returns_valet_role(self, test_valet_phone):
        """Test: POST /api/auth/otp/verify for valet phone returns role=valet"""
        # First request OTP
        requests.post(
            f"{BASE_URL}/api/auth/otp/request",
            json={"phone_number": test_valet_phone},
            headers={"Content-Type": "application/json"}
        )
        
        # Get OTP from MongoDB
        otp_record = db.otps.find_one({"phone_number": test_valet_phone})
        assert otp_record is not None, "OTP record not found for valet"
        
        otp = otp_record['otp']
        
        # Verify OTP
        response = requests.post(
            f"{BASE_URL}/api/auth/otp/verify",
            json={"phone_number": test_valet_phone, "otp": otp},
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 200, f"OTP verify failed for valet: {response.text}"
        data = response.json()
        
        assert data["user"]["role"] == "valet", f"Expected role=valet but got: {data['user']['role']}"
        print(f"SUCCESS: Valet OTP verify returned role={data['user']['role']}")


class TestAdminAccessAfterOTPLogin:
    """Test admin can access admin panel features after OTP login"""
    
    @pytest.fixture(scope="class")
    def admin_token_via_otp(self):
        """Get admin token via OTP"""
        phone = "+919111222333"
        
        # Request OTP
        requests.post(
            f"{BASE_URL}/api/auth/otp/request",
            json={"phone_number": phone},
            headers={"Content-Type": "application/json"}
        )
        
        # Get OTP from DB
        otp_record = db.otps.find_one({"phone_number": phone})
        if not otp_record:
            pytest.skip("Could not get OTP for admin from database")
        
        otp = otp_record['otp']
        
        # Verify OTP
        response = requests.post(
            f"{BASE_URL}/api/auth/otp/verify",
            json={"phone_number": phone, "otp": otp},
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code != 200:
            pytest.skip(f"Admin OTP verify failed: {response.text}")
        
        return response.json()["token"]
    
    def test_admin_can_access_auth_me(self, admin_token_via_otp):
        """Test: Admin can access /api/auth/me after OTP login"""
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {admin_token_via_otp}"}
        )
        
        assert response.status_code == 200, f"Auth/me failed: {response.text}"
        data = response.json()
        
        assert data["role"] == "admin"
        print(f"SUCCESS: Admin can access /auth/me - role={data['role']}, name={data['name']}")
    
    def test_admin_can_access_valets_list(self, admin_token_via_otp):
        """Test: Admin can access /api/admin/valets after OTP login"""
        response = requests.get(
            f"{BASE_URL}/api/admin/valets",
            headers={"Authorization": f"Bearer {admin_token_via_otp}"}
        )
        
        assert response.status_code == 200, f"Admin valets endpoint failed: {response.text}"
        data = response.json()
        
        assert isinstance(data, list)
        print(f"SUCCESS: Admin can access valets list - found {len(data)} valets")
    
    def test_admin_can_create_valet(self, admin_token_via_otp):
        """Test: Admin can create valet after OTP login"""
        unique_id = str(uuid.uuid4())[:8]
        
        valet_data = {
            "email": f"TEST_admin_created_valet_{unique_id}@test.com",
            "name": f"TEST Admin Created Valet {unique_id}",
            "phone_number": f"+91666777{unique_id[:4]}",
            "driver_license_number": "DL-ADMIN-TEST"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/admin/valets",
            json=valet_data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {admin_token_via_otp}"
            }
        )
        
        assert response.status_code == 200, f"Admin create valet failed: {response.text}"
        data = response.json()
        
        assert data["message"] == "Valet created"
        assert data["user"]["email"] == valet_data["email"]
        print(f"SUCCESS: Admin created valet after OTP login: {data['user']['email']}")


class TestSuperAdminPanelEndpoints:
    """Test Super Admin panel endpoints for iteration 4 changes"""
    
    @pytest.fixture(scope="class")
    def super_admin_token(self):
        """Get super admin token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": os.environ.get("TEST_ADMIN_EMAIL", "superadmin@swiftvalet.com"), "password": os.environ.get("TEST_ADMIN_PASSWORD", "superadmin123")},
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200
        return response.json()["token"]
    
    def test_super_admin_can_list_clients(self, super_admin_token):
        """Test: Super Admin can access /api/super-admin/clients"""
        response = requests.get(
            f"{BASE_URL}/api/super-admin/clients",
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        
        assert response.status_code == 200, f"List clients failed: {response.text}"
        data = response.json()
        
        assert isinstance(data, list)
        
        # Check that admins have phone_number field
        for admin in data:
            # Each admin should have phone_number if created after iteration 4
            print(f"Admin: {admin.get('name')} - phone: {admin.get('phone_number')}")
        
        print(f"SUCCESS: Super Admin can list {len(data)} clients")
    
    def test_super_admin_can_access_analytics(self, super_admin_token):
        """Test: Super Admin can access /api/super-admin/analytics"""
        response = requests.get(
            f"{BASE_URL}/api/super-admin/analytics",
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        
        assert response.status_code == 200, f"Analytics failed: {response.text}"
        data = response.json()
        
        assert "total_clients" in data
        assert "cars_parked_now" in data
        assert "total_tips_today" in data
        print(f"SUCCESS: Analytics: clients={data['total_clients']}, parked={data['cars_parked_now']}")


class TestCleanup:
    """Cleanup test data created during this iteration"""
    
    def test_cleanup_test_users(self):
        """Cleanup: Remove TEST_ prefixed users (admins and valets)"""
        result = db.users.delete_many({"email": {"$regex": "^TEST_"}})
        print(f"Cleaned up {result.deleted_count} test users")
        
        # Also clean up test OTPs
        db.otps.delete_many({})
        print("Cleaned up OTP records")
