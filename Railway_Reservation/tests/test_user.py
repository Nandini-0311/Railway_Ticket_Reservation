"""
Project: Railway Ticket Reservation System
File: tests/test_user.py
Purpose: Unit tests for User registration, password hashing, authentication,
         and session management.
"""

import sys
import os
import unittest

# Ensure project root directory is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from database import Database
from backend.user import UserManager, SessionManager


class TestUserModule(unittest.TestCase):
    """
    Automated test suite verifying the database connectivity,
    user lifecycle, credential verification, and session control.
    """

    @classmethod
    def setUpClass(cls):
        """Clean up previous test user records if any exist."""
        clean_query = "DELETE FROM users WHERE email IN (%s, %s) OR phone IN (%s, %s)"
        Database.execute_query(clean_query, ('testpassenger@example.com', 'updatedpassenger@example.com', '9999988888', '9999988889'), commit=True)

    @classmethod
    def tearDownClass(cls):
        """Clean up test users after all tests."""
        clean_query = "DELETE FROM users WHERE email IN (%s, %s) OR phone IN (%s, %s)"
        Database.execute_query(clean_query, ('testpassenger@example.com', 'updatedpassenger@example.com', '9999988888', '9999988889'), commit=True)

    def test_01_database_connection(self):
        """Test that MySQL server connects and responds properly."""
        is_connected = Database.check_connection()
        self.assertTrue(is_connected, "Database connection failed! Ensure MySQL service is running.")

    def test_02_password_hashing(self):
        """Test SHA-256 password hashing with salt consistency."""
        raw_pass = "SecurePass123"
        hash_1 = UserManager.hash_password(raw_pass)
        hash_2 = UserManager.hash_password(raw_pass)
        self.assertEqual(hash_1, hash_2, "Hashing function is non-deterministic.")
        self.assertNotEqual(raw_pass, hash_1, "Password is being stored in plain text!")
        self.assertEqual(len(hash_1), 64, "SHA-256 hash length must be 64 characters.")

    def test_03_user_registration_success(self):
        """Test registering a valid user."""
        res = UserManager.register_user(
            full_name="Rajesh Sharma",
            email="testpassenger@example.com",
            phone="9999988888",
            password="Password@123",
            gender="Male",
            age=28
        )
        self.assertTrue(res["success"], f"Registration failed: {res.get('error')}")
        self.assertIn("user_id", res)
        self.__class__.test_user_id = res["user_id"]

    def test_04_duplicate_registration_prevention(self):
        """Test that registering duplicate email or phone is cleanly blocked."""
        res_dup_email = UserManager.register_user(
            full_name="Duplicate Name",
            email="testpassenger@example.com",
            phone="9999988889",
            password="Password@123",
            gender="Male",
            age=30
        )
        self.assertFalse(res_dup_email["success"])
        self.assertIn("email already exists", res_dup_email["error"].lower())

    def test_05_user_login_success(self):
        """Test user login with correct credentials."""
        res = UserManager.login_user("testpassenger@example.com", "Password@123")
        self.assertTrue(res["success"], f"Login failed: {res.get('error')}")
        self.assertIn("session_token", res)
        self.assertEqual(res["user"]["full_name"], "Rajesh Sharma")
        self.__class__.session_token = res["session_token"]

    def test_06_user_login_invalid_password(self):
        """Test login with incorrect password."""
        res = UserManager.login_user("testpassenger@example.com", "WrongPassword")
        self.assertFalse(res["success"])
        self.assertIn("Invalid", res["error"])

    def test_07_session_validation_and_destruction(self):
        """Test session lifecycle: create, validate, destroy."""
        token = self.__class__.session_token
        session_info = SessionManager.validate_session(token)
        self.assertIsNotNone(session_info)
        self.assertEqual(session_info["email"], "testpassenger@example.com")

        # Destroy session (Logout)
        destroyed = SessionManager.destroy_session(token)
        self.assertTrue(destroyed)

        # After destruction, token must be invalid
        self.assertIsNone(SessionManager.validate_session(token))


if __name__ == '__main__':
    unittest.main()
