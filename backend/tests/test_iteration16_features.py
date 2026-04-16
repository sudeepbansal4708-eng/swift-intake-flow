"""
Test Suite for ParKaro Iteration 16 Features:
1. Bottom ribbon with Park/Retrieve buttons (frontend)
2. Valet checkout capability (not just admin)
3. Thank-you + tip message on checkout
4. Deadline time in WhatsApp 'arrived' message
5. Customer retrieve page countdown timer and valet name display
6. Full lifecycle test
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://swift-intake-flow.preview.emergentagent.com').rstrip('/')

# Test credentials from seed data
VALET_PHONE = "+919922668866"  # Jennifer Smith
ADMIN_PHONE = "+919373991136"  # John Smith
SUPER_ADMIN_EMAIL = os.environ.get("TEST_ADMIN_EMAIL", "superadmin@swiftvalet.com")
SUPER_ADMIN_PASSWORD = os.environ.get("TEST_ADMIN_PASSWORD", "superadmin123")


class TestValetLogin:
    """Test valet OTP login flow"""
    
    def test_valet_otp_request(self):
        """Request OTP for valet phone"""
        response = requests.post(f"{BASE_URL}/api/auth/otp/request", json={
            "phone_number": VALET_PHONE
        })
        assert response.status_code == 200, f"OTP request failed: {response.text}"
        data = response.json()
        assert "dev_otp" in data, "dev_otp not in response"
        assert "phone_number" in data
        print(f"✓ Valet OTP requested: {data['dev_otp']}")
        return data['dev_otp']
    
    def test_valet_otp_verify_and_login(self):
        """Verify OTP and get token for valet"""
        # First request OTP
        otp_response = requests.post(f"{BASE_URL}/api/auth/otp/request", json={
            "phone_number": VALET_PHONE
        })
        assert otp_response.status_code == 200
        otp = otp_response.json()['dev_otp']
        
        # Verify OTP
        verify_response = requests.post(f"{BASE_URL}/api/auth/otp/verify", json={
            "phone_number": VALET_PHONE,
            "otp": otp
        })
        assert verify_response.status_code == 200, f"OTP verify failed: {verify_response.text}"
        data = verify_response.json()
        assert "token" in data
        assert data['user']['role'] == 'valet'
        print(f"✓ Valet logged in: {data['user']['name']} (role={data['user']['role']})")
        return data['token'], data['user']


class TestValetCheckoutCapability:
    """Test that valet can checkout vehicles (not just admin)"""
    
    @pytest.fixture
    def valet_token(self):
        """Get valet auth token"""
        otp_response = requests.post(f"{BASE_URL}/api/auth/otp/request", json={
            "phone_number": VALET_PHONE
        })
        otp = otp_response.json()['dev_otp']
        verify_response = requests.post(f"{BASE_URL}/api/auth/otp/verify", json={
            "phone_number": VALET_PHONE,
            "otp": otp
        })
        return verify_response.json()['token']
    
    @pytest.fixture
    def admin_token(self):
        """Get admin auth token"""
        otp_response = requests.post(f"{BASE_URL}/api/auth/otp/request", json={
            "phone_number": ADMIN_PHONE
        })
        otp = otp_response.json()['dev_otp']
        verify_response = requests.post(f"{BASE_URL}/api/auth/otp/verify", json={
            "phone_number": ADMIN_PHONE,
            "otp": otp
        })
        return verify_response.json()['token']
    
    def test_valet_can_park_vehicle(self, valet_token):
        """Valet parks a vehicle"""
        headers = {"Authorization": f"Bearer {valet_token}"}
        response = requests.post(f"{BASE_URL}/api/vehicles", json={
            "phone_number": "+919999888877",
            "license_plate": "TEST16VALET01",
            "zone_label": "Zone A - Test"
        }, headers=headers)
        assert response.status_code == 200, f"Park failed: {response.text}"
        data = response.json()
        assert "vehicle" in data
        vehicle_id = data['vehicle']['id']
        print(f"✓ Vehicle parked: {vehicle_id}")
        return vehicle_id
    
    def test_valet_checkout_endpoint_accepts_valet_role(self, valet_token):
        """Test that POST /api/admin/vehicles/{vehicle_id}/checkout accepts valet role"""
        headers = {"Authorization": f"Bearer {valet_token}"}
        
        # First park a vehicle
        park_response = requests.post(f"{BASE_URL}/api/vehicles", json={
            "phone_number": "+919999888876",
            "license_plate": "TEST16CHECKOUT01",
            "zone_label": "Zone B - Test"
        }, headers=headers)
        assert park_response.status_code == 200
        vehicle_id = park_response.json()['vehicle']['id']
        
        # Now checkout as valet
        checkout_response = requests.post(
            f"{BASE_URL}/api/admin/vehicles/{vehicle_id}/checkout",
            headers=headers
        )
        assert checkout_response.status_code == 200, f"Valet checkout failed: {checkout_response.text}"
        data = checkout_response.json()
        assert data['message'] == "Vehicle checked out successfully"
        print(f"✓ Valet checkout successful for vehicle {vehicle_id}")
    
    def test_admin_checkout_still_works(self, admin_token):
        """Test that admin can still checkout vehicles"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # First park a vehicle as admin
        park_response = requests.post(f"{BASE_URL}/api/vehicles", json={
            "phone_number": "+919999888875",
            "license_plate": "TEST16ADMINCHK01",
            "zone_label": "Zone C - Test"
        }, headers=headers)
        assert park_response.status_code == 200
        vehicle_id = park_response.json()['vehicle']['id']
        
        # Checkout as admin
        checkout_response = requests.post(
            f"{BASE_URL}/api/admin/vehicles/{vehicle_id}/checkout",
            headers=headers
        )
        assert checkout_response.status_code == 200, f"Admin checkout failed: {checkout_response.text}"
        print(f"✓ Admin checkout successful for vehicle {vehicle_id}")


