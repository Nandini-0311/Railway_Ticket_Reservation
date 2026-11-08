"""
Project: Railway Ticket Reservation System
File: tests/test_admin.py
Purpose: Unit tests for Admin Authentication, Dashboard Metrics,
         Train & Station CRUD, and Financial Reporting.
"""

import sys
import os
import unittest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from database import Database
from backend.admin import AdminManager


class TestAdminModule(unittest.TestCase):
    """
    Automated test suite verifying the administrative functions,
    metrics aggregation, train management, and reports.
    """

    def test_01_admin_login_success(self):
        """Test admin login with default credentials."""
        res = AdminManager.login_admin("admin", "admin123")
        self.assertTrue(res['success'], f"Admin login failed: {res.get('error')}")
        self.assertIn("session_token", res)
        self.assertEqual(res['admin']['username'], "admin")

    def test_02_admin_login_invalid_password(self):
        """Test admin login rejection on bad password."""
        res = AdminManager.login_admin("admin", "wrong_admin_pass")
        self.assertFalse(res['success'])
        self.assertIn("Invalid", res['error'])

    def test_03_dashboard_metrics(self):
        """Test dashboard analytics aggregation."""
        res = AdminManager.get_dashboard_metrics()
        self.assertTrue(res['success'])
        m = res['metrics']
        self.assertGreaterEqual(m['total_trains'], 8)
        self.assertGreaterEqual(m['total_users'], 1)
        self.assertIn('gross_revenue', m)
        self.assertIn('net_revenue', m)

    def test_04_station_management(self):
        """Test adding and updating a railway station."""
        # Clean previous test station
        Database.execute_query("DELETE FROM stations WHERE station_code = 'TEST_STN'", commit=True)
        add_res = AdminManager.add_station("TEST_STN", "Test Junction", "Pune", "Maharashtra")
        self.assertTrue(add_res['success'])

        stn_id = add_res['station_id']
        upd_res = AdminManager.update_station(stn_id, "TEST_STN", "Test Cantt", "Pune", "Maharashtra")
        self.assertTrue(upd_res['success'])

        # Cleanup
        Database.execute_query("DELETE FROM stations WHERE station_code = 'TEST_STN'", commit=True)

    def test_05_train_management(self):
        """Test adding and updating a train."""
        Database.execute_query("DELETE FROM trains WHERE train_number = '99999'", commit=True)
        add_res = AdminManager.add_train(
            train_number="99999",
            train_name="Demo Express",
            source_station_id=1,
            destination_station_id=2,
            train_type="Express"
        )
        self.assertTrue(add_res['success'])
        train_id = add_res['train_id']

        del_res = AdminManager.delete_train(train_id)
        self.assertTrue(del_res['success'])

        # Cleanup
        Database.execute_query("DELETE FROM trains WHERE train_number = '99999'", commit=True)

    def test_06_booking_report_generation(self):
        """Test financial report compilation."""
        res = AdminManager.generate_booking_report()
        self.assertTrue(res['success'])
        self.assertIn('revenue_by_class', res)
        self.assertIn('revenue_by_train', res)


if __name__ == '__main__':
    unittest.main()
