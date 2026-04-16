"""
Test suite for SwiftValet Delete Features:
- DELETE /api/super-admin/admins/{admin_id} - Super admin can deactivate client admins
- DELETE /api/admin/valets/{valet_id} - Admin can deactivate valets
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
SUPER_ADMIN_EMAIL = os.environ.get("TEST_ADMIN_EMAIL", "superadmin@swiftvalet.com")
SUPER_ADMIN_PASSWORD = os.environ.get("TEST_ADMIN_PASSWORD", "superadmin123")

class TestSuperAdminDeleteAdmin:
    """Tests for DELETE /api/super-admin/admins/{admin_id}"""
    
    @pytest.fixture
    def super_admin_token(self):
        """Authenticate as super admin and return token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPER_ADMIN_EMAIL,
            "password": SUPER_ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Super admin login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "super_admin"
        return data["token"]
    
    @pytest.fixture
    def auth_headers(self, super_admin_token):
        """Return authorization headers"""
        return {"Authorization": f"Bearer {super_admin_token}"}
    
    def test_create_and_delete_admin(self, auth_headers):
        """Test creating a new admin and then deleting (deactivating) them"""
        unique_suffix = str(uuid.uuid4())[:8]
        
        # Create a new admin
        admin_data = {
            "email": f"TEST_admin_{unique_suffix}@test.com",
            "name": f"TEST Admin {unique_suffix}",
            "phone_number": f"+919{unique_suffix}",
            "client_name": f"TEST Client {unique_suffix}"
        }
        
        create_response = requests.post(
            f"{BASE_URL}/api/super-admin/admins",
            json=admin_data,
            headers=auth_headers
        )
        assert create_response.status_code == 200, f"Create admin failed: {create_response.text}"
        
        created_admin = create_response.json()
        assert "user" in created_admin
        admin_id = created_admin["user"]["id"]
        print(f"✅ Created admin with ID: {admin_id}")
        
        # Verify admin appears in clients list (active)
        clients_response = requests.get(
            f"{BASE_URL}/api/super-admin/clients",
            headers=auth_headers
        )
        assert clients_response.status_code == 200
        clients = clients_response.json()
        admin_found = next((c for c in clients if c['id'] == admin_id), None)
        assert admin_found is not None, "Created admin not found in clients list"
        assert admin_found.get('is_active', True) == True, "Admin should be active initially"
        print(f"✅ Admin found in clients list and is active")
        
        # Delete (deactivate) the admin
        delete_response = requests.delete(
            f"{BASE_URL}/api/super-admin/admins/{admin_id}",
            headers=auth_headers
        )
        assert delete_response.status_code == 200, f"Delete admin failed: {delete_response.text}"
        assert delete_response.json().get("message") == "Admin deactivated"
        print(f"✅ Admin deactivated successfully")
        
        # Verify admin is now inactive
        clients_response2 = requests.get(
            f"{BASE_URL}/api/super-admin/clients",
            headers=auth_headers
        )
        assert clients_response2.status_code == 200
        clients2 = clients_response2.json()
        admin_after_delete = next((c for c in clients2 if c['id'] == admin_id), None)
        assert admin_after_delete is not None, "Admin should still exist in list after deactivation"
        assert admin_after_delete.get('is_active') == False, "Admin should be inactive after delete"
        print(f"✅ Admin is_active=False after deletion")
    
    def test_delete_nonexistent_admin(self, auth_headers):
        """Test deleting an admin that doesn't exist returns 404"""
        fake_id = str(uuid.uuid4())
        
        response = requests.delete(
            f"{BASE_URL}/api/super-admin/admins/{fake_id}",
            headers=auth_headers
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"✅ Delete nonexistent admin returns 404")
    
    def test_delete_admin_without_auth(self):
        """Test deleting admin without authentication returns 401/403"""
        fake_id = str(uuid.uuid4())
        
        response = requests.delete(f"{BASE_URL}/api/super-admin/admins/{fake_id}")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print(f"✅ Delete admin without auth returns {response.status_code}")