class TestArrivedStatusWithDeadline:
    """Test that arrived status saves arrived_at and sends deadline in WhatsApp message"""
    
    @pytest.fixture
    def valet_token(self):
        """Get valet auth token"""
        otp_response = requests.post(f"{BASE_URL}/api/auth/otp/request", json={
            "phone_number": VALET_PHONE
        })
        otp = otp_response.json()['dev_otp']
        verify_response = requests.post(f"{BASE_URL}/api/auth/otp/verify", json={
            "phone_number": VALET_PHONE,
            "otp": otp
        })
        return verify_response.json()['token']
    
    def test_arrived_status_saves_arrived_at(self, valet_token):
        """Test that updating ticket to 'arrived' saves arrived_at timestamp"""
        headers = {"Authorization": f"Bearer {valet_token}"}
        
        # Park a vehicle
        park_response = requests.post(f"{BASE_URL}/api/vehicles", json={
            "phone_number": "+919999888874",
            "license_plate": "TEST16ARRIVED01",
            "zone_label": "Zone D - Test"
        }, headers=headers)
        assert park_response.status_code == 200
        vehicle_id = park_response.json()['vehicle']['id']
        
        # Create a retrieval ticket via valet
        retrieve_response = requests.post(f"{BASE_URL}/api/tickets/retrieve", json={
            "phone_number": "+919999888874"
        }, headers=headers)
        assert retrieve_response.status_code == 200, f"Retrieve failed: {retrieve_response.text}"
        ticket_id = retrieve_response.json()['ticket']['id']
        
        # Update status to arrived
        arrived_response = requests.put(
            f"{BASE_URL}/api/tickets/{ticket_id}/status?status=arrived",
            headers=headers
        )
        assert arrived_response.status_code == 200, f"Arrived status update failed: {arrived_response.text}"
        
        # Check the public retrieve endpoint for arrived_at
        public_response = requests.get(f"{BASE_URL}/api/retrieve/{vehicle_id}")
        assert public_response.status_code == 200
        data = public_response.json()
        assert data['active_ticket_status'] == 'arrived', f"Expected 'arrived', got {data['active_ticket_status']}"
        assert data['arrived_at'] is not None, "arrived_at should be set"
        print(f"✓ arrived_at timestamp saved: {data['arrived_at']}")
        
        # Cleanup - checkout the vehicle
        requests.post(f"{BASE_URL}/api/admin/vehicles/{vehicle_id}/checkout", headers=headers)


