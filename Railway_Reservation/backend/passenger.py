"""
Project: Railway Ticket Reservation System
File: backend/passenger.py
Purpose: Passenger details validation, berth allotment, and coach/seat numbering.
"""

import re
from database import Database

COACH_PREFIX_MAP = {
    'SL': 'S1',
    '3A': 'B1',
    '2A': 'A1',
    '1A': 'H1'
}

VALID_GENDERS = ['Male', 'Female', 'Other']
VALID_BERTHS = ['Lower', 'Middle', 'Upper', 'Side Lower', 'Side Upper', 'Window']


class PassengerManager:
    """
    Manages passenger manifest operations, input sanitization,
    and realistic seat/coach numbering.
    """

    @staticmethod
    def validate_passenger_list(passengers):
        """
        Validates passenger list constraints (1 to 6 passengers per booking).
        
        Parameters:
            passengers (list[dict]): List of passenger dictionaries.
            
        Returns:
            tuple (bool, str): (True, "OK") or (False, error_message).
        """
        if not passengers or not isinstance(passengers, list):
            return False, "At least one passenger must be provided."

        if len(passengers) > 6:
            return False, "Maximum of 6 passengers allowed per booking."

        for idx, p in enumerate(passengers, start=1):
            name = (p.get('passenger_name') or '').strip()
            if len(name) < 2 or not re.match(r"^[A-Za-z\s\.]+$", name):
                return False, f"Passenger #{idx}: Invalid name. Use alphabetic characters only."

            try:
                age = int(p.get('age', 0))
                if age < 1 or age > 120:
                    return False, f"Passenger #{idx}: Age must be between 1 and 120."
            except (ValueError, TypeError):
                return False, f"Passenger #{idx}: Age must be a valid number."

            gender = p.get('gender', 'Male')
            if gender not in VALID_GENDERS:
                return False, f"Passenger #{idx}: Invalid gender selection."

            berth = p.get('berth_preference', 'Lower')
            if berth not in VALID_BERTHS:
                p['berth_preference'] = 'Lower'

        return True, "Valid"

    @classmethod
    def generate_seat_assignments(cls, class_type, total_already_booked, count):
        """
        Generates realistic coach and seat numbers for passengers.
        Example: B1-15, B1-16
        """
        coach = COACH_PREFIX_MAP.get(class_type.upper(), 'S1')
        seats = []
        for i in range(count):
            seat_num = total_already_booked + i + 1
            seats.append(f"{coach}-{seat_num}")
        return seats

    @classmethod
    def insert_passengers(cls, booking_id, passengers_data, class_type, already_booked_count=0, conn=None):
        """
        Saves passenger records linked to a confirmed booking.
        Can run within an active database transaction.
        
        Returns:
            list[dict]: Saved passengers with assigned seat numbers.
        """
        seat_tags = cls.generate_seat_assignments(class_type, already_booked_count, len(passengers_data))
        inserted_list = []

        query = """
            INSERT INTO passengers (booking_id, passenger_name, age, gender, seat_number, berth_preference)
            VALUES (%s, %s, %s, %s, %s, %s)
        """

        cursor = conn.cursor(dictionary=True) if conn else None
        try:
            for idx, p in enumerate(passengers_data):
                name = p.get('passenger_name', '').strip()
                age = int(p.get('age', 25))
                gender = p.get('gender', 'Male')
                berth = p.get('berth_preference', 'Lower')
                seat_num = seat_tags[idx]

                if cursor:
                    cursor.execute(query, (booking_id, name, age, gender, seat_num, berth))
                    p_id = cursor.lastrowid
                else:
                    p_id = Database.execute_query(query, (booking_id, name, age, gender, seat_num, berth), commit=True)

                inserted_list.append({
                    "passenger_id": p_id,
                    "passenger_name": name,
                    "age": age,
                    "gender": gender,
                    "seat_number": seat_num,
                    "berth_preference": berth
                })
        finally:
            if cursor:
                cursor.close()

        return inserted_list

    @classmethod
    def get_passengers_by_booking(cls, booking_id):
        """
        Fetches all passengers assigned to a specific booking ID.
        """
        query = "SELECT * FROM passengers WHERE booking_id = %s ORDER BY passenger_id ASC"
        return Database.execute_query(query, (booking_id,), fetch_all=True) or []
