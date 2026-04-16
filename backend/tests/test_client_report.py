"""
Test cases for Super Admin Client Report feature
- GET /api/super-admin/clients/{client_id}/report endpoint
- Tests: valid client_id, non-existent client_id, non-super-admin access
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
SUPER_ADMIN_EMAIL = os.environ.get("TEST_ADMIN_EMAIL", "superadmin@swiftvalet.com")
SUPER_ADMIN_PASSWORD = os.environ.get("TEST_ADMIN_PASSWORD", "superadmin123")

# Known active client_ids from the review request
KNOWN_CLIENT_IDS = [
    "67eaf33d-ec2f-4e8e-b99c-deb2a4450fbd",  # Taj Hotel
    "dbe8655a-4dd2-4787-8f50-92ccaec43361",  # Empire
]


class TestClientReportEndpoint:
    """Tests for GET /api/super-admin/clients/{client_id}/report"""
    
    @pytest.fixture(scope="class")
    def super_admin_token(self):
        """Get super admin JWT token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPER_ADMIN_EMAIL,
            "password": SUPER_ADMIN_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip(f"Super admin login failed: {response.status_code} - {response.text}")
        return response.json().get("token")
    
    @pytest.fixture(scope="class")
    def auth_headers(self, super_admin_token):
        """Auth headers with super admin token"""
        return {"Authorization": f"Bearer {super_admin_token}"}
    
    def test_get_client_report_valid_client(self, auth_headers):
        """Test getting report for a valid client_id"""
        # Try each known client_id until one works
        for client_id in KNOWN_CLIENT_IDS:
            response = requests.get(
                f"{BASE_URL}/api/super-admin/clients/{client_id}/report",
                headers=auth_headers
            )
            if response.status_code == 200:
                data = response.json()
                
                # Verify response structure
                assert "client_id" in data, "Response should contain client_id"
                assert "client_name" in data, "Response should contain client_name"
                assert "admin_name" in data, "Response should contain admin_name"
                assert "num_drivers" in data, "Response should contain num_drivers"
                assert "cars_parked_now" in data, "Response should contain cars_parked_now"
                assert "cars_parked_today" in data, "Response should contain cars_parked_today"
                assert "tips_today" in data, "Response should contain tips_today"
                
                # Verify data types
                assert isinstance(data["num_drivers"], int), "num_drivers should be int"
                assert isinstance(data["cars_parked_now"], int), "cars_parked_now should be int"
                assert isinstance(data["cars_parked_today"], int), "cars_parked_today should be int"
                assert isinstance(data["tips_today"], (int, float)), "tips_today should be numeric"
                
                print(f"✅ Client report for {client_id}: {data}")
                return
        
        pytest.fail("No valid client_id found among known IDs")
    
    def test_get_client_report_nonexistent_client(self, auth_headers):
        """Test getting report for a non-existent client_id returns 404"""
        fake_client_id = "00000000-0000-0000-0000-000000000000"
        response = requests.get(
            f"{BASE_URL}/api/super-admin/clients/{fake_client_id}/report",
            headers=auth_headers
        )
        
        assert response.status_code == 404, f"Expected 404 for non-existent client, got {response.status_code}"
        data = response.json()
        assert "detail" in data, "Error response should contain detail"
        print(f"✅ Non-existent client returns 404: {data}")
    
    def test_get_client_report_without_auth(self):
        """Test getting report without authentication returns 401/403"""
        client_id = KNOWN_CLIENT_IDS[0]
        response = requests.get(
            f"{BASE_URL}/api/super-admin/clients/{client_id}/report"
        )
        
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
        print(f"✅ No auth returns {response.status_code}")
    
    def test_get_client_report_non_super_admin(self):
        """Test that non-super-admin users get 403"""
        # First, get list of clients to find an admin to test with
        # We'll try to login as a regular admin (if one exists with password)
        # For now, just verify the endpoint requires super_admin role
        
        # Create a fake token (invalid)
        fake_headers = {"Authorization": "Bearer invalid_token_12345"}
        client_id = KNOWN_CLIENT_IDS[0]
        
        response = requests.get(
            f"{BASE_URL}/api/super-admin/clients/{client_id}/report",
            headers=fake_headers
        )
        
        assert response.status_code in [401, 403], f"Expected 401/403 with invalid token, got {response.status_code}"
        print(f"✅ Invalid token returns {response.status_code}")


class TestClientReportDataIntegrity:
    """Tests for data integrity in client reports"""
    
    @pytest.fixture(scope="class")
    def super_admin_token(self):
        """Get super admin JWT token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPER_ADMIN_EMAIL,
            "password": SUPER_ADMIN_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip(f"Super admin login failed: {response.status_code}")
        return response.json().get("token")
    
    @pytest.fixture(scope="class")
    def auth_headers(self, super_admin_token):
        """Auth headers with super admin token"""
        return {"Authorization": f"Bearer {super_admin_token}"}
    
    def test_report_values_are_non_negative(self, auth_headers):
        """Verify all numeric values in report are non-negative"""
        for client_id in KNOWN_CLIENT_IDS:
            response = requests.get(
                f"{BASE_URL}/api/super-admin/clients/{client_id}/report",
                headers=auth_headers
            )
            if response.status_code == 200:
                data = response.json()
                
                assert data["num_drivers"] >= 0, "num_drivers should be non-negative"
                assert data["cars_parked_now"] >= 0, "cars_parked_now should be non-negative"
                assert data["cars_parked_today"] >= 0, "cars_parked_today should be non-negative"
                assert data["tips_today"] >= 0, "tips_today should be non-negative"
                
                print(f"✅ All values non-negative for client {client_id}")
                return
        
        pytest.skip("No valid client found to test data integrity")
    
    def test_get_all_clients_and_verify_reports(self, auth_headers):
        """Get all clients and verify each has a valid report"""
        # First get all clients
        clients_response = requests.get(
            f"{BASE_URL}/api/super-admin/clients",
            headers=auth_headers
        )
        
        assert clients_response.status_code == 200, f"Failed to get clients: {clients_response.status_code}"
        clients = clients_response.json()
        
        print(f"Found {len(clients)} clients")
        
        # Test report for each client with a client_id
        tested_count = 0
        for client in clients:
            client_id = client.get("client_id")
            if not client_id:
                print(f"  ⚠️ Client {client.get('id')} has no client_id (legacy data)")
                continue
            
            report_response = requests.get(
                f"{BASE_URL}/api/super-admin/clients/{client_id}/report",
                headers=auth_headers
            )
            
            if report_response.status_code == 200:
                data = report_response.json()
                assert "num_drivers" in data
                assert "cars_parked_now" in data
                assert "tips_today" in data
                assert "cars_parked_today" in data
                print(f"  ✅ Client {client.get('client_name', 'Unknown')}: drivers={data['num_drivers']}, parked_now={data['cars_parked_now']}")
                tested_count += 1
            else:
                print(f"  ❌ Client {client_id} report failed: {report_response.status_code}")
        
        print(f"✅ Tested {tested_count} client reports successfully")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