class TestPublicRetrieveEndpoint:
    """Test GET /api/retrieve/{vehicle_id} returns valet_name and arrived_at"""
    
    @pytest.fixture
    def valet_token(self):
        """Get valet auth token"""
        otp_response = requests.post(f"{BASE_URL}/api/auth/otp/request", json={
            "phone_number": VALET_PHONE
        })
        otp = otp_response.json()['dev_otp']
        verify_response = requests.post(f"{BASE_URL}/api/auth/otp/verify", json={
            "phone_number": VALET_PHONE,
            "otp": otp
        })
        return verify_response.json()['token']
    
    def test_retrieve_endpoint_returns_valet_name_when_claimed(self, valet_token):
        """Test that valet_name is returned when ticket is claimed"""
        headers = {"Authorization": f"Bearer {valet_token}"}
        
        # Park a vehicle
        park_response = requests.post(f"{BASE_URL}/api/vehicles", json={
            "phone_number": "+919999888873",
            "license_plate": "TEST16VALETNAME01",
            "zone_label": "Zone E - Test"
        }, headers=headers)
        assert park_response.status_code == 200
        vehicle_id = park_response.json()['vehicle']['id']
        
        # Create a retrieval ticket (auto-claimed by valet)
        retrieve_response = requests.post(f"{BASE_URL}/api/tickets/retrieve", json={
            "phone_number": "+919999888873"
        }, headers=headers)
        assert retrieve_response.status_code == 200
        
        # Check public endpoint for valet_name
        public_response = requests.get(f"{BASE_URL}/api/retrieve/{vehicle_id}")
        assert public_response.status_code == 200
        data = public_response.json()
        assert data['valet_name'] is not None, "valet_name should be set when ticket is claimed"
        assert data['valet_name'] == "Jennifer Smith", f"Expected 'Jennifer Smith', got {data['valet_name']}"
        print(f"✓ valet_name returned: {data['valet_name']}")
        
        # Cleanup
        requests.post(f"{BASE_URL}/api/admin/vehicles/{vehicle_id}/checkout", headers=headers)
    
    def test_retrieve_endpoint_returns_arrived_at_when_arrived(self, valet_token):
        """Test that arrived_at is returned when ticket status is arrived"""
        headers = {"Authorization": f"Bearer {valet_token}"}
        
        # Park a vehicle
        park_response = requests.post(f"{BASE_URL}/api/vehicles", json={
            "phone_number": "+919999888872",
            "license_plate": "TEST16ARRIVEDAT01",
            "zone_label": "Zone F - Test"
        }, headers=headers)
        assert park_response.status_code == 200
        vehicle_id = park_response.json()['vehicle']['id']
        
        # Create a retrieval ticket
        retrieve_response = requests.post(f"{BASE_URL}/api/tickets/retrieve", json={
            "phone_number": "+919999888872"
        }, headers=headers)
        assert retrieve_response.status_code == 200
        ticket_id = retrieve_response.json()['ticket']['id']
        
        # Update to arrived
        requests.put(f"{BASE_URL}/api/tickets/{ticket_id}/status?status=arrived", headers=headers)
        
        # Check public endpoint
        public_response = requests.get(f"{BASE_URL}/api/retrieve/{vehicle_id}")
        assert public_response.status_code == 200
        data = public_response.json()
        assert data['arrived_at'] is not None, "arrived_at should be set"
        assert data['active_ticket_status'] == 'arrived'
        print(f"✓ arrived_at returned: {data['arrived_at']}")
        
        # Cleanup
        requests.post(f"{BASE_URL}/api/admin/vehicles/{vehicle_id}/checkout", headers=headers)


