"""
Project: Railway Ticket Reservation System
File: backend/user.py
Purpose: Handles user account registration, authentication, password encryption (SHA-256),
         session lifecycle management, and profile operations.
"""

import hashlib
import re
import secrets
from datetime import datetime, timedelta
from database import Database
from config import SECRET_SALT, SESSION_EXPIRY_HOURS


class SessionManager:
    """
    In-memory session registry for authenticated users and administrators.
    Maps cryptographic session tokens to user context with automatic expiry checking.
    """
    _sessions = {}

    @classmethod
    def create_session(cls, user_id, email, full_name, role='user'):
        """
        Creates a unique cryptographically secure 48-character hex session token.
        """
        token = secrets.token_hex(24)
        expires_at = datetime.now() + timedelta(hours=SESSION_EXPIRY_HOURS)
        cls._sessions[token] = {
            'user_id': user_id,
            'email': email,
            'full_name': full_name,
            'role': role,
            'expires_at': expires_at
        }
        return token

    @classmethod
    def validate_session(cls, token):
        """
        Validates token existence and expiry.
        Returns user dictionary if valid, None if invalid or expired.
        """
        if not token or token not in cls._sessions:
            return None

        session_data = cls._sessions[token]
        if datetime.now() > session_data['expires_at']:
            del cls._sessions[token]
            return None

        return session_data

    @classmethod
    def destroy_session(cls, token):
        """
        Invalidates a session token upon user logout.
        """
        if token in cls._sessions:
            del cls._sessions[token]
            return True
        return False


