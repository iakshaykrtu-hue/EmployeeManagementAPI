import sqlite3
from getpass import getpass
from pwdlib import PasswordHash

from database import DATABASE_PATH

# Password hashing configuration
password_hash = PasswordHash.recommended()

# Get admin credentials
username = input("Enter admin username: ").strip()
password = getpass("Enter admin password: ")

if not username or not password:
    print("Username and password cannot be empty.")
    raise SystemExit

# Hash the password
hashed_password = password_hash.hash(password)

# Save admin account in SQLite
connection = sqlite3.connect(DATABASE_PATH)

try:
    connection.execute(
        """
        INSERT INTO users (username, password_hash, role)
        VALUES (?, ?, ?)
        """,
        (username, hashed_password, "admin")
    )

    connection.commit()
    print("Admin account created successfully!")

except sqlite3.IntegrityError:
    print("This username already exists.")

finally:
    connection.close()