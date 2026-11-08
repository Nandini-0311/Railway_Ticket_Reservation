"""
Project: Railway Ticket Reservation System
File: backend/admin.py
Purpose: Administrative control panel, authentication, system KPI analytics,
         Train/Station/Schedule/Fare CRUD operations, and passenger manifests.
"""

import hashlib
from database import Database
from config import SECRET_SALT
from backend.user import SessionManager


class AdminManager:
    """
    Controller for railway system administrator functions:
    analytics, train catalog, station networks, inventory adjustments, and reports.
    """

    @staticmethod
    def hash_password(plain_password):
        """
        Computes salted SHA-256 hash for administrator credentials.
        """
        salted = f"{plain_password}{SECRET_SALT}".encode('utf-8')
        return hashlib.sha256(salted).hexdigest()

    @classmethod
    def login_admin(cls, username, password):
        """
        Authenticates an administrator and returns an admin session token.
        Supports both salted and standard hash comparisons for flexibility.
        """
        if not username or not password:
            return {"success": False, "error": "Username and password are required."}

        username_clean = username.strip()
        query = "SELECT * FROM admin WHERE username = %s OR email = %s LIMIT 1"
        admin = Database.execute_query(query, (username_clean, username_clean), fetch_one=True)

        if not admin:
            return {"success": False, "error": "Invalid administrator credentials."}

        salted_hash = cls.hash_password(password)
        plain_sha256 = hashlib.sha256(password.encode('utf-8')).hexdigest()

        # Match either salted hash or direct seed hash
        if admin['password_hash'] not in (salted_hash, plain_sha256):
            return {"success": False, "error": "Invalid administrator credentials."}

        # If stored with legacy plain hash, upgrade to salted hash
        if admin['password_hash'] == plain_sha256:
            upgrade_query = "UPDATE admin SET password_hash = %s WHERE admin_id = %s"
            Database.execute_query(upgrade_query, (salted_hash, admin['admin_id']), commit=True)

        session_token = SessionManager.create_session(
            user_id=admin['admin_id'],
            email=admin['email'],
            full_name=admin['full_name'],
            role='admin'
        )

        return {
            "success": True,
            "message": "Admin login successful!",
            "session_token": session_token,
            "admin": {
                "admin_id": admin['admin_id'],
                "username": admin['username'],
                "email": admin['email'],
                "full_name": admin['full_name']
            }
        }

    @classmethod
    def get_dashboard_metrics(cls):
        """
        Aggregates high-level system analytics for the administrator dashboard.
        """
        # 1. Total trains
        trains_stat = Database.execute_query("SELECT COUNT(*) AS total FROM trains", fetch_one=True)
        total_trains = trains_stat['total'] if trains_stat else 0

        # 2. Total registered users
        users_stat = Database.execute_query("SELECT COUNT(*) AS total FROM users", fetch_one=True)
        total_users = users_stat['total'] if users_stat else 0

        # 3. Total confirmed and cancelled bookings
        confirmed_stat = Database.execute_query(
            "SELECT COUNT(*) AS total FROM bookings WHERE booking_status = 'CONFIRMED'",
            fetch_one=True
        )
        total_confirmed = confirmed_stat['total'] if confirmed_stat else 0

        cancelled_stat = Database.execute_query(
            "SELECT COUNT(*) AS total FROM bookings WHERE booking_status = 'CANCELLED'",
            fetch_one=True
        )
        total_cancelled = cancelled_stat['total'] if cancelled_stat else 0

        # 4. Gross revenue and refunds
        revenue_stat = Database.execute_query(
            "SELECT COALESCE(SUM(amount), 0) AS gross FROM payments WHERE payment_status = 'SUCCESS'",
            fetch_one=True
        )
        gross_revenue = float(revenue_stat['gross'] if revenue_stat else 0.0)

        refund_stat = Database.execute_query(
            "SELECT COALESCE(SUM(refund_amount), 0) AS total_refunds FROM cancellations",
            fetch_one=True
        )
        total_refunds = float(refund_stat['total_refunds'] if refund_stat else 0.0)
        net_revenue = round(gross_revenue - total_refunds, 2)

        # 5. Recent 5 bookings
        recent_query = """
            SELECT b.booking_id, b.pnr_number, b.journey_date, b.class_type,
                   b.total_passengers, b.total_fare, b.booking_status, b.booked_at,
                   t.train_number, t.train_name, u.full_name AS user_name
            FROM bookings b
            JOIN trains t ON b.train_id = t.train_id
            JOIN users u ON b.user_id = u.user_id
            ORDER BY b.booking_id DESC LIMIT 5
        """
        recent_bookings = Database.execute_query(recent_query, fetch_all=True) or []
        for r in recent_bookings:
            r['journey_date'] = str(r['journey_date'])
            r['booked_at'] = str(r['booked_at'])
            r['total_fare'] = float(r['total_fare'])

        return {
            "success": True,
            "metrics": {
                "total_trains": total_trains,
                "total_users": total_users,
                "total_bookings": total_confirmed + total_cancelled,
                "confirmed_bookings": total_confirmed,
                "cancelled_bookings": total_cancelled,
                "gross_revenue": gross_revenue,
                "total_refunds": total_refunds,
                "net_revenue": net_revenue,
                "recent_bookings": recent_bookings
            }
        }

    @classmethod
    def add_station(cls, station_code, station_name, city, state):
        """
        Registers a new railway station into the system.
        """
        code = station_code.strip().upper()
        name = station_name.strip()
        if not code or not name:
            return {"success": False, "error": "Station code and name are required."}

        existing = Database.execute_query("SELECT station_id FROM stations WHERE station_code = %s", (code,), fetch_one=True)
        if existing:
            return {"success": False, "error": f"Station with code '{code}' already exists."}

        insert_q = "INSERT INTO stations (station_code, station_name, city, state) VALUES (%s, %s, %s, %s)"
        station_id = Database.execute_query(insert_q, (code, name, city.strip(), state.strip()), commit=True)
        return {"success": True, "message": f"Station '{name}' ({code}) added successfully!", "station_id": station_id}

    @classmethod
    def update_station(cls, station_id, station_code, station_name, city, state):
        """
        Updates an existing station record.
        """
        code = station_code.strip().upper()
        name = station_name.strip()
        query = "UPDATE stations SET station_code = %s, station_name = %s, city = %s, state = %s WHERE station_id = %s"
        Database.execute_query(query, (code, name, city.strip(), state.strip(), station_id), commit=True)
        return {"success": True, "message": f"Station '{code}' updated successfully."}

    @classmethod
    def add_train(cls, train_number, train_name, source_station_id, destination_station_id,
                  train_type='Superfast Express', seats_dict=None, fares_dict=None, schedule_dict=None):
        """
        Creates a new train and sets its default operating schedule.
        """
        train_number = str(train_number).strip()
        train_name = train_name.strip()

        # Check duplicate train number
        existing = Database.execute_query("SELECT train_id FROM trains WHERE train_number = %s", (train_number,), fetch_one=True)
        if existing:
            return {"success": False, "error": f"Train #{train_number} already exists in database."}

        seats = seats_dict or {'SL': 120, '3A': 64, '2A': 48, '1A': 24}
        fares = fares_dict or {'SL': 450.0, '3A': 1150.0, '2A': 1750.0, '1A': 2850.0}

        insert_train_q = """
            INSERT INTO trains (
                train_number, train_name, source_station_id, destination_station_id, train_type,
                total_seats_sl, total_seats_3a, total_seats_2a, total_seats_1a,
                base_fare_sl, base_fare_3a, base_fare_2a, base_fare_1a, is_active
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE)
        """
        train_id = Database.execute_query(
            insert_train_q,
            (
                train_number, train_name, source_station_id, destination_station_id, train_type,
                seats.get('SL', 120), seats.get('3A', 64), seats.get('2A', 48), seats.get('1A', 24),
                fares.get('SL', 450.0), fares.get('3A', 1150.0), fares.get('2A', 1750.0), fares.get('1A', 2850.0)
            ),
            commit=True
        )

        # Attach schedule
        sch = schedule_dict or {}
        dep_time = sch.get('departure_time', '12:00:00')
        arr_time = sch.get('arrival_time', '20:00:00')
        duration = float(sch.get('duration_hours', 8.0))

        insert_sch_q = """
            INSERT INTO schedules (
                train_id, runs_on_mon, runs_on_tue, runs_on_wed, runs_on_thu,
                runs_on_fri, runs_on_sat, runs_on_sun, departure_time, arrival_time, duration_hours
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        Database.execute_query(
            insert_sch_q,
            (
                train_id,
                sch.get('runs_on_mon', True), sch.get('runs_on_tue', True),
                sch.get('runs_on_wed', True), sch.get('runs_on_thu', True),
                sch.get('runs_on_fri', True), sch.get('runs_on_sat', True),
                sch.get('runs_on_sun', True),
                dep_time, arr_time, duration
            ),
            commit=True
        )

        return {"success": True, "message": f"Train '{train_name}' (#{train_number}) added successfully!", "train_id": train_id}

    @classmethod
    def update_train(cls, train_id, train_number, train_name, source_station_id, destination_station_id,
                     train_type, seats_dict, fares_dict, schedule_dict):
        """
        Updates train details, capacities, base fares, and schedule timings.
        """
        train_q = """
            UPDATE trains
            SET train_number = %s, train_name = %s, source_station_id = %s, destination_station_id = %s,
                train_type = %s, total_seats_sl = %s, total_seats_3a = %s, total_seats_2a = %s, total_seats_1a = %s,
                base_fare_sl = %s, base_fare_3a = %s, base_fare_2a = %s, base_fare_1a = %s
            WHERE train_id = %s
        """
        Database.execute_query(
            train_q,
            (
                train_number, train_name, source_station_id, destination_station_id, train_type,
                seats_dict.get('SL', 120), seats_dict.get('3A', 64), seats_dict.get('2A', 48), seats_dict.get('1A', 24),
                fares_dict.get('SL', 450.0), fares_dict.get('3A', 1150.0), fares_dict.get('2A', 1750.0), fares_dict.get('1A', 2850.0),
                train_id
            ),
            commit=True
        )

        if schedule_dict:
            sch_q = """
                UPDATE schedules
                SET departure_time = %s, arrival_time = %s, duration_hours = %s,
                    runs_on_mon = %s, runs_on_tue = %s, runs_on_wed = %s, runs_on_thu = %s,
                    runs_on_fri = %s, runs_on_sat = %s, runs_on_sun = %s
                WHERE train_id = %s
            """
            Database.execute_query(
                sch_q,
                (
                    schedule_dict.get('departure_time'), schedule_dict.get('arrival_time'),
                    float(schedule_dict.get('duration_hours', 10.0)),
                    schedule_dict.get('runs_on_mon', True), schedule_dict.get('runs_on_tue', True),
                    schedule_dict.get('runs_on_wed', True), schedule_dict.get('runs_on_thu', True),
                    schedule_dict.get('runs_on_fri', True), schedule_dict.get('runs_on_sat', True),
                    schedule_dict.get('runs_on_sun', True),
                    train_id
                ),
                commit=True
            )

        return {"success": True, "message": f"Train #{train_number} updated successfully."}

    @classmethod
    def delete_train(cls, train_id):
        """
        Soft-deletes or deactivates a train so historic bookings remain intact.
        """
        query = "UPDATE trains SET is_active = FALSE WHERE train_id = %s"
        Database.execute_query(query, (train_id,), commit=True)
        return {"success": True, "message": "Train deactivated successfully."}

    @classmethod
    def get_all_bookings_admin(cls, limit=100, status=None):
        """
        Retrieves all bookings across the portal for audit and reporting.
        """
        params = []
        where_clause = ""
        if status in ['CONFIRMED', 'CANCELLED']:
            where_clause = "WHERE b.booking_status = %s"
            params.append(status)

        query = f"""
            SELECT 
                b.booking_id, b.pnr_number, b.journey_date, b.class_type,
                b.total_passengers, b.total_fare, b.booking_status, b.booked_at,
                t.train_number, t.train_name,
                src.station_name AS source_name, src.station_code AS source_code,
                dst.station_name AS destination_name, dst.station_code AS destination_code,
                u.full_name AS passenger_username, u.email AS passenger_email, u.phone AS passenger_phone
            FROM bookings b
            JOIN trains t ON b.train_id = t.train_id
            JOIN stations src ON b.source_station_id = src.station_id
            JOIN stations dst ON b.destination_station_id = dst.station_id
            JOIN users u ON b.user_id = u.user_id
            {where_clause}
            ORDER BY b.booking_id DESC
            LIMIT {int(limit)}
        """
        bookings = Database.execute_query(query, tuple(params), fetch_all=True) or []
        for b in bookings:
            b['journey_date'] = str(b['journey_date'])
            b['booked_at'] = str(b['booked_at'])
            b['total_fare'] = float(b['total_fare'])
        return bookings

    @classmethod
    def get_all_cancellations_admin(cls, limit=100):
        """
        Retrieves all ticket cancellation and refund audit logs.
        """
        query = f"""
            SELECT 
                c.cancellation_id, c.booking_id, c.pnr_number, c.refund_amount,
                c.cancellation_charge, c.cancelled_at, c.cancellation_reason,
                b.journey_date, b.class_type, b.total_fare,
                t.train_number, t.train_name,
                u.full_name AS user_name, u.email AS user_email
            FROM cancellations c
            JOIN bookings b ON c.booking_id = b.booking_id
            JOIN trains t ON b.train_id = t.train_id
            JOIN users u ON b.user_id = u.user_id
            ORDER BY c.cancellation_id DESC
            LIMIT {int(limit)}
        """
        records = Database.execute_query(query, fetch_all=True) or []
        for r in records:
            r['refund_amount'] = float(r['refund_amount'])
            r['cancellation_charge'] = float(r['cancellation_charge'])
            r['cancelled_at'] = str(r['cancelled_at'])
            r['journey_date'] = str(r['journey_date'])
            r['total_fare'] = float(r['total_fare'])
        return records

    @classmethod
    def get_passenger_manifest(cls, train_id, journey_date_str):
        """
        Returns full passenger reservation chart for a train and journey date.
        """
        query = """
            SELECT 
                p.passenger_id, p.passenger_name, p.age, p.gender,
                p.seat_number, p.berth_preference,
                b.pnr_number, b.class_type, b.booking_status,
                src.station_code AS source_code, dst.station_code AS destination_code
            FROM passengers p
            JOIN bookings b ON p.booking_id = b.booking_id
            JOIN stations src ON b.source_station_id = src.station_id
            JOIN stations dst ON b.destination_station_id = dst.station_id
            WHERE b.train_id = %s AND b.journey_date = %s
            ORDER BY p.seat_number ASC
        """
        manifest = Database.execute_query(query, (train_id, journey_date_str), fetch_all=True) or []
        return manifest

    @classmethod
    def generate_booking_report(cls):
        """
        Compiles class-wise and train-wise financial performance summary.
        """
        # Revenue by Class
        class_query = """
            SELECT class_type, COUNT(*) AS total_bookings,
                   SUM(total_passengers) AS total_passengers,
                   SUM(total_fare) AS class_revenue
            FROM bookings
            WHERE booking_status = 'CONFIRMED'
            GROUP BY class_type
        """
        by_class = Database.execute_query(class_query, fetch_all=True) or []
        for c in by_class:
            c['class_revenue'] = float(c['class_revenue'] or 0.0)

        # Revenue by Train
        train_query = """
            SELECT t.train_number, t.train_name,
                   COUNT(b.booking_id) AS total_bookings,
                   COALESCE(SUM(b.total_fare), 0) AS train_revenue
            FROM trains t
            LEFT JOIN bookings b ON t.train_id = b.train_id AND b.booking_status = 'CONFIRMED'
            GROUP BY t.train_id, t.train_number, t.train_name
            ORDER BY train_revenue DESC
        """
        by_train = Database.execute_query(train_query, fetch_all=True) or []
        for tr in by_train:
            tr['train_revenue'] = float(tr['train_revenue'] or 0.0)

        return {
            "success": True,
            "revenue_by_class": by_class,
            "revenue_by_train": by_train
        }
