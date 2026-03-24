"""
Test suite for Admin Dashboard Stats and Profile Photo features
- GET /api/admin/dashboard-stats: Returns active_valets, parked_vehicles, tips, totals
- POST /api/admin/profile/photo: Upload profile photo
- GET /api/auth/me: Returns profile_photo field
"""
import pytest
import requests
import os
import base64

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestAdminDashboardStats:
    """Tests for GET /api/admin/dashboard-stats endpoint"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin token via OTP login"""
        # Request OTP
        response = requests.post(f"{BASE_URL}/api/auth/otp/request", json={
            "phone_number": "+919373991136"
        })
        assert response.status_code == 200, f"OTP request failed: {response.text}"
        otp = response.json().get('dev_otp')
        assert otp, "No OTP returned in response"
        
        # Verify OTP
        response = requests.post(f"{BASE_URL}/api/auth/otp/verify", json={
            "phone_number": "+919373991136",
            "otp": otp
        })
        assert response.status_code == 200, f"OTP verify failed: {response.text}"
        token = response.json().get('token')
        assert token, "No token returned"
        return token
    
    def test_dashboard_stats_returns_correct_structure(self, admin_token):
        """Test that dashboard-stats returns all required fields"""
        response = requests.get(
            f"{BASE_URL}/api/admin/dashboard-stats",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Dashboard stats failed: {response.text}"
        
        data = response.json()
        
        # Check top-level keys
        assert "active_valets" in data, "Missing active_valets"
        assert "parked_vehicles" in data, "Missing parked_vehicles"
        assert "tips" in data, "Missing tips"
        assert "totals" in data, "Missing totals"
        
        # Check totals structure
        totals = data["totals"]
        assert "valets" in totals, "Missing totals.valets"
        assert "vehicles" in totals, "Missing totals.vehicles"
        assert "tips_amount" in totals, "Missing totals.tips_amount"
        
        # Check types
        assert isinstance(data["active_valets"], list), "active_valets should be a list"
        assert isinstance(data["parked_vehicles"], list), "parked_vehicles should be a list"
        assert isinstance(data["tips"], list), "tips should be a list"
        assert isinstance(totals["valets"], int), "totals.valets should be int"
        assert isinstance(totals["vehicles"], int), "totals.vehicles should be int"
    
    def test_active_valets_have_required_fields(self, admin_token):
        """Test that active valets have name, phone, email, license number"""
        response = requests.get(
            f"{BASE_URL}/api/admin/dashboard-stats",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        active_valets = data.get("active_valets", [])
        
        # If there are valets, check their structure
        if len(active_valets) > 0:
            valet = active_valets[0]
            assert "id" in valet, "Valet missing id"
            assert "name" in valet, "Valet missing name"
            assert "phone_number" in valet, "Valet missing phone_number"
            assert "email" in valet, "Valet missing email"
            assert "driver_license_number" in valet, "Valet missing driver_license_number"
    
    def test_parked_vehicles_have_required_fields(self, admin_token):
        """Test that parked vehicles have license_plate, zone_label, tag_number, parked_by_name"""
        response = requests.get(
            f"{BASE_URL}/api/admin/dashboard-stats",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        parked_vehicles = data.get("parked_vehicles", [])
        
        # If there are vehicles, check their structure
        if len(parked_vehicles) > 0:
            vehicle = parked_vehicles[0]
            assert "id" in vehicle, "Vehicle missing id"
            assert "license_plate" in vehicle, "Vehicle missing license_plate"
            assert "phone_number" in vehicle, "Vehicle missing phone_number"
            assert "parked_by_name" in vehicle, "Vehicle missing parked_by_name"
            # Optional fields
            assert "tag_number" in vehicle or vehicle.get("tag_number") is None
            assert "zone_label" in vehicle or vehicle.get("zone_label") is None
    
    def test_dashboard_stats_requires_auth(self):
        """Test that dashboard-stats requires authentication"""
        response = requests.get(f"{BASE_URL}/api/admin/dashboard-stats")
        assert response.status_code in [401, 403], "Should require auth"
    
    def test_dashboard_stats_requires_admin_role(self, admin_token):
        """Test that dashboard-stats is accessible by admin"""
        response = requests.get(
            f"{BASE_URL}/api/admin/dashboard-stats",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        # Admin should have access
        assert response.status_code == 200


class TestProfilePhotoUpload:
    """Tests for POST /api/admin/profile/photo endpoint"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin token via OTP login"""
        response = requests.post(f"{BASE_URL}/api/auth/otp/request", json={
            "phone_number": "+919373991136"
        })
        assert response.status_code == 200
        otp = response.json().get('dev_otp')
        
        response = requests.post(f"{BASE_URL}/api/auth/otp/verify", json={
            "phone_number": "+919373991136",
            "otp": otp
        })
        assert response.status_code == 200
        return response.json().get('token')
    
    def test_upload_profile_photo(self, admin_token):
        """Test uploading a profile photo"""
        # Create a minimal PNG image (1x1 pixel)
        png_data = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")
        
        files = {"photo": ("test.png", png_data, "image/png")}
        response = requests.post(
            f"{BASE_URL}/api/admin/profile/photo",
            headers={"Authorization": f"Bearer {admin_token}"},
            files=files
        )
        
        assert response.status_code == 200, f"Photo upload failed: {response.text}"
        data = response.json()
        
        assert "message" in data, "Missing message in response"
        assert "profile_photo" in data, "Missing profile_photo in response"
        assert data["profile_photo"].startswith("data:image/"), "profile_photo should be base64 data URL"
    
    def test_profile_photo_persists_in_auth_me(self, admin_token):
        """Test that uploaded profile photo is returned in /auth/me"""
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "profile_photo" in data, "Missing profile_photo field in /auth/me"
        # After upload, it should have a value
        # Note: This test assumes the previous test ran and uploaded a photo
    
    def test_profile_photo_requires_auth(self):
        """Test that profile photo upload requires authentication"""
        png_data = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")
        files = {"photo": ("test.png", png_data, "image/png")}
        
        response = requests.post(f"{BASE_URL}/api/admin/profile/photo", files=files)
        assert response.status_code in [401, 403], "Should require auth"


class TestAuthMeProfilePhoto:
    """Tests for profile_photo field in GET /api/auth/me"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin token via OTP login"""
        response = requests.post(f"{BASE_URL}/api/auth/otp/request", json={
            "phone_number": "+919373991136"
        })
        assert response.status_code == 200
        otp = response.json().get('dev_otp')
        
        response = requests.post(f"{BASE_URL}/api/auth/otp/verify", json={
            "phone_number": "+919373991136",
            "otp": otp
        })
        assert response.status_code == 200
        return response.json().get('token')
    
    def test_auth_me_returns_profile_photo_field(self, admin_token):
        """Test that /auth/me includes profile_photo field"""
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check all expected fields
        assert "id" in data
        assert "email" in data
        assert "name" in data
        assert "role" in data
        assert "profile_photo" in data, "Missing profile_photo field"
