import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship

from app.database import Base


class RoleEnum(str, enum.Enum):
    PATIENT = "patient"
    DOCTOR = "doctor"
    ADMIN = "admin"


class AppointmentStatus(str, enum.Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    RESCHEDULED = "RESCHEDULED"
    DOCTOR_LEAVE = "DOCTOR_LEAVE"


class SlotHoldStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    USED = "USED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class NotificationStatus(str, enum.Enum):
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default=RoleEnum.PATIENT.value)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    patient_profile = relationship("PatientProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    doctor_profile = relationship("DoctorProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="recipient", foreign_keys='Notification.recipient_user_id')
    audit_logs = relationship("AuditLog", back_populates="user")


class PatientProfile(Base):
    __tablename__ = "patient_profiles"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), unique=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=True)
    date_of_birth = Column(Date, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", back_populates="patient_profile")


class DoctorProfile(Base):
    __tablename__ = "doctor_profiles"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    specialization = Column(String(255), nullable=False)
    qualification = Column(String(255), nullable=True)
    experience_years = Column(Integer, nullable=True, default=0)
    slot_duration_minutes = Column(Integer, nullable=False, default=30)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", back_populates="doctor_profile")
    working_hours = relationship("DoctorWorkingHour", back_populates="doctor", cascade="all, delete-orphan")
    leave_days = relationship("DoctorLeaveDay", back_populates="doctor", cascade="all, delete-orphan")
    appointments = relationship("Appointment", back_populates="doctor", foreign_keys='Appointment.doctor_id', cascade="all, delete-orphan")
    slot_holds = relationship("AppointmentSlotHold", back_populates="doctor", cascade="all, delete-orphan")


class DoctorWorkingHour(Base):
    __tablename__ = "doctor_working_hours"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    doctor_id = Column(String, ForeignKey("doctor_profiles.id"), nullable=False)
    weekday = Column(Integer, nullable=False)
    start_time = Column(String(10), nullable=False)
    end_time = Column(String(10), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    doctor = relationship("DoctorProfile", back_populates="working_hours")

    __table_args__ = (
        UniqueConstraint("doctor_id", "weekday", "start_time", "end_time", name="uq_doctor_working_hour"),
    )


class DoctorLeaveDay(Base):
    __tablename__ = "doctor_leave_days"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    doctor_id = Column(String, ForeignKey("doctor_profiles.id"), nullable=False)
    leave_date = Column(Date, nullable=False)
    reason = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    doctor = relationship("DoctorProfile", back_populates="leave_days")

    __table_args__ = (
        UniqueConstraint("doctor_id", "leave_date", name="uq_doctor_leave_day"),
    )


class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    doctor_id = Column(String, ForeignKey("doctor_profiles.id"), nullable=False)
    patient_id = Column(String, ForeignKey("users.id"), nullable=False)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(50), default=AppointmentStatus.CONFIRMED.value, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    doctor = relationship("DoctorProfile", back_populates="appointments", foreign_keys=[doctor_id])
    patient = relationship("User", foreign_keys=[patient_id])
    symptoms = relationship("Symptom", back_populates="appointment", cascade="all, delete-orphan")
    pre_visit_summary = relationship("PreVisitSummary", back_populates="appointment", uselist=False, cascade="all, delete-orphan")
    clinical_notes = relationship("ClinicalNote", back_populates="appointment", cascade="all, delete-orphan")
    prescriptions = relationship("Prescription", back_populates="appointment", cascade="all, delete-orphan")
    post_visit_summary = relationship("PostVisitSummary", back_populates="appointment", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("doctor_id", "start_time", name="uq_appointment_doctor_start_time"),
    )


class AppointmentSlotHold(Base):
    __tablename__ = "appointment_slot_holds"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    doctor_id = Column(String, ForeignKey("doctor_profiles.id"), nullable=False)
    patient_id = Column(String, ForeignKey("users.id"), nullable=False)
    start_time = Column(DateTime(timezone=True), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(20), default=SlotHoldStatus.ACTIVE.value, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    doctor = relationship("DoctorProfile", back_populates="slot_holds")
    patient = relationship("User", foreign_keys=[patient_id])

    __table_args__ = (
        UniqueConstraint("doctor_id", "start_time", "status", name="uq_slot_hold_active_slot"),
    )


class Symptom(Base):
    __tablename__ = "symptoms"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    appointment_id = Column(String, ForeignKey("appointments.id"), nullable=False)
    chief_complaint = Column(Text, nullable=False)
    symptoms = Column(Text, nullable=False)
    duration = Column(String(100), nullable=True)
    severity = Column(String(50), nullable=True)
    additional_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    appointment = relationship("Appointment", back_populates="symptoms")


class PreVisitSummary(Base):
    __tablename__ = "pre_visit_summaries"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    appointment_id = Column(String, ForeignKey("appointments.id"), unique=True, nullable=False)
    urgency_level = Column(String(50), nullable=True)
    chief_complaint = Column(Text, nullable=True)
    suggested_questions = Column(JSON, nullable=True)
    provider_response = Column(JSON, nullable=True)
    status = Column(String(30), default="PENDING", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    appointment = relationship("Appointment", back_populates="pre_visit_summary")


class ClinicalNote(Base):
    __tablename__ = "clinical_notes"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    appointment_id = Column(String, ForeignKey("appointments.id"), nullable=False)
    note_text = Column(Text, nullable=False)
    diagnosis = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    appointment = relationship("Appointment", back_populates="clinical_notes")


class Prescription(Base):
    __tablename__ = "prescriptions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    appointment_id = Column(String, ForeignKey("appointments.id"), nullable=False)
    doctor_id = Column(String, ForeignKey("doctor_profiles.id"), nullable=False)
    follow_up_instructions = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    appointment = relationship("Appointment", back_populates="prescriptions")
    medications = relationship("PrescriptionMedication", back_populates="prescription", cascade="all, delete-orphan")


class PrescriptionMedication(Base):
    __tablename__ = "prescription_medications"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    prescription_id = Column(String, ForeignKey("prescriptions.id"), nullable=False)
    name = Column(String(255), nullable=False)
    dosage = Column(String(100), nullable=False)
    frequency = Column(String(100), nullable=False)
    duration = Column(String(100), nullable=True)
    special_instructions = Column(Text, nullable=True)

    prescription = relationship("Prescription", back_populates="medications")


class PostVisitSummary(Base):
    __tablename__ = "post_visit_summaries"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    appointment_id = Column(String, ForeignKey("appointments.id"), unique=True, nullable=False)
    summary = Column(Text, nullable=False)
    medication_schedule = Column(JSON, nullable=True)
    follow_up_steps = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    appointment = relationship("Appointment", back_populates="post_visit_summary")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    recipient_user_id = Column(String, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    channel = Column(String(50), default="email", nullable=False)
    status = Column(String(20), default=NotificationStatus.PENDING.value, nullable=False)
    retry_count = Column(Integer, default=0, nullable=False)
    next_retry_at = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    recipient = relationship("User", back_populates="notifications", foreign_keys=[recipient_user_id])
    attempts = relationship("NotificationAttempt", back_populates="notification", cascade="all, delete-orphan")


class NotificationAttempt(Base):
    __tablename__ = "notification_attempts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    notification_id = Column(String, ForeignKey("notifications.id"), nullable=False)
    attempt_number = Column(Integer, nullable=False)
    status = Column(String(20), default=NotificationStatus.PENDING.value, nullable=False)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    notification = relationship("Notification", back_populates="attempts")


class CalendarConnection(Base):
    __tablename__ = "calendar_connections"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), unique=True, nullable=False)
    google_email = Column(String(255), nullable=True)
    access_token = Column(Text, nullable=True)
    refresh_token = Column(Text, nullable=True)
    scope = Column(String(255), nullable=True)
    connected_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    action = Column(String(255), nullable=False)
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="audit_logs")
