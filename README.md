# Healthcare Appointment & Follow-up Manager

A practical healthcare management MVP built with FastAPI, SQLAlchemy, PostgreSQL-ready models, JWT auth, and a React frontend. It covers patient, doctor, and admin flows for booking, scheduling, doctor management, symptom intake, AI-generated summaries, notifications, and calendar-ready appointment handling.

## Features

- Patient, doctor, and admin authentication with JWT and RBAC
- Doctor directory and specialization filtering
- Appointment booking with slot hold and conflict prevention logic
- Doctor working hours, leaves, and availability generation
- Symptom intake and AI-style pre-visit summary generation
- Post-visit summary and clinical note workflow
- Admin management for doctor profiles and leave records
- Notification and email service integration hooks
- Google Calendar integration hooks for appointment events
- SQLite-based local testing and PostgreSQL-ready schema

## Tech stack

- Backend: FastAPI, SQLAlchemy, PostgreSQL-compatible models, Alembic
- Auth: JWT, bcrypt/passlib
- Frontend: React + Vite
- Testing: pytest

## Project structure

- backend/ — FastAPI application
- backend/app/ — config, database, models, services, routers
- backend/alembic/ — migration files
- backend/tests/ — backend test suite
- frontend/ — React app
- .env.example — sample environment configuration

## Local setup

1. Create and activate a Python 3.13 virtual environment.
2. Install backend dependencies:

   cd backend
   python -m pip install -r requirements.txt

3. Create a local environment file from .env.example and adjust values as needed.
4. Start the backend:

   cd backend
   python -m uvicorn app.main:app --host 0.0.0.0 --port 8001

5. In a separate terminal, install and start the frontend:

   cd frontend
   npm install
   npm run dev -- --host 0.0.0.0 --port 5173

6. Open the app in a browser:
   - Frontend: http://localhost:5173
   - Backend: http://localhost:8001

## Demo accounts

- Admin: admin@example.com / Admin123!
- Doctor: doctor@example.com / Doctor123!
- Patient: patient@example.com / Patient123!

## Environment variables

Copy .env.example to a local .env file and set the values you need. The project supports:

- Database URL
- JWT settings
- Redis URL
- OpenAI-compatible LLM API key and base URL
- SMTP or SendGrid settings
- Google OAuth credentials
- Frontend/backend URLs

When credentials are missing, the app uses graceful fallback behavior instead of failing hard.

## Validation

Run the backend tests:

cd backend
python -m pytest -q tests

The project is currently validated against the backend test suite and the frontend build succeeded in the local environment.

## Notes

This is an MVP designed for local development and practical demo scenarios. It is PostgreSQL-ready and production-structured enough to extend, but real cloud integrations such as Google Calendar and email delivery require actual credentials in the environment.
