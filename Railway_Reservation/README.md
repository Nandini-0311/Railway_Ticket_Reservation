# Railway Ticket Reservation System

A complete, advanced-level BCA final-year college project built with **Core Python (`http.server`)**, **MySQL (`mysql-connector-python`)**, and **vanilla HTML5, CSS3, and JavaScript**.

This application implements a complete railway reservation portal without third-party frameworks like Flask, Django, or FastAPI, relying strictly on native Python standard libraries and object-oriented programming.

---

## 🌟 Key Features

### 1. Passenger / User Module
* **User Registration & Profile:** Secure account creation with validation for email and 10-digit phone numbers.
* **Authentication & Password Hashing:** Salted SHA-256 password encryption; cryptographic session token management.
* **Train Search:** Search by origin, destination, and journey date. Supports direct and intermediate route trains.
* **Day-of-Week Schedule Verification:** Validates whether a train runs on the selected day of the week.
* **Class & Fare Selection:** Real-time seat availability and fare calculation for **Sleeper (SL)**, **AC 3 Tier (3A)**, **AC 2 Tier (2A)**, and **AC First Class (1A)** in Indian Rupees (₹).
* **Multi-Passenger Booking:** Accommodates 1 to 6 passengers per booking with coach and seat number allotment (e.g. `B1-12`, `B1-13`).
* **10-Digit Unique PNR Generation:** Generates authentic 10-digit PNR numbers conforming to Indian Railway formatting.
* **Simulated Payment Gateway:** Mock payment processing with unique transaction IDs (`TXN_...`).
* **Electronic Reservation Slip (ERS):** Printable confirmed ticket with passenger chart and QR/barcode styling.
* **Live PNR Enquiry:** Public lookup tool for real-time reservation status.
* **One-Click Ticket Cancellation:** Automatic 15% cancellation charge deduction, 85% refund disbursement, and instant seat inventory restoration.
* **Booking History:** User dashboard summarizing lifetime trips, active trips, and cancellations.

### 2. Administrator Module
* **Secure Admin Login:** Dedicated administrator authentication.
* **Dashboard Analytics:** Live KPIs including total registered trains, traveler accounts, confirmed bookings, cancellations, gross revenue, refunds, and net revenue.
* **Train CRUD:** Add new trains with schedules, update operating times, or soft-delete trains.
* **Station Directory:** Register new stations and modify station codes.
* **Bookings & Cancellation Audit:** Filter and review all bookings across the portal.
* **Passenger Manifest:** View passenger charts for any train on a specific journey date.
* **Financial Reports:** Class-wise occupancy and train-wise ticket revenue rankings.

---

## 🏗️ Project Architecture & Technologies

* **Backend:** Core Python 3.10+ (Built-in `http.server`, `urllib.parse`, `json`, `hashlib`, `secrets`)
* **Database:** MySQL 8.0 / MariaDB (`mysql-connector-python`)
* **Frontend:** HTML5, CSS3 (Custom Railway Theme), Vanilla JavaScript
* **Database Design:** 11 Normalized Tables (3rd Normal Form - 3NF) with Foreign Key constraints and ACID transactions.

---

## 📁 Project Folder Structure

```text
Railway_Reservation/
│
├── main.py                      # Application bootstrap script
├── server.py                    # Native http.server request router & static file handler
├── database.py                  # MySQL connection helper & parameterized query runner
├── config.py                    # Database credentials & application settings
├── requirements.txt             # Python dependencies (mysql-connector-python)
├── README.md                    # Project manual & documentation
├── PROJECT_REPORT.md            # Complete college submission project report
│
├── backend/
│   ├── __init__.py
│   ├── user.py                  # User registration, login & session manager
│   ├── train.py                 # Train directory, route search & seat inventory
│   ├── booking.py               # Ticket booking, 10-digit PNR & cancellation logic
│   ├── passenger.py             # Passenger validation & coach/seat allotment
│   ├── admin.py                 # Admin dashboard KPIs, train CRUD & reports
│   └── payment.py               # Mock payment gateway & transaction log
│
├── frontend/
│   ├── index.html               # Portal home page
│   ├── login.html               # Passenger login
│   ├── register.html            # User account registration
│   ├── search_train.html        # Train search interface
│   ├── train_results.html       # Train listings & class fare cards
│   ├── booking.html             # Multi-passenger form & payment
│   ├── ticket.html              # Confirmed e-ticket (Print-ready)
│   ├── pnr_status.html          # Public PNR lookup tool
│   ├── user_dashboard.html      # Traveler profile & quick stats
│   ├── booking_history.html     # My Trips & cancellation interface
│   ├── admin_login.html         # Staff login
│   └── admin_dashboard.html     # Administrator control center
│
├── css/
│   └── style.css                # Cohesive railway theme stylesheet
│
├── js/
│   └── validation.js            # Input validation & fetch API wrapper
│
├── database/
│   └── railway.sql              # Database schema & sample seed data
│
└── tests/
    ├── __init__.py
    ├── test_user.py             # Unit tests for User module
    ├── test_train.py            # Unit tests for Train module
    ├── test_booking.py          # Unit tests for Booking & Cancellation
    ├── test_admin.py            # Unit tests for Admin module
    └── test_server.py           # Integration tests for HTTP API
```

---

## 🚀 Installation & Running Instructions

### 1. Prerequisites
* **Python 3.10 or higher** installed.
* **MySQL Server** (or XAMPP / WampServer) running on port `3306`.

### 2. Clone or Extract the Project
Open a terminal in the project directory:
```bash
cd Railway_Reservation
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure MySQL Database
1. Start your MySQL service (e.g. via XAMPP Control Panel or MySQL Command Line).
2. Open `config.py` and verify your MySQL root password (default is empty `""` for XAMPP):
   ```python
   DB_CONFIG = {
       'host': 'localhost',
       'port': 3306,
       'user': 'root',
       'password': '',  # Update if you have a MySQL password
       'database': 'railway_reservation',
   }
   ```
3. Import the database schema and sample seed data:
   ```bash
   mysql -u root -p < database/railway.sql
   ```

### 5. Run Automated Tests
Verify that all backend modules pass the test suite:
```bash
py tests/test_user.py
py tests/test_train.py
py tests/test_booking.py
py tests/test_admin.py
py tests/test_server.py
```

### 6. Start the Web Server
Launch the application:
```bash
py main.py
```

Open your browser and navigate to:
* **Traveler Portal:** [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
* **Administrator Portal:** [http://127.0.0.1:8000/admin_login.html](http://127.0.0.1:8000/admin_login.html)
  * **Default Admin Username:** `admin`
  * **Default Admin Password:** `admin123`

---

## 🔒 Security & ACID Integrity
1. **SQL Injection Protection:** All database queries utilize parameterized placeholders (`%s`) handled by the database driver.
2. **Password Protection:** Cryptographic salted SHA-256 prevents plaintext exposure and dictionary attacks.
3. **Transaction Rollback:** If seat deduction, booking insertion, passenger record creation, or payment fails, `conn.rollback()` restores the database state atomically.
4. **Overbooking Prevention:** Database rows are locked using `SELECT ... FOR UPDATE` during booking transactions.

---

## 📜 Disclaimer
This software is developed strictly as an academic college project for educational demonstration. It is not affiliated with, authorized by, or associated with the Ministry of Railways (Government of India), IRCTC, or CRIS.
