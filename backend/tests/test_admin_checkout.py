"""
Test suite for Admin Manual Vehicle Checkout Feature
Tests POST /api/admin/vehicles/{vehicle_id}/checkout endpoint
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_PHONE = "+919373991136"
VALET_PHONE = "+919999888877"
SUPER_ADMIN_EMAIL = os.environ.get("TEST_ADMIN_EMAIL", "superadmin@swiftvalet.com")
SUPER_ADMIN_PASSWORD = os.environ.get("TEST_ADMIN_PASSWORD", "superadmin123")


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def admin_token(api_client):
    """Get admin authentication token via OTP"""
    # Request OTP
    response = api_client.post(f"{BASE_URL}/api/auth/otp/request", json={"phone_number": ADMIN_PHONE})
    if response.status_code != 200:
        pytest.skip(f"Failed to request OTP for admin: {response.text}")
    
    otp = response.json().get("dev_otp")
    if not otp:
        pytest.skip("No dev_otp returned for admin")
    
    # Verify OTP
    verify_response = api_client.post(f"{BASE_URL}/api/auth/otp/verify", json={
        "phone_number": ADMIN_PHONE,
        "otp": otp
    })
    if verify_response.status_code != 200:
        pytest.skip(f"Failed to verify OTP for admin: {verify_response.text}")
    
    return verify_response.json().get("token")


@pytest.fixture(scope="module")
def valet_token(api_client):
    """Get valet authentication token via OTP"""
    # Request OTP
    response = api_client.post(f"{BASE_URL}/api/auth/otp/request", json={"phone_number": VALET_PHONE})
    if response.status_code != 200:
        pytest.skip(f"Failed to request OTP for valet: {response.text}")
    
    otp = response.json().get("dev_otp")
    if not otp:
        pytest.skip("No dev_otp returned for valet")
    
    # Verify OTP
    verify_response = api_client.post(f"{BASE_URL}/api/auth/otp/verify", json={
        "phone_number": VALET_PHONE,
        "otp": otp
    })
    if verify_response.status_code != 200:
        pytest.skip(f"Failed to verify OTP for valet: {verify_response.text}")
    
    return verify_response.json().get("token")


@pytest.fixture(scope="module")
def super_admin_token(api_client):
    """Get super admin authentication token via email/password"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": SUPER_ADMIN_EMAIL,
        "password": SUPER_ADMIN_PASSWORD
    })
    if response.status_code != 200:
        pytest.skip(f"Failed to login as super admin: {response.text}")
    
    return response.json().get("token")


