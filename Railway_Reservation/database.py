"""
Project: Railway Ticket Reservation System
File: database.py
Purpose: Database connectivity layer and query execution engine using mysql-connector-python.
         Provides parameterized query execution to safeguard against SQL injection and
         supports atomic transactions for ticket booking and cancellations.
"""

import mysql.connector
from mysql.connector import Error
from config import DB_CONFIG


class Database:
    """
    Database management class providing static and instance methods for
    connecting to MySQL, executing queries safely, and managing transactions.
    """

    @staticmethod
    def get_connection():
        """
        Establishes and returns a fresh MySQL connection.
        
        Returns:
            mysql.connector.connection.MySQLConnection: Active database connection.
            
        Raises:
            Exception: If connection to MySQL fails.
        """
        try:
            connection = mysql.connector.connect(**DB_CONFIG)
            return connection
        except Error as err:
            print(f"[Database Error] Connection failed: {err}")
            raise

    @classmethod
    def execute_query(cls, query, params=None, fetch_one=False, fetch_all=False, commit=False):
        """
        Executes a single parameterized SQL query safely.
        
        Parameters:
            query (str): Parameterized SQL query containing %s placeholders.
            params (tuple|list|dict, optional): Values to bind to placeholders.
            fetch_one (bool): If True, returns a single matched row as a dict.
            fetch_all (bool): If True, returns all matched rows as a list of dicts.
            commit (bool): If True, commits the transaction immediately (for INSERT/UPDATE/DELETE).
            
        Returns:
            dict | list | int | None:
                - Single dictionary if fetch_one is True.
                - List of dictionaries if fetch_all is True.
                - Generated lastrowid if commit is True and query is an INSERT.
                - Number of affected rows if commit is True and query is UPDATE/DELETE.
                - None if an error occurs.
        """
        conn = None
        cursor = None
        try:
            conn = cls.get_connection()
            # dictionary=True ensures records are returned as key-value pairs
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, params or ())

            if fetch_one:
                result = cursor.fetchone()
                return result

            if fetch_all:
                result = cursor.fetchall()
                return result

            if commit:
                conn.commit()
                # If an INSERT statement was executed, return the newly generated auto_increment ID
                if cursor.lastrowid:
                    return cursor.lastrowid
                return cursor.rowcount

            return None

        except Error as err:
            print(f"[Database Error] Query Execution Failed: {err}")
            if conn and commit:
                try:
                    conn.rollback()
                except Exception:
                    pass
            raise
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    @classmethod
    def check_connection(cls):
        """
        Pings MySQL database to verify that the server is up and accessible.
        
        Returns:
            bool: True if connection is healthy, False otherwise.
        """
        try:
            conn = cls.get_connection()
            if conn.is_connected():
                conn.close()
                return True
            return False
        except Exception:
            return False
