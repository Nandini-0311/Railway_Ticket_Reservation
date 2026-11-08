"""
Project: Railway Ticket Reservation System
File: backend/train.py
Purpose: Handles train directory, station lookups, route searching,
         dynamic seat inventory generation, and class fare calculations.
"""

from datetime import datetime, date, timedelta
from database import Database

DAY_COLUMNS = {
    0: 'runs_on_mon',
    1: 'runs_on_tue',
    2: 'runs_on_wed',
    3: 'runs_on_thu',
    4: 'runs_on_fri',
    5: 'runs_on_sat',
    6: 'runs_on_sun'
}

CLASS_CONFIG = {
    'SL': {'seat_col': 'total_seats_sl', 'fare_col': 'base_fare_sl', 'name': 'Sleeper (SL)'},
    '3A': {'seat_col': 'total_seats_3a', 'fare_col': 'base_fare_3a', 'name': 'AC 3 Tier (3A)'},
    '2A': {'seat_col': 'total_seats_2a', 'fare_col': 'base_fare_2a', 'name': 'AC 2 Tier (2A)'},
    '1A': {'seat_col': 'total_seats_1a', 'fare_col': 'base_fare_1a', 'name': 'AC First Class (1A)'}
}


class TrainManager:
    """
    Core management class for Train routes, Station catalogs,
    and Real-Time Seat Availability / Fare calculations.
    """

    @staticmethod
    def get_all_stations():
        """
        Retrieves all railway stations ordered alphabetically by name.
        
        Returns:
            list[dict]: List of station objects with ID, code, name, city, state.
        """
        query = "SELECT station_id, station_code, station_name, city, state FROM stations ORDER BY station_name ASC"
        return Database.execute_query(query, fetch_all=True) or []

    @staticmethod
    def get_station_by_id(station_id):
        """
        Fetches single station by primary key ID.
        """
        query = "SELECT station_id, station_code, station_name, city, state FROM stations WHERE station_id = %s"
        return Database.execute_query(query, (station_id,), fetch_one=True)

    @staticmethod
    def get_station_by_code_or_name(term):
        """
        Resolves station ID from code (e.g., 'NDLS') or approximate name.
        """
        term_clean = term.strip().upper()
        query = """
            SELECT station_id, station_code, station_name, city, state
            FROM stations
            WHERE station_code = %s OR UPPER(station_name) LIKE %s
            LIMIT 1
        """
        return Database.execute_query(query, (term_clean, f"%{term_clean}%"), fetch_one=True)

    @classmethod
    def get_or_create_seat_inventory(cls, train_id, journey_date_str, class_type):
        """
        Ensures seat inventory exists for a given train, date, and travel class.
        If inventory for this date does not exist, automatically seeds it from master train capacities.
        
        Parameters:
            train_id (int): Train primary key ID.
            journey_date_str (str): Date formatted as YYYY-MM-DD.
            class_type (str): 'SL', '3A', '2A', or '1A'.
            
        Returns:
            dict: Inventory record with available_seats and fare.
        """
        class_type = class_type.upper()
        if class_type not in CLASS_CONFIG:
            raise ValueError(f"Invalid travel class: {class_type}")

        # Check existing inventory
        inv_query = """
            SELECT inventory_id, train_id, journey_date, class_type, available_seats, fare
            FROM seat_inventory
            WHERE train_id = %s AND journey_date = %s AND class_type = %s
        """
        inv = Database.execute_query(inv_query, (train_id, journey_date_str, class_type), fetch_one=True)
        if inv:
            inv['fare'] = float(inv['fare'])
            inv['journey_date'] = str(inv['journey_date'])
            return inv

        # If not present, query train master details to initialize
        train_query = "SELECT * FROM trains WHERE train_id = %s"
        train = Database.execute_query(train_query, (train_id,), fetch_one=True)
        if not train:
            raise ValueError(f"Train with ID {train_id} not found.")

        cfg = CLASS_CONFIG[class_type]
        init_seats = train.get(cfg['seat_col'], 0)
        base_fare = float(train.get(cfg['fare_col'], 0.0))

        # Insert new date inventory
        insert_query = """
            INSERT INTO seat_inventory (train_id, journey_date, class_type, available_seats, fare)
            VALUES (%s, %s, %s, %s, %s)
        """
        Database.execute_query(
            insert_query,
            (train_id, journey_date_str, class_type, init_seats, base_fare),
            commit=True
        )

        return {
            "train_id": train_id,
            "journey_date": journey_date_str,
            "class_type": class_type,
            "available_seats": init_seats,
            "fare": base_fare
        }

    @classmethod
    def get_all_classes_availability(cls, train_id, journey_date_str):
        """
        Retrieves availability and fare for all 4 classes (SL, 3A, 2A, 1A) for a train on a given date.
        
        Returns:
            dict: Dictionary mapped by class code.
        """
        result = {}
        for c in ['SL', '3A', '2A', '1A']:
            inv = cls.get_or_create_seat_inventory(train_id, journey_date_str, c)
            result[c] = {
                "class_code": c,
                "class_name": CLASS_CONFIG[c]['name'],
                "available_seats": inv['available_seats'],
                "fare": inv['fare'],
                "status": "AVAILABLE" if inv['available_seats'] > 0 else "REGRET"
            }
        return result

    @classmethod
    def search_trains(cls, source_id_or_code, dest_id_or_code, journey_date_str):
        """
        Searches available trains between source and destination stations on a given journey date.
        Checks operating day of the week and pulls real-time seat availability for all classes.
        
        Parameters:
            source_id_or_code: Station ID (int) or Station Code (str) like 'NDLS'
            dest_id_or_code: Station ID (int) or Station Code (str) like 'BCT'
            journey_date_str: Date string 'YYYY-MM-DD'
            
        Returns:
            list[dict]: List of available trains with route, timings, and class inventory.
        """
        # Resolve source station
        src_station = None
        if isinstance(source_id_or_code, int) or str(source_id_or_code).isdigit():
            src_station = cls.get_station_by_id(int(source_id_or_code))
        else:
            src_station = cls.get_station_by_code_or_name(str(source_id_or_code))

        # Resolve destination station
        dst_station = None
        if isinstance(dest_id_or_code, int) or str(dest_id_or_code).isdigit():
            dst_station = cls.get_station_by_id(int(dest_id_or_code))
        else:
            dst_station = cls.get_station_by_code_or_name(str(dest_id_or_code))

        if not src_station or not dst_station:
            return {"success": False, "error": "Invalid source or destination station.", "trains": []}

        if src_station['station_id'] == dst_station['station_id']:
            return {"success": False, "error": "Source and Destination stations cannot be the same.", "trains": []}

        # Parse date and determine day of the week
        try:
            parsed_date = datetime.strptime(journey_date_str, '%Y-%m-%d').date()
            if parsed_date < date.today():
                return {"success": False, "error": "Journey date cannot be in the past.", "trains": []}
        except ValueError:
            return {"success": False, "error": "Invalid date format. Expected YYYY-MM-DD.", "trains": []}

        day_column = DAY_COLUMNS[parsed_date.weekday()]

        # Query direct and route-matched trains
        src_id = src_station['station_id']
        dst_id = dst_station['station_id']

        # 1. Direct trains where train starts at src and ends at dst
        direct_query = f"""
            SELECT 
                t.train_id, t.train_number, t.train_name, t.train_type,
                src.station_name AS source_name, src.station_code AS source_code,
                dst.station_name AS destination_name, dst.station_code AS destination_code,
                TIME_FORMAT(s.departure_time, '%%H:%%i') AS departure_time,
                TIME_FORMAT(s.arrival_time, '%%H:%%i') AS arrival_time,
                s.duration_hours,
                s.{day_column} AS runs_on_target_day
            FROM trains t
            JOIN stations src ON t.source_station_id = src.station_id
            JOIN stations dst ON t.destination_station_id = dst.station_id
            JOIN schedules s ON t.train_id = s.train_id
            WHERE t.is_active = TRUE
              AND t.source_station_id = %s
              AND t.destination_station_id = %s
        """
        direct_trains = Database.execute_query(direct_query, (src_id, dst_id), fetch_all=True) or []

        # 2. Intermediate route trains (where source stop < destination stop)
        intermediate_query = f"""
            SELECT 
                t.train_id, t.train_number, t.train_name, t.train_type,
                s1.station_name AS source_name, s1.station_code AS source_code,
                s2.station_name AS destination_name, s2.station_code AS destination_code,
                TIME_FORMAT(COALESCE(r1.departure_time, sch.departure_time), '%%H:%%i') AS departure_time,
                TIME_FORMAT(COALESCE(r2.arrival_time, sch.arrival_time), '%%H:%%i') AS arrival_time,
                sch.duration_hours,
                sch.{day_column} AS runs_on_target_day
            FROM routes r1
            JOIN routes r2 ON r1.train_id = r2.train_id AND r1.stop_number < r2.stop_number
            JOIN trains t ON r1.train_id = t.train_id
            JOIN stations s1 ON r1.station_id = s1.station_id
            JOIN stations s2 ON r2.station_id = s2.station_id
            JOIN schedules sch ON t.train_id = sch.train_id
            WHERE t.is_active = TRUE
              AND r1.station_id = %s
              AND r2.station_id = %s
        """
        intermediate_trains = Database.execute_query(intermediate_query, (src_id, dst_id), fetch_all=True) or []

        # Merge unique trains by train_id
        seen_train_ids = set()
        matched_trains = []

        for tr in (direct_trains + intermediate_trains):
            if tr['train_id'] not in seen_train_ids:
                seen_train_ids.add(tr['train_id'])
                # Check day-of-week operation
                if not tr.get('runs_on_target_day'):
                    continue

                # Convert duration_hours to display string like "15h 40m"
                hours = float(tr.get('duration_hours') or 0.0)
                h = int(hours)
                m = int(round((hours - h) * 60))
                tr['duration_formatted'] = f"{h}h {m}m"

                # Attach classes availability
                tr['classes'] = cls.get_all_classes_availability(tr['train_id'], journey_date_str)
                matched_trains.append(tr)

        return {
            "success": True,
            "source": src_station,
            "destination": dst_station,
            "journey_date": journey_date_str,
            "total_trains": len(matched_trains),
            "trains": matched_trains
        }

    @classmethod
    def get_train_by_id(cls, train_id):
        """
        Fetches detailed train information including schedule and station names.
        """
        query = """
            SELECT 
                t.*,
                src.station_name AS source_station_name, src.station_code AS source_station_code,
                dst.station_name AS destination_station_name, dst.station_code AS destination_station_code,
                TIME_FORMAT(s.departure_time, '%H:%i') AS departure_time,
                TIME_FORMAT(s.arrival_time, '%H:%i') AS arrival_time,
                s.duration_hours,
                s.runs_on_mon, s.runs_on_tue, s.runs_on_wed, s.runs_on_thu,
                s.runs_on_fri, s.runs_on_sat, s.runs_on_sun
            FROM trains t
            JOIN stations src ON t.source_station_id = src.station_id
            JOIN stations dst ON t.destination_station_id = dst.station_id
            LEFT JOIN schedules s ON t.train_id = s.train_id
            WHERE t.train_id = %s
        """
        train = Database.execute_query(query, (train_id,), fetch_one=True)
        if train:
            for k in ['base_fare_sl', 'base_fare_3a', 'base_fare_2a', 'base_fare_1a', 'duration_hours']:
                if k in train and train[k] is not None:
                    train[k] = float(train[k])
        return train

    @classmethod
    def get_all_trains(cls):
        """
        Fetches all registered trains with schedule and origin-destination stations.
        """
        query = """
            SELECT 
                t.train_id, t.train_number, t.train_name, t.train_type, t.is_active,
                t.total_seats_sl, t.total_seats_3a, t.total_seats_2a, t.total_seats_1a,
                t.base_fare_sl, t.base_fare_3a, t.base_fare_2a, t.base_fare_1a,
                src.station_name AS source_name, src.station_code AS source_code,
                dst.station_name AS destination_name, dst.station_code AS destination_code,
                TIME_FORMAT(s.departure_time, '%H:%i') AS departure_time,
                TIME_FORMAT(s.arrival_time, '%H:%i') AS arrival_time,
                s.duration_hours
            FROM trains t
            JOIN stations src ON t.source_station_id = src.station_id
            JOIN stations dst ON t.destination_station_id = dst.station_id
            LEFT JOIN schedules s ON t.train_id = s.train_id
            ORDER BY t.train_number ASC
        """
        trains = Database.execute_query(query, fetch_all=True) or []
        for tr in trains:
            for k in ['base_fare_sl', 'base_fare_3a', 'base_fare_2a', 'base_fare_1a', 'duration_hours']:
                if k in tr and tr[k] is not None:
                    tr[k] = float(tr[k])
        return trains
