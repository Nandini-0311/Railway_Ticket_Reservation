"""
Project: Railway Ticket Reservation System
File: config.py
Purpose: Central configuration management for database connections, server parameters,
         and application-wide security settings.
"""

import os

# Base directory of the project
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Database Configuration (MySQL)
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': '',                 # Default XAMPP/MySQL local password
    'database': 'railway_reservation',
    'charset': 'utf8mb4',
    'autocommit': False,            # Transactions explicitly controlled
    'raise_on_warnings': True
}

# HTTP Server Configuration
SERVER_HOST = '127.0.0.1'
SERVER_PORT = 8000

# Application Configuration
APP_NAME = 'Indian Railways Reservation Portal'
APP_VERSION = '1.0.0'

# Security & Business Logic Constants
SECRET_SALT = 'railway_secure_salt_key_2026'
CANCELLATION_CHARGE_PERCENTAGE = 15.0  # 15% cancellation fee deducted upon refund
SESSION_EXPIRY_HOURS = 24
