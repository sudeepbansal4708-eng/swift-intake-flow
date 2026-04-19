"""
Test Shift Management Features for ParKaro Valet Platform
- Admin toggle valet online/offline
- Valet request online
- Admin view online requests
- Offline valets blocked from parking/retrieving (403)
- Online valets can park/retrieve
- Admins not blocked by online check
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
SUPER_ADMIN_EMAIL = os.environ.get("TEST_ADMIN_EMAIL", os.environ.get("TEST_ADMIN_EMAIL", "superadmin@swiftvalet.com"))
SUPER_ADMIN_PASSWORD = os.environ.get("TEST_ADMIN_PASSWORD", os.environ.get("TEST_ADMIN_PASSWORD", "superadmin123"))
ADMIN_PHONE = "+919373991136"
VALET_PHONE = "+919922668866"  # Jennifer Smith - has client_id


class TestShiftManagementBackend:
    """Test shift management API endpoints"""
    
    @pytest.fixture(scope="class")
    def super_admin_token(self):
        """Get super admin token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPER_ADMIN_EMAIL,
            "password": SUPER_ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Super admin login failed: {response.text}"
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin token via OTP"""
        # Request OTP
        otp_req = requests.post(f"{BASE_URL}/api/auth/otp/request", json={
            "phone_number": ADMIN_PHONE
        })
        assert otp_req.status_code == 200, f"OTP request failed: {otp_req.text}"
        otp = otp_req.json().get("dev_otp")
        assert otp, "No dev_otp in response"
        
        # Verify OTP
        verify_res = requests.post(f"{BASE_URL}/api/auth/otp/verify", json={
            "phone_number": ADMIN_PHONE,
            "otp": otp
        })
        assert verify_res.status_code == 200, f"OTP verify failed: {verify_res.text}"
        data = verify_res.json()
        assert data["user"]["role"] == "admin", "Expected admin role"
        return data["token"]
    
    @pytest.fixture(scope="class")
    def valet_token_and_id(self):
        """Get valet token via OTP and return (token, valet_id)"""
        # Request OTP
        otp_req = requests.post(f"{BASE_URL}/api/auth/otp/request", json={
            "phone_number": VALET_PHONE
        })
        assert otp_req.status_code == 200, f"OTP request failed: {otp_req.text}"
        otp = otp_req.json().get("dev_otp")
        assert otp, "No dev_otp in response"
        
        # Verify OTP
        verify_res = requests.post(f"{BASE_URL}/api/auth/otp/verify", json={
            "phone_number": VALET_PHONE,
            "otp": otp
        })
        assert verify_res.status_code == 200, f"OTP verify failed: {verify_res.text}"
        data = verify_res.json()
        assert data["user"]["role"] == "valet", "Expected valet role"
        return (data["token"], data["user"]["id"])
    
    # ============ Test GET /api/auth/me returns is_online ============
    def test_auth_me_returns_is_online(self, valet_token_and_id):
        """GET /api/auth/me should return is_online field"""
        token, _ = valet_token_and_id
        response = requests.get(f"{BASE_URL}/api/auth/me", headers={
            "Authorization": f"Bearer {token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert "is_online" in data, "is_online field missing from /api/auth/me response"
        print(f"✓ GET /api/auth/me returns is_online: {data['is_online']}")
    
    # ============ Test OTP verify returns is_online ============
    def test_otp_verify_returns_is_online(self):
        """OTP verify should return is_online in user object"""
        # Request OTP
        otp_req = requests.post(f"{BASE_URL}/api/auth/otp/request", json={
            "phone_number": VALET_PHONE
        })
        assert otp_req.status_code == 200
        otp = otp_req.json().get("dev_otp")
        
        # Verify OTP
        verify_res = requests.post(f"{BASE_URL}/api/auth/otp/verify", json={
            "phone_number": VALET_PHONE,
            "otp": otp
        })
        assert verify_res.status_code == 200
        data = verify_res.json()
        assert "is_online" in data["user"], "is_online field missing from OTP verify response"
        print(f"✓ OTP verify returns is_online: {data['user']['is_online']}")
    
    # ============ Test PUT /api/admin/valets/{valet_id}/toggle-online ============
    def test_toggle_online_requires_admin(self, valet_token_and_id):
        """PUT /api/admin/valets/{valet_id}/toggle-online requires admin role"""
        token, valet_id = valet_token_and_id
        response = requests.put(f"{BASE_URL}/api/admin/valets/{valet_id}/toggle-online", headers={
            "Authorization": f"Bearer {token}"
        })
        assert response.status_code == 403, f"Expected 403 for valet, got {response.status_code}"
        print("✓ Toggle online requires admin role (403 for valet)")
    
    def test_toggle_online_admin_can_toggle(self, admin_token, valet_token_and_id):
        """Admin can toggle valet online/offline"""
        _, valet_id = valet_token_and_id
        
        # First toggle
        response = requests.put(f"{BASE_URL}/api/admin/valets/{valet_id}/toggle-online", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200, f"Toggle failed: {response.text}"
        data = response.json()
        assert "is_online" in data, "is_online missing from response"
        first_status = data["is_online"]
        print(f"✓ Admin toggled valet to is_online={first_status}")
        
        # Toggle again to verify it flips
        response2 = requests.put(f"{BASE_URL}/api/admin/valets/{valet_id}/toggle-online", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response2.status_code == 200
        data2 = response2.json()
        assert data2["is_online"] != first_status, "Toggle should flip the status"
        print(f"✓ Admin toggled valet again to is_online={data2['is_online']}")
    
    def test_toggle_online_returns_404_for_invalid_valet(self, admin_token):
        """Toggle returns 404 for non-existent valet"""
        fake_id = str(uuid.uuid4())
        response = requests.put(f"{BASE_URL}/api/admin/valets/{fake_id}/toggle-online", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Toggle returns 404 for non-existent valet")
    
    # ============ Test POST /api/valet/request-online ============
    def test_request_online_requires_valet(self, admin_token):
        """POST /api/valet/request-online requires valet role"""
        response = requests.post(f"{BASE_URL}/api/valet/request-online", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 403, f"Expected 403 for admin, got {response.status_code}"
        print("✓ Request online requires valet role (403 for admin)")
    
    def test_valet_can_request_online(self, admin_token, valet_token_and_id):
        """Valet can request to go online"""
        token, valet_id = valet_token_and_id
        
        # First ensure valet is offline
        requests.put(f"{BASE_URL}/api/admin/valets/{valet_id}/toggle-online", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        # Check current status
        me_res = requests.get(f"{BASE_URL}/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        if me_res.json().get("is_online"):
            # Toggle again to make offline
            requests.put(f"{BASE_URL}/api/admin/valets/{valet_id}/toggle-online", headers={
                "Authorization": f"Bearer {admin_token}"
            })
        
        # Now request online
        response = requests.post(f"{BASE_URL}/api/valet/request-online", headers={
            "Authorization": f"Bearer {token}"
        })
        assert response.status_code == 200, f"Request online failed: {response.text}"
        data = response.json()
        assert "message" in data
        print(f"✓ Valet request online: {data['message']}")
    
    # ============ Test GET /api/admin/online-requests ============
    def test_online_requests_requires_admin(self, valet_token_and_id):
        """GET /api/admin/online-requests requires admin role"""
        token, _ = valet_token_and_id
        response = requests.get(f"{BASE_URL}/api/admin/online-requests", headers={
            "Authorization": f"Bearer {token}"
        })
        assert response.status_code == 403, f"Expected 403 for valet, got {response.status_code}"
        print("✓ Online requests requires admin role (403 for valet)")
    
    def test_admin_can_view_online_requests(self, admin_token):
        """Admin can view pending online requests"""
        response = requests.get(f"{BASE_URL}/api/admin/online-requests", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200, f"Failed to get online requests: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Expected list of requests"
        print(f"✓ Admin can view online requests: {len(data)} pending")
    
    # ============ Test offline valet blocked from parking ============
    def test_offline_valet_blocked_from_parking(self, admin_token, valet_token_and_id):
        """POST /api/vehicles returns 403 for offline valet"""
        token, valet_id = valet_token_and_id
        
        # Ensure valet is offline
        me_res = requests.get(f"{BASE_URL}/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        if me_res.json().get("is_online"):
            requests.put(f"{BASE_URL}/api/admin/valets/{valet_id}/toggle-online", headers={
                "Authorization": f"Bearer {admin_token}"
            })
        
        # Try to park a vehicle
        response = requests.post(f"{BASE_URL}/api/vehicles", json={
            "phone_number": "+919999999999",
            "license_plate": "TEST-OFFLINE-001",
            "zone_label": "Test Zone"
        }, headers={
            "Authorization": f"Bearer {token}"
        })
        assert response.status_code == 403, f"Expected 403 for offline valet, got {response.status_code}: {response.text}"
        assert "online" in response.json().get("detail", "").lower(), "Error should mention online status"
        print("✓ Offline valet blocked from parking (403)")
    
    # ============ Test offline valet blocked from retrieving ============
    def test_offline_valet_blocked_from_retrieving(self, admin_token, valet_token_and_id):
        """POST /api/tickets/retrieve returns 403 for offline valet"""
        token, valet_id = valet_token_and_id
        
        # Ensure valet is offline
        me_res = requests.get(f"{BASE_URL}/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        if me_res.json().get("is_online"):
            requests.put(f"{BASE_URL}/api/admin/valets/{valet_id}/toggle-online", headers={
                "Authorization": f"Bearer {admin_token}"
            })
        
        # Try to retrieve a vehicle
        response = requests.post(f"{BASE_URL}/api/tickets/retrieve", json={
            "phone_number": "+919999999999"
        }, headers={
            "Authorization": f"Bearer {token}"
        })
        # Should be 403 (offline) or 404 (no vehicle) - we expect 403 first
        assert response.status_code == 403, f"Expected 403 for offline valet, got {response.status_code}: {response.text}"
        assert "online" in response.json().get("detail", "").lower(), "Error should mention online status"
        print("✓ Offline valet blocked from retrieving (403)")
    
    # ============ Test online valet can park ============
    def test_online_valet_can_park(self, admin_token, valet_token_and_id):
        """POST /api/vehicles works for online valet"""
        token, valet_id = valet_token_and_id
        
        # Ensure valet is online
        me_res = requests.get(f"{BASE_URL}/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        if not me_res.json().get("is_online"):
            requests.put(f"{BASE_URL}/api/admin/valets/{valet_id}/toggle-online", headers={
                "Authorization": f"Bearer {admin_token}"
            })
        
        # Park a vehicle
        unique_phone = f"+91999{uuid.uuid4().hex[:7]}"
        response = requests.post(f"{BASE_URL}/api/vehicles", json={
            "phone_number": unique_phone,
            "license_plate": f"TEST-ONLINE-{uuid.uuid4().hex[:4].upper()}",
            "zone_label": "Test Zone Online"
        }, headers={
            "Authorization": f"Bearer {token}"
        })
        assert response.status_code == 200, f"Online valet should be able to park: {response.text}"
        data = response.json()
        assert "vehicle" in data, "Response should contain vehicle"
        print(f"✓ Online valet can park vehicle: {data['vehicle']['license_plate']}")
    
    # ============ Test admin not blocked by online check ============
    def test_admin_can_park_regardless_of_online_status(self, admin_token):
        """Admin can park vehicles regardless of online status"""
        unique_phone = f"+91888{uuid.uuid4().hex[:7]}"
        response = requests.post(f"{BASE_URL}/api/vehicles", json={
            "phone_number": unique_phone,
            "license_plate": f"ADMIN-PARK-{uuid.uuid4().hex[:4].upper()}",
            "zone_label": "Admin Test Zone"
        }, headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200, f"Admin should be able to park: {response.text}"
        data = response.json()
        assert "vehicle" in data
        print(f"✓ Admin can park vehicle regardless of online status: {data['vehicle']['license_plate']}")
    
    # ============ Test approving request clears it ============
    def test_approving_online_clears_request(self, admin_token, valet_token_and_id):
        """When admin toggles valet online, pending request is cleared"""
        token, valet_id = valet_token_and_id
        
        # Ensure valet is offline first
        me_res = requests.get(f"{BASE_URL}/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        if me_res.json().get("is_online"):
            requests.put(f"{BASE_URL}/api/admin/valets/{valet_id}/toggle-online", headers={
                "Authorization": f"Bearer {admin_token}"
            })
        
        # Valet requests online
        requests.post(f"{BASE_URL}/api/valet/request-online", headers={
            "Authorization": f"Bearer {token}"
        })
        
        # Check request exists
        req_res = requests.get(f"{BASE_URL}/api/admin/online-requests", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        requests_before = [r for r in req_res.json() if r.get("valet_id") == valet_id]
        
        # Admin approves (toggles online)
        toggle_res = requests.put(f"{BASE_URL}/api/admin/valets/{valet_id}/toggle-online", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert toggle_res.status_code == 200
        assert toggle_res.json().get("is_online") == True, "Valet should be online after toggle"
        
        # Check request is cleared
        req_res2 = requests.get(f"{BASE_URL}/api/admin/online-requests", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        requests_after = [r for r in req_res2.json() if r.get("valet_id") == valet_id]
        assert len(requests_after) == 0, "Request should be cleared after approval"
        print("✓ Approving online clears pending request")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
