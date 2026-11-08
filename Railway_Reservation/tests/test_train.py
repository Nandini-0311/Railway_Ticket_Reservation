"""
Project: Railway Ticket Reservation System
File: tests/test_train.py
Purpose: Unit tests for Station lookup, Train search, Schedule verification,
         and Real-Time Seat Availability / Fare calculations.
"""

import sys
import os
import unittest
from datetime import date, timedelta

# Ensure project root directory is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.train import TrainManager


class TestTrainModule(unittest.TestCase):
    """
    Automated test suite verifying the station directory,
    train route matching, and class seat inventory calculations.
    """

    def setUp(self):
        # Always pick a valid future date (tomorrow)
        self.future_date = (date.today() + timedelta(days=2)).strftime('%Y-%m-%d')
        self.past_date = (date.today() - timedelta(days=2)).strftime('%Y-%m-%d')

    def test_01_get_all_stations(self):
        """Test retrieving stations directory from database."""
        stations = TrainManager.get_all_stations()
        self.assertIsInstance(stations, list)
        self.assertGreater(len(stations), 0, "No stations found in the database.")
        codes = [s['station_code'] for s in stations]
        self.assertIn('NDLS', codes, "Station NDLS (New Delhi) not found.")
        self.assertIn('BCT', codes, "Station BCT (Mumbai Central) not found.")

    def test_02_station_lookup_by_code(self):
        """Test resolving station details from station code."""
        station = TrainManager.get_station_by_code_or_name('NDLS')
        self.assertIsNotNone(station)
        self.assertEqual(station['station_code'], 'NDLS')
        self.assertIn('Delhi', station['city'])

    def test_03_train_search_direct(self):
        """Test searching trains between New Delhi (NDLS) and Mumbai Central (BCT)."""
        res = TrainManager.search_trains('NDLS', 'BCT', self.future_date)
        self.assertTrue(res['success'], f"Train search failed: {res.get('error')}")
        self.assertGreater(res['total_trains'], 0, "Expected at least 1 train between NDLS and BCT.")

        train = res['trains'][0]
        self.assertEqual(train['train_number'], '12952')
        self.assertIn('Mumbai Rajdhani', train['train_name'])
        self.assertIn('classes', train)
        self.assertIn('3A', train['classes'])
        self.assertIn('SL', train['classes'])
        self.assertGreater(train['classes']['3A']['available_seats'], 0)
        self.assertGreater(train['classes']['3A']['fare'], 0)

    def test_04_seat_inventory_auto_seeding(self):
        """Test that seat inventory dynamically seeds for uninitialized future dates."""
        target_date = (date.today() + timedelta(days=30)).strftime('%Y-%m-%d')
        inv = TrainManager.get_or_create_seat_inventory(train_id=1, journey_date_str=target_date, class_type='3A')
        self.assertIsNotNone(inv)
        self.assertEqual(inv['class_type'], '3A')
        self.assertEqual(inv['available_seats'], 64)  # Master 3A capacity for Rajdhani
        self.assertEqual(inv['fare'], 1650.00)

    def test_05_search_same_source_destination_error(self):
        """Test that searching with identical source and destination is cleanly blocked."""
        res = TrainManager.search_trains('NDLS', 'NDLS', self.future_date)
        self.assertFalse(res['success'])
        self.assertIn("cannot be the same", res['error'])

    def test_06_search_past_date_error(self):
        """Test that searching with a past journey date is blocked."""
        res = TrainManager.search_trains('NDLS', 'BCT', self.past_date)
        self.assertFalse(res['success'])
        self.assertIn("cannot be in the past", res['error'])


if __name__ == '__main__':
    unittest.main()
