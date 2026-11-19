
import sqlite3
from getpass import getpass
from pwdlib import PasswordHash

from database import DATABASE_PATH

password_hash = PasswordHash.recommended()

username = input("Enter employee username: ").strip()
password = getpass("Enter employee password: ")

if not username or not password:
    print("Username and password cannot be empty.")
    raise SystemExit

hashed_password = password_hash.hash(password)

connection = sqlite3.connect(DATABASE_PATH)

try:
    connection.execute(
        """
        INSERT INTO users (username, password_hash, role)
        VALUES (?, ?, ?)
        """,
        (username, hashed_password, "employee")
    )

    connection.commit()
    print("Employee account created successfully!")

except sqlite3.IntegrityError:
    print("This username already exists.")

finally:
    connection.close()
