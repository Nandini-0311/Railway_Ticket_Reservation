"""
Project: Railway Ticket Reservation System
File: backend/booking.py
Purpose: Core business logic for Ticket Booking, 10-Digit PNR generation,
         atomic database transactions, PNR status lookups, and Ticket Cancellations.
"""

import random
from datetime import datetime
from database import Database
from config import CANCELLATION_CHARGE_PERCENTAGE
from backend.train import TrainManager
from backend.passenger import PassengerManager
from backend.payment import PaymentManager


class BookingManager:
    """
    Core Controller managing ticket reservations, PNR generation,
    and seat restorations with full ACID transactional integrity.
    """

    @staticmethod
    def generate_unique_pnr():
        """
        Generates a unique 10-digit Indian Railway PNR number.
        Standard IR format: 10 digits starting with numbers 2-9.
        Guarantees uniqueness against the bookings database.
        
        Returns:
            str: 10-digit unique PNR string (e.g., '8219472015').
        """
        while True:
            # First digit 2-9, followed by 9 random digits
            pnr = str(random.randint(2, 9)) + "".join([str(random.randint(0, 9)) for _ in range(9)])
            existing = Database.execute_query(
                "SELECT booking_id FROM bookings WHERE pnr_number = %s",
                (pnr,),
                fetch_one=True
            )
            if not existing:
                return pnr

    @classmethod
    def book_ticket(cls, user_id, train_id, source_station_id, destination_station_id,
                    journey_date_str, class_type, passengers_data, payment_method='UPI'):
        """
        Executes an atomic booking transaction:
        1. Validates passenger payload.
        2. Prepares & locks seat inventory (FOR UPDATE).
        3. Prevents overbooking.
        4. Decrements seat inventory.
        5. Inserts master booking record with 10-digit PNR.
        6. Allocates seats and inserts passenger records.
        7. Records mock payment.
        8. Commits or rolls back on any error.
        
        Returns:
            dict: Complete booking confirmation payload or failure error.
        """
        # Step 1: Validate passengers format
        is_valid, err_msg = PassengerManager.validate_passenger_list(passengers_data)
        if not is_valid:
            return {"success": False, "error": err_msg}

        class_type = class_type.upper()
        num_passengers = len(passengers_data)

        # Step 2: Ensure inventory is initialized for this date/train/class
        try:
            TrainManager.get_or_create_seat_inventory(train_id, journey_date_str, class_type)
        except Exception as e:
            return {"success": False, "error": f"Failed to initialize inventory: {str(e)}"}

        conn = None
        try:
            conn = Database.get_connection()
            conn.start_transaction()
            cursor = conn.cursor(dictionary=True)

            # Step 3: Lock seat inventory row for atomic check & update
            lock_query = """
                SELECT inventory_id, available_seats, fare
                FROM seat_inventory
                WHERE train_id = %s AND journey_date = %s AND class_type = %s
                FOR UPDATE
            """
            cursor.execute(lock_query, (train_id, journey_date_str, class_type))
            inv = cursor.fetchone()

            if not inv:
                conn.rollback()
                return {"success": False, "error": "Seat inventory not found for selected train and date."}

            avail_seats = inv['available_seats']
            if avail_seats < num_passengers:
                conn.rollback()
                return {
                    "success": False,
                    "error": f"Overbooking prevented! Only {avail_seats} seat(s) available in {class_type}, but {num_passengers} requested."
                }

            # Step 4: Decrement available seats
            unit_fare = float(inv['fare'])
            total_fare = round(unit_fare * num_passengers, 2)

            update_inv_query = """
                UPDATE seat_inventory
                SET available_seats = available_seats - %s
                WHERE inventory_id = %s
            """
            cursor.execute(update_inv_query, (num_passengers, inv['inventory_id']))

            # Step 5: Generate 10-digit PNR & insert master booking
            pnr = cls.generate_unique_pnr()
            insert_booking_query = """
                INSERT INTO bookings (
                    pnr_number, user_id, train_id, source_station_id, destination_station_id,
                    journey_date, class_type, total_passengers, total_fare, booking_status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'CONFIRMED')
            """
            cursor.execute(insert_booking_query, (
                pnr, user_id, train_id, source_station_id, destination_station_id,
                journey_date_str, class_type, num_passengers, total_fare
            ))
            booking_id = cursor.lastrowid

            # Step 6: Allocate and insert passengers
            passengers_assigned = PassengerManager.insert_passengers(
                booking_id=booking_id,
                passengers_data=passengers_data,
                class_type=class_type,
                already_booked_count=max(0, 100 - avail_seats),
                conn=conn
            )

            # Step 7: Record simulated payment
            payment_info = PaymentManager.process_payment(
                booking_id=booking_id,
                amount=total_fare,
                payment_method=payment_method,
                conn=conn
            )

            # Step 8: Commit all operations atomically
            conn.commit()
            cursor.close()

            # Retrieve rich booking details for confirmation receipt
            return {
                "success": True,
                "message": "Ticket booked successfully!",
                "pnr_number": pnr,
                "booking_id": booking_id,
                "total_fare": total_fare,
                "total_passengers": num_passengers,
                "class_type": class_type,
                "journey_date": journey_date_str,
                "passengers": passengers_assigned,
                "payment": payment_info
            }

        except Exception as e:
            if conn:
                try:
                    conn.rollback()
                except Exception:
                    pass
            return {"success": False, "error": f"Booking failed due to an error: {str(e)}"}
        finally:
            if conn and conn.is_connected():
                conn.close()

    @classmethod
    def get_pnr_status(cls, pnr_number):
        """
        Retrieves complete ticket and journey manifest by 10-digit PNR.
        Publicly accessible for travelers checking live reservation status.
        """
        pnr_clean = str(pnr_number).strip()
        query = """
            SELECT 
                b.booking_id, b.pnr_number, b.user_id, b.journey_date, b.class_type,
                b.total_passengers, b.total_fare, b.booking_status, b.booked_at,
                t.train_number, t.train_name, t.train_type,
                src.station_name AS source_name, src.station_code AS source_code,
                dst.station_name AS destination_name, dst.station_code AS destination_code,
                TIME_FORMAT(s.departure_time, '%H:%i') AS departure_time,
                TIME_FORMAT(s.arrival_time, '%H:%i') AS arrival_time,
                s.duration_hours,
                u.full_name AS booked_by_name, u.email AS booked_by_email, u.phone AS booked_by_phone
            FROM bookings b
            JOIN trains t ON b.train_id = t.train_id
            JOIN stations src ON b.source_station_id = src.station_id
            JOIN stations dst ON b.destination_station_id = dst.station_id
            LEFT JOIN schedules s ON t.train_id = s.train_id
            LEFT JOIN users u ON b.user_id = u.user_id
            WHERE b.pnr_number = %s
        """
        booking = Database.execute_query(query, (pnr_clean,), fetch_one=True)
        if not booking:
            return {"success": False, "error": f"PNR '{pnr_clean}' not found in reservation database."}

        # Convert types for JSON serialization
        booking['journey_date'] = str(booking['journey_date'])
        booking['booked_at'] = str(booking['booked_at'])
        booking['total_fare'] = float(booking['total_fare'])
        booking['duration_hours'] = float(booking['duration_hours'] or 0.0)

        # Fetch passenger list
        booking['passengers'] = PassengerManager.get_passengers_by_booking(booking['booking_id'])

        # Fetch payment record
        booking['payment'] = PaymentManager.get_payment_by_booking(booking['booking_id'])

        # If cancelled, fetch cancellation audit details
        if booking['booking_status'] == 'CANCELLED':
            cancel_query = "SELECT * FROM cancellations WHERE booking_id = %s LIMIT 1"
            cancellation = Database.execute_query(cancel_query, (booking['booking_id'],), fetch_one=True)
            if cancellation:
                cancellation['refund_amount'] = float(cancellation['refund_amount'])
                cancellation['cancellation_charge'] = float(cancellation['cancellation_charge'])
                cancellation['cancelled_at'] = str(cancellation['cancelled_at'])
                booking['cancellation_details'] = cancellation

        return {"success": True, "booking": booking}

    @classmethod
    def get_user_bookings(cls, user_id):
        """
        Retrieves all booking history records belonging to a user ID.
        """
        query = """
            SELECT 
                b.booking_id, b.pnr_number, b.journey_date, b.class_type,
                b.total_passengers, b.total_fare, b.booking_status, b.booked_at,
                t.train_number, t.train_name,
                src.station_name AS source_name, src.station_code AS source_code,
                dst.station_name AS destination_name, dst.station_code AS destination_code,
                TIME_FORMAT(s.departure_time, '%H:%i') AS departure_time,
                TIME_FORMAT(s.arrival_time, '%H:%i') AS arrival_time
            FROM bookings b
            JOIN trains t ON b.train_id = t.train_id
            JOIN stations src ON b.source_station_id = src.station_id
            JOIN stations dst ON b.destination_station_id = dst.station_id
            LEFT JOIN schedules s ON t.train_id = s.train_id
            WHERE b.user_id = %s
            ORDER BY b.booking_id DESC
        """
        rows = Database.execute_query(query, (user_id,), fetch_all=True) or []
        for r in rows:
            r['journey_date'] = str(r['journey_date'])
            r['booked_at'] = str(r['booked_at'])
            r['total_fare'] = float(r['total_fare'])
        return rows

    @classmethod
    def cancel_ticket(cls, pnr_number, user_id=None, cancellation_reason='User requested cancellation'):
        """
        Cancels a confirmed ticket atomically:
        1. Verifies booking status is CONFIRMED.
        2. Calculates cancellation charge (15%) and refund amount (85%).
        3. Updates booking status to CANCELLED.
        4. Restores seats to seat_inventory for that train/date/class.
        5. Inserts audit record into cancellations table.
        6. Updates payment status to REFUNDED.
        
        Returns:
            dict: Cancellation receipt and refund summary.
        """
        conn = None
        try:
            conn = Database.get_connection()
            conn.start_transaction()
            cursor = conn.cursor(dictionary=True)

            # Step 1: Lock booking record
            query = "SELECT * FROM bookings WHERE pnr_number = %s FOR UPDATE"
            cursor.execute(query, (pnr_number,))
            booking = cursor.fetchone()

            if not booking:
                conn.rollback()
                return {"success": False, "error": f"PNR '{pnr_number}' not found."}

            if user_id and booking['user_id'] != user_id:
                conn.rollback()
                return {"success": False, "error": "Unauthorized: You do not own this booking."}

            if booking['booking_status'] == 'CANCELLED':
                conn.rollback()
                return {"success": False, "error": "This ticket has already been cancelled."}

            # Step 2: Compute financial deductions
            total_fare = float(booking['total_fare'])
            charge_pct = float(CANCELLATION_CHARGE_PERCENTAGE)
            cancellation_charge = round(total_fare * (charge_pct / 100.0), 2)
            refund_amount = round(total_fare - cancellation_charge, 2)

            # Step 3: Update booking status
            cursor.execute(
                "UPDATE bookings SET booking_status = 'CANCELLED' WHERE booking_id = %s",
                (booking['booking_id'],)
            )

            # Step 4: Restore seats to inventory
            cursor.execute("""
                UPDATE seat_inventory
                SET available_seats = available_seats + %s
                WHERE train_id = %s AND journey_date = %s AND class_type = %s
            """, (
                booking['total_passengers'],
                booking['train_id'],
                booking['journey_date'],
                booking['class_type']
            ))

            # Step 5: Log into cancellations audit table
            cursor.execute("""
                INSERT INTO cancellations (
                    booking_id, pnr_number, refund_amount, cancellation_charge, cancellation_reason
                ) VALUES (%s, %s, %s, %s, %s)
            """, (
                booking['booking_id'],
                pnr_number,
                refund_amount,
                cancellation_charge,
                cancellation_reason
            ))

            # Step 6: Mark payment as REFUNDED
            cursor.execute(
                "UPDATE payments SET payment_status = 'REFUNDED' WHERE booking_id = %s",
                (booking['booking_id'],)
            )

            conn.commit()
            cursor.close()

            return {
                "success": True,
                "message": "Ticket cancelled successfully. Refund initiated.",
                "pnr_number": pnr_number,
                "total_fare": total_fare,
                "cancellation_charge": cancellation_charge,
                "refund_amount": refund_amount,
                "restored_seats": booking['total_passengers']
            }

        except Exception as e:
            if conn:
                try:
                    conn.rollback()
                except Exception:
                    pass
            return {"success": False, "error": f"Cancellation failed: {str(e)}"}
        finally:
            if conn and conn.is_connected():
                conn.close()
