
import sqlite3

import pytest
from fastapi.testclient import TestClient
from pwdlib import PasswordHash

from main import app
from database import get_db


password_hash = PasswordHash.recommended()

ADMIN_PASSWORD = "TestAdmin123!"
EMPLOYEE_PASSWORD = "TestEmployee123!"


# Create a fresh test database for every test
@pytest.fixture
def client(tmp_path):

    db_path = tmp_path / "test_employees.db"

    connection = sqlite3.connect(db_path)

    connection.execute("""
        CREATE TABLE employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            department TEXT NOT NULL,
            salary REAL NOT NULL
        )
    """)

    connection.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'admin',
            employee_id INTEGER
        )
    """)

    # Sample employees
    connection.execute("""
        INSERT INTO employees (name, email, department, salary)
        VALUES (?, ?, ?, ?)
    """, ("Akshay", "akshay@test.com", "IT", 50000))

    connection.execute("""
        INSERT INTO employees (name, email, department, salary)
        VALUES (?, ?, ?, ?)
    """, ("Test User", "testuser@test.com", "HR", 40000))

    # Sample admin account
    connection.execute("""
        INSERT INTO users (username, password_hash, role, employee_id)
        VALUES (?, ?, ?, ?)
    """, (
        "admin",
        password_hash.hash(ADMIN_PASSWORD),
        "admin",
        None
    ))

    # Sample employee account
    connection.execute("""
        INSERT INTO users (username, password_hash, role, employee_id)
        VALUES (?, ?, ?, ?)
    """, (
        "Akshay",
        password_hash.hash(EMPLOYEE_PASSWORD),
        "employee",
        1
    ))

    connection.commit()
    connection.close()

    # Override the application's database dependency
    def override_get_db():
        db = sqlite3.connect(db_path)
        db.row_factory = sqlite3.Row

        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    # Restore the original dependency
    app.dependency_overrides.clear()


# Helper function: Admin login
def get_admin_token(client):
    response = client.post(
        "/login",
        data={
            "username": "admin",
            "password": ADMIN_PASSWORD
        }
    )

    assert response.status_code == 200
    return response.json()["access_token"]


# Helper function: Employee login
def get_employee_token(client):
    response = client.post(
        "/login",
        data={
            "username": "Akshay",
            "password": EMPLOYEE_PASSWORD
        }
    )

    assert response.status_code == 200
    return response.json()["access_token"]


# TEST 1: Home endpoint
def test_root_endpoint(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["message"] == (
        "Welcome to Employee Management API"
    )


# TEST 2: Admin login
def test_admin_login(client):
    token = get_admin_token(client)

    assert token is not None


# TEST 3: Employee login
def test_employee_login(client):
    token = get_employee_token(client)

    assert token is not None


# TEST 4: Invalid login
def test_invalid_login(client):
    response = client.post(
        "/login",
        data={
            "username": "admin",
            "password": "WrongPassword"
        }
    )

    assert response.status_code == 401


# TEST 5: Access without authentication
def test_access_without_token(client):
    response = client.get("/employees")

    assert response.status_code == 401


# TEST 6: Admin can view all employees
def test_admin_get_employees(client):
    token = get_admin_token(client)

    response = client.get(
        "/employees",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    assert len(response.json()) == 2


# TEST 7: Employee can view only own record
def test_employee_get_own_record(client):
    token = get_employee_token(client)

    response = client.get(
        "/employees",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == 1


# TEST 8: Employee cannot view another employee
def test_employee_cannot_view_other_record(client):
    token = get_employee_token(client)

    response = client.get(
        "/employees/2",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 403


# TEST 9: Admin can add an employee
def test_admin_add_employee(client):
    token = get_admin_token(client)

    response = client.post(
        "/employees",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "New Employee",
            "email": "newemployee@test.com",
            "department": "Finance",
            "salary": 45000
        }
    )

    assert response.status_code == 201


# TEST 10: Employee cannot add an employee
def test_employee_cannot_add_employee(client):
    token = get_employee_token(client)

    response = client.post(
        "/employees",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Another Employee",
            "email": "another@test.com",
            "department": "IT",
            "salary": 40000
        }
    )

    assert response.status_code == 403


# TEST 11: Duplicate email prevention
def test_duplicate_email(client):
    token = get_admin_token(client)

    response = client.post(
        "/employees",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Duplicate User",
            "email": "akshay@test.com",
            "department": "IT",
            "salary": 30000
        }
    )

    assert response.status_code == 409


# TEST 12: Admin can update employee using PUT
def test_admin_update_employee(client):
    token = get_admin_token(client)

    response = client.put(
        "/employees/1",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Akshay Updated",
            "email": "akshayupdated@test.com",
            "department": "Cloud",
            "salary": 60000
        }
    )

    assert response.status_code == 200


# TEST 13: Employee cannot use PUT
def test_employee_cannot_use_put(client):
    token = get_employee_token(client)

    response = client.put(
        "/employees/1",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Akshay Updated",
            "email": "akshayupdated@test.com",
            "department": "Cloud",
            "salary": 60000
        }
    )

    assert response.status_code == 403


# TEST 14: Employee can update own profile
def test_employee_update_own_profile(client):
    token = get_employee_token(client)

    response = client.patch(
        "/employees/1",
        headers={"Authorization": f"Bearer {token}"},
        json={"department": "Networking"}
    )

    assert response.status_code == 200


# TEST 15: Employee cannot update salary
def test_employee_cannot_update_salary(client):
    token = get_employee_token(client)

    response = client.patch(
        "/employees/1",
        headers={"Authorization": f"Bearer {token}"},
        json={"salary": 90000}
    )

    assert response.status_code == 403


# TEST 16: Employee cannot update another employee
def test_employee_cannot_update_other_profile(client):
    token = get_employee_token(client)

    response = client.patch(
        "/employees/2",
        headers={"Authorization": f"Bearer {token}"},
        json={"department": "Finance"}
    )

    assert response.status_code == 403


# TEST 17: Admin can partially update salary
def test_admin_patch_salary(client):
    token = get_admin_token(client)

    response = client.patch(
        "/employees/1",
        headers={"Authorization": f"Bearer {token}"},
        json={"salary": 75000}
    )

    assert response.status_code == 200


# TEST 18: Empty PATCH request
def test_empty_patch(client):
    token = get_admin_token(client)

    response = client.patch(
        "/employees/1",
        headers={"Authorization": f"Bearer {token}"},
        json={}
    )

    assert response.status_code == 400


# TEST 19: Admin can delete employee
def test_admin_delete_employee(client):
    token = get_admin_token(client)

    response = client.delete(
        "/employees/2",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200


# TEST 20: Employee cannot delete employee
def test_employee_cannot_delete(client):
    token = get_employee_token(client)

    response = client.delete(
        "/employees/1",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 403
