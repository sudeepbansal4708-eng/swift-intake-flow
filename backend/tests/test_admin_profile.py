"""
Test cases for Admin Profile feature:
- Admin login returns client_name and client_id
- GET /api/auth/me returns client_name and client_id
- PUT /api/admin/profile updates profile successfully
- PUT /api/admin/profile returns 403 for non-admins
- PUT /api/admin/profile returns 400 when no data provided
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestAdminProfile:
    """Admin Profile endpoint tests"""
    
    @pytest.fixture(scope="class")
    def admin_credentials(self):
        return {"email": "admin@swift.com", "password": "admin123"}
    
    @pytest.fixture(scope="class")
    def valet_credentials(self):
        return {"email": "valet@swift.com", "password": "valet123"}
    
    @pytest.fixture(scope="class")
    def admin_token(self, admin_credentials):
        """Get admin token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json=admin_credentials,
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def valet_token(self, valet_credentials):
        """Get valet token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json=valet_credentials,
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200, f"Valet login failed: {response.text}"
        return response.json()["token"]
    
    def test_admin_login_returns_client_name_and_client_id(self, admin_credentials):
        """Test: Admin login returns client_name and client_id in response"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json=admin_credentials,
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "token" in data
        assert "user" in data
        
        # Verify client_name and client_id are in user object
        assert "client_name" in data["user"], "client_name should be in login response"
        assert "client_id" in data["user"], "client_id should be in login response"
        assert data["user"]["role"] == "admin"
    
    def test_auth_me_returns_client_name_and_client_id(self, admin_token):
        """Test: GET /api/auth/me returns client_name and client_id for admin"""
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify client_name and client_id are returned
        assert "client_name" in data, "client_name should be in /auth/me response"
        assert "client_id" in data, "client_id should be in /auth/me response"
        assert data["role"] == "admin"
    
    def test_update_admin_profile_success(self, admin_token):
        """Test: PUT /api/admin/profile updates name and client_name"""
        # Update profile
        response = requests.put(
            f"{BASE_URL}/api/admin/profile?name=TEST_AdminName&client_name=TEST_ClientBusiness",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify update response
        assert data["message"] == "Profile updated successfully"
        assert data["name"] == "TEST_AdminName"
        assert data["client_name"] == "TEST_ClientBusiness"
        
        # Verify persistence via /auth/me
        verify_response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert verify_response.status_code == 200
        verify_data = verify_response.json()
        assert verify_data["name"] == "TEST_AdminName"
        assert verify_data["client_name"] == "TEST_ClientBusiness"
    
    def test_update_admin_profile_partial_update(self, admin_token):
        """Test: PUT /api/admin/profile allows partial updates (only name or client_name)"""
        # Update only name
        response = requests.put(
            f"{BASE_URL}/api/admin/profile?name=PartialNameUpdate",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "PartialNameUpdate"
        
        # Update only client_name
        response2 = requests.put(
            f"{BASE_URL}/api/admin/profile?client_name=PartialClientUpdate",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response2.status_code == 200
        data2 = response2.json()
        assert data2["client_name"] == "PartialClientUpdate"
    
    def test_update_profile_returns_403_for_non_admin(self, valet_token):
        """Test: PUT /api/admin/profile returns 403 for valet users"""
        response = requests.put(
            f"{BASE_URL}/api/admin/profile?name=ValetTryingToUpdate",
            headers={"Authorization": f"Bearer {valet_token}"}
        )
        
        assert response.status_code == 403
        data = response.json()
        assert "Admin access required" in data.get("detail", "")
    
    def test_update_profile_returns_400_when_no_data(self, admin_token):
        """Test: PUT /api/admin/profile returns 400 when no data provided"""
        response = requests.put(
            f"{BASE_URL}/api/admin/profile",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "No data to update" in data.get("detail", "")
    
    def test_cleanup_restore_original_values(self, admin_token):
        """Cleanup: Restore original admin profile values"""
        response = requests.put(
            f"{BASE_URL}/api/admin/profile?name=Sudeep&client_name=The%20Grand%20Restaurant",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        
        # Verify cleanup
        verify_response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert verify_response.status_code == 200


class TestValetLogin:
    """Verify valet login also returns client_name"""
    
    def test_valet_login_returns_client_name(self):
        """Test: Valet login returns client_name and client_id"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "valet@swift.com", "password": "valet123"},
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify client_name and client_id are present
        assert "client_name" in data["user"]
        assert "client_id" in data["user"]