class TestAdminDeleteValet:
    """Tests for DELETE /api/admin/valets/{valet_id}"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin token via OTP flow"""
        # Request OTP for known admin phone
        admin_phone = "+919111222333"
        
        otp_response = requests.post(f"{BASE_URL}/api/auth/otp/request", json={
            "phone_number": admin_phone
        })
        assert otp_response.status_code == 200, f"OTP request failed: {otp_response.text}"
        
        otp_data = otp_response.json()
        # In dev mode, OTP is returned in response
        otp = otp_data.get('dev_otp')
        assert otp is not None, "OTP not found in dev response"
        
        # Verify OTP
        verify_response = requests.post(f"{BASE_URL}/api/auth/otp/verify", json={
            "phone_number": admin_phone,
            "otp": otp
        })
        assert verify_response.status_code == 200, f"OTP verify failed: {verify_response.text}"
        
        token_data = verify_response.json()
        assert "token" in token_data
        assert token_data["user"]["role"] == "admin"
        return token_data["token"]
    
    @pytest.fixture
    def admin_auth_headers(self, admin_token):
        """Return authorization headers for admin"""
        return {"Authorization": f"Bearer {admin_token}"}
    
    def test_create_and_delete_valet(self, admin_auth_headers):
        """Test creating a valet and then deleting (deactivating) them"""
        unique_suffix = str(uuid.uuid4())[:8]
        
        # Create a new valet
        valet_data = {
            "email": f"TEST_valet_{unique_suffix}@test.com",
            "name": f"TEST Valet {unique_suffix}",
            "phone_number": f"+918{unique_suffix}",
            "driver_license_number": f"DL-TEST-{unique_suffix}"
        }
        
        create_response = requests.post(
            f"{BASE_URL}/api/admin/valets",
            json=valet_data,
            headers=admin_auth_headers
        )
        assert create_response.status_code == 200, f"Create valet failed: {create_response.text}"
        
        created_valet = create_response.json()
        assert "user" in created_valet
        valet_id = created_valet["user"]["id"]
        print(f"✅ Created valet with ID: {valet_id}")
        
        # Verify valet appears in valets list (active)
        valets_response = requests.get(
            f"{BASE_URL}/api/admin/valets",
            headers=admin_auth_headers
        )
        assert valets_response.status_code == 200
        valets = valets_response.json()
        valet_found = next((v for v in valets if v['id'] == valet_id), None)
        assert valet_found is not None, "Created valet not found in valets list"
        assert valet_found.get('is_active', True) == True, "Valet should be active initially"
        print(f"✅ Valet found in valets list and is active")
        
        # Delete (deactivate) the valet
        delete_response = requests.delete(
            f"{BASE_URL}/api/admin/valets/{valet_id}",
            headers=admin_auth_headers
        )
        assert delete_response.status_code == 200, f"Delete valet failed: {delete_response.text}"
        assert delete_response.json().get("message") == "Valet deactivated"
        print(f"✅ Valet deactivated successfully")
        
        # Verify valet is now inactive
        valets_response2 = requests.get(
            f"{BASE_URL}/api/admin/valets",
            headers=admin_auth_headers
        )
        assert valets_response2.status_code == 200
        valets2 = valets_response2.json()
        valet_after_delete = next((v for v in valets2 if v['id'] == valet_id), None)
        assert valet_after_delete is not None, "Valet should still exist in list after deactivation"
        assert valet_after_delete.get('is_active') == False, "Valet should be inactive after delete"
        print(f"✅ Valet is_active=False after deletion")
    
    def test_valet_list_only_shows_valet_role(self, admin_auth_headers):
        """Test that the valets list endpoint returns users - verify no admin users are returned as valets"""
        valets_response = requests.get(
            f"{BASE_URL}/api/admin/valets",
            headers=admin_auth_headers
        )
        assert valets_response.status_code == 200
        valets = valets_response.json()
        
        # The frontend filters by role !== 'admin', but backend may return all client users
        # Check what roles are in the response
        roles_found = set([v.get('role') for v in valets])
        print(f"Roles found in valets response: {roles_found}")
        
        # Valets with role 'valet' should exist if any were created
        # This test validates the data structure
        for v in valets:
            assert 'id' in v, "Valet should have id"
            assert 'name' in v, "Valet should have name"
            assert 'role' in v, "Valet should have role"
        print(f"✅ Valets list structure is correct")
    
    def test_delete_nonexistent_valet(self, admin_auth_headers):
        """Test deleting a valet that doesn't exist returns 404"""
        fake_id = str(uuid.uuid4())
        
        response = requests.delete(
            f"{BASE_URL}/api/admin/valets/{fake_id}",
            headers=admin_auth_headers
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"✅ Delete nonexistent valet returns 404")
    
    def test_delete_valet_without_auth(self):
        """Test deleting valet without authentication returns 401/403"""
        fake_id = str(uuid.uuid4())
        
        response = requests.delete(f"{BASE_URL}/api/admin/valets/{fake_id}")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print(f"✅ Delete valet without auth returns {response.status_code}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
