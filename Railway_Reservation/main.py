"""
Project: Railway Ticket Reservation System
File: main.py
Purpose: Application bootstrap script.
         Performs initial database health-check, starts the native Core Python HTTP server,
         and serves the web application on http://127.0.0.1:8000.
"""

import sys
import os
from http.server import HTTPServer

# Configure sys.stdout to handle utf-8 if supported
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# Add project root to sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from config import SERVER_HOST, SERVER_PORT, APP_NAME, APP_VERSION
from database import Database
from server import RailwayRequestHandler


def print_banner():
    """Prints a styled terminal startup banner with quick URLs."""
    banner = f"""
=============================================================================
             {APP_NAME.upper()}
                         Version: {APP_VERSION}
=============================================================================
 [OK] Core Engine:    Python native http.server (No external frameworks)
 [OK] Database:       MySQL 8.0 (Database: railway_reservation)
 [OK] Server URL:     http://{SERVER_HOST}:{SERVER_PORT}/
 [OK] User Portal:    http://{SERVER_HOST}:{SERVER_PORT}/index.html
 [OK] Admin Portal:   http://{SERVER_HOST}:{SERVER_PORT}/admin_login.html
                      (Default Admin: admin | Password: admin123)
-----------------------------------------------------------------------------
 Server is actively running. Press Ctrl+C in this terminal to shut down.
=============================================================================
"""
    print(banner)


def start_server():
    """Validates database connectivity and starts the HTTP server listener."""
    print("\n[*] Initializing system components...")

    # Step 1: Probe Database
    if not Database.check_connection():
        print("[!] ERROR: Cannot establish connection to MySQL server!")
        print("    Please ensure that:")
        print("    1. MySQL or XAMPP service is running on port 3306.")
        print("    2. Database 'railway_reservation' is created (run database/railway.sql).")
        print("    3. Credentials in config.py match your MySQL server.")
        sys.exit(1)

    print("[OK] MySQL Database connection verified successfully.")

    # Step 2: Bind HTTP Server
    server_address = (SERVER_HOST, SERVER_PORT)
    try:
        httpd = HTTPServer(server_address, RailwayRequestHandler)
    except OSError as err:
        print(f"[!] ERROR: Port {SERVER_PORT} is already in use or unavailable: {err}")
        sys.exit(1)

    print_banner()

    # Step 3: Event Loop
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Received shutdown signal (Ctrl+C). Terminating server...")
    finally:
        httpd.server_close()
        print("[OK] Railway HTTP server closed cleanly. Goodbye!\n")


if __name__ == '__main__':
    start_server()
