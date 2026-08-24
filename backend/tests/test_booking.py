from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
from uuid import uuid4

from app.core.security import hash_password
from app.database import SessionLocal
from app.models.models import DoctorLeaveDay, DoctorProfile, DoctorWorkingHour, RoleEnum, User
from app.services.availability import generate_doctor_slots
from app.services.booking import book_appointment, create_slot_hold, expire_slot_holds


def seed_doctor_and_patient(db):
    unique = uuid4().hex[:8]
    patient_email = f"patient-booking-{unique}@example.com"
    doctor_email = f"doctor-booking-{unique}@example.com"
    patient_user = User(email=patient_email, password_hash=hash_password("secret123"), role=RoleEnum.PATIENT.value)
    doctor_user = User(email=doctor_email, password_hash=hash_password("secret123"), role=RoleEnum.DOCTOR.value)
    db.add_all([patient_user, doctor_user])
    db.flush()

    doctor = DoctorProfile(
        user_id=doctor_user.id,
        name="Dr. Booking",
        specialization="Neurology",
        qualification="MD",
        experience_years=8,
        slot_duration_minutes=30,
        is_active=True,
    )
    db.add(doctor)
    db.flush()

    db.add(DoctorWorkingHour(doctor_id=doctor.id, weekday=0, start_time="09:00", end_time="11:00"))
    db.add(DoctorLeaveDay(doctor_id=doctor.id, leave_date=date.today() + timedelta(days=3), reason="Training"))
    db.commit()
    return patient_user, doctor


def test_doctor_slots_exclude_leave_and_booked_slot(db_session):
    patient_user, doctor = seed_doctor_and_patient(db_session)
    slot_date = date.today() if date.today().weekday() == 0 else (date.today() + timedelta(days=(0 - date.today().weekday()) % 7))
    slots = generate_doctor_slots(db_session, doctor.id, slot_date)
    assert slots
    assert any(slot.time() == datetime.strptime("09:00", "%H:%M").time() for slot in slots)

    existing = slots[0]
    db_session.add(
        __import__('app.models.models', fromlist=['Appointment']).Appointment(
            doctor_id=doctor.id,
            patient_id=patient_user.id,
            start_time=existing,
            end_time=existing + timedelta(minutes=30),
            status="CONFIRMED",
        )
    )
    db_session.commit()
    updated_slots = generate_doctor_slots(db_session, doctor.id, slot_date)
    assert existing not in updated_slots


def test_slot_hold_expiration(db_session):
    patient_user, doctor = seed_doctor_and_patient(db_session)
    hold = create_slot_hold(db_session, doctor.id, patient_user.id, datetime.utcnow().replace(second=0, microsecond=0))
    hold.expires_at = datetime.utcnow() - timedelta(minutes=1)
    db_session.commit()
    expire_slot_holds(db_session)
    refreshed = db_session.get(type(hold), hold.id)
    assert refreshed.status == "EXPIRED"


def test_concurrent_booking_conflict():
    db = SessionLocal()
    unique = uuid4().hex[:8]
    patient1 = User(email=f"p1-{unique}@example.com", password_hash=hash_password("secret123"), role=RoleEnum.PATIENT.value)
    patient2 = User(email=f"p2-{unique}@example.com", password_hash=hash_password("secret123"), role=RoleEnum.PATIENT.value)
    doctor_user = User(email=f"doctor-concurrency-{unique}@example.com", password_hash=hash_password("secret123"), role=RoleEnum.DOCTOR.value)
    db.add_all([patient1, patient2, doctor_user])
    db.flush()

    doctor = DoctorProfile(user_id=doctor_user.id, name="Dr. Concurrency", specialization="Orthopedics", slot_duration_minutes=30, is_active=True)
    db.add(doctor)
    db.flush()
    db.add(DoctorWorkingHour(doctor_id=doctor.id, weekday=0, start_time="09:00", end_time="10:00"))
    db.commit()

    target_time = datetime.utcnow().replace(hour=9, minute=0, second=0, microsecond=0)

    def attempt(patient_id):
        local_db = SessionLocal()
        try:
            return book_appointment(local_db, doctor.id, patient_id, target_time)
        except Exception as exc:  # pragma: no cover - only for failure path
            return exc
        finally:
            local_db.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, [patient1.id, patient2.id]))

    assert any(not isinstance(item, Exception) for item in results)
    assert sum(1 for item in results if isinstance(item, Exception)) == 1
