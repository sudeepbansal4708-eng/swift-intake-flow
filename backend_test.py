import requests
import sys
from datetime import datetime
import json
import base64
import io

class SwiftValetAPITester:
    def __init__(self, base_url="https://swift-valet-preview.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.admin_token = None
        self.valet_token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.created_vehicle_id = None
        self.created_ticket_id = None

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}"
        test_headers = {'Content-Type': 'application/json'}
        if headers:
            test_headers.update(headers)

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=test_headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=test_headers, timeout=30)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=test_headers, timeout=30)
            elif method == 'DELETE':
                response = requests.delete(url, headers=test_headers, timeout=30)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    return success, response.json() if response.text else {}
                except:
                    return success, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                print(f"Response: {response.text[:200]}")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_admin_login(self):
        """Test admin login and get token"""
        print("\n=== Testing Admin Authentication ===")
        success, response = self.run_test(
            "Admin Login",
            "POST",
            "auth/login",
            200,
            data={"email": "admin@swift.com", "password": "admin123"}
        )
        if success and 'token' in response:
            self.admin_token = response['token']
            print(f"Admin token acquired: {self.admin_token[:20]}...")
            return True
        return False

    def test_valet_login(self):
        """Test valet login and get token"""
        print("\n=== Testing Valet Authentication ===")
        success, response = self.run_test(
            "Valet Login",
            "POST",
            "auth/login",
            200,
            data={"email": "valet@swift.com", "password": "valet123"}
        )
        if success and 'token' in response:
            self.valet_token = response['token']
            print(f"Valet token acquired: {self.valet_token[:20]}...")
            return True
        return False

    def test_invalid_login(self):
        """Test invalid credentials"""
        success, response = self.run_test(
            "Invalid Login",
            "POST", 
            "auth/login",
            401,
            data={"email": "invalid@test.com", "password": "wrongpass"}
        )
        return success

    def test_get_current_user(self):
        """Test get current user info"""
        if not self.admin_token:
            return False
            
        success, response = self.run_test(
            "Get Current User (Admin)",
            "GET",
            "auth/me",
            200,
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        
        if success and response.get('role') == 'admin':
            print(f"✅ Admin user verified: {response.get('name')}")
            return True
        return False

    def test_create_vehicle(self):
        """Test vehicle creation"""
        if not self.valet_token:
            return False
            
        print("\n=== Testing Vehicle Operations ===")
        vehicle_data = {
            "phone_number": "+1234567890",
            "license_plate": "TEST-123",
            "zone_label": "Level 1, Section A",
            "gps_latitude": 37.7749,
            "gps_longitude": -122.4194
        }
        
        success, response = self.run_test(
            "Create Vehicle",
            "POST",
            "vehicles",
            200,
            data=vehicle_data,
            headers={"Authorization": f"Bearer {self.valet_token}"}
        )
        
        if success and 'vehicle' in response:
            self.created_vehicle_id = response['vehicle']['id']
            print(f"✅ Vehicle created with ID: {self.created_vehicle_id}")
            return True
        return False

    def test_upload_vehicle_photo(self):
        """Test vehicle photo upload"""
        if not self.valet_token or not self.created_vehicle_id:
            return False
            
        # Create a simple test image
        test_image_data = base64.b64encode(b"fake-image-data").decode()
        
        # Use multipart form data
        try:
            url = f"{self.api_url}/vehicles/upload-photo"
            files = {'photo': ('test.jpg', io.BytesIO(b"fake-image-data"), 'image/jpeg')}
            data = {'vehicle_id': self.created_vehicle_id}
            headers = {"Authorization": f"Bearer {self.valet_token}"}
            
            response = requests.post(url, files=files, data=data, headers=headers, timeout=30)
            success = response.status_code == 200
            
            self.tests_run += 1
            if success:
                self.tests_passed += 1
                print(f"✅ Photo Upload - Status: {response.status_code}")
                return True
            else:
                print(f"❌ Photo Upload Failed - Status: {response.status_code}")
                print(f"Response: {response.text[:200]}")
                return False
                
        except Exception as e:
            self.tests_run += 1
            print(f"❌ Photo Upload Failed - Error: {str(e)}")
            return False

    def test_get_vehicles(self):
        """Test get all vehicles"""
        if not self.valet_token:
            return False
            
        success, response = self.run_test(
            "Get Vehicles",
            "GET",
            "vehicles",
            200,
            headers={"Authorization": f"Bearer {self.valet_token}"}
        )
        
        if success and isinstance(response, list):
            print(f"✅ Retrieved {len(response)} vehicles")
            return True
        return False

    def test_create_ticket(self):
        """Test ticket creation"""
        if not self.valet_token or not self.created_vehicle_id:
            return False
            
        print("\n=== Testing Ticket Operations ===")
        success, response = self.run_test(
            "Create Ticket",
            "POST",
            f"tickets?vehicle_id={self.created_vehicle_id}",
            200,
            headers={"Authorization": f"Bearer {self.valet_token}"}
        )
        
        if success and 'id' in response:
            self.created_ticket_id = response['id']
            print(f"✅ Ticket created with ID: {self.created_ticket_id}")
            return True
        return False

    def test_get_tickets(self):
        """Test get all tickets"""
        if not self.valet_token:
            return False
            
        success, response = self.run_test(
            "Get Tickets",
            "GET",
            "tickets",
            200,
            headers={"Authorization": f"Bearer {self.valet_token}"}
        )
        
        if success and isinstance(response, list):
            print(f"✅ Retrieved {len(response)} tickets")
            return True
        return False

    def test_claim_ticket(self):
        """Test ticket claiming"""
        if not self.valet_token or not self.created_ticket_id:
            return False
            
        success, response = self.run_test(
            "Claim Ticket",
            "PUT",
            f"tickets/{self.created_ticket_id}/claim",
            200,
            headers={"Authorization": f"Bearer {self.valet_token}"}
        )
        
        if success:
            print("✅ Ticket claimed successfully")
            return True
        return False

    def test_update_ticket_status(self):
        """Test ticket status updates"""
        if not self.valet_token or not self.created_ticket_id:
            return False
            
        statuses = ["en_route", "arrived", "completed"]
        
        for status in statuses:
            success, response = self.run_test(
                f"Update Status to {status}",
                "PUT",
                f"tickets/{self.created_ticket_id}/status?status={status}",
                200,
                headers={"Authorization": f"Bearer {self.valet_token}"}
            )
            
            if not success:
                return False
                
        return True

    def test_whatsapp_webhook(self):
        """Test WhatsApp webhook"""
        print("\n=== Testing WhatsApp Integration ===")
        success, response = self.run_test(
            "WhatsApp RETR Message",
            "POST",
            "whatsapp/webhook?phone_number=%2B1234567890&message=RETR",
            200
        )
        
        if success and 'reply' in response:
            print(f"✅ WhatsApp response: {response['reply'][:50]}...")
            return True
        return False

    def test_admin_operations(self):
        """Test admin-specific operations"""
        if not self.admin_token:
            return False
            
        print("\n=== Testing Admin Operations ===")
        
        # Test get valets
        success1, response1 = self.run_test(
            "Get Valets (Admin)",
            "GET",
            "admin/valets",
            200,
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        
        # Test get tips
        success2, response2 = self.run_test(
            "Get Tips (Admin)",
            "GET",
            "admin/tips",
            200,
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        
        return success1 and success2

    def test_unauthorized_access(self):
        """Test unauthorized access to admin endpoints"""
        if not self.valet_token:
            return False
            
        print("\n=== Testing Authorization ===")
        success, response = self.run_test(
            "Unauthorized Admin Access",
            "GET",
            "admin/valets",
            403,
            headers={"Authorization": f"Bearer {self.valet_token}"}
        )
        
        return success

def main():
    """Run all tests"""
    tester = SwiftValetAPITester()
    
    print("🚀 Starting SwiftValet API Testing")
    print(f"Backend URL: {tester.base_url}")
    
    # Authentication Tests
    if not tester.test_admin_login():
        print("❌ Admin login failed, stopping tests")
        return 1
        
    if not tester.test_valet_login():
        print("❌ Valet login failed, stopping tests")
        return 1
        
    tester.test_invalid_login()
    tester.test_get_current_user()
    
    # Core Operations
    tester.test_create_vehicle()
    tester.test_upload_vehicle_photo()
    tester.test_get_vehicles()
    tester.test_create_ticket()
    tester.test_get_tickets()
    tester.test_claim_ticket()
    tester.test_update_ticket_status()
    
    # Integration Tests
    tester.test_whatsapp_webhook()
    
    # Admin Tests
    tester.test_admin_operations()
    tester.test_unauthorized_access()
    
    # Results
    print(f"\n📊 Test Results:")
    print(f"Tests passed: {tester.tests_passed}/{tester.tests_run}")
    print(f"Success rate: {(tester.tests_passed/tester.tests_run)*100:.1f}%")
    
    if tester.tests_passed == tester.tests_run:
        print("✅ All tests passed!")
        return 0
    else:
        print(f"❌ {tester.tests_run - tester.tests_passed} test(s) failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())