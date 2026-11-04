# ShopEase Authentication Microservice

Independent FastAPI authentication service for ShopEase. It provides user registration, secure password hashing, login, JWT access tokens, current-user lookup, token verification, and authenticated password changes. It uses its own MySQL 8 database and runs with Docker Compose.

## 1. Features

- User registration with email validation, password-strength checks, password confirmation, and duplicate-email prevention.
- Password hashes stored with bcrypt through Passlib. Plain-text passwords are never stored or returned.
- User login with generic invalid-credential responses and inactive-account protection.
- Signed JWT access tokens containing the user ID (`sub`) and role, with issuer and expiry validation.
- Reusable `get_current_user` dependency for protecting future microservice endpoints.
- Current-user, verify-token, and change-password endpoints.
- SQLAlchemy 2 ORM, Alembic migrations, MySQL 8, Docker Compose health checks, and a persistent named database volume.

## 2. Technology Stack

| Area | Technology |
|---|---|
| API | Python 3.11, FastAPI, Uvicorn |
| Validation | Pydantic v2, EmailStr |
| Database | MySQL 8.4, SQLAlchemy 2, PyMySQL |
| Migration | Alembic |
| Password security | Passlib + bcrypt |
| Token security | PyJWT (HS256) |
| Containerization | Docker, Docker Compose |
| API testing | Swagger UI, Postman |

## 3. Project Structure

```text
shopease-auth-service/
├── app/
│   ├── main.py
│   ├── routers/auth_routes.py
│   ├── models/user_model.py
│   ├── schemas/auth_schema.py
│   ├── services/auth_service.py
│   ├── core/security.py
│   ├── core/config.py
│   └── database/connection.py
├── alembic/
│   ├── env.py
│   └── versions/0001_create_users_table.py
├── postman/ShopEase_Auth_Service.postman_collection.json
├── tests/test_auth_api.py
├── scripts/create_expired_token.py
├── Dockerfile
├── docker-compose.yml
├── alembic.ini
├── requirements.txt
├── .env.example
├── .gitignore
├── .dockerignore
└── README.md
```

## 4. Environment Configuration

Do not commit `.env`. Create it from the example.

PowerShell:

```powershell
Copy-Item .env.example .env
```

Edit `.env` and replace `DB_PASSWORD`, `DB_ROOT_PASSWORD`, and `JWT_SECRET_KEY` with unique values. `JWT_SECRET_KEY` must contain at least 32 characters; use a cryptographically random secret in real environments.

Important example values:

```dotenv
APP_PORT=8002
DB_HOST=127.0.0.1
DB_PORT=3308
DB_NAME=shopease_auth_db
DB_USER=shopease_auth_user
DB_PASSWORD=replace-with-a-strong-db-password
DB_ROOT_PASSWORD=replace-with-a-different-root-password
JWT_SECRET_KEY=replace-with-a-random-secret-of-at-least-32-characters
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_ISSUER=shopease-auth-service
```

The host-side MySQL port is `3308` to avoid clashing with other local MySQL containers. Inside Docker Compose, the API connects to MySQL through service DNS name `auth-db` on port `3306`; it does not use `localhost`.

## 5. Run with Docker Compose (Recommended)

Prerequisites: Docker Desktop running and a `.env` file created as described above.

From the project root:

```powershell
docker compose up --build -d
```

Compose starts:

- `shopease-auth-mysql` – MySQL 8.4 database.
- `shopease-auth-container` – FastAPI authentication service.

The API container waits for the database health check, runs `alembic upgrade head`, and then starts Uvicorn.

Check services and logs:

```powershell
docker compose ps
docker compose logs auth-db
docker compose logs auth-api
```

Open Swagger UI:

- `http://localhost:8002/docs`
- Health endpoint: `http://localhost:8002/health`

Stop the services (the named database volume remains):

```powershell
docker compose down
```

Stop and remove the database volume too (this deletes stored user data):

```powershell
docker compose down -v
```

## 6. Local Development Without the API Container

You can run the MySQL service in Docker and run FastAPI from your Python environment. The `.env` defaults use `127.0.0.1:3308` for the host connection.

```powershell
py -3.11 -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt

docker compose up -d auth-db
alembic upgrade head
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8002
```

Swagger: `http://127.0.0.1:8002/docs`.

## 7. Database and Alembic

Database name: `shopease_auth_db`.

The `users` table contains:

| Column | Type | Notes |
|---|---|---|
| id | Integer | Primary key |
| full_name | String(150) | Required |
| email | String(255) | Unique, indexed, normalized to lowercase |
| password_hash | String(255) | bcrypt hash only |
| role | String(50) | Defaults to `customer` |
| is_active | Boolean | Defaults to true |
| created_at | DateTime | Database-generated timestamp |
| updated_at | DateTime | Updated on ORM update |

Migration commands:

