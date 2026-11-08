"""
Project: Railway Ticket Reservation System
File: backend/payment.py
Purpose: Simulated payment gateway processing and transaction management.
         Generates mock transaction references and tracks payment statuses.
"""

import secrets
from datetime import datetime
from database import Database


class PaymentManager:
    """
    Simulated payment processing engine for academic final-year project.
    Provides mock settlement, transaction ID generation, and refund handling.
    """

    @staticmethod
    def generate_transaction_id():
        """
        Generates a unique mock banking transaction ID.
        Example format: TXN_20261104_A1B2C3D4
        """
        timestamp = datetime.now().strftime('%Y%m%d%H%M')
        random_suffix = secrets.token_hex(4).upper()
        return f"TXN_{timestamp}_{random_suffix}"

    @classmethod
    def process_payment(cls, booking_id, amount, payment_method='UPI', conn=None):
        """
        Records a successful simulated payment transaction.
        Can run within an active database transaction if 'conn' is provided.
        
        Parameters:
            booking_id (int): Foreign key reference to bookings table.
            amount (float): Total ticket fare amount in INR (₹).
            payment_method (str): 'UPI', 'DEBIT_CARD', 'CREDIT_CARD', or 'NET_BANKING'.
            conn (mysql.connector.connection, optional): Active transaction connection.
            
        Returns:
            dict: Payment summary with transaction ID.
        """
        valid_methods = ['UPI', 'DEBIT_CARD', 'CREDIT_CARD', 'NET_BANKING']
        if payment_method not in valid_methods:
            payment_method = 'UPI'

        txn_id = cls.generate_transaction_id()
        amount_clean = round(float(amount), 2)

        query = """
            INSERT INTO payments (booking_id, transaction_id, payment_method, amount, payment_status)
            VALUES (%s, %s, %s, %s, 'SUCCESS')
        """

        if conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, (booking_id, txn_id, payment_method, amount_clean))
            payment_id = cursor.lastrowid
            cursor.close()
        else:
            payment_id = Database.execute_query(
                query,
                (booking_id, txn_id, payment_method, amount_clean),
                commit=True
            )

        return {
            "payment_id": payment_id,
            "transaction_id": txn_id,
            "payment_method": payment_method,
            "amount": amount_clean,
            "payment_status": "SUCCESS"
        }

    @classmethod
    def get_payment_by_booking(cls, booking_id):
        """
        Retrieves payment details for a specific booking ID.
        """
        query = "SELECT * FROM payments WHERE booking_id = %s ORDER BY payment_id DESC LIMIT 1"
        res = Database.execute_query(query, (booking_id,), fetch_one=True)
        if res and 'amount' in res:
            res['amount'] = float(res['amount'])
            res['payment_date'] = str(res['payment_date'])
        return res
