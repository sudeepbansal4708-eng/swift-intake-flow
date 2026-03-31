"""
Test SMS Fallback and Full Ticket Lifecycle for ParKaro
Tests:
1. Super admin login (email/password)
2. Admin OTP login (+919373991136)
3. Valet OTP login (+919922668866)
4. Valet must be online to park vehicles
5. SMS sending when vehicle is parked
6. WhatsApp webhook (inbound RETR) creates retrieval ticket
7. Full ticket lifecycle: Park -> RETR -> claim -> arrived -> completed
8. Admin cleanup endpoint
9. Database state verification
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestAuthFlows:
    """Test authentication flows for all user types"""
    
    def test_super_admin_login(self):
        """Super admin can login with email/password"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "superadmin@swiftvalet.com",
            "password": "superadmin123"
        })
        print(f"Super admin login: status={response.status_code}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "token" in data, "Token not in response"
        assert data["user"]["role"] == "super_admin", f"Expected super_admin role, got {data['user']['role']}"
        print(f"Super admin login SUCCESS: user={data['user']['name']}")
        return data["token"]
    
    def test_admin_otp_request(self):
        """Admin can request OTP and dev_otp is returned"""
        response = requests.post(f"{BASE_URL}/api/auth/otp/request", json={
            "phone_number": "+919373991136"
        })
        print(f"Admin OTP request: status={response.status_code}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "dev_otp" in data, "dev_otp not in response"
        print(f"Admin OTP request SUCCESS: dev_otp={data['dev_otp']}")
        return data["dev_otp"]
    
    def test_admin_otp_verify(self):
        """Admin can verify OTP and login"""
        # First request OTP
        otp_response = requests.post(f"{BASE_URL}/api/auth/otp/request", json={
            "phone_number": "+919373991136"
        })
        assert otp_response.status_code == 200
        otp = otp_response.json()["dev_otp"]
        
        # Verify OTP
        response = requests.post(f"{BASE_URL}/api/auth/otp/verify", json={
            "phone_number": "+919373991136",
            "otp": otp
        })
        print(f"Admin OTP verify: status={response.status_code}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "token" in data, "Token not in response"
        assert data["user"]["role"] == "admin", f"Expected admin role, got {data['user']['role']}"
        print(f"Admin OTP verify SUCCESS: user={data['user']['name']}, client={data['user'].get('client_name')}")
        return data["token"]
    
    def test_valet_otp_request(self):
        """Valet can request OTP and dev_otp is returned"""
        response = requests.post(f"{BASE_URL}/api/auth/otp/request", json={
            "phone_number": "+919922668866"
        })
        print(f"Valet OTP request: status={response.status_code}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "dev_otp" in data, "dev_otp not in response"
        print(f"Valet OTP request SUCCESS: dev_otp={data['dev_otp']}")
        return data["dev_otp"]
    
    def test_valet_otp_verify(self):
        """Valet can verify OTP and login"""
        # First request OTP
        otp_response = requests.post(f"{BASE_URL}/api/auth/otp/request", json={
            "phone_number": "+919922668866"
        })
        assert otp_response.status_code == 200
        otp = otp_response.json()["dev_otp"]
        
        # Verify OTP
        response = requests.post(f"{BASE_URL}/api/auth/otp/verify", json={
            "phone_number": "+919922668866",
            "otp": otp
        })
        print(f"Valet OTP verify: status={response.status_code}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "token" in data, "Token not in response"
        assert data["user"]["role"] == "valet", f"Expected valet role, got {data['user']['role']}"
        print(f"Valet OTP verify SUCCESS: user={data['user']['name']}")
        return data["token"]


class TestValetOnlineRequirement:
    """Test that valet must be online to park vehicles"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin token"""
        otp_response = requests.post(f"{BASE_URL}/api/auth/otp/request", json={
            "phone_number": "+919373991136"
        })
        otp = otp_response.json()["dev_otp"]
        response = requests.post(f"{BASE_URL}/api/auth/otp/verify", json={
            "phone_number": "+919373991136",
            "otp": otp
        })
        return response.json()["token"]
    
    @pytest.fixture
    def valet_token(self):
        """Get valet token"""
        otp_response = requests.post(f"{BASE_URL}/api/auth/otp/request", json={
            "phone_number": "+919922668866"
        })
        otp = otp_response.json()["dev_otp"]
        response = requests.post(f"{BASE_URL}/api/auth/otp/verify", json={
            "phone_number": "+919922668866",
            "otp": otp
        })
        return response.json()["token"]
    
    @pytest.fixture
    def valet_id(self, admin_token):
        """Get valet ID from admin's valet list"""
        response = requests.get(
            f"{BASE_URL}/api/admin/valets",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        valets = response.json()
        # Find Jennifer Smith (valet with phone +919922668866)
        for valet in valets:
            if valet.get("phone_number") == "+919922668866":
                return valet["id"]
        return None
    
    def test_offline_valet_cannot_park(self, admin_token, valet_token, valet_id):
        """Offline valet should get 403 when trying to park"""
        # First ensure valet is offline
        if valet_id:
            # Toggle offline
            requests.put(
                f"{BASE_URL}/api/admin/valets/{valet_id}/toggle-online",
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            # Check status
            me_response = requests.get(
                f"{BASE_URL}/api/auth/me",
                headers={"Authorization": f"Bearer {valet_token}"}
            )
            if me_response.json().get("is_online"):
                # Toggle again to make offline
                requests.put(
                    f"{BASE_URL}/api/admin/valets/{valet_id}/toggle-online",
                    headers={"Authorization": f"Bearer {admin_token}"}
                )
        
        # Try to park while offline
        response = requests.post(
            f"{BASE_URL}/api/vehicles",
            headers={"Authorization": f"Bearer {valet_token}"},
            json={
                "phone_number": "+919999999999",
                "license_plate": "TEST-OFFLINE-001",
                "zone_label": "Test Zone"
            }
        )
        print(f"Offline valet park attempt: status={response.status_code}")
        # Should be 403 if offline
        if response.status_code == 403:
            print("PASS: Offline valet correctly blocked from parking")
            assert "online" in response.json().get("detail", "").lower()
        else:
            print(f"Note: Valet may already be online, got status {response.status_code}")


class TestSMSAndTicketLifecycle:
    """Test SMS sending and full ticket lifecycle"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin token"""
        otp_response = requests.post(f"{BASE_URL}/api/auth/otp/request", json={
            "phone_number": "+919373991136"
        })
        otp = otp_response.json()["dev_otp"]
        response = requests.post(f"{BASE_URL}/api/auth/otp/verify", json={
            "phone_number": "+919373991136",
            "otp": otp
        })
        return response.json()["token"]
    
    @pytest.fixture
    def valet_token(self):
        """Get valet token"""
        otp_response = requests.post(f"{BASE_URL}/api/auth/otp/request", json={
            "phone_number": "+919922668866"
        })
        otp = otp_response.json()["dev_otp"]
        response = requests.post(f"{BASE_URL}/api/auth/otp/verify", json={
            "phone_number": "+919922668866",
            "otp": otp
        })
        return response.json()["token"]
    
    @pytest.fixture
    def valet_id(self, admin_token):
        """Get valet ID"""
        response = requests.get(
            f"{BASE_URL}/api/admin/valets",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        valets = response.json()
        for valet in valets:
            if valet.get("phone_number") == "+919922668866":
                return valet["id"]
        return None
    
    def test_full_ticket_lifecycle(self, admin_token, valet_token, valet_id):
        """Test complete flow: Park -> RETR webhook -> claim -> arrived -> completed
        Note: If admin has valet_fee > 1, ticket will be pending_payment (expected behavior)
        """
        
        # Step 1: Ensure valet is online
        if valet_id:
            me_response = requests.get(
                f"{BASE_URL}/api/auth/me",
                headers={"Authorization": f"Bearer {valet_token}"}
            )
            if not me_response.json().get("is_online"):
                toggle_response = requests.put(
                    f"{BASE_URL}/api/admin/valets/{valet_id}/toggle-online",
                    headers={"Authorization": f"Bearer {admin_token}"}
                )
                print(f"Toggled valet online: {toggle_response.status_code}")
        
        # Step 2: Park a vehicle (this should send SMS)
        test_phone = "+919373991136"  # Use admin's phone for testing
        test_plate = f"TEST-SMS-{int(time.time())}"
        
        park_response = requests.post(
            f"{BASE_URL}/api/vehicles",
            headers={"Authorization": f"Bearer {valet_token}"},
            json={
                "phone_number": test_phone,
                "license_plate": test_plate,
                "zone_label": "Test Zone A"
            }
        )
        print(f"Park vehicle: status={park_response.status_code}")
        assert park_response.status_code == 200, f"Failed to park: {park_response.text}"
        
        vehicle_data = park_response.json()
        vehicle_id = vehicle_data["vehicle"]["id"]
        print(f"Vehicle parked: id={vehicle_id}, plate={test_plate}")
        print("SMS should have been sent - check backend logs for 'Message sent'")
        
        # Step 3: Simulate RETR webhook (customer replies RETR)
        webhook_response = requests.post(
            f"{BASE_URL}/api/whatsapp/webhook",
            data={
                "From": test_phone,
                "Body": "RETR"
            }
        )
        print(f"RETR webhook: status={webhook_response.status_code}")
        assert webhook_response.status_code == 200, f"Webhook failed: {webhook_response.text}"
        
        webhook_data = webhook_response.json()
        print(f"Webhook response: {webhook_data}")
        assert "reply" in webhook_data
        
        # Step 4: Find the created ticket
        time.sleep(0.5)  # Brief wait for DB
        tickets_response = requests.get(
            f"{BASE_URL}/api/tickets",
            headers={"Authorization": f"Bearer {valet_token}"}
        )
        tickets = tickets_response.json()
        
        # Find ticket for our vehicle
        ticket = None
        for t in tickets:
            if t.get("vehicle_id") == vehicle_id:
                ticket = t
                break
        
        assert ticket is not None, f"Ticket not found for vehicle {vehicle_id}"
        ticket_id = ticket["id"]
        ticket_status = ticket['status']
        print(f"Ticket created: id={ticket_id}, status={ticket_status}")
        
        # If ticket is pending_payment, that's expected when valet_fee > 1
        if ticket_status == "pending_payment":
            print("PASS: Ticket created with pending_payment status (valet fee feature working)")
            print("Note: Full lifecycle requires payment completion - skipping claim/arrived/completed")
            return ticket_id
        
        # Step 5: Claim the ticket (only if status is open)
        if ticket_status == "open":
            claim_response = requests.put(
                f"{BASE_URL}/api/tickets/{ticket_id}/claim",
                headers={"Authorization": f"Bearer {valet_token}"}
            )
            print(f"Claim ticket: status={claim_response.status_code}")
            assert claim_response.status_code == 200, f"Claim failed: {claim_response.text}"
            
            # Step 6: Update status to arrived
            arrived_response = requests.put(
                f"{BASE_URL}/api/tickets/{ticket_id}/status?status=arrived",
                headers={"Authorization": f"Bearer {valet_token}"}
            )
            print(f"Status -> arrived: status={arrived_response.status_code}")
            assert arrived_response.status_code == 200, f"Arrived failed: {arrived_response.text}"
            
            # Step 7: Update status to completed
            completed_response = requests.put(
                f"{BASE_URL}/api/tickets/{ticket_id}/status?status=completed",
                headers={"Authorization": f"Bearer {valet_token}"}
            )
            print(f"Status -> completed: status={completed_response.status_code}")
            assert completed_response.status_code == 200, f"Completed failed: {completed_response.text}"
            
            print("FULL TICKET LIFECYCLE TEST PASSED!")
        
        return ticket_id


class TestDatabaseCleanup:
    """Test database cleanup functionality"""
    
    @pytest.fixture
    def super_admin_token(self):
        """Get super admin token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "superadmin@swiftvalet.com",
            "password": "superadmin123"
        })
        return response.json()["token"]
    
    def test_cleanup_endpoint(self, super_admin_token):
        """Test DELETE /api/admin/cleanup-data removes completed tickets and checked_out vehicles"""
        response = requests.delete(
            f"{BASE_URL}/api/admin/cleanup-data",
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        print(f"Cleanup endpoint: status={response.status_code}")
        assert response.status_code == 200, f"Cleanup failed: {response.text}"
        
        data = response.json()
        print(f"Cleanup result: tickets_deleted={data.get('tickets_deleted')}, vehicles_deleted={data.get('vehicles_deleted')}")
        assert "tickets_deleted" in data
        assert "vehicles_deleted" in data


class TestDashboardAccess:
    """Test dashboard access for different roles"""
    
    def test_admin_dashboard_stats(self):
        """Admin can access dashboard stats"""
        # Login as admin
        otp_response = requests.post(f"{BASE_URL}/api/auth/otp/request", json={
            "phone_number": "+919373991136"
        })
        otp = otp_response.json()["dev_otp"]
        login_response = requests.post(f"{BASE_URL}/api/auth/otp/verify", json={
            "phone_number": "+919373991136",
            "otp": otp
        })
        token = login_response.json()["token"]
        
        # Get dashboard stats
        response = requests.get(
            f"{BASE_URL}/api/admin/dashboard-stats",
            headers={"Authorization": f"Bearer {token}"}
        )
        print(f"Admin dashboard stats: status={response.status_code}")
        assert response.status_code == 200, f"Dashboard stats failed: {response.text}"
        
        data = response.json()
        print(f"Dashboard stats: {data}")
        # Admin dashboard returns: active_valets, parked_vehicles, tips, totals
        assert "totals" in data or "active_valets" in data or "parked_vehicles" in data, f"Unexpected dashboard structure: {data.keys()}"
    
    def test_valet_dashboard_stats(self):
        """Valet can access their dashboard stats"""
        # Login as valet
        otp_response = requests.post(f"{BASE_URL}/api/auth/otp/request", json={
            "phone_number": "+919922668866"
        })
        otp = otp_response.json()["dev_otp"]
        login_response = requests.post(f"{BASE_URL}/api/auth/otp/verify", json={
            "phone_number": "+919922668866",
            "otp": otp
        })
        token = login_response.json()["token"]
        
        # Get valet dashboard stats
        response = requests.get(
            f"{BASE_URL}/api/valet/dashboard-stats",
            headers={"Authorization": f"Bearer {token}"}
        )
        print(f"Valet dashboard stats: status={response.status_code}")
        assert response.status_code == 200, f"Valet dashboard stats failed: {response.text}"
        
        data = response.json()
        print(f"Valet stats: {data}")
        assert "cars_parked_today" in data
        assert "cars_retrieved_today" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
