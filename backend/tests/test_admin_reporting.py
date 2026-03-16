"""
Test Admin Reporting Dashboard API Endpoints
Tests the new 'Nightly Pulse' reporting features for admin users.
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestAdminReporting:
    """Test Admin Reporting API - The Nightly Pulse"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as Super Admin before each test"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as super admin
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "superadmin@swiftvalet.com",
            "password": "superadmin123"
        })
        
        if login_response.status_code == 200:
            token = login_response.json().get("token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
        else:
            pytest.skip("Super Admin login failed - skipping tests")

    def test_admin_reporting_endpoint_returns_200(self):
        """GET /api/admin/reporting should return 200 for admin user"""
        response = self.session.get(f"{BASE_URL}/api/admin/reporting")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

    def test_admin_reporting_response_structure(self):
        """GET /api/admin/reporting should return correct structure with all required fields"""
        response = self.session.get(f"{BASE_URL}/api/admin/reporting")
        assert response.status_code == 200
        
        data = response.json()
        
        # Check top-level fields
        assert "summary" in data, "Missing 'summary' field"
        assert "leaderboard" in data, "Missing 'leaderboard' field"
        assert "hourly_volume" in data, "Missing 'hourly_volume' field"
        assert "waitlist" in data, "Missing 'waitlist' field"
        assert "financial" in data, "Missing 'financial' field"

    def test_admin_reporting_summary_structure(self):
        """Summary object should have all required fields"""
        response = self.session.get(f"{BASE_URL}/api/admin/reporting")
        assert response.status_code == 200
        
        summary = response.json().get("summary", {})
        
        # Check summary fields
        assert "cars_parked" in summary, "Missing 'cars_parked' in summary"
        assert "cars_retrieved" in summary, "Missing 'cars_retrieved' in summary"
        assert "active_inventory" in summary, "Missing 'active_inventory' in summary"
        assert "avg_retrieval_mins" in summary, "Missing 'avg_retrieval_mins' in summary"
        assert "retrieval_status" in summary, "Missing 'retrieval_status' in summary"
        assert "total_tips" in summary, "Missing 'total_tips' in summary"
        assert "collection_rate" in summary, "Missing 'collection_rate' in summary"

    def test_admin_reporting_retrieval_status_valid(self):
        """retrieval_status should be one of green, amber, red"""
        response = self.session.get(f"{BASE_URL}/api/admin/reporting")
        assert response.status_code == 200
        
        summary = response.json().get("summary", {})
        retrieval_status = summary.get("retrieval_status")
        
        assert retrieval_status in ["green", "amber", "red"], f"Invalid retrieval_status: {retrieval_status}"

    def test_admin_reporting_leaderboard_is_list(self):
        """Leaderboard should be a list"""
        response = self.session.get(f"{BASE_URL}/api/admin/reporting")
        assert response.status_code == 200
        
        leaderboard = response.json().get("leaderboard")
        assert isinstance(leaderboard, list), f"Leaderboard should be a list, got {type(leaderboard)}"

    def test_admin_reporting_hourly_volume_structure(self):
        """hourly_volume should have 24 hours of data"""
        response = self.session.get(f"{BASE_URL}/api/admin/reporting")
        assert response.status_code == 200
        
        hourly = response.json().get("hourly_volume", [])
        assert isinstance(hourly, list), "hourly_volume should be a list"
        assert len(hourly) == 24, f"hourly_volume should have 24 entries, got {len(hourly)}"
        
        # Check structure of first hour
        if hourly:
            first_hour = hourly[0]
            assert "hour" in first_hour, "Missing 'hour' in hourly_volume entry"
            assert "intake" in first_hour, "Missing 'intake' in hourly_volume entry"
            assert "retrieval" in first_hour, "Missing 'retrieval' in hourly_volume entry"

    def test_admin_reporting_waitlist_is_list(self):
        """Waitlist should be a list"""
        response = self.session.get(f"{BASE_URL}/api/admin/reporting")
        assert response.status_code == 200
        
        waitlist = response.json().get("waitlist")
        assert isinstance(waitlist, list), f"Waitlist should be a list, got {type(waitlist)}"

    def test_admin_reporting_financial_structure(self):
        """Financial object should have all required fields"""
        response = self.session.get(f"{BASE_URL}/api/admin/reporting")
        assert response.status_code == 200
        
        financial = response.json().get("financial", {})
        
        assert "pending_tips_count" in financial, "Missing 'pending_tips_count' in financial"
        assert "paid_tips_total" in financial, "Missing 'paid_tips_total' in financial"
        assert "platform_fees" in financial, "Missing 'platform_fees' in financial"
        assert "payout" in financial, "Missing 'payout' in financial"
        assert isinstance(financial.get("payout"), list), "payout should be a list"

    def test_admin_reporting_export_csv(self):
        """GET /api/admin/reporting/export should return CSV file"""
        response = self.session.get(f"{BASE_URL}/api/admin/reporting/export")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Check Content-Type
        content_type = response.headers.get("Content-Type", "")
        assert "text/csv" in content_type, f"Expected text/csv, got {content_type}"
        
        # Check Content-Disposition header for filename
        content_disp = response.headers.get("Content-Disposition", "")
        assert "attachment" in content_disp, f"Expected attachment, got {content_disp}"
        assert "swiftvalet_payout" in content_disp, f"Filename should contain 'swiftvalet_payout'"

    def test_admin_reporting_export_csv_has_headers(self):
        """CSV export should have proper headers"""
        response = self.session.get(f"{BASE_URL}/api/admin/reporting/export")
        assert response.status_code == 200
        
        csv_content = response.text
        lines = csv_content.strip().split('\n')
        
        # Check header row
        assert len(lines) >= 1, "CSV should have at least header row"
        header = lines[0]
        assert "Valet Name" in header, "Missing 'Valet Name' column"
        assert "Tip Amount" in header, "Missing 'Tip Amount' column"
        assert "Status" in header, "Missing 'Status' column"
        assert "Date" in header, "Missing 'Date' column"

    def test_admin_reporting_unauthorized_access(self):
        """Unauthorized users should get 401/403"""
        # Create new session without auth
        unauth_session = requests.Session()
        response = unauth_session.get(f"{BASE_URL}/api/admin/reporting")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"

    def test_admin_reporting_export_unauthorized_access(self):
        """Unauthorized users should not access export"""
        unauth_session = requests.Session()
        response = unauth_session.get(f"{BASE_URL}/api/admin/reporting/export")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
