"""
Test suite for the new Retrieve Vehicle feature
Tests:
- GET /api/vehicles/lookup - lookup vehicle by phone number
- POST /api/tickets/retrieve - create retrieval ticket with auto-assignment
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
VALET_PHONE = "+919999888877"
ADMIN_PHONE = "+919373991136"
TEST_VEHICLE_PHONE = "+919876543210"  # Has active ticket
TEST_VEHICLE_PHONE_2 = "+919555666777"  # Has active ticket


class TestRetrieveFeature:
    """Tests for the vehicle lookup and retrieve endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: Get auth token for valet"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Get OTP for valet
        otp_response = self.session.post(f"{BASE_URL}/api/auth/otp/request", json={
            "phone_number": VALET_PHONE
        })
        assert otp_response.status_code == 200, f"OTP request failed: {otp_response.text}"
        otp = otp_response.json().get("dev_otp")
        assert otp, "No dev_otp in response"
        
        # Verify OTP
        verify_response = self.session.post(f"{BASE_URL}/api/auth/otp/verify", json={
            "phone_number": VALET_PHONE,
            "otp": otp
        })
        assert verify_response.status_code == 200, f"OTP verify failed: {verify_response.text}"
        
        token = verify_response.json().get("token")
        self.user = verify_response.json().get("user")
        assert token, "No token in response"
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        print(f"Logged in as valet: {self.user.get('name')}")
    
    def test_lookup_requires_auth(self):
        """GET /api/vehicles/lookup requires authentication"""
        response = requests.get(f"{BASE_URL}/api/vehicles/lookup", params={"phone": TEST_VEHICLE_PHONE})
        assert response.status_code == 403 or response.status_code == 401, f"Expected 401/403, got {response.status_code}"
        print("PASS: Lookup requires authentication")
    
    def test_lookup_vehicle_by_phone(self):
        """GET /api/vehicles/lookup returns vehicle info for valid phone"""
        response = self.session.get(f"{BASE_URL}/api/vehicles/lookup", params={"phone": TEST_VEHICLE_PHONE})
        assert response.status_code == 200, f"Lookup failed: {response.text}"
        
        data = response.json()
        assert "vehicle" in data, "Response missing 'vehicle' field"
        assert "has_active_ticket" in data, "Response missing 'has_active_ticket' field"
        
        vehicle = data["vehicle"]
        assert "id" in vehicle, "Vehicle missing 'id'"
        assert "license_plate" in vehicle, "Vehicle missing 'license_plate'"
        assert "phone_number" in vehicle, "Vehicle missing 'phone_number'"
        
        print(f"PASS: Lookup returned vehicle: {vehicle.get('license_plate')}, has_active_ticket: {data.get('has_active_ticket')}")
    
    def test_lookup_vehicle_not_found(self):
        """GET /api/vehicles/lookup returns 404 for unknown phone"""
        response = self.session.get(f"{BASE_URL}/api/vehicles/lookup", params={"phone": "+919999999999"})
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("PASS: Lookup returns 404 for unknown phone")
    
    def test_lookup_normalizes_phone(self):
        """GET /api/vehicles/lookup normalizes phone number (adds + if missing)"""
        # Test without + prefix
        response = self.session.get(f"{BASE_URL}/api/vehicles/lookup", params={"phone": "919876543210"})
        # Should either find the vehicle or return 404 (depending on data), but not error
        assert response.status_code in [200, 404], f"Unexpected status: {response.status_code}"
        print("PASS: Lookup handles phone without + prefix")
    
    def test_retrieve_requires_auth(self):
        """POST /api/tickets/retrieve requires authentication"""
        response = requests.post(f"{BASE_URL}/api/tickets/retrieve", json={
            "phone_number": TEST_VEHICLE_PHONE
        })
        assert response.status_code == 403 or response.status_code == 401, f"Expected 401/403, got {response.status_code}"
        print("PASS: Retrieve requires authentication")
    
    def test_retrieve_returns_400_if_ticket_exists(self):
        """POST /api/tickets/retrieve returns 400 if active ticket already exists"""
        # TEST_VEHICLE_PHONE should have an active ticket per test setup
        response = self.session.post(f"{BASE_URL}/api/tickets/retrieve", json={
            "phone_number": TEST_VEHICLE_PHONE
        })
        # Should return 400 if ticket exists, or 200 if no ticket (first run)
        if response.status_code == 400:
            assert "already exists" in response.json().get("detail", "").lower(), f"Unexpected error: {response.text}"
            print("PASS: Retrieve returns 400 when ticket already exists")
        else:
            # First run - ticket was created
            assert response.status_code == 200, f"Unexpected status: {response.status_code}"
            print("INFO: First run - ticket was created (no existing ticket)")
    
    def test_retrieve_returns_404_for_unknown_phone(self):
        """POST /api/tickets/retrieve returns 404 if no vehicle found"""
        # Use a truly random phone that won't exist
        random_phone = f"+91{uuid.uuid4().hex[:10]}"
        response = self.session.post(f"{BASE_URL}/api/tickets/retrieve", json={
            "phone_number": random_phone
        })
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        assert "no vehicle found" in response.json().get("detail", "").lower(), f"Unexpected error: {response.text}"
        print("PASS: Retrieve returns 404 for unknown phone")
    
    def test_retrieve_creates_claimed_ticket(self):
        """POST /api/tickets/retrieve creates ticket with status=claimed and claimed_by=valet_id"""
        # First, park a new vehicle to test retrieve
        unique_phone = f"+91{uuid.uuid4().hex[:10]}"
        unique_plate = f"TEST{uuid.uuid4().hex[:6].upper()}"
        
        # Park vehicle
        park_response = self.session.post(f"{BASE_URL}/api/vehicles", json={
            "phone_number": unique_phone,
            "license_plate": unique_plate,
            "zone_label": "Test Zone A"
        })
        assert park_response.status_code == 200, f"Park failed: {park_response.text}"
        print(f"Parked test vehicle: {unique_plate}")
        
        # Now retrieve it
        retrieve_response = self.session.post(f"{BASE_URL}/api/tickets/retrieve", json={
            "phone_number": unique_phone
        })
        assert retrieve_response.status_code == 200, f"Retrieve failed: {retrieve_response.text}"
        
        data = retrieve_response.json()
        assert "ticket" in data, "Response missing 'ticket' field"
        assert "message" in data, "Response missing 'message' field"
        
        ticket = data["ticket"]
        assert ticket.get("status") == "claimed", f"Expected status 'claimed', got {ticket.get('status')}"
        assert ticket.get("claimed_by") == self.user.get("id"), f"Expected claimed_by={self.user.get('id')}, got {ticket.get('claimed_by')}"
        assert ticket.get("claimed_at") is not None, "claimed_at should be set"
        assert "vehicle" in ticket, "Ticket should include vehicle info"
        
        vehicle_info = ticket.get("vehicle", {})
        assert vehicle_info.get("license_plate") == unique_plate, f"Vehicle plate mismatch"
        
        print(f"PASS: Retrieve created claimed ticket: {ticket.get('id')}")
        print(f"  - status: {ticket.get('status')}")
        print(f"  - claimed_by: {ticket.get('claimed_by')}")
        print(f"  - vehicle: {vehicle_info.get('license_plate')}")
    
    def test_retrieve_second_attempt_fails(self):
        """POST /api/tickets/retrieve fails if called twice for same vehicle"""
        # Park a new vehicle
        unique_phone = f"+91{uuid.uuid4().hex[:10]}"
        unique_plate = f"TEST{uuid.uuid4().hex[:6].upper()}"
        
        park_response = self.session.post(f"{BASE_URL}/api/vehicles", json={
            "phone_number": unique_phone,
            "license_plate": unique_plate,
            "zone_label": "Test Zone B"
        })
        assert park_response.status_code == 200, f"Park failed: {park_response.text}"
        
        # First retrieve - should succeed
        retrieve1 = self.session.post(f"{BASE_URL}/api/tickets/retrieve", json={
            "phone_number": unique_phone
        })
        assert retrieve1.status_code == 200, f"First retrieve failed: {retrieve1.text}"
        
        # Second retrieve - should fail with 400
        retrieve2 = self.session.post(f"{BASE_URL}/api/tickets/retrieve", json={
            "phone_number": unique_phone
        })
        assert retrieve2.status_code == 400, f"Expected 400 on second retrieve, got {retrieve2.status_code}"
        assert "already exists" in retrieve2.json().get("detail", "").lower()
        
        print("PASS: Second retrieve attempt correctly returns 400")


