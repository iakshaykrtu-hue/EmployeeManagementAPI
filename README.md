# Employee Management REST API

## Overview

A backend Employee Management System developed using Python and FastAPI. The application provides REST APIs for managing employee records, with JWT authentication and role-based access control.

## Technologies Used

- Python
- FastAPI
- SQLite
- Pydantic
- JWT Authentication
- Argon2 Password Hashing
- Uvicorn
- Python-dotenv

## Features

### Employee Management
- Create employee records
- Retrieve all employees
- Retrieve employee details by ID
- Update employee information
- Partially update employee information
- Delete employee records

### Authentication and Security
- Login using username and password
- JWT access token generation
- Token expiration and verification
- Password hashing using Argon2
- Role-based access control

### User Roles

**Admin**
- View all employee records
- Create employees
- Update employee details
- Update employee salaries
- Delete employees

**Employee**
- View their own employee profile
- Update their own profile using PATCH
- Cannot modify their salary
- Cannot access or modify other employees' records

### Additional Features
- Email validation
- Duplicate email prevention
- Employee search and filtering
- Pagination
- HTTP error handling

## Project Structure

```text
EmployeeManagementAPI/
│
├── create_admin.py
├── create_employee_user.py
├── database.py
├── db_models.py
├── main.py
├── .gitignore
├── README.md
└── requirements.txt
```

## Installation

### 1. Clone the repository

```bash
git clone YOUR_REPOSITORY_URL
cd EmployeeManagementAPI
```

### 2. Create a virtual environment

```bash
python -m venv venv
```

### 3. Activate the environment (Windows)

```powershell
.\venv\Scripts\Activate.ps1
```

### 4. Install dependencies

```bash
python -m pip install -r requirements.txt
```

### 5. Configure environment variables

Create a `.env` file in the project root:

```env
SECRET_KEY=YOUR_SECRET_KEY
```

Generate your own secure secret key. Never publish it.

### 6. Run the application

```bash
python -m uvicorn main:app --reload
```

## API Documentation

After starting the server, access:

- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

## Database

SQLite is used to persist employee and user records.

The application includes employee and user tables. Passwords are stored as hashes rather than plain-text values.

## Future Enhancements

- Automated testing using Pytest
- Frontend integration
- Docker deployment
- Cloud deployment
- Logging and monitoring