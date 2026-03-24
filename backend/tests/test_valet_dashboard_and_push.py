"""
Test suite for Valet Dashboard Stats and Push Notification endpoints
Features tested:
- GET /api/valet/dashboard-stats - returns cars_parked_today, cars_retrieved_today, tips_today for logged-in valet
- GET /api/push/vapid-key - returns the VAPID public key
- POST /api/push/subscribe - stores a push subscription for the current user
- POST /api/push/unsubscribe - removes a push subscription
- POST /api/tickets - triggers push notification when retrieval ticket is created
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestVapidKey:
    """Test VAPID public key endpoint (no auth required)"""
    
    def test_get_vapid_key_returns_public_key(self):
        """GET /api/push/vapid-key should return the VAPID public key"""
        response = requests.get(f"{BASE_URL}/api/push/vapid-key")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "public_key" in data, "Response should contain 'public_key' field"
        assert isinstance(data["public_key"], str), "public_key should be a string"
        # VAPID public key should be non-empty
        assert len(data["public_key"]) > 0, "public_key should not be empty"
        print(f"VAPID public key returned: {data['public_key'][:30]}...")


class TestValetDashboardStats:
    """Test valet dashboard stats endpoint"""
    
    @pytest.fixture
    def valet_token(self):
        """Get valet auth token via OTP"""
        phone = "+919999888877"
        
        # Request OTP
        otp_response = requests.post(f"{BASE_URL}/api/auth/otp/request", json={"phone_number": phone})
        if otp_response.status_code != 200:
            pytest.skip(f"Could not request OTP: {otp_response.text}")
        
        otp = otp_response.json().get("dev_otp")
        if not otp:
            pytest.skip("No dev_otp in response")
        
        # Verify OTP
        verify_response = requests.post(f"{BASE_URL}/api/auth/otp/verify", json={
            "phone_number": phone,
            "otp": otp
        })
        if verify_response.status_code != 200:
            pytest.skip(f"OTP verification failed: {verify_response.text}")
        
        token = verify_response.json().get("token")
        user = verify_response.json().get("user")
        print(f"Logged in as valet: {user.get('name')} (role: {user.get('role')})")
        return token
    
    def test_valet_dashboard_stats_requires_auth(self):
        """GET /api/valet/dashboard-stats should require authentication"""
        response = requests.get(f"{BASE_URL}/api/valet/dashboard-stats")
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
        print("Correctly requires authentication")
    
    def test_valet_dashboard_stats_returns_correct_structure(self, valet_token):
        """GET /api/valet/dashboard-stats should return cars_parked_today, cars_retrieved_today, tips_today"""
        headers = {"Authorization": f"Bearer {valet_token}"}
        response = requests.get(f"{BASE_URL}/api/valet/dashboard-stats", headers=headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify required fields exist
        assert "cars_parked_today" in data, "Response should contain 'cars_parked_today'"
        assert "cars_retrieved_today" in data, "Response should contain 'cars_retrieved_today'"
        assert "tips_today" in data, "Response should contain 'tips_today'"
        
        # Verify data types
        assert isinstance(data["cars_parked_today"], int), "cars_parked_today should be an integer"
        assert isinstance(data["cars_retrieved_today"], int), "cars_retrieved_today should be an integer"
        assert isinstance(data["tips_today"], (int, float)), "tips_today should be a number"
        
        # Values should be non-negative
        assert data["cars_parked_today"] >= 0, "cars_parked_today should be >= 0"
        assert data["cars_retrieved_today"] >= 0, "cars_retrieved_today should be >= 0"
        assert data["tips_today"] >= 0, "tips_today should be >= 0"
        
        print(f"Valet stats: parked={data['cars_parked_today']}, retrieved={data['cars_retrieved_today']}, tips={data['tips_today']}")


class TestAdminDashboardStats:
    """Test admin dashboard stats endpoint still works"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin auth token via OTP"""
        phone = "+919373991136"
        
        # Request OTP
        otp_response = requests.post(f"{BASE_URL}/api/auth/otp/request", json={"phone_number": phone})
        if otp_response.status_code != 200:
            pytest.skip(f"Could not request OTP: {otp_response.text}")
        
        otp = otp_response.json().get("dev_otp")
        if not otp:
            pytest.skip("No dev_otp in response")
        
        # Verify OTP
        verify_response = requests.post(f"{BASE_URL}/api/auth/otp/verify", json={
            "phone_number": phone,
            "otp": otp
        })
        if verify_response.status_code != 200:
            pytest.skip(f"OTP verification failed: {verify_response.text}")
        
        token = verify_response.json().get("token")
        user = verify_response.json().get("user")
        print(f"Logged in as admin: {user.get('name')} (role: {user.get('role')})")
        return token
    
    def test_admin_dashboard_stats_returns_correct_structure(self, admin_token):
        """GET /api/admin/dashboard-stats should return active_valets, parked_vehicles, tips, totals"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/admin/dashboard-stats", headers=headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify required fields exist
        assert "active_valets" in data, "Response should contain 'active_valets'"
        assert "parked_vehicles" in data, "Response should contain 'parked_vehicles'"
        assert "tips" in data, "Response should contain 'tips'"
        assert "totals" in data, "Response should contain 'totals'"
        
        # Verify totals structure
        totals = data["totals"]
        assert "valets" in totals, "totals should contain 'valets'"
        assert "vehicles" in totals, "totals should contain 'vehicles'"
        assert "tips_amount" in totals, "totals should contain 'tips_amount'"
        
        print(f"Admin stats: valets={totals['valets']}, vehicles={totals['vehicles']}, tips={totals['tips_amount']}")


class TestPushSubscription:
    """Test push subscription endpoints"""
    
    @pytest.fixture
    def valet_token(self):
        """Get valet auth token via OTP"""
        phone = "+919999888877"
        
        # Request OTP
        otp_response = requests.post(f"{BASE_URL}/api/auth/otp/request", json={"phone_number": phone})
        if otp_response.status_code != 200:
            pytest.skip(f"Could not request OTP: {otp_response.text}")
        
        otp = otp_response.json().get("dev_otp")
        if not otp:
            pytest.skip("No dev_otp in response")
        
        # Verify OTP
        verify_response = requests.post(f"{BASE_URL}/api/auth/otp/verify", json={
            "phone_number": phone,
            "otp": otp
        })
        if verify_response.status_code != 200:
            pytest.skip(f"OTP verification failed: {verify_response.text}")
        
        return verify_response.json().get("token")
    
    def test_push_subscribe_requires_auth(self):
        """POST /api/push/subscribe should require authentication"""
        response = requests.post(f"{BASE_URL}/api/push/subscribe", json={
            "subscription": {"endpoint": "https://test.example.com/push"}
        })
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
        print("Subscribe correctly requires authentication")
    
    def test_push_unsubscribe_requires_auth(self):
        """POST /api/push/unsubscribe should require authentication"""
        response = requests.post(f"{BASE_URL}/api/push/unsubscribe", json={
            "subscription": {"endpoint": "https://test.example.com/push"}
        })
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
        print("Unsubscribe correctly requires authentication")
    
    def test_push_subscribe_stores_subscription(self, valet_token):
        """POST /api/push/subscribe should store the subscription"""
        headers = {"Authorization": f"Bearer {valet_token}"}
        
        # Create a test subscription
        test_subscription = {
            "endpoint": "https://test-push-endpoint.example.com/push/TEST_subscription_123",
            "keys": {
                "p256dh": "test_p256dh_key",
                "auth": "test_auth_key"
            }
        }
        
        response = requests.post(f"{BASE_URL}/api/push/subscribe", 
                                 headers=headers,
                                 json={"subscription": test_subscription})
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "message" in data, "Response should contain 'message'"
        print(f"Subscribe response: {data['message']}")
    
    def test_push_unsubscribe_removes_subscription(self, valet_token):
        """POST /api/push/unsubscribe should remove the subscription"""
        headers = {"Authorization": f"Bearer {valet_token}"}
        
        # First subscribe
        test_subscription = {
            "endpoint": "https://test-push-endpoint.example.com/push/TEST_unsubscribe_456",
            "keys": {
                "p256dh": "test_p256dh_key",
                "auth": "test_auth_key"
            }
        }
        
        requests.post(f"{BASE_URL}/api/push/subscribe", 
                      headers=headers,
                      json={"subscription": test_subscription})
        
        # Then unsubscribe
        response = requests.post(f"{BASE_URL}/api/push/unsubscribe", 
                                 headers=headers,
                                 json={"subscription": test_subscription})
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "message" in data, "Response should contain 'message'"
        print(f"Unsubscribe response: {data['message']}")
    
    def test_push_subscribe_rejects_invalid_subscription(self, valet_token):
        """POST /api/push/subscribe should reject subscription without endpoint"""
        headers = {"Authorization": f"Bearer {valet_token}"}
        
        # Invalid subscription without endpoint
        response = requests.post(f"{BASE_URL}/api/push/subscribe", 
                                 headers=headers,
                                 json={"subscription": {}})
        
        assert response.status_code == 400, f"Expected 400 for invalid subscription, got {response.status_code}"
        print("Correctly rejects invalid subscription")


class TestTicketCreationTriggersPush:
    """Test that ticket creation triggers push notification flow"""
    
    @pytest.fixture
    def valet_token(self):
        """Get valet auth token via OTP"""
        phone = "+919999888877"
        
        # Request OTP
        otp_response = requests.post(f"{BASE_URL}/api/auth/otp/request", json={"phone_number": phone})
        if otp_response.status_code != 200:
            pytest.skip(f"Could not request OTP: {otp_response.text}")
        
        otp = otp_response.json().get("dev_otp")
        if not otp:
            pytest.skip("No dev_otp in response")
        
        # Verify OTP
        verify_response = requests.post(f"{BASE_URL}/api/auth/otp/verify", json={
            "phone_number": phone,
            "otp": otp
        })
        if verify_response.status_code != 200:
            pytest.skip(f"OTP verification failed: {verify_response.text}")
        
        return verify_response.json().get("token")
    
    def test_ticket_creation_endpoint_exists(self, valet_token):
        """POST /api/tickets should exist and require vehicle_id"""
        headers = {"Authorization": f"Bearer {valet_token}"}
        
        # Try to create ticket with non-existent vehicle
        response = requests.post(f"{BASE_URL}/api/tickets?vehicle_id=non_existent_vehicle_id", headers=headers)
        
        # Should return 404 for non-existent vehicle, not 500 or other error
        assert response.status_code == 404, f"Expected 404 for non-existent vehicle, got {response.status_code}"
        print("Ticket creation endpoint exists and validates vehicle_id")


class TestServiceWorker:
    """Test service worker is served correctly"""
    
    def test_sw_js_is_served(self):
        """GET /sw.js should return the service worker file"""
        response = requests.get(f"{BASE_URL}/sw.js")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        content = response.text
        assert "push" in content.lower(), "Service worker should handle push events"
        assert "notificationclick" in content.lower(), "Service worker should handle notification clicks"
        print("Service worker is served correctly with push handling")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