class UserManager:
    """
    Core business logic controller for User operations:
    registration, credential verification, profile retrieval, and updates.
    """

    @staticmethod
    def hash_password(plain_password):
        """
        Hashes a plain-text password using SHA-256 with application secret salt.
        
        Parameters:
            plain_password (str): Raw password entered by the user.
            
        Returns:
            str: 64-character hexadecimal SHA-256 hash.
        """
        salted = f"{plain_password}{SECRET_SALT}".encode('utf-8')
        return hashlib.sha256(salted).hexdigest()

    @staticmethod
    def validate_registration_inputs(full_name, email, phone, password, age):
        """
        Validates format constraints for user registration details.
        
        Returns:
            tuple (bool, str): (True, "OK") if valid; (False, error_message) if invalid.
        """
        if not full_name or len(full_name.strip()) < 2:
            return False, "Full name must be at least 2 characters long."

        email_pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
        if not email or not re.match(email_pattern, email.strip()):
            return False, "Invalid email address format."

        phone_clean = re.sub(r'\D', '', str(phone or ''))
        if len(phone_clean) != 10:
            return False, "Phone number must be exactly 10 digits."

        if not password or len(password) < 6:
            return False, "Password must be at least 6 characters long."

        try:
            age_int = int(age)
            if age_int < 5 or age_int > 120:
                return False, "Age must be between 5 and 120 years."
        except (ValueError, TypeError):
            return False, "Age must be a valid integer."

        return True, "Valid"

    @classmethod
    def register_user(cls, full_name, email, phone, password, gender='Male', age=25):
        """
        Registers a new user into the railway_reservation database.
        
        Parameters:
            full_name (str): Passenger's full legal name.
            email (str): Unique contact email address.
            phone (str): 10-digit mobile number.
            password (str): Plain-text password to be hashed.
            gender (str): 'Male', 'Female', or 'Other'.
            age (int): Passenger's age.
            
        Returns:
            dict: Response object indicating success or failure message.
        """
        # Step 1: Input validation
        is_valid, err_msg = cls.validate_registration_inputs(full_name, email, phone, password, age)
        if not is_valid:
            return {"success": False, "error": err_msg}

        email = email.strip().lower()
        phone = re.sub(r'\D', '', str(phone).strip())

        # Step 2: Check for existing duplicate email or phone
        existing_query = "SELECT user_id, email, phone FROM users WHERE email = %s OR phone = %s"
        existing = Database.execute_query(existing_query, (email, phone), fetch_one=True)
        if existing:
            if existing['email'] == email:
                return {"success": False, "error": "An account with this email already exists."}
            if existing['phone'] == phone:
                return {"success": False, "error": "An account with this phone number already exists."}

        # Step 3: Hash password securely
        pwd_hash = cls.hash_password(password)

        # Step 4: Insert new user record
        insert_query = """
            INSERT INTO users (full_name, email, phone, password_hash, gender, age)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        try:
            new_id = Database.execute_query(
                insert_query,
                (full_name.strip(), email, phone, pwd_hash, gender, int(age)),
                commit=True
            )
            return {
                "success": True,
                "message": "User registered successfully! You may now log in.",
                "user_id": new_id
            }
        except Exception as e:
            return {"success": False, "error": f"Database insertion failed: {str(e)}"}

    @classmethod
    def login_user(cls, identifier, password):
        """
        Authenticates a user via Email or Mobile number and plain password.
        
        Parameters:
            identifier (str): User's registered email or 10-digit phone number.
            password (str): User's plain password.
            
        Returns:
            dict: Authentication status, user summary, and session token upon success.
        """
        if not identifier or not password:
            return {"success": False, "error": "Please provide both identifier and password."}

        identifier_clean = identifier.strip().lower()
        phone_clean = re.sub(r'\D', '', identifier.strip())

        # Query user record by email OR phone
        query = """
            SELECT user_id, full_name, email, phone, password_hash, gender, age, created_at
            FROM users
            WHERE email = %s OR phone = %s
        """
        user = Database.execute_query(query, (identifier_clean, phone_clean), fetch_one=True)

        if not user:
            return {"success": False, "error": "Invalid email/phone or password."}

        # Compute hash and compare
        provided_hash = cls.hash_password(password)
        if provided_hash != user['password_hash']:
            return {"success": False, "error": "Invalid email/phone or password."}

        # Issue session token
        session_token = SessionManager.create_session(
            user_id=user['user_id'],
            email=user['email'],
            full_name=user['full_name'],
            role='user'
        )

        # Sanitize sensitive fields before returning
        safe_user = {
            "user_id": user['user_id'],
            "full_name": user['full_name'],
            "email": user['email'],
            "phone": user['phone'],
            "gender": user['gender'],
            "age": user['age'],
            "created_at": str(user['created_at'])
        }

        return {
            "success": True,
            "message": "Login successful!",
            "session_token": session_token,
            "user": safe_user
        }

    @classmethod
    def get_user_by_id(cls, user_id):
        """
        Retrieves user public profile details by ID.
        """
        query = "SELECT user_id, full_name, email, phone, gender, age, created_at FROM users WHERE user_id = %s"
        user = Database.execute_query(query, (user_id,), fetch_one=True)
        if user and 'created_at' in user:
            user['created_at'] = str(user['created_at'])
        return user

    @classmethod
    def update_profile(cls, user_id, full_name, phone, gender, age):
        """
        Updates an existing user's contact and demographic profile.
        """
        phone_clean = re.sub(r'\D', '', str(phone).strip())
        if len(phone_clean) != 10:
            return {"success": False, "error": "Phone number must be exactly 10 digits."}

        # Ensure phone is not taken by another user
        dup_query = "SELECT user_id FROM users WHERE phone = %s AND user_id != %s"
        existing = Database.execute_query(dup_query, (phone_clean, user_id), fetch_one=True)
        if existing:
            return {"success": False, "error": "This phone number is already registered by another account."}

        update_query = """
            UPDATE users
            SET full_name = %s, phone = %s, gender = %s, age = %s
            WHERE user_id = %s
        """
        try:
            Database.execute_query(update_query, (full_name.strip(), phone_clean, gender, int(age), user_id), commit=True)
            return {"success": True, "message": "Profile updated successfully!"}
        except Exception as e:
            return {"success": False, "error": f"Failed to update profile: {str(e)}"}
