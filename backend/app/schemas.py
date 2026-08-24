from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field, EmailStr


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    user_id: str


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: str = Field(..., min_length=2)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: str
    email: str
    role: str
    full_name: Optional[str] = None


class DoctorCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: str
    specialization: str
    qualification: Optional[str] = None
    experience_years: int = 0
    slot_duration_minutes: int = 30
    profile_photo_url: Optional[str] = None
    bio: Optional[str] = None
    languages: Optional[str] = None
    consultation_fee: Optional[int] = 0
    clinic_name: Optional[str] = None
    status: Optional[str] = "available"


class DoctorWorkingHourItem(BaseModel):
    weekday: int
    start_time: str
    end_time: str


class DoctorLeaveInput(BaseModel):
    leave_date: date
    reason: Optional[str] = None


class SlotHoldRequest(BaseModel):
    doctor_id: str
    start_time: datetime


class AppointmentCreate(BaseModel):
    doctor_id: str
    start_time: datetime


class AppointmentOut(BaseModel):
    id: str
    patient_id: str
    doctor_id: str
    start_time: datetime
    end_time: datetime
    status: str


class AvailabilitySlot(BaseModel):
    start_time: datetime
    end_time: datetime


class SymptomCreate(BaseModel):
    chief_complaint: str
    symptoms: str
    duration: Optional[str] = None
    severity: Optional[str] = None
    additional_notes: Optional[str] = None


class PreVisitSummaryOut(BaseModel):
    urgency_level: Optional[str] = None
    chief_complaint: Optional[str] = None
    suggested_questions: Optional[List[str]] = None
    status: Optional[str] = None


class ClinicalNoteCreate(BaseModel):
    note_text: str
    diagnosis: Optional[str] = None


class PrescriptionMedicationInput(BaseModel):
    name: str
    dosage: str
    frequency: str
    duration: Optional[str] = None
    special_instructions: Optional[str] = None


class PrescriptionCreate(BaseModel):
    follow_up_instructions: Optional[str] = None
    medications: List[PrescriptionMedicationInput] = []


class PostVisitSummaryOut(BaseModel):
    summary: str
    medication_schedule: Optional[List[dict]] = None
    follow_up_steps: Optional[List[str]] = None


class DoctorProfileOut(BaseModel):
    id: str
    user_id: str
    name: str
    specialization: str
    qualification: Optional[str] = None
    experience_years: Optional[int] = 0
    slot_duration_minutes: int = 30
    is_active: bool = True


class WorkingHourCreate(BaseModel):
    weekday: int
    start_time: str
    end_time: str


class AppointmentSummaryResponse(BaseModel):
    urgency_level: Optional[str] = None
    chief_complaint: Optional[str] = None
    suggested_questions: Optional[List[str]] = None
    status: Optional[str] = None
    fallback: bool = False
