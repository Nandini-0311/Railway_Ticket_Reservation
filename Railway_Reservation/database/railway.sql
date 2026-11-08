-- ==============================================================
-- RAILWAY TICKET RESERVATION SYSTEM
-- Database: railway_reservation
-- ==============================================================

CREATE DATABASE IF NOT EXISTS railway_reservation;
USE railway_reservation;

-- Drop existing tables if re-importing (in correct foreign key order)
DROP TABLE IF EXISTS cancellations;
DROP TABLE IF EXISTS payments;
DROP TABLE IF EXISTS passengers;
DROP TABLE IF EXISTS bookings;
DROP TABLE IF EXISTS seat_inventory;
DROP TABLE IF EXISTS schedules;
DROP TABLE IF EXISTS routes;
DROP TABLE IF EXISTS trains;
DROP TABLE IF EXISTS stations;
DROP TABLE IF EXISTS admin;
DROP TABLE IF EXISTS users;

-- 1. USERS TABLE
CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    phone VARCHAR(15) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    gender ENUM('Male', 'Female', 'Other') DEFAULT 'Male',
    age INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_email (email),
    INDEX idx_user_phone (phone)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2. ADMIN TABLE
CREATE TABLE admin (
    admin_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_admin_username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 3. STATIONS TABLE
CREATE TABLE stations (
    station_id INT AUTO_INCREMENT PRIMARY KEY,
    station_code VARCHAR(10) NOT NULL UNIQUE,
    station_name VARCHAR(100) NOT NULL,
    city VARCHAR(50) NOT NULL,
    state VARCHAR(50) NOT NULL,
    INDEX idx_station_code (station_code),
    INDEX idx_station_city (city)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 4. TRAINS TABLE
CREATE TABLE trains (
    train_id INT AUTO_INCREMENT PRIMARY KEY,
    train_number VARCHAR(10) NOT NULL UNIQUE,
    train_name VARCHAR(100) NOT NULL,
    source_station_id INT NOT NULL,
    destination_station_id INT NOT NULL,
    train_type VARCHAR(50) DEFAULT 'Superfast Express',
    total_seats_sl INT NOT NULL DEFAULT 120,
    total_seats_3a INT NOT NULL DEFAULT 64,
    total_seats_2a INT NOT NULL DEFAULT 48,
    total_seats_1a INT NOT NULL DEFAULT 24,
    base_fare_sl DECIMAL(10,2) NOT NULL DEFAULT 450.00,
    base_fare_3a DECIMAL(10,2) NOT NULL DEFAULT 1150.00,
    base_fare_2a DECIMAL(10,2) NOT NULL DEFAULT 1750.00,
    base_fare_1a DECIMAL(10,2) NOT NULL DEFAULT 2850.00,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    FOREIGN KEY (source_station_id) REFERENCES stations(station_id) ON UPDATE CASCADE,
    FOREIGN KEY (destination_station_id) REFERENCES stations(station_id) ON UPDATE CASCADE,
    INDEX idx_train_number (train_number),
    INDEX idx_train_stations (source_station_id, destination_station_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 5. ROUTES TABLE
CREATE TABLE routes (
    route_id INT AUTO_INCREMENT PRIMARY KEY,
    train_id INT NOT NULL,
    station_id INT NOT NULL,
    stop_number INT NOT NULL,
    arrival_time TIME NULL,
    departure_time TIME NULL,
    distance_km INT NOT NULL DEFAULT 0,
    FOREIGN KEY (train_id) REFERENCES trains(train_id) ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (station_id) REFERENCES stations(station_id) ON UPDATE CASCADE,
    UNIQUE KEY uq_train_stop (train_id, stop_number),
    UNIQUE KEY uq_train_station (train_id, station_id),
    INDEX idx_route_train (train_id),
    INDEX idx_route_station (station_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 6. SCHEDULES TABLE
CREATE TABLE schedules (
    schedule_id INT AUTO_INCREMENT PRIMARY KEY,
    train_id INT NOT NULL,
    runs_on_mon BOOLEAN NOT NULL DEFAULT TRUE,
    runs_on_tue BOOLEAN NOT NULL DEFAULT TRUE,
    runs_on_wed BOOLEAN NOT NULL DEFAULT TRUE,
    runs_on_thu BOOLEAN NOT NULL DEFAULT TRUE,
    runs_on_fri BOOLEAN NOT NULL DEFAULT TRUE,
    runs_on_sat BOOLEAN NOT NULL DEFAULT TRUE,
    runs_on_sun BOOLEAN NOT NULL DEFAULT TRUE,
    departure_time TIME NOT NULL,
    arrival_time TIME NOT NULL,
    duration_hours DECIMAL(4,2) NOT NULL,
    FOREIGN KEY (train_id) REFERENCES trains(train_id) ON DELETE CASCADE ON UPDATE CASCADE,
    INDEX idx_schedule_train (train_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 7. SEAT INVENTORY TABLE (Per Date & Class Availability)
CREATE TABLE seat_inventory (
    inventory_id INT AUTO_INCREMENT PRIMARY KEY,
    train_id INT NOT NULL,
    journey_date DATE NOT NULL,
    class_type ENUM('SL', '3A', '2A', '1A') NOT NULL,
    available_seats INT NOT NULL,
    fare DECIMAL(10,2) NOT NULL,
    FOREIGN KEY (train_id) REFERENCES trains(train_id) ON DELETE CASCADE ON UPDATE CASCADE,
    UNIQUE KEY uq_train_date_class (train_id, journey_date, class_type),
    INDEX idx_inventory_lookup (train_id, journey_date, class_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 8. BOOKINGS TABLE
CREATE TABLE bookings (
    booking_id INT AUTO_INCREMENT PRIMARY KEY,
    pnr_number VARCHAR(10) NOT NULL UNIQUE,
    user_id INT NOT NULL,
    train_id INT NOT NULL,
    source_station_id INT NOT NULL,
    destination_station_id INT NOT NULL,
    journey_date DATE NOT NULL,
    class_type ENUM('SL', '3A', '2A', '1A') NOT NULL,
    total_passengers INT NOT NULL,
    total_fare DECIMAL(10,2) NOT NULL,
    booking_status ENUM('CONFIRMED', 'CANCELLED') NOT NULL DEFAULT 'CONFIRMED',
    booked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON UPDATE CASCADE,
    FOREIGN KEY (train_id) REFERENCES trains(train_id) ON UPDATE CASCADE,
    FOREIGN KEY (source_station_id) REFERENCES stations(station_id) ON UPDATE CASCADE,
    FOREIGN KEY (destination_station_id) REFERENCES stations(station_id) ON UPDATE CASCADE,
    INDEX idx_booking_pnr (pnr_number),
    INDEX idx_booking_user (user_id),
    INDEX idx_booking_train_date (train_id, journey_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 9. PASSENGERS TABLE
CREATE TABLE passengers (
    passenger_id INT AUTO_INCREMENT PRIMARY KEY,
    booking_id INT NOT NULL,
    passenger_name VARCHAR(100) NOT NULL,
    age INT NOT NULL,
    gender ENUM('Male', 'Female', 'Other') NOT NULL,
    seat_number VARCHAR(10) NOT NULL,
    berth_preference ENUM('Lower', 'Middle', 'Upper', 'Side Lower', 'Side Upper', 'Window') DEFAULT 'Lower',
    FOREIGN KEY (booking_id) REFERENCES bookings(booking_id) ON DELETE CASCADE ON UPDATE CASCADE,
    INDEX idx_passenger_booking (booking_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 10. PAYMENTS TABLE (Simulated Payment)
CREATE TABLE payments (
    payment_id INT AUTO_INCREMENT PRIMARY KEY,
    booking_id INT NOT NULL,
    transaction_id VARCHAR(50) NOT NULL UNIQUE,
    payment_method ENUM('UPI', 'DEBIT_CARD', 'CREDIT_CARD', 'NET_BANKING') NOT NULL DEFAULT 'UPI',
    amount DECIMAL(10,2) NOT NULL,
    payment_status ENUM('SUCCESS', 'FAILED', 'REFUNDED') NOT NULL DEFAULT 'SUCCESS',
    payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (booking_id) REFERENCES bookings(booking_id) ON DELETE CASCADE ON UPDATE CASCADE,
    INDEX idx_payment_booking (booking_id),
    INDEX idx_payment_txnid (transaction_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 11. CANCELLATIONS TABLE
CREATE TABLE cancellations (
    cancellation_id INT AUTO_INCREMENT PRIMARY KEY,
    booking_id INT NOT NULL,
    pnr_number VARCHAR(10) NOT NULL,
    refund_amount DECIMAL(10,2) NOT NULL,
    cancellation_charge DECIMAL(10,2) NOT NULL,
    cancelled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    cancellation_reason VARCHAR(255) DEFAULT 'User requested cancellation',
    FOREIGN KEY (booking_id) REFERENCES bookings(booking_id) ON UPDATE CASCADE,
    INDEX idx_cancel_booking (booking_id),
    INDEX idx_cancel_pnr (pnr_number)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ==============================================================
-- INSERT INITIAL SEED DATA
-- ==============================================================

-- Default Admin Account (Password: admin123 -> SHA256 hashed)
INSERT INTO admin (username, email, password_hash, full_name) VALUES
('admin', 'admin@railway.local', '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9', 'System Administrator');

-- Default Traveler Account (Password: traveler123 -> salted SHA256 hashed)
INSERT INTO users (full_name, email, phone, password_hash, gender, age) VALUES
('Rajesh Sharma', 'traveler@example.com', '9876543210', '2a9afe2a178922c401cc8edf7bb828688b9edccd9f1b2868cb14e79ff8d29884', 'Male', 28);

-- Sample Stations across major Indian routes
INSERT INTO stations (station_code, station_name, city, state) VALUES
('NDLS', 'New Delhi Railway Station', 'New Delhi', 'Delhi'),
('BCT',  'Mumbai Central', 'Mumbai', 'Maharashtra'),
('HWH',  'Howrah Junction', 'Kolkata', 'West Bengal'),
('MAS',  'Chennai Central', 'Chennai', 'Tamil Nadu'),
('SBC',  'KSR Bengaluru City', 'Bengaluru', 'Karnataka'),
('CNB',  'Kanpur Central', 'Kanpur', 'Uttar Pradesh'),
('PRYJ', 'Prayagraj Junction', 'Prayagraj', 'Uttar Pradesh'),
('BRC',  'Vadodara Junction', 'Vadodara', 'Gujarat'),
('BPL',  'Bhopal Junction', 'Bhopal', 'Madhya Pradesh'),
('NGP',  'Nagpur Junction', 'Nagpur', 'Maharashtra');

-- Sample Trains
INSERT INTO trains (train_number, train_name, source_station_id, destination_station_id, train_type, total_seats_sl, total_seats_3a, total_seats_2a, total_seats_1a, base_fare_sl, base_fare_3a, base_fare_2a, base_fare_1a) VALUES
('12952', 'Mumbai Rajdhani Express', 1, 2, 'Rajdhani Express', 120, 64, 48, 24, 650.00, 1650.00, 2450.00, 3950.00),
('12951', 'New Delhi Rajdhani Express', 2, 1, 'Rajdhani Express', 120, 64, 48, 24, 650.00, 1650.00, 2450.00, 3950.00),
('12301', 'Howrah Rajdhani Express', 3, 1, 'Rajdhani Express', 120, 64, 48, 24, 680.00, 1720.00, 2520.00, 4100.00),
('12302', 'Kolkata Rajdhani Express', 1, 3, 'Rajdhani Express', 120, 64, 48, 24, 680.00, 1720.00, 2520.00, 4100.00),
('12622', 'Tamil Nadu Express', 1, 4, 'Superfast Express', 140, 72, 48, 24, 520.00, 1420.00, 2150.00, 3600.00),
('12621', 'Tamil Nadu Superfast', 4, 1, 'Superfast Express', 140, 72, 48, 24, 520.00, 1420.00, 2150.00, 3600.00),
('22692', 'Bengaluru Rajdhani Express', 1, 5, 'Rajdhani Express', 120, 64, 48, 24, 710.00, 1850.00, 2750.00, 4400.00),
('12004', 'Lucknow Shatabdi Express', 1, 6, 'Shatabdi Express', 0, 80, 50, 20, 0.00, 780.00, 1350.00, 2100.00);

-- Train Schedules (Timings & Run Days)
INSERT INTO schedules (train_id, runs_on_mon, runs_on_tue, runs_on_wed, runs_on_thu, runs_on_fri, runs_on_sat, runs_on_sun, departure_time, arrival_time, duration_hours) VALUES
(1, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, '16:55:00', '08:35:00', 15.67),
(2, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, '17:00:00', '08:32:00', 15.53),
(3, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, FALSE, '16:50:00', '10:05:00', 17.25),
(4, TRUE, TRUE, TRUE, TRUE, TRUE, FALSE, TRUE, '16:55:00', '09:55:00', 17.00),
(5, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, '21:05:00', '06:15:00', 33.17),
(6, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, '22:00:00', '07:05:00', 33.08),
(7, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, '20:45:00', '05:20:00', 32.58),
(8, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, '06:10:00', '11:40:00', 5.50);

-- Intermediate Routes for Train 1 (NDLS -> BCT)
INSERT INTO routes (train_id, station_id, stop_number, arrival_time, departure_time, distance_km) VALUES
(1, 1, 1, NULL, '16:55:00', 0),
(1, 8, 2, '03:10:00', '03:18:00', 992),
(1, 2, 3, '08:35:00', NULL, 1386);

-- Intermediate Routes for Train 3 (HWH -> NDLS)
INSERT INTO routes (train_id, station_id, stop_number, arrival_time, departure_time, distance_km) VALUES
(3, 3, 1, NULL, '16:50:00', 0),
(3, 7, 2, '00:45:00', '00:50:00', 820),
(3, 6, 3, '02:40:00', '02:45:00', 1015),
(3, 1, 4, '10:05:00', NULL, 1451);
