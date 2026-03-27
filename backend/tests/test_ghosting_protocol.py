"""
Test Ghosting Protocol (Phase C) - ParKaro Valet Platform
Tests for:
- PUT /api/tickets/{id}/status?status=arrived - sets arrived_at timestamp
- PUT /api/tickets/{id}/status?status=returned - sets returned_at, resets vehicle to 'parked' status, sends WhatsApp
- PUT /api/tickets/{id}/status?status=completed - marks vehicle as 'checked_out'
- PUT /api/vehicles/{id}/location - updates vehicle location when returning to different spot
"""

import pytest
import requests
import os
import uuid
from datetime import datetime, timezone, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_PHONE = "+919373991136"


class TestGhostingProtocol:
    """Test the Ghosting Protocol feature for valet parking"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test data and authentication"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin via OTP
        otp_response = self.session.post(f"{BASE_URL}/api/auth/otp/request", json={
            "phone_number": ADMIN_PHONE
        })
        assert otp_response.status_code == 200, f"OTP request failed: {otp_response.text}"
        otp = otp_response.json().get("dev_otp")
        
        verify_response = self.session.post(f"{BASE_URL}/api/auth/otp/verify", json={
            "phone_number": ADMIN_PHONE,
            "otp": otp
        })
        assert verify_response.status_code == 200, f"OTP verify failed: {verify_response.text}"
        
        self.token = verify_response.json().get("token")
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        
        yield
        
        # Cleanup is handled by test data prefixes
    
    def _create_test_vehicle(self):
        """Helper to create a test vehicle"""
        unique_id = str(uuid.uuid4())[:8]
        vehicle_data = {
            "phone_number": f"+91TEST{unique_id}",
            "license_plate": f"TEST-GHOST-{unique_id}",
            "tag_number": f"G{unique_id[:4]}",
            "zone_label": "Level 1, Section A",
            "gps_latitude": 19.0760,
            "gps_longitude": 72.8777
        }
        
        response = self.session.post(f"{BASE_URL}/api/vehicles", json=vehicle_data)
        assert response.status_code == 200, f"Failed to create vehicle: {response.text}"
        return response.json()["vehicle"]
    
    def _create_retrieval_ticket(self, phone_number):
        """Helper to create a retrieval ticket"""
        response = self.session.post(f"{BASE_URL}/api/tickets/retrieve", json={
            "phone_number": phone_number
        })
        assert response.status_code == 200, f"Failed to create retrieval ticket: {response.text}"
        return response.json()["ticket"]
    
    # ==================== ARRIVED STATUS TESTS ====================
    
    def test_arrived_status_sets_arrived_at_timestamp(self):
        """Test that marking ticket as 'arrived' sets arrived_at timestamp"""
        # Create vehicle and retrieval ticket
        vehicle = self._create_test_vehicle()
        ticket = self._create_retrieval_ticket(vehicle["phone_number"])
        
        # Mark as arrived
        before_time = datetime.now(timezone.utc)
        response = self.session.put(f"{BASE_URL}/api/tickets/{ticket['id']}/status?status=arrived")
        after_time = datetime.now(timezone.utc)
        
        assert response.status_code == 200, f"Failed to update status: {response.text}"
        
        # Verify arrived_at is set
        tickets_response = self.session.get(f"{BASE_URL}/api/tickets")
        assert tickets_response.status_code == 200
        
        updated_ticket = next((t for t in tickets_response.json() if t["id"] == ticket["id"]), None)
        assert updated_ticket is not None, "Ticket not found after update"
        assert updated_ticket["status"] == "arrived", f"Expected status 'arrived', got '{updated_ticket['status']}'"
        assert updated_ticket.get("arrived_at") is not None, "arrived_at timestamp not set"
        
        # Verify timestamp is within expected range
        arrived_at = datetime.fromisoformat(updated_ticket["arrived_at"].replace("Z", "+00:00"))
        assert before_time <= arrived_at <= after_time, "arrived_at timestamp out of expected range"
        
        print(f"✅ Arrived status test passed - arrived_at: {updated_ticket['arrived_at']}")
    
    # ==================== RETURNED STATUS TESTS (GHOSTING) ====================
    
    def test_returned_status_sets_returned_at_timestamp(self):
        """Test that marking ticket as 'returned' sets returned_at timestamp"""
        # Create vehicle and retrieval ticket
        vehicle = self._create_test_vehicle()
        ticket = self._create_retrieval_ticket(vehicle["phone_number"])
        
        # Mark as arrived first
        self.session.put(f"{BASE_URL}/api/tickets/{ticket['id']}/status?status=arrived")
        
        # Mark as returned (ghosted)
        before_time = datetime.now(timezone.utc)
        response = self.session.put(f"{BASE_URL}/api/tickets/{ticket['id']}/status?status=returned")
        after_time = datetime.now(timezone.utc)
        
        assert response.status_code == 200, f"Failed to update status to returned: {response.text}"
        
        # Verify returned_at is set
        tickets_response = self.session.get(f"{BASE_URL}/api/tickets")
        assert tickets_response.status_code == 200
        
        updated_ticket = next((t for t in tickets_response.json() if t["id"] == ticket["id"]), None)
        assert updated_ticket is not None, "Ticket not found after update"
        assert updated_ticket["status"] == "returned", f"Expected status 'returned', got '{updated_ticket['status']}'"
        assert updated_ticket.get("returned_at") is not None, "returned_at timestamp not set"
        
        print(f"✅ Returned status test passed - returned_at: {updated_ticket['returned_at']}")
    
    def test_returned_status_resets_vehicle_to_parked(self):
        """Test that 'returned' status resets vehicle status to 'parked'"""
        # Create vehicle and retrieval ticket
        vehicle = self._create_test_vehicle()
        ticket = self._create_retrieval_ticket(vehicle["phone_number"])
        
        # Mark as arrived then returned
        self.session.put(f"{BASE_URL}/api/tickets/{ticket['id']}/status?status=arrived")
        response = self.session.put(f"{BASE_URL}/api/tickets/{ticket['id']}/status?status=returned")
        
        assert response.status_code == 200, f"Failed to update status to returned: {response.text}"
        
        # Verify vehicle status is reset to 'parked'
        vehicles_response = self.session.get(f"{BASE_URL}/api/vehicles")
        assert vehicles_response.status_code == 200
        
        updated_vehicle = next((v for v in vehicles_response.json() if v["id"] == vehicle["id"]), None)
        assert updated_vehicle is not None, "Vehicle not found after update"
        assert updated_vehicle.get("status") == "parked", f"Expected vehicle status 'parked', got '{updated_vehicle.get('status')}'"
        
        print(f"✅ Vehicle reset to parked test passed - vehicle status: {updated_vehicle.get('status')}")
    
    def test_returned_vehicle_can_be_retrieved_again(self):
        """Test that a ghosted vehicle can be retrieved again later"""
        # Create vehicle and retrieval ticket
        vehicle = self._create_test_vehicle()
        ticket = self._create_retrieval_ticket(vehicle["phone_number"])
        
        # Mark as arrived then returned (ghosted)
        self.session.put(f"{BASE_URL}/api/tickets/{ticket['id']}/status?status=arrived")
        self.session.put(f"{BASE_URL}/api/tickets/{ticket['id']}/status?status=returned")
        
        # Try to create a new retrieval ticket for the same vehicle
        new_ticket_response = self.session.post(f"{BASE_URL}/api/tickets/retrieve", json={
            "phone_number": vehicle["phone_number"]
        })
        
        assert new_ticket_response.status_code == 200, f"Failed to create new retrieval ticket: {new_ticket_response.text}"
        new_ticket = new_ticket_response.json()["ticket"]
        assert new_ticket["id"] != ticket["id"], "New ticket should have different ID"
        assert new_ticket["status"] == "claimed", f"Expected status 'claimed', got '{new_ticket['status']}'"
        
        print(f"✅ Vehicle can be retrieved again test passed - new ticket ID: {new_ticket['id']}")
    
    # ==================== COMPLETED STATUS TESTS ====================
    
    def test_completed_status_marks_vehicle_checked_out(self):
        """Test that 'completed' status marks vehicle as 'checked_out'"""
        # Create vehicle and retrieval ticket
        vehicle = self._create_test_vehicle()
        ticket = self._create_retrieval_ticket(vehicle["phone_number"])
        
        # Mark as arrived then completed
        self.session.put(f"{BASE_URL}/api/tickets/{ticket['id']}/status?status=arrived")
        response = self.session.put(f"{BASE_URL}/api/tickets/{ticket['id']}/status?status=completed")
        
        assert response.status_code == 200, f"Failed to update status to completed: {response.text}"
        
        # Verify ticket status
        tickets_response = self.session.get(f"{BASE_URL}/api/tickets")
        assert tickets_response.status_code == 200
        
        updated_ticket = next((t for t in tickets_response.json() if t["id"] == ticket["id"]), None)
        assert updated_ticket is not None, "Ticket not found after update"
        assert updated_ticket["status"] == "completed", f"Expected status 'completed', got '{updated_ticket['status']}'"
        assert updated_ticket.get("completed_at") is not None, "completed_at timestamp not set"
        
        # Verify vehicle status is 'checked_out'
        vehicles_response = self.session.get(f"{BASE_URL}/api/vehicles")
        assert vehicles_response.status_code == 200
        
        updated_vehicle = next((v for v in vehicles_response.json() if v["id"] == vehicle["id"]), None)
        assert updated_vehicle is not None, "Vehicle not found after update"
        assert updated_vehicle.get("status") == "checked_out", f"Expected vehicle status 'checked_out', got '{updated_vehicle.get('status')}'"
        
        print(f"✅ Completed status test passed - vehicle status: {updated_vehicle.get('status')}")
    
    # ==================== VEHICLE LOCATION UPDATE TESTS ====================
    
    def test_update_vehicle_location_on_return(self):
        """Test updating vehicle location when returning to different spot"""
        # Create vehicle
        vehicle = self._create_test_vehicle()
        original_zone = vehicle.get("zone_label")
        
        # Update location
        new_zone = "Level 2, Section B (Closer spot)"
        new_lat = 19.0800
        new_lng = 72.8800
        
        response = self.session.put(
            f"{BASE_URL}/api/vehicles/{vehicle['id']}/location",
            params={
                "zone_label": new_zone,
                "gps_latitude": new_lat,
                "gps_longitude": new_lng
            }
        )
        
        assert response.status_code == 200, f"Failed to update vehicle location: {response.text}"
        
        # Verify location was updated
        vehicles_response = self.session.get(f"{BASE_URL}/api/vehicles")
        assert vehicles_response.status_code == 200
        
        updated_vehicle = next((v for v in vehicles_response.json() if v["id"] == vehicle["id"]), None)
        assert updated_vehicle is not None, "Vehicle not found after update"
        assert updated_vehicle.get("zone_label") == new_zone, f"Expected zone '{new_zone}', got '{updated_vehicle.get('zone_label')}'"
        assert updated_vehicle.get("gps_latitude") == new_lat, f"Expected lat {new_lat}, got {updated_vehicle.get('gps_latitude')}"
        assert updated_vehicle.get("gps_longitude") == new_lng, f"Expected lng {new_lng}, got {updated_vehicle.get('gps_longitude')}"
        
        print(f"✅ Vehicle location update test passed - new zone: {updated_vehicle.get('zone_label')}")
    
    # ==================== FULL GHOSTING FLOW TEST ====================
    
    def test_full_ghosting_flow(self):
        """Test the complete ghosting protocol flow"""
        # 1. Park a vehicle
        vehicle = self._create_test_vehicle()
        print(f"1. Vehicle parked: {vehicle['license_plate']}")
        
        # 2. Create retrieval ticket
        ticket = self._create_retrieval_ticket(vehicle["phone_number"])
        assert ticket["status"] == "claimed"
        print(f"2. Retrieval ticket created: {ticket['id']}")
        
        # 3. Mark as arrived (timer starts)
        arrived_response = self.session.put(f"{BASE_URL}/api/tickets/{ticket['id']}/status?status=arrived")
        assert arrived_response.status_code == 200
        print("3. Marked as arrived - 5 minute timer started")
        
        # 4. Update vehicle location (return to different spot)
        new_zone = "Level 3, Section C (Ghosted)"
        location_response = self.session.put(
            f"{BASE_URL}/api/vehicles/{vehicle['id']}/location",
            params={"zone_label": new_zone}
        )
        assert location_response.status_code == 200
        print(f"4. Vehicle location updated to: {new_zone}")
        
        # 5. Mark as returned (ghosted)
        returned_response = self.session.put(f"{BASE_URL}/api/tickets/{ticket['id']}/status?status=returned")
        assert returned_response.status_code == 200
        print("5. Marked as returned (ghosted)")
        
        # 6. Verify final state
        tickets_response = self.session.get(f"{BASE_URL}/api/tickets")
        final_ticket = next((t for t in tickets_response.json() if t["id"] == ticket["id"]), None)
        
        vehicles_response = self.session.get(f"{BASE_URL}/api/vehicles")
        final_vehicle = next((v for v in vehicles_response.json() if v["id"] == vehicle["id"]), None)
        
        assert final_ticket["status"] == "returned", f"Expected ticket status 'returned', got '{final_ticket['status']}'"
        assert final_ticket.get("arrived_at") is not None, "arrived_at should be set"
        assert final_ticket.get("returned_at") is not None, "returned_at should be set"
        assert final_vehicle.get("status") == "parked", f"Expected vehicle status 'parked', got '{final_vehicle.get('status')}'"
        assert final_vehicle.get("zone_label") == new_zone, f"Expected zone '{new_zone}', got '{final_vehicle.get('zone_label')}'"
        
        print("6. ✅ Full ghosting flow completed successfully!")
        print(f"   - Ticket status: {final_ticket['status']}")
        print(f"   - Vehicle status: {final_vehicle.get('status')}")
        print(f"   - Vehicle zone: {final_vehicle.get('zone_label')}")
    
    # ==================== VALET DASHBOARD STATS TEST ====================
    
    def test_valet_dashboard_stats_still_work(self):
        """Test that valet dashboard stats endpoint still works"""
        response = self.session.get(f"{BASE_URL}/api/valet/dashboard-stats")
        
        assert response.status_code == 200, f"Dashboard stats failed: {response.text}"
        
        data = response.json()
        assert "cars_parked_today" in data, "Missing cars_parked_today"
        assert "cars_retrieved_today" in data, "Missing cars_retrieved_today"
        assert "tips_today" in data, "Missing tips_today"
        
        print(f"✅ Valet dashboard stats test passed")
        print(f"   - Cars parked today: {data['cars_parked_today']}")
        print(f"   - Cars retrieved today: {data['cars_retrieved_today']}")
        print(f"   - Tips today: {data['tips_today']}")


class TestTicketStatusTransitions:
    """Test ticket status transitions"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test data and authentication"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin via OTP
        otp_response = self.session.post(f"{BASE_URL}/api/auth/otp/request", json={
            "phone_number": ADMIN_PHONE
        })
        assert otp_response.status_code == 200
        otp = otp_response.json().get("dev_otp")
        
        verify_response = self.session.post(f"{BASE_URL}/api/auth/otp/verify", json={
            "phone_number": ADMIN_PHONE,
            "otp": otp
        })
        assert verify_response.status_code == 200
        
        self.token = verify_response.json().get("token")
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        
        yield
    
    def _create_test_vehicle(self):
        """Helper to create a test vehicle"""
        unique_id = str(uuid.uuid4())[:8]
        vehicle_data = {
            "phone_number": f"+91TEST{unique_id}",
            "license_plate": f"TEST-TRANS-{unique_id}",
            "tag_number": f"T{unique_id[:4]}",
            "zone_label": "Test Zone"
        }
        
        response = self.session.post(f"{BASE_URL}/api/vehicles", json=vehicle_data)
        assert response.status_code == 200
        return response.json()["vehicle"]
    
    def test_status_transition_claimed_to_arrived(self):
        """Test transition from claimed to arrived"""
        vehicle = self._create_test_vehicle()
        ticket_response = self.session.post(f"{BASE_URL}/api/tickets/retrieve", json={
            "phone_number": vehicle["phone_number"]
        })
        ticket = ticket_response.json()["ticket"]
        
        assert ticket["status"] == "claimed"
        
        response = self.session.put(f"{BASE_URL}/api/tickets/{ticket['id']}/status?status=arrived")
        assert response.status_code == 200
        
        print("✅ Transition claimed → arrived passed")
    
    def test_status_transition_arrived_to_completed(self):
        """Test transition from arrived to completed (normal handover)"""
        vehicle = self._create_test_vehicle()
        ticket_response = self.session.post(f"{BASE_URL}/api/tickets/retrieve", json={
            "phone_number": vehicle["phone_number"]
        })
        ticket = ticket_response.json()["ticket"]
        
        self.session.put(f"{BASE_URL}/api/tickets/{ticket['id']}/status?status=arrived")
        
        response = self.session.put(f"{BASE_URL}/api/tickets/{ticket['id']}/status?status=completed")
        assert response.status_code == 200
        
        print("✅ Transition arrived → completed passed")
    
    def test_status_transition_arrived_to_returned(self):
        """Test transition from arrived to returned (ghosting)"""
        vehicle = self._create_test_vehicle()
        ticket_response = self.session.post(f"{BASE_URL}/api/tickets/retrieve", json={
            "phone_number": vehicle["phone_number"]
        })
        ticket = ticket_response.json()["ticket"]
        
        self.session.put(f"{BASE_URL}/api/tickets/{ticket['id']}/status?status=arrived")
        
        response = self.session.put(f"{BASE_URL}/api/tickets/{ticket['id']}/status?status=returned")
        assert response.status_code == 200
        
        print("✅ Transition arrived → returned passed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