```powershell
alembic current
alembic history
alembic upgrade head
alembic downgrade -1
```

The Compose startup command automatically applies migrations before starting the API. Do not use `Base.metadata.create_all()` as a substitute for Alembic in this service.

## 8. API Endpoints

Base URL: `http://localhost:8002`

| Method | Endpoint | Authentication | Success |
|---|---|---|---|
| POST | `/api/auth/register` | No | 201 Created |
| POST | `/api/auth/login` | No | 200 OK |
| GET | `/api/auth/me` | Bearer token | 200 OK |
| POST | `/api/auth/verify-token` | Bearer token | 200 OK |
| POST | `/api/auth/change-password` | Bearer token | 200 OK |
| GET | `/health` | No | 200 OK |

### Registration example

```json
{
  "full_name": "Sai User",
  "email": "sai@example.com",
  "password": "StrongPass123!",
  "confirm_password": "StrongPass123!"
}
```

Password policy: minimum 8 characters, at least one uppercase letter, one lowercase letter, one digit, one special character, and no more than 72 UTF-8 bytes (bcrypt input limit). New accounts receive the `customer` role and are active by default.

### Login example

```json
{
  "email": "sai@example.com",
  "password": "StrongPass123!"
}
```

The response contains `access_token`, `token_type`, `expires_in`, and a public user object. Password and password hash are never returned.

### Protected API usage

Send this HTTP header:

```http
Authorization: Bearer <access_token>
```

`GET /api/auth/me`, `POST /api/auth/verify-token`, and `POST /api/auth/change-password` use the reusable `get_current_user` dependency.

### Change password example

```json
{
  "current_password": "StrongPass123!",
  "new_password": "NewStrongPass456!",
  "confirm_new_password": "NewStrongPass456!"
}
```

After changing the password, use the new password for subsequent logins. Already-issued access tokens remain valid until they expire; the configured expiration is controlled by `ACCESS_TOKEN_EXPIRE_MINUTES` (default 30 minutes).

## 9. Expected Error Responses

| Scenario | HTTP status |
|---|---:|
| Invalid request body / invalid email / password mismatch | 422 |
| Duplicate email | 409 Conflict |
| Wrong email or password | 401 Unauthorized |
| Missing, malformed, invalid, or expired bearer token | 401 Unauthorized |
| Inactive account login or protected access | 403 Forbidden |
| Incorrect current password during password change | 400 Bad Request |

Login deliberately returns the same message for an unknown email and incorrect password to avoid exposing account existence.

## 10. Postman Testing

Import `postman/ShopEase_Auth_Service.postman_collection.json` into Postman. Set collection variables:

- `base_url` = `http://localhost:8002`
- `access_token` = token returned by login (the Login request also saves it automatically)

Suggested test order:

1. Register a user.
2. Register the same email again (expect 409).
3. Try malformed email and mismatched passwords (expect 422).
4. Login with correct credentials (expect 200 and a JWT).
5. Login with a wrong password (expect 401).
6. Call `/me` and `/verify-token` with the saved bearer token.
7. Call `/me` without a token and with an invalid token (expect 401).
8. Change password with the correct current password.
9. Login using the new password.
10. Test expired tokens using a token whose `exp` claim is in the past.
11. Test inactive-account behavior by setting a test user's `is_active` to false in MySQL, then attempting login (expect 403).

A user can be marked inactive for testing with a SQL client connected to the authentication database:

```sql
UPDATE users SET is_active = 0 WHERE email = 'sai@example.com';
```

## 11. Automated Tests

The included tests use an in-memory SQLite database so that API behavior can be checked without a running MySQL service. The actual application and Docker Compose configuration use MySQL.

```powershell
pip install -r requirements.txt
pytest -v
```

## 12. Security Notes

- Use a unique, random JWT secret per environment; never commit `.env`.
- Use strong, unique database passwords; do not use the example values in a deployed environment.
- Passwords are hashed with bcrypt and are never included in response schemas.
- JWTs are signed, expire, and are checked for signature, issuer, algorithm, and required claims.
- The service runs as a non-root user in its application container.
- Compose stores MySQL data in the named `auth_mysql_data` volume.
- This service is independent. Do not combine it with Product Service code; other microservices can validate its bearer tokens using the shared verification rules and secret-management strategy.

## 13. GitHub Submission

The `.gitignore` excludes `.env`, virtual environments, Python caches, and test caches. Commit `.env.example`, not `.env`.

```powershell
git init
git branch -M main
git add app alembic tests scripts postman Dockerfile docker-compose.yml alembic.ini requirements.txt README.md .env.example .gitignore .dockerignore
git status
git commit -m "Build ShopEase JWT Authentication Microservice"
git remote add origin https://github.com/<YOUR-USERNAME>/shopease-auth-service.git
git push -u origin main
```

Before pushing, confirm that `.env` and all real secrets are absent from `git status`.
