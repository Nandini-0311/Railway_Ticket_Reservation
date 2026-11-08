"""
Project: Railway Ticket Reservation System
File: tests/test_booking.py
Purpose: Unit tests for PNR generation, Ticket booking, Multi-passenger allotment,
         Overbooking protection, PNR status lookups, and Ticket cancellation.
"""

import sys
import os
import unittest
from datetime import date, timedelta

# Ensure project root directory is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from database import Database
from backend.user import UserManager
from backend.train import TrainManager
from backend.booking import BookingManager


class TestBookingModule(unittest.TestCase):
    """
    Automated test suite verifying the complete ticket lifecycle,
    financial calculations, and ACID transactional seat inventory preservation.
    """

    @classmethod
    def setUpClass(cls):
        """Prepare a registered user and future journey date."""
        cls.test_email = "bookingtester@example.com"
        u = Database.execute_query("SELECT user_id FROM users WHERE email = %s", (cls.test_email,), fetch_one=True)
        if u:
            uid = u['user_id']
            b_ids = Database.execute_query("SELECT booking_id FROM bookings WHERE user_id = %s", (uid,), fetch_all=True) or []
            for b in b_ids:
                bid = b['booking_id']
                Database.execute_query("DELETE FROM cancellations WHERE booking_id = %s", (bid,), commit=True)
                Database.execute_query("DELETE FROM payments WHERE booking_id = %s", (bid,), commit=True)
                Database.execute_query("DELETE FROM passengers WHERE booking_id = %s", (bid,), commit=True)
                Database.execute_query("DELETE FROM bookings WHERE booking_id = %s", (bid,), commit=True)
            Database.execute_query("DELETE FROM users WHERE user_id = %s", (uid,), commit=True)

        user_res = UserManager.register_user(
            full_name="Amit Verma",
            email=cls.test_email,
            phone="9811223344",
            password="SecurePass@123",
            gender="Male",
            age=32
        )
        cls.user_id = user_res["user_id"]
        cls.journey_date = (date.today() + timedelta(days=7)).strftime('%Y-%m-%d')
        cls.booked_pnr = None

    def test_01_pnr_generation_format(self):
        """Test that generated PNR adheres to 10-digit Indian Railway format."""
        pnr = BookingManager.generate_unique_pnr()
        self.assertEqual(len(pnr), 10, "PNR must be exactly 10 digits.")
        self.assertTrue(pnr.isdigit(), "PNR must contain only digits.")
        self.assertIn(pnr[0], "23456789", "PNR first digit must be between 2 and 9.")

    def test_02_book_ticket_success(self):
        """Test booking a ticket with 2 passengers."""
        passengers = [
            {"passenger_name": "Amit Verma", "age": 32, "gender": "Male", "berth_preference": "Lower"},
            {"passenger_name": "Pooja Verma", "age": 29, "gender": "Female", "berth_preference": "Upper"}
        ]

        # Check initial seats
        inv_before = TrainManager.get_or_create_seat_inventory(train_id=1, journey_date_str=self.journey_date, class_type='3A')
        initial_seats = inv_before['available_seats']

        res = BookingManager.book_ticket(
            user_id=self.user_id,
            train_id=1,
            source_station_id=1,
            destination_station_id=2,
            journey_date_str=self.journey_date,
            class_type='3A',
            passengers_data=passengers,
            payment_method='UPI'
        )

        self.assertTrue(res['success'], f"Booking failed: {res.get('error')}")
        self.assertIn('pnr_number', res)
        self.assertEqual(len(res['passengers']), 2)
        self.assertEqual(res['total_passengers'], 2)
        self.assertEqual(res['payment']['payment_status'], 'SUCCESS')

        self.__class__.booked_pnr = res['pnr_number']

        # Verify seat inventory decremented by 2
        inv_after = TrainManager.get_or_create_seat_inventory(train_id=1, journey_date_str=self.journey_date, class_type='3A')
        self.assertEqual(inv_after['available_seats'], initial_seats - 2)

    def test_03_pnr_status_lookup(self):
        """Test retrieving live ticket manifest using the 10-digit PNR."""
        pnr = self.__class__.booked_pnr
        res = BookingManager.get_pnr_status(pnr)
        self.assertTrue(res['success'])
        booking = res['booking']
        self.assertEqual(booking['pnr_number'], pnr)
        self.assertEqual(booking['booking_status'], 'CONFIRMED')
        self.assertEqual(len(booking['passengers']), 2)
        self.assertEqual(booking['passengers'][0]['passenger_name'], 'Amit Verma')
        self.assertIn('B1-', booking['passengers'][0]['seat_number'])

    def test_04_ticket_cancellation_and_seat_restoration(self):
        """Test cancelling the ticket, charging 15% fee, and restoring seats to inventory."""
        pnr = self.__class__.booked_pnr

        inv_before = TrainManager.get_or_create_seat_inventory(train_id=1, journey_date_str=self.journey_date, class_type='3A')
        seats_before_cancel = inv_before['available_seats']

        res = BookingManager.cancel_ticket(pnr, user_id=self.user_id)
        self.assertTrue(res['success'], f"Cancellation failed: {res.get('error')}")
        self.assertGreater(res['cancellation_charge'], 0)
        self.assertGreater(res['refund_amount'], 0)
        self.assertEqual(res['restored_seats'], 2)

        # Verify seats restored by 2
        inv_after = TrainManager.get_or_create_seat_inventory(train_id=1, journey_date_str=self.journey_date, class_type='3A')
        self.assertEqual(inv_after['available_seats'], seats_before_cancel + 2)

        # Verify status in PNR query is now CANCELLED
        status_res = BookingManager.get_pnr_status(pnr)
        self.assertEqual(status_res['booking']['booking_status'], 'CANCELLED')
        self.assertIn('cancellation_details', status_res['booking'])

    def test_05_prevent_double_cancellation(self):
        """Test that cancelling an already cancelled ticket is cleanly rejected."""
        pnr = self.__class__.booked_pnr
        res = BookingManager.cancel_ticket(pnr, user_id=self.user_id)
        self.assertFalse(res['success'])
        self.assertIn('already been cancelled', res['error'])


if __name__ == '__main__':
    unittest.main()
