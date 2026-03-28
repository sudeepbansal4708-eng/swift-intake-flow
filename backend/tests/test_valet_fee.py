"""
Test Valet Fee Feature for ParKaro Platform
Tests:
1. PUT /api/admin/profile?valet_fee=200 - sets the valet fee for the admin's client
2. GET /api/auth/me - returns valet_fee field
3. POST /api/tickets/retrieve with valet_fee > 1 - creates pending_payment ticket
4. POST /api/tickets/retrieve with valet_fee = 0 - creates claimed ticket directly
5. POST /api/tickets/retrieve with valet_fee = 1 - creates claimed ticket directly (threshold is > 1)
6. Duplicate retrieval blocked for pending_payment tickets too
"""

import pytest
import requests
import os
import uuid
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
ADMIN_PHONE = "+919373991136"


class TestValetFeeFeature:
    """Test valet fee feature for ParKaro platform"""
    
    token = None
    admin_user = None
    test_vehicle_id = None
    test_ticket_id = None
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: Login as admin via OTP"""
        if TestValetFeeFeature.token is None:
            # Request OTP
            otp_res = requests.post(f"{BASE_URL}/api/auth/otp/request", json={"phone_number": ADMIN_PHONE})
            assert otp_res.status_code == 200, f"OTP request failed: {otp_res.text}"
            dev_otp = otp_res.json().get("dev_otp")
            assert dev_otp, "No dev_otp returned"
            
            # Verify OTP
            verify_res = requests.post(f"{BASE_URL}/api/auth/otp/verify", json={
                "phone_number": ADMIN_PHONE,
                "otp": dev_otp
            })
            assert verify_res.status_code == 200, f"OTP verify failed: {verify_res.text}"
            TestValetFeeFeature.token = verify_res.json().get("token")
            TestValetFeeFeature.admin_user = verify_res.json().get("user")
        
        self.headers = {"Authorization": f"Bearer {TestValetFeeFeature.token}"}
    
    def test_01_set_valet_fee_200(self):
        """Test setting valet fee to 200"""
        res = requests.put(f"{BASE_URL}/api/admin/profile?valet_fee=200", headers=self.headers)
        assert res.status_code == 200, f"Failed to set valet fee: {res.text}"
        data = res.json()
        assert data.get("valet_fee") == 200, f"Expected valet_fee=200, got {data.get('valet_fee')}"
        print(f"✓ Set valet fee to 200: {data}")
    
    def test_02_get_me_returns_valet_fee(self):
        """Test GET /api/auth/me returns valet_fee field"""
        res = requests.get(f"{BASE_URL}/api/auth/me", headers=self.headers)
        assert res.status_code == 200, f"Failed to get /auth/me: {res.text}"
        data = res.json()
        assert "valet_fee" in data, f"valet_fee field missing in response: {data}"
        assert data["valet_fee"] == 200, f"Expected valet_fee=200, got {data['valet_fee']}"
        print(f"✓ GET /auth/me returns valet_fee: {data['valet_fee']}")
    
    def test_03_park_vehicle_for_fee_test(self):
        """Park a test vehicle for fee testing"""
        unique_phone = f"+91999{datetime.now().strftime('%H%M%S%f')[:7]}"
        vehicle_data = {
            "phone_number": unique_phone,
            "license_plate": f"TEST-FEE-{uuid.uuid4().hex[:6].upper()}",
            "tag_number": "FEE01",
            "zone_label": "Test Zone A"
        }
        res = requests.post(f"{BASE_URL}/api/vehicles", json=vehicle_data, headers=self.headers)
        assert res.status_code == 200, f"Failed to park vehicle: {res.text}"
        TestValetFeeFeature.test_vehicle_id = res.json()["vehicle"]["id"]
        TestValetFeeFeature.test_phone = unique_phone
        print(f"✓ Parked test vehicle: {vehicle_data['license_plate']} with phone {unique_phone}")
    
    def test_04_retrieve_with_fee_creates_pending_payment(self):
        """Test POST /api/tickets/retrieve with valet_fee > 1 creates pending_payment ticket"""
        res = requests.post(f"{BASE_URL}/api/tickets/retrieve", 
                           json={"phone_number": TestValetFeeFeature.test_phone},
                           headers=self.headers)
        assert res.status_code == 200, f"Failed to retrieve: {res.text}"
        data = res.json()
        
        # Check pending_payment flag
        assert data.get("pending_payment") == True, f"Expected pending_payment=True, got {data.get('pending_payment')}"
        
        # Check ticket status
        ticket = data.get("ticket", {})
        assert ticket.get("status") == "pending_payment", f"Expected status=pending_payment, got {ticket.get('status')}"
        
        # Check valet_fee in response
        assert ticket.get("valet_fee") == 200, f"Expected valet_fee=200 in ticket, got {ticket.get('valet_fee')}"
        
        TestValetFeeFeature.test_ticket_id = ticket.get("id")
        print(f"✓ Retrieve with fee creates pending_payment ticket: {ticket['id']}")
        print(f"  - status: {ticket['status']}")
        print(f"  - valet_fee: {ticket['valet_fee']}")
        print(f"  - message: {data.get('message')}")
    
    def test_05_duplicate_retrieval_blocked_for_pending_payment(self):
        """Test duplicate retrieval is blocked for pending_payment tickets"""
        res = requests.post(f"{BASE_URL}/api/tickets/retrieve", 
                           json={"phone_number": TestValetFeeFeature.test_phone},
                           headers=self.headers)
        assert res.status_code == 400, f"Expected 400 for duplicate retrieval, got {res.status_code}"
        assert "already exists" in res.json().get("detail", "").lower(), f"Unexpected error: {res.text}"
        print(f"✓ Duplicate retrieval blocked for pending_payment ticket")
    
    def test_06_set_valet_fee_to_zero(self):
        """Test setting valet fee to 0"""
        res = requests.put(f"{BASE_URL}/api/admin/profile?valet_fee=0", headers=self.headers)
        assert res.status_code == 200, f"Failed to set valet fee: {res.text}"
        data = res.json()
        assert data.get("valet_fee") == 0, f"Expected valet_fee=0, got {data.get('valet_fee')}"
        print(f"✓ Set valet fee to 0")
    
    def test_07_park_vehicle_for_no_fee_test(self):
        """Park another test vehicle for no-fee testing"""
        unique_phone = f"+91888{datetime.now().strftime('%H%M%S%f')[:7]}"
        vehicle_data = {
            "phone_number": unique_phone,
            "license_plate": f"TEST-NOFEE-{uuid.uuid4().hex[:6].upper()}",
            "tag_number": "NOFEE01",
            "zone_label": "Test Zone B"
        }
        res = requests.post(f"{BASE_URL}/api/vehicles", json=vehicle_data, headers=self.headers)
        assert res.status_code == 200, f"Failed to park vehicle: {res.text}"
        TestValetFeeFeature.test_vehicle_id_nofee = res.json()["vehicle"]["id"]
        TestValetFeeFeature.test_phone_nofee = unique_phone
        print(f"✓ Parked test vehicle for no-fee test: {vehicle_data['license_plate']}")
    
    def test_08_retrieve_with_zero_fee_creates_claimed(self):
        """Test POST /api/tickets/retrieve with valet_fee = 0 creates claimed ticket directly"""
        res = requests.post(f"{BASE_URL}/api/tickets/retrieve", 
                           json={"phone_number": TestValetFeeFeature.test_phone_nofee},
                           headers=self.headers)
        assert res.status_code == 200, f"Failed to retrieve: {res.text}"
        data = res.json()
        
        # Check NO pending_payment flag (or it's False)
        assert data.get("pending_payment") != True, f"Expected no pending_payment, got {data.get('pending_payment')}"
        
        # Check ticket status is claimed (not pending_payment)
        ticket = data.get("ticket", {})
        assert ticket.get("status") == "claimed", f"Expected status=claimed, got {ticket.get('status')}"
        
        print(f"✓ Retrieve with zero fee creates claimed ticket: {ticket['id']}")
        print(f"  - status: {ticket['status']}")
    
    def test_09_set_valet_fee_to_one(self):
        """Test setting valet fee to 1 (threshold is > 1, so 1 should NOT trigger payment)"""
        res = requests.put(f"{BASE_URL}/api/admin/profile?valet_fee=1", headers=self.headers)
        assert res.status_code == 200, f"Failed to set valet fee: {res.text}"
        print(f"✓ Set valet fee to 1")
    
    def test_10_park_vehicle_for_fee_one_test(self):
        """Park another test vehicle for fee=1 testing"""
        unique_phone = f"+91777{datetime.now().strftime('%H%M%S%f')[:7]}"
        vehicle_data = {
            "phone_number": unique_phone,
            "license_plate": f"TEST-FEE1-{uuid.uuid4().hex[:6].upper()}",
            "tag_number": "FEE1",
            "zone_label": "Test Zone C"
        }
        res = requests.post(f"{BASE_URL}/api/vehicles", json=vehicle_data, headers=self.headers)
        assert res.status_code == 200, f"Failed to park vehicle: {res.text}"
        TestValetFeeFeature.test_vehicle_id_fee1 = res.json()["vehicle"]["id"]
        TestValetFeeFeature.test_phone_fee1 = unique_phone
        print(f"✓ Parked test vehicle for fee=1 test: {vehicle_data['license_plate']}")
    
    def test_11_retrieve_with_fee_one_creates_claimed(self):
        """Test POST /api/tickets/retrieve with valet_fee = 1 creates claimed ticket (threshold is > 1)"""
        res = requests.post(f"{BASE_URL}/api/tickets/retrieve", 
                           json={"phone_number": TestValetFeeFeature.test_phone_fee1},
                           headers=self.headers)
        assert res.status_code == 200, f"Failed to retrieve: {res.text}"
        data = res.json()
        
        # Check NO pending_payment flag (threshold is > 1, so fee=1 should NOT trigger payment)
        assert data.get("pending_payment") != True, f"Expected no pending_payment for fee=1, got {data.get('pending_payment')}"
        
        # Check ticket status is claimed (not pending_payment)
        ticket = data.get("ticket", {})
        assert ticket.get("status") == "claimed", f"Expected status=claimed for fee=1, got {ticket.get('status')}"
        
        print(f"✓ Retrieve with fee=1 creates claimed ticket (threshold is > 1): {ticket['id']}")
        print(f"  - status: {ticket['status']}")
    
    def test_12_cleanup_reset_fee_to_zero(self):
        """Cleanup: Reset valet fee to 0"""
        res = requests.put(f"{BASE_URL}/api/admin/profile?valet_fee=0", headers=self.headers)
        assert res.status_code == 200, f"Failed to reset valet fee: {res.text}"
        print(f"✓ Reset valet fee to 0 for cleanup")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
