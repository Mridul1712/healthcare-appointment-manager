# Implementation plan

Current state: the workspace was empty at the start of this session. The project is being built from scratch in a single, incremental pass, with emphasis on the backend requirements prioritised by the user: database schema, authentication and RBAC, working hours/leave logic, slot generation, appointment booking, slot holds, and transactional concurrency protection.

## Architecture

- Backend: FastAPI + SQLAlchemy + PostgreSQL-compatible models with Alembic migrations.
- Auth: JWT access tokens, role-based authorization, secure password hashing.
- Domain logic: doctor availability, leave handling, slot holds, appointment bookings, and audit logging.
- Background jobs: Celery-ready notification and retry infrastructure, even if the full feature set is not yet expanded.
- Frontend: React + Vite skeleton with page structure, not a full production UI yet.

## Database model focus

- users
- patient_profiles
- doctor_profiles
- doctor_working_hours
- doctor_leave_days
- appointments
- appointment_slot_holds
- symptoms
- pre_visit_summaries
- notifications
- audit_logs

## Priority implementation sequence

1. Project infrastructure and dependency scaffolding
2. Database models and migration
3. Auth and role enforcement
4. Doctor schedules, leave periods, and slots
5. Booking + hold + double-booking safety
6. Automated tests for auth and concurrency
7. Documentation and deployment setup cleanup

## Current status

- Project structure created.
- Core backend service layer and SQLAlchemy schema are being implemented.
- Auth, availability, hold, and booking flow are the main functional focus.
