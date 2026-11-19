
import sqlite3
from pathlib import Path

# Database file location
DATABASE_PATH = Path(__file__).resolve().parent / "employees.db"


# Database connection
def get_db():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row

    try:
        yield connection
    finally:
        connection.close()


# Initialize database and create tables
def init_db():

    connection = sqlite3.connect(DATABASE_PATH)

    try:
        # 1. Create employees table
        connection.execute("""
            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                department TEXT NOT NULL,
                salary REAL NOT NULL
            )
        """)

        # 2. Prevent duplicate employee emails
        connection.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_employees_email
            ON employees(email)
        """)

        # 3. Create users table
        connection.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'admin'
            )
        """)

        # 4. Check whether employee_id column exists
        columns = connection.execute(
            "PRAGMA table_info(users)"
        ).fetchall()

        existing_columns = [column[1] for column in columns]

        # 5. Add employee_id if missing
        if "employee_id" not in existing_columns:
            connection.execute("""
                ALTER TABLE users
                ADD COLUMN employee_id INTEGER
            """)

        connection.commit()

        print("Database initialized successfully!")

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()
