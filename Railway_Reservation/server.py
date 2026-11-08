"""
Project: Railway Ticket Reservation System
File: server.py
Purpose: Core HTTP server built on Python's native http.server module.
         Dispatches incoming HTTP requests, serves static frontend assets (HTML, CSS, JS),
         and routes RESTful API requests to corresponding backend controllers.
"""

import os
import json
import urllib.parse
from decimal import Decimal
import datetime
import traceback
from http.server import HTTPServer, BaseHTTPRequestHandler
from config import BASE_DIR, SERVER_HOST, SERVER_PORT
from database import Database

# Import backend business logic controllers
from backend.user import UserManager, SessionManager
from backend.train import TrainManager
from backend.booking import BookingManager
from backend.admin import AdminManager

class CustomJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder handling Decimal, date, datetime, time, and timedelta objects."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, (datetime.date, datetime.datetime)):
            return obj.isoformat()
        if isinstance(obj, datetime.time):
            return obj.strftime('%H:%M:%S')
        if isinstance(obj, datetime.timedelta):
            total_seconds = int(obj.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            return f"{hours:02d}:{minutes:02d}"
        return super().default(obj)

# MIME Types dictionary for static file serving
MIME_TYPES = {
    '.html': 'text/html; charset=utf-8',
    '.css': 'text/css; charset=utf-8',
    '.js': 'application/javascript; charset=utf-8',
    '.json': 'application/json; charset=utf-8',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.svg': 'image/svg+xml',
    '.ico': 'image/x-icon'
}


class RailwayRequestHandler(BaseHTTPRequestHandler):
    """
    Custom HTTP request handler subclassing BaseHTTPRequestHandler.
    Implements REST API routing, session extraction, and static file delivery.
    """

    # Suppress default noisy access logs to terminal (cleaner console output)
    def log_message(self, format, *args):
        # Can uncomment for verbose debugging
        # sys.stderr.write(f"[{self.log_date_time_string()}] {format % args}\n")
        pass

    # ==============================================================
    # HELPER METHODS (Request & Response Handling)
    # ==============================================================

    def send_json(self, data, status_code=200):
        """
        Serializes a Python dictionary to JSON and sends it with appropriate HTTP headers.
        """
        try:
            response_bytes = json.dumps(data, cls=CustomJSONEncoder, indent=2).encode('utf-8')
        except Exception as err:
            err_dict = {"success": False, "error": f"JSON serialization failed: {str(err)}"}
            response_bytes = json.dumps(err_dict).encode('utf-8')
            status_code = 500

        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(response_bytes)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Session-Token')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.end_headers()
        self.wfile.write(response_bytes)

    def read_json_body(self):
        """
        Reads raw bytes from the request body according to Content-Length and parses JSON.
        """
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length <= 0:
                return {}
            raw_data = self.rfile.read(content_length).decode('utf-8')
            return json.loads(raw_data)
        except Exception as e:
            return None

    def get_query_params(self):
        """
        Parses query parameters from URL string into a single-value dictionary.
        Example: /api/search?source=NDLS&destination=BCT -> {'source': 'NDLS', 'destination': 'BCT'}
        """
        parsed_url = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed_url.query)
        # Flatten list values to single values
        return {k: v[0] for k, v in qs.items()}

    def get_session_user(self):
        """
        Extracts session token from request headers ('X-Session-Token' or 'Authorization: Bearer <token>')
        and validates against active SessionManager registry.
        """
        token = self.headers.get('X-Session-Token')
        if not token:
            auth_header = self.headers.get('Authorization', '')
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1].strip()

        if not token:
            return None

        return SessionManager.validate_session(token)

    def serve_static_file(self, file_path):
        """
        Reads a local disk file and writes it to the HTTP socket with correct MIME type.
        """
        if not os.path.isfile(file_path):
            self.send_error(404, f"File Not Found: {self.path}")
            return

        ext = os.path.splitext(file_path)[1].lower()
        mime_type = MIME_TYPES.get(ext, 'application/octet-stream')

        try:
            with open(file_path, 'rb') as f:
                content = f.read()

            self.send_response(200)
            self.send_header('Content-Type', mime_type)
            self.send_header('Content-Length', str(len(content)))
            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_error(500, f"Internal Server Error: {str(e)}")

    # ==============================================================
    # HTTP OPTIONS (CORS Pre-flight)
    # ==============================================================

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Session-Token')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.end_headers()

    # ==============================================================
    # HTTP GET REQUEST ROUTING
    # ==============================================================

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        raw_path = parsed.path

        # ----------------------------------------------------------
        # 1. API GET Endpoints
        # ----------------------------------------------------------
        if raw_path.startswith('/api/'):
            self.handle_api_get(raw_path)
            return

        # ----------------------------------------------------------
        # 2. Static File Serving
        # ----------------------------------------------------------
        # Root / -> frontend/index.html
        if raw_path == '/' or raw_path == '/index.html':
            self.serve_static_file(os.path.join(BASE_DIR, 'frontend', 'index.html'))
            return

        # CSS files: /css/<file>
        if raw_path.startswith('/css/'):
            rel_path = raw_path.lstrip('/')
            self.serve_static_file(os.path.join(BASE_DIR, rel_path))
            return

        # JS files: /js/<file>
        if raw_path.startswith('/js/'):
            rel_path = raw_path.lstrip('/')
            self.serve_static_file(os.path.join(BASE_DIR, rel_path))
            return

        # HTML pages: /<page> or /<page>.html
        clean_name = raw_path.lstrip('/')
        if not clean_name.endswith('.html'):
            clean_name += '.html'

        candidate_file = os.path.join(BASE_DIR, 'frontend', clean_name)
        if os.path.isfile(candidate_file):
            self.serve_static_file(candidate_file)
            return

        # If not found
        self.send_error(404, f"Page not found: {raw_path}")

    def handle_api_get(self, path):
        params = self.get_query_params()

        # Public: Stations directory
        if path == '/api/stations':
            stations = TrainManager.get_all_stations()
            self.send_json({"success": True, "stations": stations})
            return

        # Public: Train search
        if path == '/api/trains/search':
            source = params.get('source')
            dest = params.get('destination')
            date_str = params.get('date')
            if not source or not dest or not date_str:
                self.send_json({"success": False, "error": "Parameters 'source', 'destination', and 'date' are required."}, 400)
                return
            result = TrainManager.search_trains(source, dest, date_str)
            self.send_json(result)
            return

        # Public: All trains list
        if path == '/api/trains/all':
            trains = TrainManager.get_all_trains()
            self.send_json({"success": True, "trains": trains})
            return

        # Public: Single train details
        if path == '/api/trains/details':
            train_id = params.get('train_id')
            if not train_id:
                self.send_json({"success": False, "error": "Missing 'train_id' parameter."}, 400)
                return
            train = TrainManager.get_train_by_id(int(train_id))
            if train:
                self.send_json({"success": True, "train": train})
            else:
                self.send_json({"success": False, "error": "Train not found."}, 404)
            return

        # Public: PNR Status Lookup
        if path == '/api/bookings/pnr_status':
            pnr = params.get('pnr')
            if not pnr:
                self.send_json({"success": False, "error": "Please provide a valid 10-digit PNR number."}, 400)
                return
            result = BookingManager.get_pnr_status(pnr)
            self.send_json(result)
            return

        # Protected: User booking history
        if path == '/api/bookings/my_bookings':
            user = self.get_session_user()
            if not user:
                self.send_json({"success": False, "error": "Unauthorized: Please log in."}, 401)
                return
            bookings = BookingManager.get_user_bookings(user['user_id'])
            self.send_json({"success": True, "bookings": bookings})
            return

        # Protected: User Profile info
        if path == '/api/user/profile':
            user = self.get_session_user()
            if not user:
                self.send_json({"success": False, "error": "Unauthorized: Please log in."}, 401)
                return
            profile = UserManager.get_user_by_id(user['user_id'])
            self.send_json({"success": True, "user": profile})
            return

        # Protected (Admin): Dashboard metrics
        if path == '/api/admin/metrics':
            user = self.get_session_user()
            if not user or user.get('role') != 'admin':
                self.send_json({"success": False, "error": "Admin access required."}, 403)
                return
            metrics = AdminManager.get_dashboard_metrics()
            self.send_json(metrics)
            return

        # Protected (Admin): View all bookings
        if path == '/api/admin/bookings':
            user = self.get_session_user()
            if not user or user.get('role') != 'admin':
                self.send_json({"success": False, "error": "Admin access required."}, 403)
                return
            status = params.get('status')
            bookings = AdminManager.get_all_bookings_admin(limit=100, status=status)
            self.send_json({"success": True, "bookings": bookings})
            return

        # Protected (Admin): View all cancellations
        if path == '/api/admin/cancellations':
            user = self.get_session_user()
            if not user or user.get('role') != 'admin':
                self.send_json({"success": False, "error": "Admin access required."}, 403)
                return
            cancellations = AdminManager.get_all_cancellations_admin(limit=100)
            self.send_json({"success": True, "cancellations": cancellations})
            return

        # Protected (Admin): Financial Performance Reports
        if path == '/api/admin/reports':
            user = self.get_session_user()
            if not user or user.get('role') != 'admin':
                self.send_json({"success": False, "error": "Admin access required."}, 403)
                return
            report = AdminManager.generate_booking_report()
            self.send_json(report)
            return

        # Protected (Admin): Passenger Manifest
        if path == '/api/admin/manifest':
            user = self.get_session_user()
            if not user or user.get('role') != 'admin':
                self.send_json({"success": False, "error": "Admin access required."}, 403)
                return
            train_id = params.get('train_id')
            journey_date = params.get('date')
            if not train_id or not journey_date:
                self.send_json({"success": False, "error": "Parameters 'train_id' and 'date' are required."}, 400)
                return
            manifest = AdminManager.get_passenger_manifest(int(train_id), journey_date)
            self.send_json({"success": True, "manifest": manifest})
            return

        # Unknown API GET endpoint
        self.send_json({"success": False, "error": f"API endpoint '{path}' not found."}, 404)

    # ==============================================================
    # HTTP POST REQUEST ROUTING
    # ==============================================================

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if not path.startswith('/api/'):
            self.send_json({"success": False, "error": "POST requests must target an /api/ endpoint."}, 404)
            return

        body = self.read_json_body()
        if body is None:
            self.send_json({"success": False, "error": "Malformed JSON payload."}, 400)
            return

        # ----------------------------------------------------------
        # 1. User Authentication & Profile
        # ----------------------------------------------------------
        if path == '/api/register':
            res = UserManager.register_user(
                full_name=body.get('full_name'),
                email=body.get('email'),
                phone=body.get('phone'),
                password=body.get('password'),
                gender=body.get('gender', 'Male'),
                age=body.get('age', 25)
            )
            status_code = 200 if res.get('success') else 400
            self.send_json(res, status_code)
            return

        if path == '/api/login':
            res = UserManager.login_user(
                identifier=body.get('identifier') or body.get('email'),
                password=body.get('password')
            )
            status_code = 200 if res.get('success') else 401
            self.send_json(res, status_code)
            return

        if path == '/api/logout':
            token = self.headers.get('X-Session-Token')
            if token:
                SessionManager.destroy_session(token)
            self.send_json({"success": True, "message": "Logged out successfully."})
            return

        if path == '/api/user/update_profile':
            user = self.get_session_user()
            if not user:
                self.send_json({"success": False, "error": "Unauthorized: Please log in."}, 401)
                return
            res = UserManager.update_profile(
                user_id=user['user_id'],
                full_name=body.get('full_name'),
                phone=body.get('phone'),
                gender=body.get('gender'),
                age=body.get('age')
            )
            self.send_json(res)
            return

        # ----------------------------------------------------------
        # 2. Admin Authentication
        # ----------------------------------------------------------
        if path == '/api/admin/login':
            res = AdminManager.login_admin(
                username=body.get('username'),
                password=body.get('password')
            )
            status_code = 200 if res.get('success') else 401
            self.send_json(res, status_code)
            return

        # ----------------------------------------------------------
        # 3. Reservations & Cancellations
        # ----------------------------------------------------------
        if path == '/api/bookings/book':
            try:
                user = self.get_session_user()
                user_id = user['user_id'] if user else body.get('user_id')

                # If no user_id, check for contact details to find or auto-create account
                if not user_id:
                    c_email = (body.get('contact_email') or '').strip().lower()
                    c_phone = (body.get('contact_phone') or '').strip()
                    c_name = (body.get('contact_name') or '').strip()
                    if not c_name and body.get('passengers') and len(body['passengers']) > 0:
                        c_name = body['passengers'][0].get('passenger_name', 'Passenger')

                    if c_email:
                        existing = Database.execute_query(
                            "SELECT user_id FROM users WHERE email = %s OR phone = %s",
                            (c_email, c_phone or c_email),
                            fetch_one=True
                        )
                        if existing:
                            user_id = existing['user_id']
                        else:
                            phone_to_use = c_phone if len(c_phone) == 10 else "9876543210"
                            reg_res = UserManager.register_user(
                                full_name=c_name or "Passenger",
                                email=c_email,
                                phone=phone_to_use,
                                password="Passenger@123",
                                gender="Male",
                                age=28
                            )
                            if reg_res.get('success'):
                                user_id = reg_res.get('user_id')

                # Fallback to any registered user if still unassigned
                if not user_id:
                    fallback_user = Database.execute_query("SELECT user_id FROM users ORDER BY user_id ASC LIMIT 1", fetch_one=True)
                    if fallback_user:
                        user_id = fallback_user['user_id']

                if not user_id:
                    self.send_json({"success": False, "error": "Please log in or provide your contact email to book tickets."}, 401)
                    return

                # Safe integer parsing
                train_id_raw = body.get('train_id')
                if not train_id_raw:
                    self.send_json({"success": False, "error": "Missing train ID."}, 400)
                    return
                train_id = int(train_id_raw)

                train_info = TrainManager.get_train_by_id(train_id)
                if not train_info:
                    self.send_json({"success": False, "error": "Train not found."}, 404)
                    return

                src_raw = body.get('source_station_id')
                src_id = int(src_raw) if (src_raw and str(src_raw).isdigit()) else train_info['source_station_id']

                dst_raw = body.get('destination_station_id')
                dst_id = int(dst_raw) if (dst_raw and str(dst_raw).isdigit()) else train_info['destination_station_id']

                journey_date = str(body.get('journey_date') or '').strip()
                if not journey_date or journey_date in ('null', 'undefined'):
                    from datetime import date
                    journey_date = str(date.today())

                class_type = str(body.get('class_type') or '3A').strip().upper()
                passengers = body.get('passengers', [])
                payment_method = str(body.get('payment_method') or 'UPI').strip()

                res = BookingManager.book_ticket(
                    user_id=user_id,
                    train_id=train_id,
                    source_station_id=src_id,
                    destination_station_id=dst_id,
                    journey_date_str=journey_date,
                    class_type=class_type,
                    passengers_data=passengers,
                    payment_method=payment_method
                )
                status_code = 200 if res.get('success') else 400
                self.send_json(res, status_code)
                return
            except Exception as e:
                print("[Booking API Exception]:", traceback.format_exc())
                self.send_json({"success": False, "error": f"Booking error: {str(e)}"}, 500)
                return

        if path == '/api/bookings/cancel':
            user = self.get_session_user()
            user_id = user['user_id'] if (user and user.get('role') != 'admin') else None
            pnr = body.get('pnr_number') or body.get('pnr')
            reason = body.get('reason', 'User requested cancellation')

            if not pnr:
                self.send_json({"success": False, "error": "PNR number is required."}, 400)
                return

            res = BookingManager.cancel_ticket(pnr, user_id=user_id, cancellation_reason=reason)
            status_code = 200 if res.get('success') else 400
            self.send_json(res, status_code)
            return

        # ----------------------------------------------------------
        # 4. Admin Management Endpoints
        # ----------------------------------------------------------
        user = self.get_session_user()
        if not user or user.get('role') != 'admin':
            self.send_json({"success": False, "error": "Unauthorized: Admin privileges required."}, 403)
            return

        if path == '/api/admin/stations/add':
            res = AdminManager.add_station(
                station_code=body.get('station_code'),
                station_name=body.get('station_name'),
                city=body.get('city'),
                state=body.get('state')
            )
            self.send_json(res)
            return

        if path == '/api/admin/stations/update':
            res = AdminManager.update_station(
                station_id=int(body.get('station_id')),
                station_code=body.get('station_code'),
                station_name=body.get('station_name'),
                city=body.get('city'),
                state=body.get('state')
            )
            self.send_json(res)
            return

        if path == '/api/admin/trains/add':
            res = AdminManager.add_train(
                train_number=body.get('train_number'),
                train_name=body.get('train_name'),
                source_station_id=int(body.get('source_station_id')),
                destination_station_id=int(body.get('destination_station_id')),
                train_type=body.get('train_type', 'Superfast Express'),
                seats_dict=body.get('seats'),
                fares_dict=body.get('fares'),
                schedule_dict=body.get('schedule')
            )
            self.send_json(res)
            return

        if path == '/api/admin/trains/update':
            res = AdminManager.update_train(
                train_id=int(body.get('train_id')),
                train_number=body.get('train_number'),
                train_name=body.get('train_name'),
                source_station_id=int(body.get('source_station_id')),
                destination_station_id=int(body.get('destination_station_id')),
                train_type=body.get('train_type'),
                seats_dict=body.get('seats', {}),
                fares_dict=body.get('fares', {}),
                schedule_dict=body.get('schedule', {})
            )
            self.send_json(res)
            return

        if path == '/api/admin/trains/delete':
            train_id = body.get('train_id')
            if not train_id:
                self.send_json({"success": False, "error": "Train ID is required."}, 400)
                return
            res = AdminManager.delete_train(int(train_id))
            self.send_json(res)
            return

        # Unknown POST endpoint
        self.send_json({"success": False, "error": f"POST API endpoint '{path}' not found."}, 404)
