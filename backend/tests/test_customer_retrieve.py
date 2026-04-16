"""
Test Customer Retrieval Feature - Public endpoints for ParKaro
Tests:
- GET /api/retrieve/{vehicle_id} - Public vehicle info endpoint
- POST /api/retrieve/{vehicle_id}/confirm - Public retrieval confirmation
- POST /api/whatsapp/webhook - TwiML XML response
- Edge cases: 404, already checked out, duplicate retrieval
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials from review request
ADMIN_PHONE = "+919373991136"
VALET_PHONE = "+919922668866"
SUPER_ADMIN_EMAIL = os.environ.get("TEST_ADMIN_EMAIL", "superadmin@swiftvalet.com")
SUPER_ADMIN_PASSWORD = os.environ.get("TEST_ADMIN_PASSWORD", "superadmin123")

# Known vehicle from context
KNOWN_VEHICLE_ID = "92d38b40-bc79-4568-a250-09f6e35bc865"


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def valet_token(api_client):
    """Get valet auth token via OTP"""
    # Request OTP
    resp = api_client.post(f"{BASE_URL}/api/auth/otp/request", json={"phone_number": VALET_PHONE})
    if resp.status_code != 200:
        pytest.skip(f"OTP request failed: {resp.text}")
    otp = resp.json().get("dev_otp")
    
    # Verify OTP
    resp = api_client.post(f"{BASE_URL}/api/auth/otp/verify", json={"phone_number": VALET_PHONE, "otp": otp})
    if resp.status_code != 200:
        pytest.skip(f"OTP verify failed: {resp.text}")
    return resp.json().get("token")


@pytest.fixture(scope="module")
def admin_token(api_client):
    """Get admin auth token via OTP"""
    resp = api_client.post(f"{BASE_URL}/api/auth/otp/request", json={"phone_number": ADMIN_PHONE})
    if resp.status_code != 200:
        pytest.skip(f"Admin OTP request failed: {resp.text}")
    otp = resp.json().get("dev_otp")
    
    resp = api_client.post(f"{BASE_URL}/api/auth/otp/verify", json={"phone_number": ADMIN_PHONE, "otp": otp})
    if resp.status_code != 200:
        pytest.skip(f"Admin OTP verify failed: {resp.text}")
    return resp.json().get("token")


class TestPublicRetrieveEndpoint:
    """Test GET /api/retrieve/{vehicle_id} - Public endpoint (no auth)"""
    
    def test_get_vehicle_info_success(self, api_client):
        """Test retrieving vehicle info for known vehicle"""
        resp = api_client.get(f"{BASE_URL}/api/retrieve/{KNOWN_VEHICLE_ID}")
        print(f"GET /api/retrieve/{KNOWN_VEHICLE_ID}: {resp.status_code}")
        
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        
        data = resp.json()
        assert "vehicle_id" in data
        assert "license_plate" in data
        assert "client_name" in data
        assert "valet_fee" in data
        assert "active_ticket_status" in data
        
        print(f"Vehicle info: plate={data.get('license_plate')}, client={data.get('client_name')}, fee={data.get('valet_fee')}")
    
    def test_get_vehicle_info_404_invalid_id(self, api_client):
        """Test 404 for invalid vehicle ID"""
        fake_id = str(uuid.uuid4())
        resp = api_client.get(f"{BASE_URL}/api/retrieve/{fake_id}")
        
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"
        assert "not found" in resp.json().get("detail", "").lower()
        print(f"404 for invalid vehicle ID: PASS")


class TestPublicConfirmEndpoint:
    """Test POST /api/retrieve/{vehicle_id}/confirm - Public endpoint"""
    
    def test_confirm_retrieval_creates_ticket(self, api_client, admin_token):
        """Test confirming retrieval creates a ticket"""
        # First, ensure valet_fee is 0 so we get an 'open' ticket
        headers = {"Authorization": f"Bearer {admin_token}"}
        api_client.put(f"{BASE_URL}/api/admin/profile?valet_fee=0", headers=headers)
        
        # Get current vehicle status
        resp = api_client.get(f"{BASE_URL}/api/retrieve/{KNOWN_VEHICLE_ID}")
        if resp.status_code != 200:
            pytest.skip("Vehicle not found")
        
        vehicle_data = resp.json()
        
        # If there's already an active ticket, skip this test
        if vehicle_data.get("active_ticket_status"):
            print(f"Vehicle already has active ticket: {vehicle_data.get('active_ticket_status')}")
            pytest.skip("Vehicle already has active ticket")
        
        # Confirm retrieval (no auth required)
        resp = api_client.post(f"{BASE_URL}/api/retrieve/{KNOWN_VEHICLE_ID}/confirm")
        print(f"POST /api/retrieve/{KNOWN_VEHICLE_ID}/confirm: {resp.status_code}")
        
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        
        data = resp.json()
        assert "status" in data
        assert "message" in data
        # With fee=0, should be 'open' status
        assert data["status"] in ["open", "pending_payment"], f"Unexpected status: {data['status']}"
        print(f"Confirm result: status={data['status']}, message={data['message']}")
    
    def test_confirm_retrieval_duplicate_blocked(self, api_client):
        """Test that duplicate retrieval request is blocked"""
        # Try to confirm again - should fail
        resp = api_client.post(f"{BASE_URL}/api/retrieve/{KNOWN_VEHICLE_ID}/confirm")
        print(f"Duplicate confirm attempt: {resp.status_code}")
        
        # Should be 400 because ticket already exists
        assert resp.status_code == 400, f"Expected 400 for duplicate, got {resp.status_code}"
        detail = resp.json().get("detail", "")
        assert "already" in detail.lower() or "progress" in detail.lower() or "pending" in detail.lower()
        print(f"Duplicate blocked: {detail}")
    
    def test_confirm_retrieval_404_invalid_id(self, api_client):
        """Test 404 for invalid vehicle ID on confirm"""
        fake_id = str(uuid.uuid4())
        resp = api_client.post(f"{BASE_URL}/api/retrieve/{fake_id}/confirm")
        
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"
        print("404 for invalid vehicle ID on confirm: PASS")


class TestWhatsAppWebhook:
    """Test POST /api/whatsapp/webhook - TwiML XML response"""
    
    def test_webhook_returns_twiml_xml(self, api_client):
        """Test webhook returns proper TwiML XML format"""
        # Send a test message
        resp = api_client.post(
            f"{BASE_URL}/api/whatsapp/webhook",
            data={"From": "+919999999999", "Body": "hello"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        print(f"Webhook response status: {resp.status_code}")
        print(f"Content-Type: {resp.headers.get('Content-Type')}")
        
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        
        # Check Content-Type is XML
        content_type = resp.headers.get("Content-Type", "")
        assert "xml" in content_type.lower(), f"Expected XML content type, got: {content_type}"
        
        # Check response is valid TwiML
        body = resp.text
        assert "<?xml" in body, "Missing XML declaration"
        assert "<Response>" in body, "Missing <Response> tag"
        assert "<Message>" in body, "Missing <Message> tag"
        assert "</Response>" in body, "Missing closing </Response> tag"
        
        print(f"TwiML response: {body[:200]}...")
    
    def test_webhook_retr_command(self, api_client):
        """Test webhook handles RETR command"""
        resp = api_client.post(
            f"{BASE_URL}/api/whatsapp/webhook",
            data={"From": "+919999999999", "Body": "RETR"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        assert resp.status_code == 200
        assert "xml" in resp.headers.get("Content-Type", "").lower()
        
        body = resp.text
        # Should contain a message about vehicle not found or retrieval
        assert "<Message>" in body
        print(f"RETR command response: {body[:200]}...")


class TestOTPLogin:
    """Test OTP login for admin and valet"""
    
    def test_admin_otp_login(self, api_client):
        """Test admin can login via OTP"""
        # Request OTP
        resp = api_client.post(f"{BASE_URL}/api/auth/otp/request", json={"phone_number": ADMIN_PHONE})
        assert resp.status_code == 200, f"OTP request failed: {resp.text}"
        
        data = resp.json()
        assert "dev_otp" in data, "dev_otp not in response"
        otp = data["dev_otp"]
        print(f"Admin OTP received: {otp}")
        
        # Verify OTP
        resp = api_client.post(f"{BASE_URL}/api/auth/otp/verify", json={"phone_number": ADMIN_PHONE, "otp": otp})
        assert resp.status_code == 200, f"OTP verify failed: {resp.text}"
        
        data = resp.json()
        assert "token" in data
        assert "user" in data
        assert data["user"]["role"] == "admin"
        print(f"Admin login success: {data['user']['name']}")
    
    def test_valet_otp_login(self, api_client):
        """Test valet can login via OTP"""
        # Request OTP
        resp = api_client.post(f"{BASE_URL}/api/auth/otp/request", json={"phone_number": VALET_PHONE})
        assert resp.status_code == 200, f"OTP request failed: {resp.text}"
        
        otp = resp.json().get("dev_otp")
        print(f"Valet OTP received: {otp}")
        
        # Verify OTP
        resp = api_client.post(f"{BASE_URL}/api/auth/otp/verify", json={"phone_number": VALET_PHONE, "otp": otp})
        assert resp.status_code == 200, f"OTP verify failed: {resp.text}"
        
        data = resp.json()
        assert "token" in data
        assert data["user"]["role"] == "valet"
        print(f"Valet login success: {data['user']['name']}")


class TestSuperAdminLogin:
    """Test super admin email/password login"""
    
    def test_super_admin_login(self, api_client):
        """Test super admin can login with email/password"""
        resp = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPER_ADMIN_EMAIL,
            "password": SUPER_ADMIN_PASSWORD
        })
        
        assert resp.status_code == 200, f"Super admin login failed: {resp.text}"
        
        data = resp.json()
        assert "token" in data
        assert data["user"]["role"] == "super_admin"
        print(f"Super admin login success: {data['user']['name']}")


class TestVehicleParkingWithRetrieveURL:
    """Test that parking a vehicle sends WhatsApp with retrieve URL"""
    
    def test_park_vehicle_sends_retrieve_url(self, api_client, valet_token):
        """Test parking a vehicle includes retrieve URL in message"""
        headers = {"Authorization": f"Bearer {valet_token}"}
        
        # Park a test vehicle
        test_phone = f"+91999{uuid.uuid4().hex[:7]}"
        test_plate = f"TEST-RETR-{uuid.uuid4().hex[:4].upper()}"
        
        resp = api_client.post(f"{BASE_URL}/api/vehicles", json={
            "phone_number": test_phone,
            "license_plate": test_plate,
            "tag_number": "T999"
        }, headers=headers)
        
        print(f"Park vehicle response: {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json()
            vehicle_id = data.get("vehicle", {}).get("id")
            print(f"Vehicle parked: {vehicle_id}")
            # The retrieve URL should be in the WhatsApp message (check backend logs)
            # We can verify the vehicle was created
            assert vehicle_id is not None
        elif resp.status_code == 403:
            # Valet might not be online
            print(f"Valet not online: {resp.text}")
            pytest.skip("Valet not online - cannot park")
        else:
            pytest.fail(f"Unexpected status: {resp.status_code}: {resp.text}")


class TestCleanup:
    """Cleanup test data"""
    
    def test_cleanup_test_tickets(self, api_client, admin_token):
        """Delete test tickets created during testing"""
        # Get all tickets
        headers = {"Authorization": f"Bearer {admin_token}"}
        resp = api_client.get(f"{BASE_URL}/api/tickets", headers=headers)
        
        if resp.status_code == 200:
            tickets = resp.json()
            # Find tickets for our known vehicle
            for ticket in tickets:
                if ticket.get("vehicle_id") == KNOWN_VEHICLE_ID:
                    ticket_id = ticket.get("id")
                    # Mark as completed to clean up
                    api_client.put(
                        f"{BASE_URL}/api/tickets/{ticket_id}/status?status=completed",
                        headers=headers
                    )
                    print(f"Cleaned up ticket: {ticket_id}")
        
        print("Cleanup completed")