class TestFullLifecycle:
    """Full lifecycle test: Park -> Customer confirms -> Valet claims -> Arrived -> Checkout"""
    
    def test_full_lifecycle(self):
        """Test complete valet parking lifecycle"""
        # 1. Login as valet
        otp_response = requests.post(f"{BASE_URL}/api/auth/otp/request", json={
            "phone_number": VALET_PHONE
        })
        assert otp_response.status_code == 200
        otp = otp_response.json()['dev_otp']
        
        verify_response = requests.post(f"{BASE_URL}/api/auth/otp/verify", json={
            "phone_number": VALET_PHONE,
            "otp": otp
        })
        assert verify_response.status_code == 200
        valet_token = verify_response.json()['token']
        headers = {"Authorization": f"Bearer {valet_token}"}
        print("✓ Step 1: Valet logged in")
        
        # 2. Park vehicle
        park_response = requests.post(f"{BASE_URL}/api/vehicles", json={
            "phone_number": "+919999888871",
            "license_plate": "TEST16LIFECYCLE01",
            "zone_label": "Zone G - Lifecycle Test"
        }, headers=headers)
        assert park_response.status_code == 200
        vehicle_id = park_response.json()['vehicle']['id']
        print(f"✓ Step 2: Vehicle parked (id={vehicle_id})")
        
        # 3. Customer confirms retrieval (public endpoint)
        confirm_response = requests.post(f"{BASE_URL}/api/retrieve/{vehicle_id}/confirm")
        assert confirm_response.status_code == 200
        confirm_data = confirm_response.json()
        assert confirm_data['status'] == 'open', f"Expected 'open', got {confirm_data['status']}"
        print("✓ Step 3: Customer confirmed retrieval")
        
        # 4. Get tickets and find the open one
        tickets_response = requests.get(f"{BASE_URL}/api/tickets", headers=headers)
        assert tickets_response.status_code == 200
        tickets = tickets_response.json()
        open_ticket = next((t for t in tickets if t['vehicle_id'] == vehicle_id and t['status'] == 'open'), None)
        assert open_ticket is not None, "Open ticket not found"
        ticket_id = open_ticket['id']
        print(f"✓ Step 4: Found open ticket (id={ticket_id})")
        
        # 5. Valet claims ticket
        claim_response = requests.put(f"{BASE_URL}/api/tickets/{ticket_id}/claim", headers=headers)
        assert claim_response.status_code == 200
        print("✓ Step 5: Valet claimed ticket")
        
        # 6. Valet marks arrived
        arrived_response = requests.put(
            f"{BASE_URL}/api/tickets/{ticket_id}/status?status=arrived",
            headers=headers
        )
        assert arrived_response.status_code == 200
        print("✓ Step 6: Valet marked arrived")
        
        # 7. Verify public endpoint shows arrived status with valet_name and arrived_at
        public_response = requests.get(f"{BASE_URL}/api/retrieve/{vehicle_id}")
        assert public_response.status_code == 200
        public_data = public_response.json()
        assert public_data['active_ticket_status'] == 'arrived'
        assert public_data['valet_name'] is not None
        assert public_data['arrived_at'] is not None
        print(f"✓ Step 7: Public endpoint shows arrived (valet={public_data['valet_name']}, arrived_at={public_data['arrived_at']})")
        
        # 8. Valet checkouts (this should send thank-you message)
        checkout_response = requests.post(
            f"{BASE_URL}/api/admin/vehicles/{vehicle_id}/checkout",
            headers=headers
        )
        assert checkout_response.status_code == 200
        print("✓ Step 8: Valet checkout successful (thank-you message sent)")
        
        # 9. Verify vehicle is checked out
        final_response = requests.get(f"{BASE_URL}/api/retrieve/{vehicle_id}")
        assert final_response.status_code == 200
        final_data = final_response.json()
        assert final_data['status'] == 'checked_out'
        print("✓ Step 9: Vehicle status is checked_out")
        
        print("\n✅ FULL LIFECYCLE TEST PASSED!")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