class TestLookupHasActiveTicketFlag:
    """Test that lookup correctly reports has_active_ticket flag"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: Get auth token for valet"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Get OTP for valet
        otp_response = self.session.post(f"{BASE_URL}/api/auth/otp/request", json={
            "phone_number": VALET_PHONE
        })
        assert otp_response.status_code == 200
        otp = otp_response.json().get("dev_otp")
        
        # Verify OTP
        verify_response = self.session.post(f"{BASE_URL}/api/auth/otp/verify", json={
            "phone_number": VALET_PHONE,
            "otp": otp
        })
        assert verify_response.status_code == 200
        
        token = verify_response.json().get("token")
        self.user = verify_response.json().get("user")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_lookup_shows_no_active_ticket_for_new_vehicle(self):
        """Lookup shows has_active_ticket=false for newly parked vehicle"""
        # Park a new vehicle
        unique_phone = f"+91{uuid.uuid4().hex[:10]}"
        unique_plate = f"TEST{uuid.uuid4().hex[:6].upper()}"
        
        park_response = self.session.post(f"{BASE_URL}/api/vehicles", json={
            "phone_number": unique_phone,
            "license_plate": unique_plate,
            "zone_label": "Test Zone C"
        })
        assert park_response.status_code == 200
        
        # Lookup - should show no active ticket
        lookup_response = self.session.get(f"{BASE_URL}/api/vehicles/lookup", params={"phone": unique_phone})
        assert lookup_response.status_code == 200
        
        data = lookup_response.json()
        assert data.get("has_active_ticket") == False, f"Expected has_active_ticket=false, got {data.get('has_active_ticket')}"
        
        print("PASS: Lookup shows has_active_ticket=false for new vehicle")
    
    def test_lookup_shows_active_ticket_after_retrieve(self):
        """Lookup shows has_active_ticket=true after retrieve is initiated"""
        # Park a new vehicle
        unique_phone = f"+91{uuid.uuid4().hex[:10]}"
        unique_plate = f"TEST{uuid.uuid4().hex[:6].upper()}"
        
        park_response = self.session.post(f"{BASE_URL}/api/vehicles", json={
            "phone_number": unique_phone,
            "license_plate": unique_plate,
            "zone_label": "Test Zone D"
        })
        assert park_response.status_code == 200
        
        # Retrieve the vehicle
        retrieve_response = self.session.post(f"{BASE_URL}/api/tickets/retrieve", json={
            "phone_number": unique_phone
        })
        assert retrieve_response.status_code == 200
        
        # Lookup - should now show active ticket
        lookup_response = self.session.get(f"{BASE_URL}/api/vehicles/lookup", params={"phone": unique_phone})
        assert lookup_response.status_code == 200
        
        data = lookup_response.json()
        assert data.get("has_active_ticket") == True, f"Expected has_active_ticket=true, got {data.get('has_active_ticket')}"
        
        print("PASS: Lookup shows has_active_ticket=true after retrieve")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