class TestAdminCheckoutAuthorization:
    """Test authorization for admin checkout endpoint"""
    
    def test_checkout_requires_authentication(self, api_client):
        """Checkout endpoint should require authentication"""
        response = api_client.post(f"{BASE_URL}/api/admin/vehicles/fake-id/checkout")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("PASS: Checkout requires authentication")
    
    def test_checkout_forbidden_for_valet(self, api_client, valet_token):
        """Valet role should not be able to checkout vehicles"""
        headers = {"Authorization": f"Bearer {valet_token}"}
        response = api_client.post(f"{BASE_URL}/api/admin/vehicles/fake-id/checkout", headers=headers)
        assert response.status_code == 403, f"Expected 403 for valet, got {response.status_code}"
        assert "Admin access required" in response.json().get("detail", "")
        print("PASS: Valet cannot checkout vehicles (403)")
    
    def test_checkout_allowed_for_admin(self, api_client, admin_token):
        """Admin role should be allowed to access checkout endpoint (404 for non-existent vehicle)"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = api_client.post(f"{BASE_URL}/api/admin/vehicles/non-existent-id/checkout", headers=headers)
        # Should get 404 (not found) not 403 (forbidden)
        assert response.status_code == 404, f"Expected 404 for non-existent vehicle, got {response.status_code}"
        print("PASS: Admin can access checkout endpoint (404 for non-existent)")
    
    def test_checkout_allowed_for_super_admin(self, api_client, super_admin_token):
        """Super admin role should be allowed to access checkout endpoint"""
        headers = {"Authorization": f"Bearer {super_admin_token}"}
        response = api_client.post(f"{BASE_URL}/api/admin/vehicles/non-existent-id/checkout", headers=headers)
        # Should get 404 (not found) not 403 (forbidden)
        assert response.status_code == 404, f"Expected 404 for non-existent vehicle, got {response.status_code}"
        print("PASS: Super admin can access checkout endpoint (404 for non-existent)")


class TestAdminCheckoutFunctionality:
    """Test checkout functionality"""
    
    def test_checkout_returns_404_for_nonexistent_vehicle(self, api_client, admin_token):
        """Checkout should return 404 for non-existent vehicle"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        fake_id = str(uuid.uuid4())
        response = api_client.post(f"{BASE_URL}/api/admin/vehicles/{fake_id}/checkout", headers=headers)
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        assert "Vehicle not found" in response.json().get("detail", "")
        print("PASS: Returns 404 for non-existent vehicle")
    
    def test_checkout_parked_vehicle_success(self, api_client, admin_token):
        """Successfully checkout a parked vehicle"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # First, park a vehicle
        unique_phone = f"+91{uuid.uuid4().hex[:10]}"
        park_response = api_client.post(f"{BASE_URL}/api/vehicles", headers=headers, json={
            "phone_number": unique_phone,
            "license_plate": f"TEST-{uuid.uuid4().hex[:6].upper()}",
            "tag_number": "CHECKOUT-TEST",
            "zone_label": "Zone A"
        })
        assert park_response.status_code == 200, f"Failed to park vehicle: {park_response.text}"
        vehicle_id = park_response.json()["vehicle"]["id"]
        print(f"Parked test vehicle: {vehicle_id}")
        
        # Now checkout the vehicle
        checkout_response = api_client.post(f"{BASE_URL}/api/admin/vehicles/{vehicle_id}/checkout", headers=headers)
        assert checkout_response.status_code == 200, f"Checkout failed: {checkout_response.text}"
        
        data = checkout_response.json()
        assert data.get("message") == "Vehicle checked out successfully"
        assert data.get("vehicle_id") == vehicle_id
        print("PASS: Vehicle checked out successfully")
    
    def test_checkout_creates_completed_ticket(self, api_client, admin_token):
        """Checkout should create a completed ticket for record-keeping"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Park a vehicle
        unique_phone = f"+91{uuid.uuid4().hex[:10]}"
        park_response = api_client.post(f"{BASE_URL}/api/vehicles", headers=headers, json={
            "phone_number": unique_phone,
            "license_plate": f"TEST-{uuid.uuid4().hex[:6].upper()}",
            "tag_number": "TICKET-TEST",
            "zone_label": "Zone B"
        })
        assert park_response.status_code == 200
        vehicle_id = park_response.json()["vehicle"]["id"]
        
        # Checkout the vehicle
        checkout_response = api_client.post(f"{BASE_URL}/api/admin/vehicles/{vehicle_id}/checkout", headers=headers)
        assert checkout_response.status_code == 200
        
        # Verify a completed ticket was created
        tickets_response = api_client.get(f"{BASE_URL}/api/tickets", headers=headers)
        assert tickets_response.status_code == 200
        
        tickets = tickets_response.json()
        vehicle_tickets = [t for t in tickets if t.get("vehicle_id") == vehicle_id]
        assert len(vehicle_tickets) >= 1, "No ticket found for checked out vehicle"
        
        completed_ticket = next((t for t in vehicle_tickets if t.get("status") == "completed"), None)
        assert completed_ticket is not None, "No completed ticket found"
        assert completed_ticket.get("completed_at") is not None, "completed_at should be set"
        print("PASS: Completed ticket created for checkout")
    
    def test_checkout_handles_existing_active_ticket(self, api_client, admin_token):
        """Checkout should complete an existing active ticket"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Park a vehicle
        unique_phone = f"+91{uuid.uuid4().hex[:10]}"
        park_response = api_client.post(f"{BASE_URL}/api/vehicles", headers=headers, json={
            "phone_number": unique_phone,
            "license_plate": f"TEST-{uuid.uuid4().hex[:6].upper()}",
            "tag_number": "ACTIVE-TICKET-TEST",
            "zone_label": "Zone C"
        })
        assert park_response.status_code == 200
        vehicle_id = park_response.json()["vehicle"]["id"]
        
        # Create a retrieval ticket (active ticket)
        retrieve_response = api_client.post(f"{BASE_URL}/api/tickets/retrieve", headers=headers, json={
            "phone_number": unique_phone
        })
        assert retrieve_response.status_code == 200, f"Failed to create retrieval ticket: {retrieve_response.text}"
        ticket_id = retrieve_response.json()["ticket"]["id"]
        print(f"Created active ticket: {ticket_id}")
        
        # Now checkout the vehicle (should complete the existing ticket)
        checkout_response = api_client.post(f"{BASE_URL}/api/admin/vehicles/{vehicle_id}/checkout", headers=headers)
        assert checkout_response.status_code == 200, f"Checkout failed: {checkout_response.text}"
        
        # Verify the ticket was completed
        tickets_response = api_client.get(f"{BASE_URL}/api/tickets", headers=headers)
        tickets = tickets_response.json()
        
        the_ticket = next((t for t in tickets if t.get("id") == ticket_id), None)
        assert the_ticket is not None, "Ticket not found"
        assert the_ticket.get("status") == "completed", f"Ticket status should be completed, got {the_ticket.get('status')}"
        print("PASS: Existing active ticket was completed on checkout")


class TestAdminDashboardStats:
    """Test that dashboard stats work correctly"""
    
    def test_admin_dashboard_stats_endpoint(self, api_client, admin_token):
        """Admin dashboard stats should return correct structure"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = api_client.get(f"{BASE_URL}/api/admin/dashboard-stats", headers=headers)
        assert response.status_code == 200, f"Dashboard stats failed: {response.text}"
        
        data = response.json()
        assert "active_valets" in data
        assert "parked_vehicles" in data
        assert "tips" in data
        assert "totals" in data
        assert "valets" in data["totals"]
        assert "vehicles" in data["totals"]
        assert "tips_amount" in data["totals"]
        print("PASS: Admin dashboard stats structure is correct")
    
    def test_valet_dashboard_stats_endpoint(self, api_client, valet_token):
        """Valet dashboard stats should return correct structure"""
        headers = {"Authorization": f"Bearer {valet_token}"}
        response = api_client.get(f"{BASE_URL}/api/valet/dashboard-stats", headers=headers)
        assert response.status_code == 200, f"Valet stats failed: {response.text}"
        
        data = response.json()
        assert "cars_parked_today" in data
        assert "cars_retrieved_today" in data
        assert "tips_today" in data
        print("PASS: Valet dashboard stats structure is correct")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
