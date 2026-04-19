"""
Test suite for Valet Guys refactored backend.
Tests all modular routers: auth, vehicles, tickets, admin, super_admin, public.
"""
import pytest
import requests
import os
import uuid
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
SUPER_ADMIN_EMAIL = os.environ.get("TEST_ADMIN_EMAIL", "superadmin@swiftvalet.com")
SUPER_ADMIN_PASSWORD = os.environ.get("TEST_ADMIN_PASSWORD", "superadmin123")


class TestSuperAdminAuth:
    """Super Admin authentication and routes"""
    
    def test_super_admin_login(self):
        """POST /api/auth/login - Super admin login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPER_ADMIN_EMAIL,
            "password": SUPER_ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert "user" in data
        assert data["user"]["email"] == SUPER_ADMIN_EMAIL
        assert data["user"]["role"] == "super_admin"
        print(f"✓ Super admin login successful, token received")
    
    def test_auth_me_returns_user_data(self):
        """GET /api/auth/me - Returns user data with correct fields"""
        # First login
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPER_ADMIN_EMAIL,
            "password": SUPER_ADMIN_PASSWORD
        })
        token = login_resp.json()["token"]
        
        # Get user data
        response = requests.get(f"{BASE_URL}/api/auth/me", headers={
            "Authorization": f"Bearer {token}"
        })
        assert response.status_code == 200, f"Auth/me failed: {response.text}"
        data = response.json()
        
        # Verify required fields
        assert "id" in data
        assert "email" in data
        assert "name" in data
        assert "role" in data
        assert data["email"] == SUPER_ADMIN_EMAIL
        assert data["role"] == "super_admin"
        print(f"✓ GET /api/auth/me returns correct user data")


class TestSuperAdminRoutes:
    """Super Admin specific routes"""
    
    @pytest.fixture
    def super_admin_token(self):
        """Get super admin token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPER_ADMIN_EMAIL,
            "password": SUPER_ADMIN_PASSWORD
        })
        return response.json()["token"]
    
    def test_get_clients(self, super_admin_token):
        """GET /api/super-admin/clients - Returns clients list"""
        response = requests.get(f"{BASE_URL}/api/super-admin/clients", headers={
            "Authorization": f"Bearer {super_admin_token}"
        })
        assert response.status_code == 200, f"Get clients failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ GET /api/super-admin/clients returns {len(data)} clients")
    
    def test_get_analytics(self, super_admin_token):
        """GET /api/super-admin/analytics - Returns analytics object"""
        response = requests.get(f"{BASE_URL}/api/super-admin/analytics", headers={
            "Authorization": f"Bearer {super_admin_token}"
        })
        assert response.status_code == 200, f"Get analytics failed: {response.text}"
        data = response.json()
        
        # Verify analytics fields
        assert "total_clients" in data
        assert "cars_parked_now" in data
        assert "total_tips_today" in data
        assert "total_vehicles" in data
        assert "total_valets" in data
        assert "tickets_today" in data
        print(f"✓ GET /api/super-admin/analytics returns analytics object")
    
    def test_create_admin(self, super_admin_token):
        """POST /api/super-admin/admins - Creates new admin"""
        unique_id = str(uuid.uuid4())[:8]
        admin_data = {
            "email": f"test_admin_{unique_id}@test.com",
            "name": f"Test Admin {unique_id}",
            "phone_number": f"+1555{unique_id[:7].replace('-', '')}",
            "client_name": f"Test Client {unique_id}"
        }
        
        response = requests.post(f"{BASE_URL}/api/super-admin/admins", 
            json=admin_data,
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        assert response.status_code == 200, f"Create admin failed: {response.text}"
        data = response.json()
        assert "user" in data
        assert data["user"]["email"] == admin_data["email"]
        assert data["user"]["name"] == admin_data["name"]
        print(f"✓ POST /api/super-admin/admins creates admin: {admin_data['email']}")
        return data["user"]


class TestOTPAuth:
    """OTP authentication flow for admin/valet"""
    
    @pytest.fixture
    def super_admin_token(self):
        """Get super admin token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPER_ADMIN_EMAIL,
            "password": SUPER_ADMIN_PASSWORD
        })
        return response.json()["token"]
    
    def test_otp_request_and_verify(self, super_admin_token):
        """POST /api/auth/otp/request and /api/auth/otp/verify"""
        # First create an admin with a phone number
        unique_id = str(uuid.uuid4())[:8]
        admin_data = {
            "email": f"otp_test_{unique_id}@test.com",
            "name": f"OTP Test Admin {unique_id}",
            "phone_number": f"+1666{unique_id[:7].replace('-', '')}",
            "client_name": f"OTP Test Client {unique_id}"
        }
        
        create_resp = requests.post(f"{BASE_URL}/api/super-admin/admins", 
            json=admin_data,
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        assert create_resp.status_code == 200, f"Create admin failed: {create_resp.text}"
        
        # Request OTP
        otp_request_resp = requests.post(f"{BASE_URL}/api/auth/otp/request", json={
            "phone_number": admin_data["phone_number"]
        })
        assert otp_request_resp.status_code == 200, f"OTP request failed: {otp_request_resp.text}"
        otp_data = otp_request_resp.json()
        assert "dev_otp" in otp_data, "dev_otp not in response"
        dev_otp = otp_data["dev_otp"]
        print(f"✓ POST /api/auth/otp/request sent OTP: {dev_otp}")
        
        # Verify OTP
        verify_resp = requests.post(f"{BASE_URL}/api/auth/otp/verify", json={
            "phone_number": admin_data["phone_number"],
            "otp": dev_otp
        })
        assert verify_resp.status_code == 200, f"OTP verify failed: {verify_resp.text}"
        verify_data = verify_resp.json()
        assert "token" in verify_data
        assert "user" in verify_data
        assert verify_data["user"]["email"] == admin_data["email"]
        print(f"✓ POST /api/auth/otp/verify returns token for {admin_data['email']}")


class TestAdminRoutes:
    """Admin management routes"""
    
    @pytest.fixture
    def admin_session(self):
        """Create admin and get token via OTP"""
        # Get super admin token
        sa_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPER_ADMIN_EMAIL,
            "password": SUPER_ADMIN_PASSWORD
        })
        sa_token = sa_resp.json()["token"]
        
        # Create admin
        unique_id = str(uuid.uuid4())[:8]
        admin_data = {
            "email": f"admin_test_{unique_id}@test.com",
            "name": f"Admin Test {unique_id}",
            "phone_number": f"+1777{unique_id[:7].replace('-', '')}",
            "client_name": f"Admin Test Client {unique_id}"
        }
        
        create_resp = requests.post(f"{BASE_URL}/api/super-admin/admins", 
            json=admin_data,
            headers={"Authorization": f"Bearer {sa_token}"}
        )
        admin_user = create_resp.json()["user"]
        
        # Get OTP and login
        otp_resp = requests.post(f"{BASE_URL}/api/auth/otp/request", json={
            "phone_number": admin_data["phone_number"]
        })
        dev_otp = otp_resp.json()["dev_otp"]
        
        verify_resp = requests.post(f"{BASE_URL}/api/auth/otp/verify", json={
            "phone_number": admin_data["phone_number"],
            "otp": dev_otp
        })
        
        return {
            "token": verify_resp.json()["token"],
            "user": admin_user,
            "phone": admin_data["phone_number"]
        }
    
    def test_get_valets(self, admin_session):
        """GET /api/admin/valets - Returns valets list"""
        response = requests.get(f"{BASE_URL}/api/admin/valets", headers={
            "Authorization": f"Bearer {admin_session['token']}"
        })
        assert response.status_code == 200, f"Get valets failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ GET /api/admin/valets returns {len(data)} valets")
    
    def test_create_valet(self, admin_session):
        """POST /api/admin/valets - Creates a valet"""
        unique_id = str(uuid.uuid4())[:8]
        valet_data = {
            "email": f"valet_test_{unique_id}@test.com",
            "name": f"Valet Test {unique_id}",
            "phone_number": f"+1888{unique_id[:7].replace('-', '')}",
            "driver_license_number": f"DL{unique_id}"
        }
        
        response = requests.post(f"{BASE_URL}/api/admin/valets", 
            json=valet_data,
            headers={"Authorization": f"Bearer {admin_session['token']}"}
        )
        assert response.status_code == 200, f"Create valet failed: {response.text}"
        data = response.json()
        assert "user" in data
        assert data["user"]["email"] == valet_data["email"]
        print(f"✓ POST /api/admin/valets creates valet: {valet_data['email']}")
        return data["user"]
    
    def test_toggle_valet_online(self, admin_session):
        """PUT /api/admin/valets/{valet_id}/toggle-online - Toggles valet online status"""
        # First create a valet
        unique_id = str(uuid.uuid4())[:8]
        valet_data = {
            "email": f"toggle_valet_{unique_id}@test.com",
            "name": f"Toggle Valet {unique_id}",
            "phone_number": f"+1999{unique_id[:7].replace('-', '')}",
        }
        
        create_resp = requests.post(f"{BASE_URL}/api/admin/valets", 
            json=valet_data,
            headers={"Authorization": f"Bearer {admin_session['token']}"}
        )
        valet_id = create_resp.json()["user"]["id"]
        
        # Toggle online
        response = requests.put(f"{BASE_URL}/api/admin/valets/{valet_id}/toggle-online", 
            headers={"Authorization": f"Bearer {admin_session['token']}"}
        )
        assert response.status_code == 200, f"Toggle online failed: {response.text}"
        data = response.json()
        assert "is_online" in data
        assert data["is_online"] == True  # First toggle should set to True
        print(f"✓ PUT /api/admin/valets/{valet_id}/toggle-online toggles status to {data['is_online']}")
    
    def test_admin_dashboard_stats(self, admin_session):
        """GET /api/admin/dashboard-stats - Returns admin dashboard stats"""
        response = requests.get(f"{BASE_URL}/api/admin/dashboard-stats", headers={
            "Authorization": f"Bearer {admin_session['token']}"
        })
        assert response.status_code == 200, f"Dashboard stats failed: {response.text}"
        data = response.json()
        assert "active_valets" in data
        assert "parked_vehicles" in data
        assert "totals" in data
        print(f"✓ GET /api/admin/dashboard-stats returns dashboard data")
    
    def test_admin_reporting(self, admin_session):
        """GET /api/admin/reporting - Returns reporting data"""
        response = requests.get(f"{BASE_URL}/api/admin/reporting", headers={
            "Authorization": f"Bearer {admin_session['token']}"
        })
        assert response.status_code == 200, f"Reporting failed: {response.text}"
        data = response.json()
        assert "summary" in data
        assert "leaderboard" in data
        assert "hourly_volume" in data
        assert "financial" in data
        print(f"✓ GET /api/admin/reporting returns reporting data")


class TestVehicleRoutes:
    """Vehicle CRUD routes"""
    
    @pytest.fixture
    def valet_session(self):
        """Create valet and get token via OTP"""
        # Get super admin token
        sa_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPER_ADMIN_EMAIL,
            "password": SUPER_ADMIN_PASSWORD
        })
        sa_token = sa_resp.json()["token"]
        
        # Create admin first
        unique_id = str(uuid.uuid4())[:8]
        admin_data = {
            "email": f"veh_admin_{unique_id}@test.com",
            "name": f"Vehicle Admin {unique_id}",
            "phone_number": f"+1222{unique_id[:7].replace('-', '')}",
            "client_name": f"Vehicle Test Client {unique_id}"
        }
        
        create_admin_resp = requests.post(f"{BASE_URL}/api/super-admin/admins", 
            json=admin_data,
            headers={"Authorization": f"Bearer {sa_token}"}
        )
        admin_user = create_admin_resp.json()["user"]
        
        # Login as admin via OTP
        otp_resp = requests.post(f"{BASE_URL}/api/auth/otp/request", json={
            "phone_number": admin_data["phone_number"]
        })
        dev_otp = otp_resp.json()["dev_otp"]
        
        verify_resp = requests.post(f"{BASE_URL}/api/auth/otp/verify", json={
            "phone_number": admin_data["phone_number"],
            "otp": dev_otp
        })
        admin_token = verify_resp.json()["token"]
        
        # Create valet
        valet_data = {
            "email": f"veh_valet_{unique_id}@test.com",
            "name": f"Vehicle Valet {unique_id}",
            "phone_number": f"+1333{unique_id[:7].replace('-', '')}",
        }
        
        create_valet_resp = requests.post(f"{BASE_URL}/api/admin/valets", 
            json=valet_data,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        valet_user = create_valet_resp.json()["user"]
        
        # Toggle valet online
        requests.put(f"{BASE_URL}/api/admin/valets/{valet_user['id']}/toggle-online", 
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        # Login as valet via OTP
        otp_resp2 = requests.post(f"{BASE_URL}/api/auth/otp/request", json={
            "phone_number": valet_data["phone_number"]
        })
        dev_otp2 = otp_resp2.json()["dev_otp"]
        
        verify_resp2 = requests.post(f"{BASE_URL}/api/auth/otp/verify", json={
            "phone_number": valet_data["phone_number"],
            "otp": dev_otp2
        })
        
        return {
            "token": verify_resp2.json()["token"],
            "user": valet_user,
            "admin_token": admin_token
        }
    
    def test_create_vehicle(self, valet_session):
        """POST /api/vehicles - Creates a vehicle"""
        unique_id = str(uuid.uuid4())[:8]
        vehicle_data = {
            "phone_number": f"+1444{unique_id[:7].replace('-', '')}",
            "license_plate": f"TEST{unique_id[:6].upper()}",
            "tag_number": f"T{unique_id[:4]}",
            "zone_label": "Zone A"
        }
        
        response = requests.post(f"{BASE_URL}/api/vehicles", 
            json=vehicle_data,
            headers={"Authorization": f"Bearer {valet_session['token']}"}
        )
        assert response.status_code == 200, f"Create vehicle failed: {response.text}"
        data = response.json()
        assert "vehicle" in data
        assert data["vehicle"]["license_plate"] == vehicle_data["license_plate"]
        print(f"✓ POST /api/vehicles creates vehicle: {vehicle_data['license_plate']}")
        return data["vehicle"]
    
    def test_get_vehicles(self, valet_session):
        """GET /api/vehicles - Returns vehicle list"""
        response = requests.get(f"{BASE_URL}/api/vehicles", headers={
            "Authorization": f"Bearer {valet_session['token']}"
        })
        assert response.status_code == 200, f"Get vehicles failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ GET /api/vehicles returns {len(data)} vehicles")
    
    def test_lookup_vehicle_by_phone(self, valet_session):
        """GET /api/vehicles/lookup - Looks up vehicle by phone"""
        # First create a vehicle
        unique_id = str(uuid.uuid4())[:8]
        phone = f"+1555{unique_id[:7].replace('-', '')}"
        vehicle_data = {
            "phone_number": phone,
            "license_plate": f"LOOK{unique_id[:6].upper()}",
            "tag_number": f"L{unique_id[:4]}",
        }
        
        requests.post(f"{BASE_URL}/api/vehicles", 
            json=vehicle_data,
            headers={"Authorization": f"Bearer {valet_session['token']}"}
        )
        
        # Lookup
        response = requests.get(f"{BASE_URL}/api/vehicles/lookup", 
            params={"phone": phone},
            headers={"Authorization": f"Bearer {valet_session['token']}"}
        )
        assert response.status_code == 200, f"Lookup failed: {response.text}"
        data = response.json()
        assert "vehicle" in data
        assert data["vehicle"]["license_plate"] == vehicle_data["license_plate"]
        print(f"✓ GET /api/vehicles/lookup finds vehicle by phone")


class TestTicketRoutes:
    """Ticket lifecycle routes"""
    
    @pytest.fixture
    def valet_with_vehicle(self):
        """Create valet with a parked vehicle"""
        # Get super admin token
        sa_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPER_ADMIN_EMAIL,
            "password": SUPER_ADMIN_PASSWORD
        })
        sa_token = sa_resp.json()["token"]
        
        # Create admin
        unique_id = str(uuid.uuid4())[:8]
        admin_data = {
            "email": f"tkt_admin_{unique_id}@test.com",
            "name": f"Ticket Admin {unique_id}",
            "phone_number": f"+1666{unique_id[:7].replace('-', '')}",
            "client_name": f"Ticket Test Client {unique_id}"
        }
        
        create_admin_resp = requests.post(f"{BASE_URL}/api/super-admin/admins", 
            json=admin_data,
            headers={"Authorization": f"Bearer {sa_token}"}
        )
        
        # Login as admin
        otp_resp = requests.post(f"{BASE_URL}/api/auth/otp/request", json={
            "phone_number": admin_data["phone_number"]
        })
        dev_otp = otp_resp.json()["dev_otp"]
        
        verify_resp = requests.post(f"{BASE_URL}/api/auth/otp/verify", json={
            "phone_number": admin_data["phone_number"],
            "otp": dev_otp
        })
        admin_token = verify_resp.json()["token"]
        
        # Create valet
        valet_data = {
            "email": f"tkt_valet_{unique_id}@test.com",
            "name": f"Ticket Valet {unique_id}",
            "phone_number": f"+1777{unique_id[:7].replace('-', '')}",
        }
        
        create_valet_resp = requests.post(f"{BASE_URL}/api/admin/valets", 
            json=valet_data,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        valet_user = create_valet_resp.json()["user"]
        
        # Toggle valet online
        requests.put(f"{BASE_URL}/api/admin/valets/{valet_user['id']}/toggle-online", 
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        # Login as valet
        otp_resp2 = requests.post(f"{BASE_URL}/api/auth/otp/request", json={
            "phone_number": valet_data["phone_number"]
        })
        dev_otp2 = otp_resp2.json()["dev_otp"]
        
        verify_resp2 = requests.post(f"{BASE_URL}/api/auth/otp/verify", json={
            "phone_number": valet_data["phone_number"],
            "otp": dev_otp2
        })
        valet_token = verify_resp2.json()["token"]
        
        # Create vehicle
        customer_phone = f"+1888{unique_id[:7].replace('-', '')}"
        vehicle_data = {
            "phone_number": customer_phone,
            "license_plate": f"TKT{unique_id[:6].upper()}",
            "tag_number": f"TK{unique_id[:4]}",
        }
        
        create_vehicle_resp = requests.post(f"{BASE_URL}/api/vehicles", 
            json=vehicle_data,
            headers={"Authorization": f"Bearer {valet_token}"}
        )
        vehicle = create_vehicle_resp.json()["vehicle"]
        
        return {
            "valet_token": valet_token,
            "admin_token": admin_token,
            "vehicle": vehicle,
            "customer_phone": customer_phone
        }
    
    def test_create_retrieval_ticket(self, valet_with_vehicle):
        """POST /api/tickets/retrieve - Creates a retrieval ticket"""
        response = requests.post(f"{BASE_URL}/api/tickets/retrieve", 
            json={"phone_number": valet_with_vehicle["customer_phone"]},
            headers={"Authorization": f"Bearer {valet_with_vehicle['valet_token']}"}
        )
        assert response.status_code == 200, f"Create ticket failed: {response.text}"
        data = response.json()
        assert "ticket" in data
        assert data["ticket"]["vehicle_id"] == valet_with_vehicle["vehicle"]["id"]
        print(f"✓ POST /api/tickets/retrieve creates ticket")
        return data["ticket"]
    
    def test_get_tickets(self, valet_with_vehicle):
        """GET /api/tickets - Returns ticket list"""
        response = requests.get(f"{BASE_URL}/api/tickets", headers={
            "Authorization": f"Bearer {valet_with_vehicle['valet_token']}"
        })
        assert response.status_code == 200, f"Get tickets failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ GET /api/tickets returns {len(data)} tickets")
    
    def test_claim_and_update_ticket_status(self, valet_with_vehicle):
        """PUT /api/tickets/{ticket_id}/claim and /api/tickets/{ticket_id}/status"""
        # Create a ticket via public endpoint first
        confirm_resp = requests.post(f"{BASE_URL}/api/retrieve/{valet_with_vehicle['vehicle']['id']}/confirm")
        assert confirm_resp.status_code == 200, f"Confirm retrieval failed: {confirm_resp.text}"
        
        # Get tickets to find the open one
        tickets_resp = requests.get(f"{BASE_URL}/api/tickets", headers={
            "Authorization": f"Bearer {valet_with_vehicle['valet_token']}"
        })
        tickets = tickets_resp.json()
        open_ticket = next((t for t in tickets if t["status"] == "open" and t["vehicle_id"] == valet_with_vehicle["vehicle"]["id"]), None)
        
        if open_ticket:
            # Claim ticket
            claim_resp = requests.put(f"{BASE_URL}/api/tickets/{open_ticket['id']}/claim", headers={
                "Authorization": f"Bearer {valet_with_vehicle['valet_token']}"
            })
            assert claim_resp.status_code == 200, f"Claim failed: {claim_resp.text}"
            print(f"✓ PUT /api/tickets/{open_ticket['id']}/claim claims ticket")
            
            # Update status to arrived
            status_resp = requests.put(f"{BASE_URL}/api/tickets/{open_ticket['id']}/status", 
                params={"status": "arrived"},
                headers={"Authorization": f"Bearer {valet_with_vehicle['valet_token']}"}
            )
            assert status_resp.status_code == 200, f"Status update failed: {status_resp.text}"
            print(f"✓ PUT /api/tickets/{open_ticket['id']}/status updates to arrived")
        else:
            print("⚠ No open ticket found to claim (may already be claimed)")


class TestPublicRoutes:
    """Public routes (no auth required)"""
    
    @pytest.fixture
    def parked_vehicle(self):
        """Create a parked vehicle for public tests"""
        # Get super admin token
        sa_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPER_ADMIN_EMAIL,
            "password": SUPER_ADMIN_PASSWORD
        })
        sa_token = sa_resp.json()["token"]
        
        # Create admin
        unique_id = str(uuid.uuid4())[:8]
        admin_data = {
            "email": f"pub_admin_{unique_id}@test.com",
            "name": f"Public Admin {unique_id}",
            "phone_number": f"+1999{unique_id[:7].replace('-', '')}",
            "client_name": f"Public Test Client {unique_id}"
        }
        
        requests.post(f"{BASE_URL}/api/super-admin/admins", 
            json=admin_data,
            headers={"Authorization": f"Bearer {sa_token}"}
        )
        
        # Login as admin
        otp_resp = requests.post(f"{BASE_URL}/api/auth/otp/request", json={
            "phone_number": admin_data["phone_number"]
        })
        dev_otp = otp_resp.json()["dev_otp"]
        
        verify_resp = requests.post(f"{BASE_URL}/api/auth/otp/verify", json={
            "phone_number": admin_data["phone_number"],
            "otp": dev_otp
        })
        admin_token = verify_resp.json()["token"]
        
        # Create valet
        valet_data = {
            "email": f"pub_valet_{unique_id}@test.com",
            "name": f"Public Valet {unique_id}",
            "phone_number": f"+1000{unique_id[:7].replace('-', '')}",
        }
        
        create_valet_resp = requests.post(f"{BASE_URL}/api/admin/valets", 
            json=valet_data,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        valet_user = create_valet_resp.json()["user"]
        
        # Toggle valet online
        requests.put(f"{BASE_URL}/api/admin/valets/{valet_user['id']}/toggle-online", 
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        # Login as valet
        otp_resp2 = requests.post(f"{BASE_URL}/api/auth/otp/request", json={
            "phone_number": valet_data["phone_number"]
        })
        dev_otp2 = otp_resp2.json()["dev_otp"]
        
        verify_resp2 = requests.post(f"{BASE_URL}/api/auth/otp/verify", json={
            "phone_number": valet_data["phone_number"],
            "otp": dev_otp2
        })
        valet_token = verify_resp2.json()["token"]
        
        # Create vehicle
        customer_phone = f"+1111{unique_id[:7].replace('-', '')}"
        vehicle_data = {
            "phone_number": customer_phone,
            "license_plate": f"PUB{unique_id[:6].upper()}",
        }
        
        create_vehicle_resp = requests.post(f"{BASE_URL}/api/vehicles", 
            json=vehicle_data,
            headers={"Authorization": f"Bearer {valet_token}"}
        )
        vehicle = create_vehicle_resp.json()["vehicle"]
        
        return {
            "vehicle": vehicle,
            "customer_phone": customer_phone,
            "client_name": admin_data["client_name"]
        }
    
    def test_get_vehicle_for_retrieval(self, parked_vehicle):
        """GET /api/retrieve/{vehicle_id} - Returns vehicle retrieval info (public, no auth)"""
        response = requests.get(f"{BASE_URL}/api/retrieve/{parked_vehicle['vehicle']['id']}")
        assert response.status_code == 200, f"Get retrieval info failed: {response.text}"
        data = response.json()
        
        assert "vehicle_id" in data
        assert "license_plate" in data
        assert "client_name" in data
        assert data["license_plate"] == parked_vehicle["vehicle"]["license_plate"]
        print(f"✓ GET /api/retrieve/{parked_vehicle['vehicle']['id']} returns vehicle info (no auth)")
    
    def test_confirm_retrieval(self, parked_vehicle):
        """POST /api/retrieve/{vehicle_id}/confirm - Confirms retrieval (public, no auth)"""
        response = requests.post(f"{BASE_URL}/api/retrieve/{parked_vehicle['vehicle']['id']}/confirm")
        assert response.status_code == 200, f"Confirm retrieval failed: {response.text}"
        data = response.json()
        
        assert "status" in data
        assert "message" in data
        print(f"✓ POST /api/retrieve/{parked_vehicle['vehicle']['id']}/confirm creates ticket (no auth)")
    
    def test_get_vapid_key(self):
        """GET /api/push/vapid-key - Returns VAPID key"""
        response = requests.get(f"{BASE_URL}/api/push/vapid-key")
        assert response.status_code == 200, f"Get VAPID key failed: {response.text}"
        data = response.json()
        assert "public_key" in data
        assert len(data["public_key"]) > 0
        print(f"✓ GET /api/push/vapid-key returns VAPID public key")


class TestVehicleCheckout:
    """Vehicle checkout routes"""
    
    @pytest.fixture
    def vehicle_for_checkout(self):
        """Create a vehicle ready for checkout"""
        # Get super admin token
        sa_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPER_ADMIN_EMAIL,
            "password": SUPER_ADMIN_PASSWORD
        })
        sa_token = sa_resp.json()["token"]
        
        # Create admin
        unique_id = str(uuid.uuid4())[:8]
        admin_data = {
            "email": f"chk_admin_{unique_id}@test.com",
            "name": f"Checkout Admin {unique_id}",
            "phone_number": f"+1234{unique_id[:7].replace('-', '')}",
            "client_name": f"Checkout Test Client {unique_id}"
        }
        
        requests.post(f"{BASE_URL}/api/super-admin/admins", 
            json=admin_data,
            headers={"Authorization": f"Bearer {sa_token}"}
        )
        
        # Login as admin
        otp_resp = requests.post(f"{BASE_URL}/api/auth/otp/request", json={
            "phone_number": admin_data["phone_number"]
        })
        dev_otp = otp_resp.json()["dev_otp"]
        
        verify_resp = requests.post(f"{BASE_URL}/api/auth/otp/verify", json={
            "phone_number": admin_data["phone_number"],
            "otp": dev_otp
        })
        admin_token = verify_resp.json()["token"]
        
        # Create valet
        valet_data = {
            "email": f"chk_valet_{unique_id}@test.com",
            "name": f"Checkout Valet {unique_id}",
            "phone_number": f"+1567{unique_id[:7].replace('-', '')}",
        }
        
        create_valet_resp = requests.post(f"{BASE_URL}/api/admin/valets", 
            json=valet_data,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        valet_user = create_valet_resp.json()["user"]
        
        # Toggle valet online
        requests.put(f"{BASE_URL}/api/admin/valets/{valet_user['id']}/toggle-online", 
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        # Login as valet
        otp_resp2 = requests.post(f"{BASE_URL}/api/auth/otp/request", json={
            "phone_number": valet_data["phone_number"]
        })
        dev_otp2 = otp_resp2.json()["dev_otp"]
        
        verify_resp2 = requests.post(f"{BASE_URL}/api/auth/otp/verify", json={
            "phone_number": valet_data["phone_number"],
            "otp": dev_otp2
        })
        valet_token = verify_resp2.json()["token"]
        
        # Create vehicle
        customer_phone = f"+1890{unique_id[:7].replace('-', '')}"
        vehicle_data = {
            "phone_number": customer_phone,
            "license_plate": f"CHK{unique_id[:6].upper()}",
        }
        
        create_vehicle_resp = requests.post(f"{BASE_URL}/api/vehicles", 
            json=vehicle_data,
            headers={"Authorization": f"Bearer {valet_token}"}
        )
        vehicle = create_vehicle_resp.json()["vehicle"]
        
        return {
            "vehicle": vehicle,
            "admin_token": admin_token,
            "valet_token": valet_token,
            "client_name": admin_data["client_name"]
        }
    
    def test_admin_checkout_vehicle(self, vehicle_for_checkout):
        """POST /api/admin/vehicles/{vehicle_id}/checkout - Checks out a vehicle"""
        response = requests.post(
            f"{BASE_URL}/api/admin/vehicles/{vehicle_for_checkout['vehicle']['id']}/checkout",
            headers={"Authorization": f"Bearer {vehicle_for_checkout['admin_token']}"}
        )
        assert response.status_code == 200, f"Checkout failed: {response.text}"
        data = response.json()
        assert "message" in data
        assert "vehicle_id" in data
        print(f"✓ POST /api/admin/vehicles/{vehicle_for_checkout['vehicle']['id']}/checkout checks out vehicle")


class TestValetDashboard:
    """Valet dashboard stats"""
    
    @pytest.fixture
    def valet_token(self):
        """Create valet and get token"""
        # Get super admin token
        sa_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPER_ADMIN_EMAIL,
            "password": SUPER_ADMIN_PASSWORD
        })
        sa_token = sa_resp.json()["token"]
        
        # Create admin
        unique_id = str(uuid.uuid4())[:8]
        admin_data = {
            "email": f"vds_admin_{unique_id}@test.com",
            "name": f"VDS Admin {unique_id}",
            "phone_number": f"+1321{unique_id[:7].replace('-', '')}",
            "client_name": f"VDS Test Client {unique_id}"
        }
        
        requests.post(f"{BASE_URL}/api/super-admin/admins", 
            json=admin_data,
            headers={"Authorization": f"Bearer {sa_token}"}
        )
        
        # Login as admin
        otp_resp = requests.post(f"{BASE_URL}/api/auth/otp/request", json={
            "phone_number": admin_data["phone_number"]
        })
        dev_otp = otp_resp.json()["dev_otp"]
        
        verify_resp = requests.post(f"{BASE_URL}/api/auth/otp/verify", json={
            "phone_number": admin_data["phone_number"],
            "otp": dev_otp
        })
        admin_token = verify_resp.json()["token"]
        
        # Create valet
        valet_data = {
            "email": f"vds_valet_{unique_id}@test.com",
            "name": f"VDS Valet {unique_id}",
            "phone_number": f"+1654{unique_id[:7].replace('-', '')}",
        }
        
        create_valet_resp = requests.post(f"{BASE_URL}/api/admin/valets", 
            json=valet_data,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        valet_user = create_valet_resp.json()["user"]
        
        # Toggle valet online
        requests.put(f"{BASE_URL}/api/admin/valets/{valet_user['id']}/toggle-online", 
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        # Login as valet
        otp_resp2 = requests.post(f"{BASE_URL}/api/auth/otp/request", json={
            "phone_number": valet_data["phone_number"]
        })
        dev_otp2 = otp_resp2.json()["dev_otp"]
        
        verify_resp2 = requests.post(f"{BASE_URL}/api/auth/otp/verify", json={
            "phone_number": valet_data["phone_number"],
            "otp": dev_otp2
        })
        
        return verify_resp2.json()["token"]
    
    def test_valet_dashboard_stats(self, valet_token):
        """GET /api/valet/dashboard-stats - Returns valet stats"""
        response = requests.get(f"{BASE_URL}/api/valet/dashboard-stats", headers={
            "Authorization": f"Bearer {valet_token}"
        })
        assert response.status_code == 200, f"Valet stats failed: {response.text}"
        data = response.json()
        
        assert "cars_parked_today" in data
        assert "cars_retrieved_today" in data
        assert "tips_today" in data
        print(f"✓ GET /api/valet/dashboard-stats returns valet stats")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
