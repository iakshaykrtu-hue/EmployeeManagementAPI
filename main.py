import os
from dotenv import load_dotenv


load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")

if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY is missing from .env file")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


from fastapi import FastAPI, HTTPException, Depends, Query
from pydantic import BaseModel, Field, EmailStr
import sqlite3

from database import get_db, init_db
from pwdlib import PasswordHash
import jwt
from datetime import datetime, timedelta, timezone
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

app = FastAPI()
init_db()

# Authentication configuration
password_hash = PasswordHash.recommended()


ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


@app.post("/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: sqlite3.Connection = Depends(get_db)
):
    cursor = db.execute(
        "SELECT * FROM users WHERE username = ?",
        (form_data.username,)
    )

    user = cursor.fetchone()

    if user is None or not password_hash.verify(
        form_data.password,
        user["password_hash"]
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )

    expire = datetime.now(timezone.utc) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    token = jwt.encode(
        {
            "sub": user["username"],
            "role": user["role"],
            "exp": expire
        },
        SECRET_KEY,
        algorithm=ALGORITHM
    )

    return {
        "access_token": token,
        "token_type": "bearer"
    }



# Verify JWT token and identify logged-in user
def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: sqlite3.Connection = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"}
    )

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        username = payload.get("sub")

        if username is None:
            raise credentials_exception

    except jwt.InvalidTokenError:
        raise credentials_exception

    cursor = db.execute(
        """
        SELECT id, username, role, employee_id
        FROM users
        WHERE username = ?
        """,
        (username,)
    )

    user = cursor.fetchone()

    if user is None:
        raise credentials_exception

    return dict(user)



# Verify that the logged-in user is an admin
def get_admin_user(
    current_user: dict = Depends(get_current_user)
):
    if current_user["role"] != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )

    return current_user  

# Employee data validation
class Employee(BaseModel):
    name: str = Field(min_length=2)
    email: EmailStr
    department: str
    salary: float = Field(gt=0)

# Model for partial updates
class EmployeeUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2)
    email: EmailStr | None = None
    department: str | None = None
    salary: float | None = Field(default=None, gt=0)


# Home API
@app.get("/")
def home():
    return {
        "message": "Welcome to Employee Management API"
    }


# GET - Retrieve, filter and paginate employees
@app.get("/employees")
def get_employees(
    name: str | None = None,
    department: str | None = None,
    min_salary: float | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=5, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db)
):
    query = "SELECT * FROM employees WHERE 1=1"
    values = []

    # Employees can only view their own record
    if current_user["role"] == "employee":
        query += " AND id = ?"
        values.append(current_user["employee_id"])

    if name:
        query += " AND name LIKE ?"
        values.append(f"%{name}%")

    if department:
        query += " AND department = ?"
        values.append(department)

    if min_salary is not None:
        query += " AND salary >= ?"
        values.append(min_salary)

    query += " ORDER BY id LIMIT ? OFFSET ?"
    values.extend([limit, skip])

    cursor = db.execute(query, values)
    employees = [dict(row) for row in cursor.fetchall()]

    return employees




# GET - Retrieve employee by ID
@app.get("/employees/{employee_id}")
def get_employee(
    employee_id: int,
    current_user: dict = Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db)
):
    # Employees can only access their own ID
    if (
        current_user["role"] == "employee"
        and current_user["employee_id"] != employee_id
    ):
        raise HTTPException(
            status_code=403,
            detail="You can only view your own employee profile"
        )

    cursor = db.execute(
        "SELECT * FROM employees WHERE id = ?",
        (employee_id,)
    )

    employee = cursor.fetchone()

    if employee is None:
        raise HTTPException(
            status_code=404,
            detail="Employee not found"
        )

    return dict(employee)



# POST - Add employee
@app.post("/employees", status_code=201)
def add_employee(
    employee: Employee,
    current_user: dict = Depends(get_admin_user),
    db: sqlite3.Connection = Depends(get_db)
):
    try:
        cursor = db.execute(
            """
            INSERT INTO employees (name, email, department, salary)
            VALUES (?, ?, ?, ?)
            """,
            (
                employee.name,
                employee.email,
                employee.department,
                employee.salary
            )
        )

        db.commit()

        new_id = cursor.lastrowid

        return {
            "message": "Employee added successfully",
            "employee_id": new_id
        }

    except sqlite3.IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Email already exists"
        )



# PUT - Update complete employee record
@app.put("/employees/{employee_id}")
def update_employee(
    employee_id: int,
    employee: Employee,
    current_user: dict = Depends(get_admin_user),
    db: sqlite3.Connection = Depends(get_db)
):
    try:
        cursor = db.execute(
            """
            UPDATE employees
            SET name = ?, email = ?, department = ?, salary = ?
            WHERE id = ?
            """,
            (
                employee.name,
                employee.email,
                employee.department,
                employee.salary,
                employee_id
            )
        )

        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=404,
                detail="Employee not found"
            )

        db.commit()

        return {"message": "Employee updated successfully"}

    except sqlite3.IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Email already exists"
        )


# PATCH - Update employee details with role-based permissions
@app.patch("/employees/{employee_id}")
def partial_update_employee(
    employee_id: int,
    employee: EmployeeUpdate,
    current_user: dict = Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db)
):
    # Check employee ownership
    if (
        current_user["role"] == "employee"
        and current_user["employee_id"] != employee_id
    ):
        raise HTTPException(
            status_code=403,
            detail="You can only update your own profile"
        )

    # Get fields provided in the request
    update_data = employee.model_dump(
        exclude_unset=True,
        exclude_none=True
    )

    if not update_data:
        raise HTTPException(
            status_code=400,
            detail="No fields provided"
        )

    # Employees cannot update salary
    if (
        current_user["role"] == "employee"
        and "salary" in update_data
    ):
        raise HTTPException(
            status_code=403,
            detail="Employees cannot update salary"
        )

    allowed_fields = {"name", "email", "department", "salary"}

    if not set(update_data).issubset(allowed_fields):
        raise HTTPException(
            status_code=400,
            detail="Invalid fields"
        )

    assignments = ", ".join(
        f"{field} = ?" for field in update_data
    )

    values = list(update_data.values()) + [employee_id]

    try:
        cursor = db.execute(
            f"UPDATE employees SET {assignments} WHERE id = ?",
            values
        )

        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=404,
                detail="Employee not found"
            )

        db.commit()

        return {
            "message": "Employee details updated successfully"
        }

    except sqlite3.IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Email already exists"
        )

# DELETE - Remove employee
@app.delete("/employees/{employee_id}")
def delete_employee(
    employee_id: int,
    current_user: dict = Depends(get_admin_user),
    db: sqlite3.Connection = Depends(get_db)
):

    cursor = db.execute(
        "DELETE FROM employees WHERE id = ?",
        (employee_id,)
    )

    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Employee not found")

    db.commit()

    return {"message": "Employee deleted successfully"}
